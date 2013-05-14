""" Forseti main class
"""

from models import GoldEC2Instance, EC2AutoscaleGroup, ELBBalancer
from models import EC2AutoscaleConfig, EC2AutoscalePolicy, CloudWatchMetricAlarm
from models import Balloon


class Forseti(object):
    """Forseti main class"""

    def __init__(self, aws_properties):
        self.aws_properties = aws_properties
        self.app_properties = {}
        self.gold_properties = {}
        self.gold_instance = None
        self.group_properties = {}
        self.autoscale_properties = {}
        self.policies = {}
        self.alarms = {}
        self.autoscale_name = None

    def ami_from_gold_instance(self, application):
        self.gold_instance = GoldEC2Instance(self.gold_properties, application)

        self.gold_instance.launch_and_wait()
        self.gold_instance.provision()
        ami_id = self.gold_instance.create_image()
        self.gold_instance.terminate()
        self.gold_instance = None

        return ami_id

    def deploy(self, application):
        balloon = Balloon("")
        self.app_properties = self.aws_properties['applications'][application]
        self.gold_properties = self.app_properties['gold']
        new_ami_id = self.ami_from_gold_instance(application)
        print "New AMI from gold image %s" % (new_ami_id)
        self.configure_autoscale(application, new_ami_id)
        balloon.finish()
        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)

    def configure_autoscale(self, application, ami_id):
        self.autoscale_properties = self.aws_properties['autoscale']
        self.app_properties = self.aws_properties['applications'][application]
        self.autoscale_name = self.app_properties['autoscale_group']

        print "Creating autoscale config %s" % (self.autoscale_name)
        autoscale_config = self.configure_autoscale_config(application, ami_id)
        print "Created autoscale config %s" % (self.autoscale_name)

        print "Creating autoscale group %s" % (self.autoscale_name)
        group = self.configure_autoscale_group(application, autoscale_config)
        print "Created autoscale group %s" % (self.autoscale_name)

        print "Creating autoscale policies"
        self.configure_autoscale_policies(application, group)
        print "Created autoscale policies"

        print "Creating metric alarms which will trigger autoscaling"
        self.configure_metric_alarms(application, group)
        print "Created metric alarms"

        print "Waiting until instances are up and running"
        group.force_new_launch_configuration()
        print "All instances are running"

    def configure_elastic_load_balancing(self, application):
        elb_name = application['elb']
        elb = ELBBalancer(elb_name, {}, application)

        return elb

    def configure_autoscale_config(self, application, ami_id):
        configs_properties = self.autoscale_properties['configs']
        config_properties = configs_properties[self.autoscale_name]
        config_properties['image_id'] = ami_id
        config = EC2AutoscaleConfig(self.autoscale_name, config_properties, application)
        config.create()

        return config

    def configure_autoscale_group(self, application, autoscale_config):
        self.group_properties = self.autoscale_properties['groups']
        group_properties = self.group_properties[self.autoscale_name]
        group = EC2AutoscaleGroup(self.autoscale_name, group_properties, application)
        group.set_launch_config(autoscale_config)

        return group

    def configure_autoscale_policies(self, application, group):
        self.autoscale_properties = self.aws_properties['autoscale']
        policies = self.autoscale_properties['policies']
        for name, policy_properties in policies.items():
            policy = EC2AutoscalePolicy(name, policy_properties, application, group)
            policy.update()
            self.policies[name] = policy

    def configure_metric_alarms(self, application, group):
        self.autoscale_properties = self.aws_properties['autoscale']
        alarms = self.autoscale_properties['alarms']
        for name, alarm_properties in alarms.items():
            policy = self.policies[alarm_properties['alarm_actions']]
            alarm = CloudWatchMetricAlarm(name, alarm_properties, application, policy)
            alarm.update()
            self.alarms[name] = alarm
