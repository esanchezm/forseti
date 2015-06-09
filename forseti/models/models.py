# -*- coding: utf-8 -*-
import json
import os
import re
import time

from forseti.models.base import (
    CloudWatch,
    EC2,
    EC2AutoScale,
    ELB,
    SNS,
)
from forseti.utils import balloon_timer
from forseti.exceptions import (
    EC2InstanceException,
    EC2AutoScaleException,
    ForsetiConfigurationException,
)

from boto.ec2.autoscale import (
    AutoScalingGroup,
    LaunchConfiguration,
    ScalingPolicy,
    Tag,
)
from boto.exception import BotoServerError, EC2ResponseError
from boto.ec2.cloudwatch import MetricAlarm
import paramiko


class Application(object):
    """
    Forseti application
    """
    def __init__(self, name, forseti_configuration):
        super(Application, self).__init__()
        self.name = name
        self.forseti_configuration = forseti_configuration

    @property
    def autoscale_group(self):
        try:
            return EC2AutoScaleGroup(
                self.forseti_configuration.get_autoscale_group(self.name),
                self.name,
                self.forseti_configuration.get_autoscale_group_configuration(self.name)
            )
        except ForsetiConfigurationException:
            return None

    @property
    def scaling_policies(self):
        try:
            policies = self.forseti_configuration.get_scaling_policies(self.name)
            for policy_name in policies:
                policy = EC2AutoScalePolicy(
                    policy_name,
                    self.autoscale_group,
                    self.name,
                    self.forseti_configuration.get_policy_configuration(policy_name)
                )
                policy.update_or_create()
                self.policies[policy_name] = policy
        except ForsetiConfigurationException:
            return None


class EC2Instance(EC2):
    """
    EC2 Instance
    """

    def __init__(
        self, application, configuration=None, resource=None, instance_id=None
    ):
        super(EC2Instance, self).__init__(application, configuration, resource)
        self.instance_id = instance_id
        if self.instance_id:
            self.resource = self.ec2.get_all_instances(instance_ids=[self.instance_id])[0]
            self.instance = self.resource.instances[0]
        else:
            self.instance = None

    def load_balancers(self):
        """
        Get all the balancers for the instance.
        """
        if not self.instance_id:
            return []

        load_balancers = []
        all_load_balancers = ELB.get_all_load_balancers()

        for load_balancer in all_load_balancers:
            instances = [instance.id for instance in load_balancer.instances]
            if self.instance_id in instances:
                load_balancers.append(load_balancer)

        return load_balancers

    def launch(self):
        """
        Start EC2 instance in AWS. Raise EC2InstanceException if `instance_id`
        is set.
        """
        if self.instance and self.instance_id:
            raise EC2InstanceException(
                "Instance %s is already running" % self.instance.id
            )

        print "Starting instance"
        self.resource = self.ec2.run_instances(**self.configuration)
        self.instance = self.resource.instances[0]
        self.instance_id = self.instance.id

    def terminate(self):
        """
        Stop EC2 instance in AWS
        """
        print "Terminating instance %s" % self.instance.id
        self.ec2.terminate_instances([self.instance.id])

    def has_tag(self, tag):
        """
        Checks if an instance have an specific tag
        """
        return tag in self.instance.tags

    def create_image(self, no_reboot=False):
        """
        Create an AMI from a running instance
        """
        with balloon_timer("Instance %s creating image" % self.instance.id) as balloon:
            i = 0

            # FIXME: Sometimes, if the ami was created by forseti but couldn't
            # tag it, we may have an error. It would be better to look for amis
            # with the same name
            amis = self.ec2.get_all_images(
                owners=['self'],
                filters={
                    'tag:forseti:application': self.application,
                    'tag:forseti:date': self.today,
                }
            )
            ami_name = "%s-ami-%s-%s" % (self.application, self.today, len(amis) + 1)
            ami_id = self.instance.create_image(
                ami_name,
                description=ami_name,
                no_reboot=no_reboot
            )
            balloon.update(i)
            i += 1
            time.sleep(1)
            ami = self.ec2.get_all_images(image_ids=(ami_id,))[0]

            while ami.update() == "pending":
                balloon.update(i)
                i += 1
                time.sleep(1)

        if ami.update() == "available":
            ami.add_tag("Name", ami_name)
            ami.add_tag('forseti:application', self.application)
            ami.add_tag('forseti:date', self.today)
        else:
            raise EC2InstanceException(
                "Image %s could not be created. Reason: %s"
                % (ami.id, ami.message)
            )

        return ami_id

    def attributes(self):
        """
        Get the most importants attributes of the instance.
        """
        return {
            "instance_type": self.instance.instance_type,
            "key_name": self.instance.key_name,
            "instance_monitoring": self.instance.monitored,
            "security_groups": [g.name for g in self.instance.groups],
            "kernel_id": self.instance.kernel,
            "ramdisk_id": self.instance.ramdisk,
            "ebs_optimized": self.instance.ebs_optimized,
            "availability_zone": self.instance.placement,
            "load_balancers": [elb.name for elb in self.load_balancers()]
        }


