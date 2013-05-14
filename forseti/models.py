#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
from datetime import datetime
import time
from boto.ec2.connection import EC2Connection
from boto.ec2.autoscale import AutoScaleConnection, AutoScalingGroup, LaunchConfiguration, ScalingPolicy, Tag
from boto.ec2.cloudwatch import CloudWatchConnection, MetricAlarm
from boto.ec2.elb import ELBConnection
import paramiko
# import fish  # We will use fish soon ;)
import progressbar


# class Duck(fish.SwimFishTimeSync, fish.DuckLook):
#     pass


class Balloon(progressbar.ProgressBar):
    def __init__(self, message="Waiting"):
        widgets = [message+" ", progressbar.AnimatedMarker(markers='.oO@* '),
                   progressbar.Timer(format=" %s")]
        super(Balloon, self).__init__(widgets=widgets)
        self.start()

    # def finish(self, time_message="Time"):
    #     super(Balloon, self).finish()
    #     minutes, seconds = divmod(int(self.seconds_elapsed), 60)
    #     print "%s: %02d:%02d" % (time_message, minutes, seconds)


class EC2(object):
    """
    EC2 bae class
    """

    def __init__(self, configuration, application):
        self.ec2 = EC2Connection()
        self.configuration = configuration
        self.application = application
        self.resource = None
        self.version = datetime.today().strftime("%Y-%m-%d-%s")


class EC2Autoscale(EC2):
    """
    EC2 autoscale base class
    """

    def __init__(self, name, configuration, application):
        super(EC2Autoscale, self).__init__(configuration, application)
        self.autoscale = AutoScaleConnection()
        self.name = name+"-"+self.version


class ELB(EC2):
    """
    ELB base class
    """

    def __init__(self, name, configuration, application):
        super(ELB, self).__init__(configuration, application)
        self.elb = ELBConnection()
        self.name = name


class CloudWatch(EC2):
    """
    CloudWatch base class
    """

    def __init__(self, configuration, application):
        super(CloudWatch, self).__init__(configuration, application)
        self.cloudwatch = CloudWatchConnection()


class EC2Instance(EC2):
    """docstring for Instance"""
    def __init__(self, configuration, application):
        super(EC2Instance, self).__init__(configuration, application)
        self.instance = None

    def launch(self):
        self.resource = self.ec2.run_instances(**self.configuration)
        self.instance = self.resource.instances[0]

    def terminate(self):
        print "Terminating instance %s" % (self.instance.id)
        self.ec2.terminate_instances([self.instance.id])


class GoldEC2Instance(EC2Instance):
    """
    A gold instance is the one which is used as a base to create the
    application AMI.

    :param configuration: Parameters to ``boto.ec2.connection.run_instances``.
    :param application: Application name.
    """

    def __init__(self, configuration, application):
        self.provision_configuration = configuration.pop('provision')
        self.ssh_configuration = {
            'username': self.provision_configuration['username'],
            'key_filename': self.provision_configuration['key_filename'],
            'timeout': 2,
        }
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        super(GoldEC2Instance, self).__init__(configuration, application)

        self.configuration["monitoring_enabled"] = False

    def launch_and_wait(self):
        """
        Launch a gold instance and wait until it's running.
        """
        self.launch()

        status = self.instance.update()
        balloon = Balloon("Gold instance %s launched. Waiting until it's running" % (self.instance.id))
        i = 0
        while status == "pending":
            balloon.update(i)
            i += 1
            time.sleep(1)
            status = self.instance.update()
        balloon.finish()

        if status == "running":
            name = "gold-%s-instance-%s" % (self.application, self.version)
            self.instance.add_tag("Name", name)
        else:
            # FIXME: Raise exception
            print "Gold instance %s could not be launched" % (self.instance.id)
            return

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
        balloon = Balloon("Gold instance %s provisioned. Waiting until SSH is up" % (self.instance.id))
        i = 0
        status = self.is_ssh_running()
        while status is False:
            balloon.update(i)
            i += 1
            time.sleep(1)
            status = self.is_ssh_running()
        balloon.finish()

    def provision(self):
        """
        Provision the new application code
        """
        self.wait_for_ssh()
        balloon = Balloon("Deployed new code on gold instance %s" % (self.instance.id))
        command = self.provision_configuration['command'].format(dns_name=self.instance.public_dns_name)
        directory = os.getcwd()
        os.chdir(self.provision_configuration['working_directory'])
        os.system(command)
        os.chdir(directory)
        balloon.finish()

    def create_image(self):
        """
        Create an image from the instance.
        """
        balloon = Balloon("Gold instance %s creating image" % (self.instance.id))

        name = "golden-%s-ami-%s" % (self.application, self.version)
        ami_id = self.instance.create_image(name, name)

        ami = self.ec2.get_all_images(image_ids=[ami_id])[0]
        status = ami.update()
        i = 0
        while status == "pending":
            balloon.update(i)
            i += 1
            time.sleep(1)
            status = ami.update()
        balloon.finish()

        if status == "available":
            ami.add_tag("Name", name)
        else:
            # FIXME: Raise exception
            print "Golden image %s could not be created" % (self.instance.id)
            return None

        return ami_id


class EC2AutoscaleConfig(EC2Autoscale):
    """
    EC2 autoscale config
    """

    def create(self):
        launch_configuration = LaunchConfiguration(name=self.name, **self.configuration)
        self.resource = self.autoscale.create_launch_configuration(launch_configuration)


