#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time

from forseti.base import (
    CloudWatch,
    EC2,
    EC2AutoScale,
    ELB,
)
from forseti.utils import Balloon
from forseti.exceptions import EC2InstanceException
from boto.ec2.autoscale import (
    AutoScalingGroup,
    LaunchConfiguration,
    ScalingPolicy,
    Tag,
)
from boto.ec2.cloudwatch import MetricAlarm

import paramiko


class EC2Instance(EC2):
    """
    EC2 Instance
    """

    def __init__(self, configuration, application):
        super(EC2Instance, self).__init__(configuration, application)
        self.instance = None

    def launch(self):
        """
        Start EC2 instance in AWS
        """
        print "Starting instance"
        self.resource = self.ec2.run_instances(**self.configuration)
        self.instance = self.resource.instances[0]

    def terminate(self):
        """
        Stop EC2 instance in AWS
        """
        print "Terminating instance %s" % self.instance.id
        self.ec2.terminate_instances([self.instance.id])


class GoldenEC2Instance(EC2Instance):
    """
    A golden instance is the one which is used as a base to create the
    application AMI.
    """
    TIMEOUT = 2

    def __init__(self, configuration, application):
        """
        :param configuration: Parameters to ``boto.ec2.connection.run_instances``.
        :param application: Application name.
        """
        # SSH provisioning
        self.provision_configuration = configuration.pop('provision')
        self.ssh_configuration = {
            'username': self.provision_configuration['username'],
            'key_filename': self.provision_configuration['key_filename'],
            'timeout': self.TIMEOUT,
        }
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        super(GoldenEC2Instance, self).__init__(configuration, application)
        # No need to monitor an instance that will be terminated soon
        self.configuration["monitoring_enabled"] = False

    def launch_and_wait(self):
        """
        Launch a golden instance and wait until it's running.
        """
        self.launch()
        balloon = Balloon("Golden instance %s launched. Waiting until it's running" % self.instance.id)

        i = 0
        while self.instance.update() == "pending":
            balloon.update(i)
            i += 1
            time.sleep(1)

        balloon.finish()

        if self.instance.update() == "running":
            tag_name = "golden-%s-instance-%s" % (self.application, self.version)
            self.instance.add_tag("Name", tag_name)
        else:
            raise EC2InstanceException("Golden instance %s could not be launched" % self.instance.id)

    def is_ssh_running(self):
        """
        Check if SSH is running and working
        """
        try:
            self.ssh.connect(self.instance.public_dns_name, **self.ssh_configuration)
            self.ssh.exec_command('ls')
        except:
            return False
        return True

    def wait_for_ssh(self):
        """
        Wait until SSH is running
        """
        balloon = Balloon("Golden instance %s provisioned. Waiting until SSH is up" % self.instance.id)

        i = 0
        while not self.is_ssh_running():
            balloon.update(i)
            i += 1
            time.sleep(1)

        balloon.finish()

    def provision(self):
        """
        Provisions machine using `command` specified in configuration file, `command` is
        executed locally within `working_directory` specified path.
        """
        self.wait_for_ssh()
        balloon = Balloon("Deployed new code on golden instance %s" % self.instance.id)
        command = self.provision_configuration['command'].format(
            dns_name=self.instance.public_dns_name
        )
        former_directory = os.getcwd()
        os.chdir(self.provision_configuration['working_directory'])
        os.system(command)
        os.chdir(former_directory)
        balloon.finish()

    def create_image(self):
        """
        Create an AMI from the golden instance started
        """
        balloon = Balloon("Golden instance %s creating image" % self.instance.id)

        ami_name = "golden-%s-ami-%s" % (self.application, self.version)
        ami_id = self.instance.create_image(ami_name, description=ami_name)
        ami = self.ec2.get_all_images(image_ids=(ami_id,))[0]

        i = 0
        while ami.update() == "pending":
            balloon.update(i)
            i += 1
            time.sleep(1)

        balloon.finish()

        if ami.update() == "available":
            ami.add_tag("Name", ami_name)
        else:
            raise EC2InstanceException("Golden image %s could not be created" % self.instance.id)

        return ami_id


class EC2AutoScaleConfig(EC2AutoScale):
    """
    EC2 autoscale config
    """

    def create(self):
        """
        Creates a launch configuration using configuration file
        """
        launch_configuration = LaunchConfiguration(name=self.name, **self.configuration)
        self.resource = self.autoscale.create_launch_configuration(launch_configuration)