class GoldenEC2Instance(EC2Instance):
    """
    A golden instance is the one which is used as a base to create the
    application AMI.
    """
    TIMEOUT = 2

    def __init__(self, application, configuration=None):
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

        super(GoldenEC2Instance, self).__init__(application, configuration)
        # No need to monitor an instance that will be terminated soon
        self.configuration["monitoring_enabled"] = False

    def launch_and_wait(self):
        """
        Launch a golden instance and wait until it's running.
        """
        self.launch()
        with balloon_timer("Golden instance %s launched. Waiting until it's running" % self.instance.id) as balloon:
            i = 0
            while self.instance.update() == "pending":
                balloon.update(i)
                i += 1
                time.sleep(1)

        if self.instance.update() == "running":
            tag_name = "golden-%s-instance-%s" % (self.application, self.today)
            self.instance.add_tag('Name', tag_name)
            self.instance.add_tag('forseti:golden-instance', True)
            self.instance.add_tag('forseti:application', self.application)
            self.instance.add_tag('forseti:date', self.today)
        else:
            raise EC2InstanceException(
                "Golden instance %s could not be launched" % self.instance.id
            )

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
        with balloon_timer("Golden instance %s provisioned. Waiting until SSH is up" % self.instance.id) as balloon:
            i = 0
            while not self.is_ssh_running():
                balloon.update(i)
                i += 1
                time.sleep(1)

    def provision(self, deployer_args=None):
        """
        Provisions machine using `command` specified in configuration file,
        `command` is executed locally within `working_directory` specified path.

        Some extra arguments can be passed to the command by
        using `deployer_args`
        """
        self.wait_for_ssh()
        with balloon_timer("Deployed new code on golden instance %s" % self.instance.id) as balloon:
            command = self.provision_configuration['command'].format(
                dns_name=self.instance.public_dns_name
            )
            if deployer_args:
                # `deployer_args` is supposed to be a string
                command = '%s %s' % (command, deployer_args)

            former_directory = os.getcwd()
            os.chdir(self.provision_configuration['working_directory'])
            os.system(command)
            os.chdir(former_directory)


class EC2AMI(EC2):
    """
    EC2 AMI
    """

    def __init__(self, application, ami_id, configuration=None, resource=None):
        super(EC2AMI, self).__init__(application, configuration, resource)
        self.ami_id = ami_id

    @property
    def snapshot_id(self):
        try:
            return self.resource.block_device_mapping.current_value.snapshot_id
        except AttributeError:
            return None

    def get_snapshot(self):
        """
        Get the snapshot associated to the AMI
        """
        if not self.snapshot_id:
            return None

        snapshots = self.ec2.get_all_snapshots(snapshot_ids=[self.snapshot_id])

        return snapshots[0] if snapshots else None

    def delete(self):
        """
        Deletes the AMI and its associated snapshot
        """
        try:
            self.ec2.deregister_image(self.ami_id, delete_snapshot=True)
        except AttributeError:
            # Try to deregister the AMI without deleting the snapshot if it
            # fails
            self.ec2.deregister_image(self.ami_id, delete_snapshot=False)


