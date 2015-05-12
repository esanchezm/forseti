import abc

from forseti.models import (
    EC2AutoScaleGroup,
    EC2AutoScaleConfig,
    EC2AutoScalePolicy,
    CloudWatchMetricAlarm,
    SNSMessageSender
)
from forseti.utils import balloon_timer


class BaseDeployer(object):
    """Base deployer class"""

    def __init__(self, application, configuration, command_args=None):
        self.application = application
        self.configuration = configuration
        self.application_configuration = configuration.get_application_configuration(application)
        self.gold_instance = None
        self.policies = {}
        self.alarms = {}
        self.autoscale_group_name = None
        self.command_args = command_args or ''

    def create_autoscale_configuration(self, ami_id):
        """
        Creates an autoscale launch configuration `EC2AutoScaleConfig`

        :param ami_id: AMI id used for the new autoscale launch configuration
        """
        config_properties = self.configuration.get_launch_configuration_configuration(self.application)
        config_properties['image_id'] = ami_id
        config = EC2AutoScaleConfig(
            self.application_configuration['autoscale_group'],
            self.application,
            config_properties
        )
        config.create()

        return config

    def _get_autoscaling_group(self):
        return EC2AutoScaleGroup(
            self.autoscale_group_name,
            self.application,
        )

    def update_or_create_autoscale_group(self, autoscale_config):
        """
        Creates or updates an autoscale group `EC2AutoScaleGroup`

        :param autoscale_config: Auto scale launch configuration to be assigned
                                 to the auto scale group.
        """
        group = EC2AutoScaleGroup(
            self.autoscale_group_name,
            self.application,
            self.configuration.get_autoscale_group_configuration(self.application)
        )
        group.set_launch_configuration(autoscale_config)
        group.update_or_create()

        return group

    def update_or_create_autoscale_policies(self, group):
        """
        Creates or updates autoscale policies `EC2AutoScalePolicy`

        :param group: Auto scale group to create policies in.
        """
        policies = self.configuration.get_scaling_policies(self.application)
        for policy_name in policies:
            policy = EC2AutoScalePolicy(
                policy_name,
                group,
                self.application,
                self.configuration.get_policy_configuration(policy_name)
            )
            policy.update_or_create()
            self.policies[policy_name] = policy

    def update_or_create_metric_alarms(self, group):
        """
        Creates or updates CloudWatch alarms `CloudWatchMetricAlarm`
        """
        alarms = self.configuration.alarms
        for alarm_name, alarm_properties in alarms.items():
            alarm_actions = alarm_properties['alarm_actions']
            if alarm_actions in self.policies:
                policy = self.policies[alarm_actions]
                alarm = CloudWatchMetricAlarm(
                    alarm_name,
                    policy,
                    self.application,
                    alarm_properties
                )
                alarm.update_or_create()
                self.alarms[alarm_name] = alarm

    def setup_autoscale(self, ami_id):
        """
        Creates or updates the autoscale group, launch configuration, autoscaling
        policies and CloudWatch alarms.

        :param ami_id: AMI id used for the new autoscale system
        """
        self.send_sns_message(
            "Setting up autoscale group for %s with AMI %s" %
            (self.application, ami_id)
        )
        self.autoscale_group_name = self.application_configuration['autoscale_group']

        print "Creating autoscale config %s" % (self.autoscale_group_name)
        autoscale_config = self.create_autoscale_configuration(ami_id)
        print "Created autoscale config %s" % (self.autoscale_group_name)

        print "Creating autoscale group %s" % (self.autoscale_group_name)
        group = self.update_or_create_autoscale_group(autoscale_config)
        print "Created autoscale group %s" % (self.autoscale_group_name)

        print "Creating autoscale policies"
        self.update_or_create_autoscale_policies(group)
        print "Created autoscale policies"

        print "Creating metric alarms which will trigger autoscaling"
        self.update_or_create_metric_alarms(group)
        print "Created metric alarms"

        return group

    def deploy(self, ami_id):
        """
        Do the deployment of an AMI.
        """
        with balloon_timer("") as balloon:
            self.setup_autoscale(ami_id)

        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)

    def cleanup_autoscale_configurations(self, desired_configurations=4):
        """
        Clean up all launch configurations of the autoscaling group belonging
        to the application but leaving `desired_configurations` left.

        When a launch configuration is deleted, the AMI and snapshot will be
        deleted too.
        """
        with balloon_timer(""):
            self.autoscale_group_name = self.application_configuration['autoscale_group']
            group = self._get_autoscaling_group()
            configurations = group.get_all_launch_configurations()

            # Get the first configurations minus the `desired_configurations`
            configurations_to_be_deleted = configurations[:-desired_configurations]
            for configuration in configurations_to_be_deleted:
                self.send_sns_message(
                    "Deleting launch configuration %s" % configuration.name
                )
                print "Deleting launch configuration %s" % configuration.name
                configuration.delete()

    def list_autoscale_configurations(self):
        """
        List all the launch configurations of the autoscaling group belonging
        to the application
        """
        self.autoscale_group_name = self.application_configuration['autoscale_group']
        group = self._get_autoscaling_group()
        configurations = group.get_all_launch_configurations()
        for configuration in configurations:
            ami = configuration.ami()
            print "- %s " % configuration.name
            print "\t- AMI: %s " % (ami.ami_id if ami.ami_id else "Unknown")
            print "\t- Snapshot: %s " % (ami.snapshot_id if ami.snapshot_id else "Unknown")

    def send_sns_message(self, message, subject=None, extra_attributes=None):
        """
        """
        if 'sns_notification_arn' not in self.application_configuration:
            return

        # If there's no subject, then the subject is the message
        subject = subject or message

        sender = SNSMessageSender(
            self.application,
            self.application_configuration['sns_notification_arn']
        )

        extra_attributes = extra_attributes or {}
        if 'sns_extra_attributes' in self.application_configuration:
            extra_attributes.update(
                self.application_configuration['sns_extra_attributes']
            )

        sender.send(message, subject, extra_attributes)

    def regenerate(self):
        """
        Regenerate the autoscaling group of a given application.

        Basically, it will create an AMI from one of the machines in the
        group, creates a new launch configuration and setup the alarm and
        policies again.
        """
        ami_id = self.generate_ami()
        self.setup_autoscale(ami_id)

    @abc.abstractmethod
    def generate_ami(self):
        """
        Generate the AMI to be used in the autoscale group.
        """
        pass