class EC2AutoscaleGroup(EC2Autoscale):
    """
    EC2 autoscale group
    """

    def __init__(self, name, configuration, application):
        super(EC2AutoscaleGroup, self).__init__(name, configuration, application)
        self.group = None
        self.elb = None
        self.name = name  # Do not add version to the name

    def set_launch_config(self, launch_config):
        self.configuration["launch_config"] = launch_config.name
        self.update()

    def __get_resource(self):
        return self.autoscale.get_all_groups(names=[self.name])[0]

    def exists(self):
        try:
            self.__get_resource()
        except IndexError:
            return False
        return True

    def load_balancer(self):
        if self.elb is not None:
            return self.elb
        self.elb = ELBBalancer(self.__get_resource().load_balancers[0], {}, self.application)
        return self.elb

    def instances(self, status='running'):
        """
        Get number of instances running
        """
        group = self.__get_resource()
        instances_id = [i.instance_id for i in group.instances]
        instances = []
        if len(instances_id) is 0:
            return instances
        instance_states = self.ec2.get_all_instance_status(instances_id)
        for state in instance_states:
            if state.state_name == status:
                instances.append(state.id)
        return instances

    def update(self):
        if not self.exists():
            self.create()
        group = self.__get_resource()
        group.launch_config_name = self.configuration["launch_config"]
        group.update()

    def force_new_launch_configuration(self):
        """
        Force new launch configuration by increasing desired capacity and
        decreasing it afterwards
        """

        balloon = Balloon("Increasing desired capacity to provision new machines")
        old_instances = self.instances()
        instances = old_instances
        group = self.__get_resource()
        group.desired_capacity = len(instances) * 2
        group.max_size = group.max_size * 2
        group.update()
        for i in range(1, 15):
            balloon.update(i)
            time.sleep(1)
        balloon.finish()

        balloon = Balloon("Waiting for new instances until they're up and running")
        i = 0
        while len(instances) != group.desired_capacity:
            balloon.update(i)
            i += 1
            time.sleep(1)
            group = self.__get_resource()
            instances = self.instances()

        new_instances = set(instances) - set(old_instances)
        instances = self.instances('pending')
        while len(instances) != 0:
            balloon.update(i)
            i += 1
            time.sleep(1)
            instances = self.instances('pending')
        balloon.finish()

        balloon = Balloon("Waiting for new instances until they're added to the balancer %s" % (group.load_balancers[0]))
        balanced_instances = self.load_balancer().instance_health(new_instances)
        i = 0
        while len(balanced_instances) != len(new_instances):
            balloon.update(i)
            i += 1
            time.sleep(1)
            balanced_instances = self.load_balancer().instance_health(new_instances)
        balloon.finish()

        balloon = Balloon("Changing termination policy to terminate older instances")
        group.termination_policies = ["OldestLaunchConfiguration"]
        group.desired_capacity = self.configuration['desired_capacity']
        group.update()
        i = 0
        while len(balanced_instances) != len(new_instances):
            balloon.update(i)
            i += 1
            time.sleep(1)
        balloon.finish()

        group.termination_policies = self.configuration['termination_policies']
        group.max_size = self.configuration['max_size']
        group.update()

    def create(self):
        group = AutoScalingGroup(group_name=self.name, **self.configuration)
        self.resource = self.autoscale.create_auto_scaling_group(group)
        tags = Tag(key='Name', value=self.application, propagate_at_launch=True, resource_id=self.name)
        self.autoscale.create_or_update_tags([tags])


class EC2AutoscalePolicy(EC2Autoscale):
    """
    EC2 autoscale policy
    """

    def __init__(self, name, configuration, application, group):
        super(EC2AutoscalePolicy, self).__init__(name, configuration, application)
        self.group = group
        self.name = name
        self.configuration["as_name"] = group.name

    def __get_resource(self):
        return self.autoscale.get_all_policies(as_group=self.group.name, policy_names=[self.name])[0]

    def exists(self):
        try:
            self.__get_resource()
        except IndexError:
            return False
        return True

    def update(self):
        self.create()

    def create(self):
        policy = ScalingPolicy(name=self.name, **self.configuration)
        self.autoscale.create_scaling_policy(policy)
        # Refresh policy from EC2 to get ARN
        self.resource = self.__get_resource()


class CloudWatchMetricAlarm(CloudWatch):
    """
    Cloudwatch metric alarm
    """

    def __init__(self, name, configuration, application, policy):
        super(CloudWatchMetricAlarm, self).__init__(configuration, application)
        self.name = name
        self.policy = policy
        self.configuration["alarm_actions"] = [policy.resource.policy_arn]
        self.configuration["dimensions"] = {"AutoScalingGroupName": policy.group.name}

    def __get_resource(self):
        return self.cloudwatch.describe_alarms(alarm_names=[self.name])[0]

    def exists(self):
        try:
            self.__get_resource()
        except IndexError:
            return False
        return True

    def update(self):
        self.create()

    def create(self):
        alarm = MetricAlarm(name=self.name, **self.configuration)
        self.resource = self.cloudwatch.create_alarm(alarm)


class ELBBalancer(ELB):
    """
    ELB balancer
    """

    def __init__(self, name, configuration, application):
        super(ELBBalancer, self).__init__(name, configuration, application)
        self.balancer = self.elb.get_all_load_balancers(load_balancer_names=[self.name])[0]

    def instance_health(self, instance_ids=[], health='InService'):
        """
        Get number of instances running
        """
        instances = []
        # import ipdb; ipdb.set_trace()
        for instance in instance_ids:
            try:
                instance_health = self.balancer.get_instance_health([instance])[0]
            except:
                continue
            if instance_health.state == health:
                instances.append(instance)
        return instances