class EC2AutoScaleConfig(EC2AutoScale):
    """
    EC2 autoscale config
    """

    def create(self):
        """
        Creates a launch configuration using configuration file. It will update
        the autocale configuration `name` property by appending the current
        date and a version
        """
        version = 1
        found = False
        while not found:
            name = "%s-%s" % (self.generated_name, version)
            launch_configurations = self.autoscale.get_all_launch_configurations(names=[name])
            if launch_configurations:
                version += 1
            else:
                found = True

        self.name = name
        launch_configuration = LaunchConfiguration(
            name=self.name,
            **self.configuration
        )
        self.resource = self.autoscale.create_launch_configuration(launch_configuration)

    def delete(self):
        """
        Deletes a launch configuration and its associated AMI
        """
        try:
            self.ami().delete()
        except EC2ResponseError:
            print "The AMI %s could not be deleted" % self.resource.image_id

        self.autoscale.delete_launch_configuration(self.name)

    def ami(self):
        """
        Get the AMI associated to the launch configuration
        """
        return EC2AMI(
            self.application,
            self.resource.image_id,
            resource=self.ec2.get_image(image_id=self.resource.image_id)
        )


class EC2AutoScaleGroup(EC2AutoScale):
    """
    EC2 autoscale group
    """

    def __init__(self, name, application, configuration=None, resource=None):
        super(EC2AutoScaleGroup, self).__init__(name, application, configuration, resource)
        self.group = None
        self.elbs = []

    def set_launch_configuration(self, launch_configuration):
        """
        Sets launch configuration for autoscale group, if group is attached
        to an existing AWS autoscale group, update its configuration
        """
        self.configuration['launch_config'] = launch_configuration.name

        if self.group:
            self.group.launch_config_name = self.configuration['launch_config']
            self.group.update()

    def _get_autoscaling_group(self):
        """
        Returns a current `boto.ec2.autoscale.group.AutoScalingGroup` instance
        associated to the instance of this class
        """
        groups = self.autoscale.get_all_groups(names=[self.name])
        if groups:
            return groups[0]
        return None

    def load_balancers(self):
        """
        Returns a list of `ELBBalancer` instances associated to the autoscale
        group
        """
        self.group = self._get_autoscaling_group()
        if not self.group.load_balancers:
            return None
        if self.elbs:
            return self.elbs
        for balancer in self.group.load_balancers:
            self.elbs.append(ELBBalancer(balancer, self.application))
        return self.elbs

    def get_instances_with_status(self, status):
        """
        Get a list of instances in this autoscale group whose status matches
        `status`
        """
        group = self._get_autoscaling_group()
        if group is None:
            return []
        instances_ids = [instance.instance_id for instance in group.instances]

        if not instances_ids:
            return []

        instances = []
        instances_states = self.ec2.get_all_instance_status(instances_ids)
        for state in instances_states:
            if state.state_name == status:
                instances.append(state.id)
        return instances

    def get_instances_dns_names_with_status(self, status):
        """
        Get a list of public DNS names of the instances within this autoscale
        group whose status matches `status`
        """
        running_instances_ec2_names = self.get_instances_with_status(status)

        dns_names = []
        for instance_id in running_instances_ec2_names:
            dns_names.append(
                EC2Instance(
                    self.application,
                    configuration=None,
                    instance_id=instance_id
                ).instance.public_dns_name
            )
        return dns_names

    def increase_desired_capacity(self):
        """
        Increases the autoscale group desired capacity and max_size, this
        implies launching new EC2 instances
        """
        with balloon_timer("Increasing desired capacity to provision new machines") as balloon:

            current_instances = self.get_instances_with_status('running')
            self.old_instances = current_instances

            desired = len(current_instances) * 2
            i = 0
            while self.group.desired_capacity != desired:
                self.group.desired_capacity = desired
                self.group.max_size = self.group.max_size * 2
                self.group.update()
                balloon.update(i)
                i += 1
                time.sleep(1)
                self.group = self._get_autoscaling_group()

    def suspend_processes(self, scaling_processes=None):
        """
        Suspend autoscaling processes in the group.
        """
        self.group = self._get_autoscaling_group()
        if self.group:
            self.group.suspend_processes(scaling_processes)

    def resume_processes(self, scaling_processes=None):
        """
        Resume autoscaling processes in the group.
        """
        self.group = self._get_autoscaling_group()
        if self.group:
            self.group.resume_processes(scaling_processes)

    def deregister_instance_from_load_balancers(self, instances, wait=True):
        """
        Deregister instances in the ELB of the autoscale group
        """
        elbs = self.load_balancers()
        if elbs:
            instances_ids = [instance.instance_id for instance in instances]
            for elb in elbs:
                elb.deregister_instances(instances_ids)
                if wait:
                    elb.wait_for_instances_with_health(
                        instances_ids,
                        health='OutOfService'
                    )

    def register_instance_in_load_balancers(self, instances, wait=True):
        """
        Register instances in the ELB of the autoscale group
        """
        elbs = self.load_balancers()
        if elbs:
            instances_ids = [instance.instance_id for instance in instances]
            for elb in elbs:
                elb.register_instances(instances_ids)
                if wait:
                    elb.wait_for_instances_with_health(
                        instances_ids,
                        health='InService'
                    )

    def wait_for_new_instances_ready(self):
        """
        Wait for instances launched by autoscale group to be up, running and in
        the balancer
        """
        with balloon_timer("Waiting for new instances until they're up and running") as balloon:
            i = 0
            while len(self.get_instances_with_status('running')) != self.group.desired_capacity:
                balloon.update(i)
                i += 1
                time.sleep(1)

        # TODO: Query AWS for instances
        instances = self.get_instances_with_status('running')
        new_instances = set(instances) - set(self.old_instances)

        # Ask the balancer to wait
        for balancer in self.load_balancers():
            balancer.wait_for_instances_with_health(new_instances)

        # We do it twice, because sometimes the balancer health check is a bit tricky.
        with balloon_timer("Waiting for another balancer health check pass") as balloon:
            for i in range(1, self.load_balancers()[0].get_health_check_interval()):
                balloon.update(i)
                time.sleep(1)

        for balancer in self.load_balancers():
            balancer.wait_for_instances_with_health(new_instances)

    def terminate_instances(self, instances_ids):
        """
        Terminate instances that we no longer want in the autoscale group, the
        old ones
        """
        with balloon_timer("Terminating old instances") as balloon:
            for instance_id in instances_ids:
                try:
                    self.autoscale.terminate_instance(
                        instance_id,
                        decrement_capacity=True
                    )
                except BotoServerError:
                    pass

        # Force an updated group instance to be sure the update is done correctly
        self.group = self._get_autoscaling_group()
        self.group.max_size = self.configuration['max_size']
        self.group.update()

    def apply_launch_configuration_for_deployment(self):
        """
        Applies changes to current autoscale group launch configuration for
        creating new instances:

        * First, increases desired capacity, therefore autoscale group grows
        with the new launch configuration.
        * Then, we wait for the new instances being booted to be ready and in
        the balancer.
        * Finally, we terminate older instances by restoring initial capacity
        in autoscale group.
        """
        instances_ids = self.get_instances_with_status('running')
        self.increase_desired_capacity()
        self.wait_for_new_instances_ready()
        self.terminate_instances(instances_ids)

    def update_or_create(self):
        """
        Creates autoscaling group and sets a `propagate_at_launch` tag for
        future instances the autoscale group boots
        """
        self.group = self._get_autoscaling_group()
        if self.group is None:
            autoscaling_group = AutoScalingGroup(
                group_name=self.name,
                **self.configuration
            )
            self.resource = self.autoscale.create_auto_scaling_group(autoscaling_group)
            self.group = self._get_autoscaling_group()
            name_tag = Tag(
                key='Name',
                value=self.application,
                propagate_at_launch=True,
                resource_id=self.name
            )
            application_tag = Tag(
                key='forseti:application',
                value=self.application,
                propagate_at_launch=True,
                resource_id=self.name
            )
            date_tag = Tag(
                key='forseti:date',
                value=self.today,
                propagate_at_launch=True,
                resource_id=self.name
            )
            self.autoscale.create_or_update_tags([name_tag, application_tag, date_tag])
        else:
            self.group.launch_config_name = self.configuration['launch_config']
            self.group.availability_zones = self.configuration['availability_zones']
            if 'desired_capacity' in self.configuration:
                self.group.desired_capacity = self.configuration['desired_capacity']
            self.group.max_size = self.configuration['max_size']
            self.group.min_size = self.configuration['min_size']
            self.group.load_balancers = self.configuration['load_balancers']
            self.group.default_cooldown = self.configuration.get('default_cooldown', None)
            self.group.termination_policies = self.configuration['termination_policies']
            self.group.update()
            self.group = self._get_autoscaling_group()

    def status(self):
        """
        Returns the group status in a dictionary.
        """
        self.group = self._get_autoscaling_group()
        status = {
            'Name': self.group.name,
            'Launch configuration': self.group.launch_config_name,
            'Instances': [],
            'Activities': [],
            'Balancers': 'N/A',
            'Instances': [],
        }

        if self.load_balancers():
            balancer_names = map(lambda e: e.name, self.load_balancers())
            status['Balancers'] = ", ".join(balancer_names)

        for instance in self.group.instances:
            elb_status = {}
            for balancer in self.load_balancers():
                health = balancer.get_instance_health(instance.instance_id)
                elb_status['ELB %s status' % balancer.name] = health.state
                elb_status['ELB %s reason' % balancer.name] = health.description

            instance_status = {
                'Id': instance.instance_id,
                'Status': instance.health_status,
                'Launch configuration': instance.launch_config_name,
                'Availability zone': instance.availability_zone,
            }
            instance_status.update(elb_status)

            status['Instances'].append(instance_status)
        for activity in self.group.get_activities():
            status['Activities'].append(
                {
                    'Description': activity.description,
                    'Start': activity.start_time.strftime("%Y-%m-%d %H:%M:%S%Z"),
                    'End': activity.end_time.strftime("%Y-%m-%d %H:%M:%S%Z") if activity.end_time else 'On progress',
                    'Cause': activity.cause
                }
            )

        return status

    def get_all_launch_configurations(self):
        """
        Get all the launch configurations associated with the autoscaling
        group of the application.

        Please, notice that AWS provides no relation between autoscaling
        configuration and group. What we're doing here is get all the
        available configuration and return only the one which matches
        a given regexp. This may cause false positives and return incorrect
        launch configurations.
        """
        all_configurations = self.autoscale.get_all_launch_configurations()
        configurations_for_this_group = []
        while True:
            # I have to do this because AWS don't let you tag launch
            # configurations. Beware with false positives in case you have
            # similar names
            regex = r"^%s-\d{4}-\d{2}-\d{2}-\d+" % self.name
            for resource in all_configurations:
                # The configuration name starts with the group name and a dash
                if re.findall(regex, resource.name):
                    launch_configuration = EC2AutoScaleConfig(
                        resource.name,
                        self.application,
                        resource=resource
                    )

                    configurations_for_this_group.append(launch_configuration)

            if all_configurations.next_token is None:
                break

            all_configurations = self.autoscale.get_all_launch_configurations(
                next_token=all_configurations.next_token
            )

        configurations_for_this_group.sort(cmp=lambda x, y: x.name < y.name)

        return configurations_for_this_group


