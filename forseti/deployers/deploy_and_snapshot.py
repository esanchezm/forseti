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
from forseti.utils import Balloon


class DeployAndSnapshotDeployer(BaseDeployer):
    """Deployer for ticketea's infrastructure"""

    def __init__(self, configuration, command_args=None):
        super(DeployAndSnapshotDeployer, self).__init__(configuration, command_args)
        self.group = None

    def _get_group(self, application):
        group = EC2AutoScaleGroup(
            self.configuration.get_autoscale_group(application),
            application,
            self.configuration.get_autoscale_group_configuration(application)
        )

        return group

    def _get_instances(self, application, group):
        running_instances = group.get_instances_with_status('running')
        if not running_instances:
            return None

        instances = []
        for instance_id in running_instances:
            instance = EC2Instance(application, configuration=None, instance_id=instance_id)
            instances.append(instance)

        return instances

    def deploy_instances_in_group(self, application, group):
        """
        Deploy conde into the instances of the autoscale group. This is done
        by executing `command` from `deploy` configuration in `working_directory`.
        """
        instances = self._get_instances(application, group)
        if not instances:
            raise ForsetiException(
                'This deployer needs to have some instances running in the group'
            )

        balloon = Balloon("Deploying new code on instances")
        deploy_configuration = self.configuration.get_application_configuration(application)['deploy']
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

        balloon.finish()

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

    def deploy(self, application, ami_id=None):
        """
        Do the code deployment by pushing the code in all instances and create
        an AMI from an.
        """
        balloon = Balloon("")

        group = self._get_group(application)
        # We must suspend autoscaling processes to avoid adding instances with
        # outdated code
        group.suspend_processes()
        try:
            self.deploy_instances_in_group(application, group)
        except ForsetiException as exception:
            group.resume_processes()
            raise exception

        if not ami_id:
            ami_id = self.generate_ami()

        try:
            self.setup_autoscale(application, ami_id)
        finally:
            group.resume_processes()

        balloon.finish()
        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)

    def generate_ami(self, application):
        """
        Generate the AMI to be used in the autoscale group.
        """
        group = self._get_group(application)
        instances = self._get_instances(application, group)
        # Select a random instance and create an AMI from it
        instance = None
        try:
            instance = self.choice_instance(instances)
            group.deregister_instance_from_load_balancers([instance])
            ami_id = instance.create_image(no_reboot=False)
        except Exception as exception:
            group.resume_processes()
            raise exception
        finally:
            if instance:
                group.register_instance_in_load_balancers([instance], wait=False)

        print "New AMI %s from instance %s" % (ami_id, instance.instance_id)

        return ami_id