class EC2AutoScaleGroup(EC2AutoScale):
    """
    EC2 autoscale group
    """

    def __init__(self, name, configuration, application):
        super(EC2AutoScaleGroup, self).__init__(name, configuration, application)
        self.group = None
        self.elb = None
        self.name = name  # Do not add version to the name

    def set_launch_configuration(self, launch_configuration):
        """
        Sets launch configuration for autoscale group, if group is attached
        to an existing AWS autoscale group, update its configuration
        """
        self.configuration["launch_config"] = launch_configuration.name

        if self.group:
            self.group.launch_config_name = self.configuration["launch_config"]
            self.group.update()

    def _get_autoscaling_group(self):
        """
        Returns a current `boto.ec2.autoscale.group.AutoScalingGroup` instance associated to
        the instance of this class
        """
        return self.autoscale.get_all_groups(names=[self.name])[0]

    def load_balancer(self):
        """
        Returns an `ELBBalancer` instance associated to the autoscale group
        """
        if self.elb is not None:
            return self.elb
        self.elb = ELBBalancer(self.__get_resource().load_balancers[0], self.application)
        return self.elb

    def get_instances_with_status(self, status):
        """
        Get a list of instances in this autoscale group whose status matches `status`
        """
        instances_ids = [instance.instance_id for instance in self._get_autoscaling_group()]

        if not instances_ids:
            return []

        instances = []
        instances_states = self.ec2.get_all_instance_status(instances_ids)
        for state in instances_states:
            if state.state_name == status:
                instances.append(state.id)
        return instances

    def increase_desired_capacity(self):
        """
        Increases the autoscale group desired capacity and max_size, this implies launching
        new EC2 instances

        Current policy: "Las gallinas que entran por las que salen"
        """
        balloon = Balloon("Increasing desired capacity to provision new machines")

        current_instances = self.get_instances_with_status('running')
        self.old_instances = current_instances
        self.group.desired_capacity = len(current_instances) * 2
        self.group.max_size = self.group.max_size * 2
        self.group.update()

        for i in range(1, 15):
            balloon.update(i)
            time.sleep(1)

        balloon.finish()

    def wait_for_new_instances_ready(self):
        """
        Wait for instances launched by autoscale group to be up, running and in the balancer
        """
        balloon = Balloon("Waiting for new instances until they're up and running")
        i = 0
        while len(self.get_instances_with_status('running')) != self.group.desired_capacity:
            balloon.update(i)
            i += 1
            time.sleep(1)

        balloon.finish()

        # TODO: Query AWS for instances
        instances = self.get_instances_with_status('running')
        new_instances = set(instances) - set(self.old_instances)

        # Ask the balancer to wait
        self.load_balancer().wait_for_instances_with_health(self, new_instances)

    def terminate_older_instances(self):
        """
        Terminate instances that we no longer want in the autoscale group, the old ones
        """
        balloon = Balloon("Changing termination policy to terminate older instances")
        self.group.termination_policies = ["OldestLaunchConfiguration"]
        self.group.desired_capacity = self.configuration['desired_capacity']
        self.group.update()

        i = 0
        while len(self.get_instances_with_status('running')) != self.group.desired_capacity:
            balloon.update(i)
            i += 1
            time.sleep(1)
        balloon.finish()

        self.group.termination_policies = self.configuration['termination_policies']
        self.group.max_size = self.configuration['max_size']
        self.group.update()

    def apply_launch_configuration_for_deployment(self):
        """
        Applies changes to current autoscale group launch configuration for creating new instances:

        * First, increases desired capacity, therefore autoscale group grows with the new launch
        configuration
        * Then, we wait for the new instances being booted to be ready and in the balancer
        * Finally, we terminate older instances by restoring initial capacity in autoscale group
        """
        self.increase_desired_capacity()
        self.wait_for_new_instances_ready()
        self.terminate_older_instances()

    def create(self):
        """
        Creates autoscaling group and sets a `propagate_at_launch` tag for future instances
        the autoscale group boots
        """
        autoscaling_group = AutoScalingGroup(group_name=self.name, **self.configuration)
        self.resource = self.autoscale.create_auto_scaling_group(autoscaling_group)
        self.group = self._get_autoscaling_group()
        tag = Tag(
            key='Name',
            value=self.application,
            propagate_at_launch=True,
            resource_id=self.name
        )
        self.autoscale.create_or_update_tags([tag])


class EC2AutoScalePolicy(EC2AutoScale):
    """
    EC2 autoscale policy
    """

    def __init__(self, name, configuration, application, group):
        """
        :param name: Autoscale policy name
        :param configuration: Dictionary containing configuration
        :param application: Application name
        :param group: `EC2AutoScaleGroup` instance to which the policy will be applied
        """
        super(EC2AutoScalePolicy, self).__init__(name, configuration, application)
        self.group = group
        self.name = name
        self.configuration["as_name"] = group.name

    def update_or_create(self):
        """
        Creates the scalinig policy in AWS and stores in `self.reource` a `boto.ec2.autoscale.policy.ScalingPolicy`
        """
        policy = ScalingPolicy(name=self.name, **self.configuration)
        self.autoscale.create_scaling_policy(policy)
        # Refresh policy from EC2 to get ARN
        self.resource = self.autoscale.get_all_policies(as_group=self.group.name, policy_names=[self.name])[0]

    def get_policy_arn(self):
        return self.resource.policy_arn

    def get_group_name(self):
        return self.group.name


class CloudWatchMetricAlarm(CloudWatch):
    """
    Cloudwatch metric alarm
    """

    def __init__(self, name, configuration, application, policy):
        super(CloudWatchMetricAlarm, self).__init__(configuration, application)
        self.name = name
        self.policy = policy
        self.configuration["alarm_actions"] = [policy.get_policy_arn()]
        self.configuration["dimensions"] = {"AutoScalingGroupName": policy.get_group_name()}

    def update_or_create(self):
        alarm = MetricAlarm(name=self.name, **self.configuration)
        self.resource = self.cloudwatch.create_alarm(alarm)


class ELBBalancer(ELB):
    """
    ELB balancer
    """

    def __init__(self, name, application, configuration=None):
        super(ELBBalancer, self).__init__(name, configuration or {}, application)
        self.balancer = self.elb.get_all_load_balancers(load_balancer_names=[self.name])[0]

    def filter_instances_with_health(self, instance_ids, health='InService'):
        """
        Get number of instances running
        """
        instances = []
        for instance in instance_ids:
            try:
                instance_health = self.balancer.get_instance_health([instance])[0]
            except:
                continue
            if instance_health.state == health:
                instances.append(instance)
        return instances

    def wait_for_instances_with_health(self, instances_ids, health='InService'):
        balloon = Balloon("Waiting for instances until they're in the balancer %s with status %s" % (
            self.balancer.name,
            health
        ))

        i = 0
        while len(self.filter_instances_with_health(instances_ids, health=health)) != len(instances_ids):
            balloon.update(i)
            i += 1
            time.sleep(1)

        balloon.finish()