class EC2AutoScaleNotification(EC2AutoScale):
    """
    EC2 Autoscale notification
    """
    LAUNCH = 'autoscaling:EC2_INSTANCE_LAUNCH'
    LAUNCH_ERROR = 'autoscaling:EC2_INSTANCE_LAUNCH_ERROR'
    TERMINATE = 'autoscaling:EC2_INSTANCE_TERMINATE'
    TERMINATE_ERROR = 'autoscaling:EC2_INSTANCE_TERMINATE_ERROR'
    TEST_NOTIFICATION = 'autoscaling:TEST_NOTIFICATION'

    ALL_TYPES = [
        LAUNCH,
        LAUNCH_ERROR,
        TERMINATE,
        TERMINATE_ERROR,
        TEST_NOTIFICATION
    ]

    def __init__(self, autoscale_group_name, application, notification_type, topic, configuration=None, resource=None):
        super(EC2AutoScaleNotification, self).__init__(autoscale_group_name, application, configuration, resource)
        if notification_type != 'ALL' and notification_type not in ALL_TYPES:
            raise EC2AutoScaleException(
                "Invalid notification_type: %s" % notification_type
            )

        if notification_type == 'ALL':
            self.notification_types = self.ALL_TYPES
        else:
            self.notification_types = [notification_type]
        self.topic = topic
        self.autoscale_group_name = autoscale_group_name

    def update_or_create(self):
        """
        Updates or create an autoscaling notification
        """
        self.autoscale.put_notification_configuration(
            self.autoscale_group_name,
            self.topic,
            self.notification_types
        )


