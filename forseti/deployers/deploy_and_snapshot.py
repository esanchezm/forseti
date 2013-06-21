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

    def __init__(self, configuration):
        super(DeployAndSnapshotDeployer, self).__init__(configuration)
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

    def deploy(self, application, ami_id=None):
        """
        Do the code deployment by pushing the code in all instances and create
        an AMI from an.
        """
        balloon = Balloon("")
        group = self._get_group(application)
        if not ami_id:
            # We must suspend autoscaling processes to avoid adding instances with
            # outdated code
            group.suspend_processes()
            try:
                instances = self.deploy_instances_in_group(application, group)
            except ForsetiException as exception:
                group.resume_processes()
                raise exception

            # Select a random instance and create an AMI from it
            instance = choice(instances)
            try:
                ami_id = instance.create_image()
            except Exception as exception:
                group.resume_processes()
                raise exception

            print "New AMI %s from instance %s" % (ami_id, instance.instance_id)

        try:
            self.setup_autoscale(application, ami_id)
        except Exception as exception:
            group.resume_processes()
            raise exception
        group.resume_processes()

        balloon.finish()
        minutes, seconds = divmod(int(balloon.seconds_elapsed), 60)
        print "Total deployment time: %02d:%02d" % (minutes, seconds)