from random import choice
import os

from forseti.exceptions import (
    ForsetiDeployException,
    ForsetiException,
)
from forseti.models import (
    EC2AutoScaleGroup,
    EC2Instance,
)
from forseti.deployers.base import BaseDeployer
from forseti.utils import balloon_timer


class DeployAndSnapshotDeployer(BaseDeployer):
    """Deployer for ticketea's infrastructure"""

    name = "deploy_and_snapshot"

    def __init__(self, application, configuration, command_args=None):
        super(DeployAndSnapshotDeployer, self).__init__(application, configuration, command_args)
        self.group = None

    def _get_group(self):
        group = EC2AutoScaleGroup(
            self.configuration.get_autoscale_group(self.application),
            self.application,
            self.configuration.get_autoscale_group_configuration(self.application)
        )

        return group

    def _get_instances(self, group):
        running_instances = group.get_instances_with_status('running')
        if not running_instances:
            return None

        instances = []
        for instance_id in running_instances:
            instance = EC2Instance(
                self.application,
                configuration=None,
                instance_id=instance_id
            )
            instances.append(instance)

        return instances

    def deploy_instances_in_group(self, group):
        """
        Deploy conde into the instances of the autoscale group. This is done
        by executing `command` from `deploy` configuration in `working_directory`.
        """
        instances = self._get_instances(group)
        if not instances:
            raise ForsetiException(
                'This deployer needs to have some instances running in the group'
            )

        with balloon_timer("Deploying new code on instances") as balloon:
            deploy_configuration = self.configuration.get_application_configuration(self.application)['deploy']
            command = deploy_configuration['command'].format(
                dns_name=','.join([instance.instance.public_dns_name for instance in instances])
            )
            if self.command_args:
                command = '%s %s' % (command, self.command_args)

            former_directory = os.getcwd()
            os.chdir(deploy_configuration['working_directory'])
            retvalue = os.system(command)
            if retvalue != 0:
                raise ForsetiDeployException(
                    'Deployment command did not return 0 as expected, returned: %s' % retvalue
                )
            os.chdir(former_directory)

        return instances

    def choice_instance(self, instances):
        """
        Choice a random instance to generate an AMI from it.

        It will avoid selecting instances with the tag 'forseti:avoid_ami_creation'
        """
        have_instance = False
        while not have_instance and len(instances):
            instance = choice(instances)
            if instance.has_tag('forseti:avoid_ami_creation'):
                print "Avoiding instance %s from AMI creation" % (instance.instance_id)
                instances.remove(instance)
            else:
                have_instance = True

        if not have_instance:
            raise ForsetiException(
                "No instance found to create image from. "
                "Are all of them marked with `forseti:avoid_ami_creation` tag?"
            )

        return instance

    def deploy(self, ami_id=None):
        """
        Do the code deployment by pushing the code in all instances and create
        an AMI from an.
        """
        self.send_sns_message(
            "Starting deployment of %s" % self.application
        )

        with balloon_timer("") as balloon:
            group = self._get_group()
            if not ami_id:
                # We must suspend autoscaling processes to avoid adding instances with
                # outdated code
                group.suspend_processes()
                try:
                    self.deploy_instances_in_group(group)
                except ForsetiException:
                    group.resume_processes()
                    raise
                ami_id = self.generate_ami()

            try:
                self.setup_autoscale(ami_id)
            finally:
                group.resume_processes()

        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)

        self.send_sns_message(
            "Finished deployment of %s in %02d:%02d" % \
            (self.application, minutes, seconds)
        )

    def generate_ami(self):
        """
        Generate the AMI to be used in the autoscale group.
        """
        self.send_sns_message(
            "Generating an AMI for %s" % self.application
        )
        group = self._get_group()
        group.suspend_processes()

        instances = self._get_instances(group)
        # Select a random instance and create an AMI from it
        instance = None
        try:
            instance = self.choice_instance(instances)
            group.deregister_instance_from_load_balancers([instance])
            ami_id = instance.create_image(no_reboot=False)
        except Exception:
            group.resume_processes()
            raise
        finally:
            if instance:
                group.register_instance_in_load_balancers([instance], wait=False)

        print "New AMI %s from instance %s" % (ami_id, instance.instance_id)

        self.send_sns_message(
            "Finished AMI generation for %s. AMI id: %s" % (self.application, ami_id)
        )

        return ami_id

    def init_application(self, instance_id, no_reboot=False):
        """
        Initialize an application and autoscale group using an existing instance
        from AWS.
        """
        self.send_sns_message(
            "Setting up a new application %s" % self.application
        )

        instance = EC2Instance(
            self.application,
            configuration=None,
            instance_id=instance_id
        )
        instance_attributes = instance.attributes()
        self.configuration.add_application(
            self.application,
            self._build_application_configuration(),
            self._build_autoscale_group_configuration(instance_attributes),
            self._build_autoscale_launch_configuration(instance_attributes),
        )

        self.send_sns_message(
            "Generating an AMI for %s" % self.application
        )
        ami_id = instance.create_image(no_reboot=no_reboot)
        print "New AMI %s from instance %s" % (ami_id, instance.instance_id)

        self.send_sns_message(
            "Finished AMI generation for %s. AMI id: %s" % (self.application, ami_id)
        )

        self.setup_autoscale(ami_id)

    def _build_application_configuration(self):
        return {
            "autoscale_group": self.application.upper(),
            "scaling_policies": [],
            "deployment_strategy": self.name,
            "deploy": {
                "working_directory": os.getcwd(),
                "command": "<add your deployment command here>",
            }
        }

    def _build_autoscale_group_configuration(self, instance_attributes):
        return {
            self.application.upper(): {
                "availability_zones": [instance_attributes['availability_zone']],
                "max_size": 3,
                "min_size": 1,
                "load_balancers": instance_attributes['load_balancers'],
                "termination_policies": [
                    "ClosestToNextInstanceHour",
                    "OldestInstance"
                ],
                "health_check_period": 60,
                "health_check_type": "ELB" if instance_attributes['load_balancers'] else "EC2"
            }
        }

    def _build_autoscale_launch_configuration(self, instance_attributes):
        return {
            self.application.upper(): {
                "security_groups": instance_attributes['security_groups'],
                "instance_type": instance_attributes['instance_type'],
                "key_name": instance_attributes['key_name'],
                "instance_monitoring": instance_attributes['instance_monitoring'],
                "kernel_id": instance_attributes['kernel_id'],
                "ramdisk_id": instance_attributes['ramdisk_id'],
                "ebs_optimized": instance_attributes['ebs_optimized'],
            }
        }