class EC2AutoScalePolicy(EC2AutoScale):
    """
    EC2 autoscale policy
    """

    def __init__(self, name, group, application, configuration=None):
        """
        :param name: Autoscale policy name
        :param configuration: Dictionary containing configuration
        :param application: Application name
        :param group: `EC2AutoScaleGroup` instance to which the policy will be
                                          applied
        """
        super(EC2AutoScalePolicy, self).__init__(name, application, configuration)
        self.group = group
        self.name = name
        self.configuration["as_name"] = group.name

    def update_or_create(self):
        """
        Creates the scaling policy in AWS and stores in `self.reource` a
        `boto.ec2.autoscale.policy.ScalingPolicy`
        """
        policy = ScalingPolicy(name=self.name, **self.configuration)
        self.autoscale.create_scaling_policy(policy)
        # Refresh policy from EC2 to get ARN
        self.resource = self.autoscale.get_all_policies(
            as_group=self.group.name,
            policy_names=[self.name]
        )[0]

    def get_policy_arn(self):
        return self.resource.policy_arn

    def get_group_name(self):
        return self.group.name


class CloudWatchMetricAlarm(CloudWatch):
    """
    Cloudwatch metric alarm
    """

    def __init__(self, name, policy, application, configuration=None):
        super(CloudWatchMetricAlarm, self).__init__(application, configuration)
        self.name = name
        self.policy = policy
        self.configuration["alarm_actions"] = policy.get_policy_arn()
        if 'dimensions' not in self.configuration:
            self.configuration["dimensions"] = {
                "AutoScalingGroupName": policy.get_group_name()
            }

    def update_or_create(self):
        alarm = MetricAlarm(name=self.name, **self.configuration)
        self.resource = self.cloudwatch.create_alarm(alarm)


