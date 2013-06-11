from forseti.models import (
    GoldenEC2Instance,
    EC2AutoScaleGroup,
    EC2AutoScaleConfig,
    EC2AutoScalePolicy,
    CloudWatchMetricAlarm
)
from forseti.utils import Balloon
from forseti.configuration_reader import ForsetiConfiguration


class TicketeaDeployer(object):
    """Deployer for ticketea's infrastructure"""

    def __init__(self, aws_properties):
        self.configuration = ForsetiConfiguration(aws_properties)
        self.gold_instance = None
        self.policies = {}
        self.alarms = {}
        self.autoscale_group_name = None

    def create_ami_from_golden_instance(self, application):
        """
        Create an AMI from a golden EC2 instance
        """
        self.gold_instance = GoldenEC2Instance(
            application,
            self.configuration.get_gold_instance_configuration(application)
        )

        self.gold_instance.launch_and_wait()
        self.gold_instance.provision()
        ami_id = self.gold_instance.create_image()
        self.gold_instance.terminate()
        self.gold_instance = None

        return ami_id

    def create_autoscale_configuration(self, application, ami_id):
        """
        Creates an autoscale launch configuration `EC2AutoScaleConfig`
        """
        config_properties = self.configuration.get_launch_configuration_configuration(application)
        config_properties['image_id'] = ami_id
        config = EC2AutoScaleConfig(
            self.configuration.get_application_configuration(application)['autoscale_group'],
            application,
            config_properties
        )
        config.create()

        return config

    def update_or_create_autoscale_group(self, application, autoscale_config):
        """
        Creates or updates an autoscale group `EC2AutoScaleGroup`
        """
        group = EC2AutoScaleGroup(
            self.autoscale_group_name,
            application,
            self.configuration.get_autoscale_group_configuration(application)
        )
        group.set_launch_configuration(autoscale_config)
        group.update_or_create()

        return group

    def update_or_create_autoscale_policies(self, application, group):
        """
        Creates or updates autoscale policies `EC2AutoScalePolicy`
        """
        policies = self.configuration.get_scaling_policies(application)
        for policy_name in policies:
            policy = EC2AutoScalePolicy(
                policy_name,
                group,
                application,
                self.configuration.get_policy_configuration(policy_name)
            )
            policy.update_or_create()
            self.policies[policy_name] = policy

    def update_or_create_metric_alarms(self, application, group):
        """
        Creates or updates CloudWatch alarms `CloudWatchMetricAlarm`
        """
        alarms = self.configuration.alarms
        for alarm_name, alarm_properties in alarms.items():
            alarm_actions = alarm_properties['alarm_actions']
            if alarm_actions in self.policies:
                policy = self.policies[alarm_actions]
                alarm = CloudWatchMetricAlarm(alarm_name, policy, application, alarm_properties)
                alarm.update_or_create()
                self.alarms[alarm_name] = alarm

    def setup_autoscale(self, application, ami_id):
        """
        Creates or updates the autoscale group, launch configuration, autoscaling
        policies and CloudWatch alarms.

        :param application: Application name
        :param ami_id: AMI id used for the new autoscale system
        """
        self.autoscale_group_name = self.configuration.get_application_configuration(application)['autoscale_group']

        print "Creating autoscale config %s" % (self.autoscale_group_name)
        autoscale_config = self.create_autoscale_configuration(application, ami_id)
        print "Created autoscale config %s" % (self.autoscale_group_name)

        print "Creating autoscale group %s" % (self.autoscale_group_name)
        group = self.update_or_create_autoscale_group(application, autoscale_config)
        print "Created autoscale group %s" % (self.autoscale_group_name)

        print "Creating autoscale policies"
        self.update_or_create_autoscale_policies(application, group)
        print "Created autoscale policies"

        print "Creating metric alarms which will trigger autoscaling"
        self.update_or_create_metric_alarms(application, group)
        print "Created metric alarms"

        print "Waiting until instances are up and running"
        group.apply_launch_configuration_for_deployment()
        print "All instances are running"

    def deploy(self, application, ami_id=None):
        """
        Do the code deployment in a golden instance and setup an autoscale group
        with an AMI created from it.
        """
        balloon = Balloon("")
        if not ami_id:
            ami_id = self.create_ami_from_golden_instance(application)
            print "New AMI from golden image %s" % (ami_id)
        self.setup_autoscale(application, ami_id)

        balloon.finish()
        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)