class ELBBalancer(ELB):
    """
    ELB balancer
    """

    def __init__(self, name, application, configuration=None):
        super(ELBBalancer, self).__init__(name, application, configuration)
        self.balancer = self.elb.get_all_load_balancers(load_balancer_names=[self.name])[0]

    def get_instance_health(self, instance_id):
        """
        Get number of instances running
        """
        try:
            instance_health = self.balancer.get_instance_health([instance_id])[0]
            return instance_health
        except:
            pass
        return None

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
        with balloon_timer("Waiting for %d instances until they're in the balancer %s with status %s" % (
            len(instances_ids),
            self.balancer.name,
            health
        )) as balloon:
            i = 0
            while len(self.filter_instances_with_health(instances_ids, health=health)) != len(instances_ids):
                balloon.update(i)
                i += 1
                time.sleep(1)

    def get_health_check_interval(self):
        return self.balancer.health_check.interval

    def deregister_instances(self, instances):
        return self.balancer.deregister_instances(instances)

    def register_instances(self, instances):
        return self.balancer.register_instances(instances)


class SNSMessageSender(SNS):
    """
    Class which represents a message sent to a SNS topic
    """
    def __init__(self, application, topic_arn, configuration=None, resource=None):
        super(SNSMessageSender, self).__init__(application, configuration, resource)
        self.topic_arn = topic_arn

    def send(self, message, subject=None, message_attributes=None):
        """
        Send a message to a SNS topic
        """
        message_attributes = message_attributes or {}
        message_attributes.update(
            {
                "Type": "Notification",
                "Application": self.application,
                "Message": message
            }
        )

        message = {
            "default": json.dumps(message_attributes)
        }

        self.sns.publish(
            subject=subject,
            message=json.dumps(message),
            message_structure='json',
            topic=self.topic_arn
        )
