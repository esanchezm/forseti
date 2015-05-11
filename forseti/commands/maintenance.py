import os

from forseti.models import EC2AutoScaleGroup, EC2Instance
from forseti.exceptions import ForsetiDeployException


class MaintenanceCommand(object):
    def __init__(self, configuration, application):
        self.configuration = configuration
        self.application = application
        self.application_configuration = self.configuration.get_application_configuration(
            self.application
        )

    def _running_instances_dns_names(self):
        autoscale_group_name = self.configuration.get_autoscale_group(self.application)
        autoscale_group = EC2AutoScaleGroup(autoscale_group_name, self.application)
        return autoscale_group.get_instances_dns_names_with_status('running')

    def _run_cap_command(self, command_name):
        """
        Moves into working_directory specified in `application` deploy configuration
        and runs a capistrano command from there, goes back to previous directory and returns command's retvalue
        """
        running_instances_dns_names = self._running_instances_dns_names()
        command = self.application_configuration[command_name]['command'].format(
            dns_name=','.join(running_instances_dns_names)
        )

        former_directory = os.getcwd()
        os.chdir(self.application_configuration[command_name]['working_directory'])
        retvalue = os.system(command)
        os.chdir(former_directory)
        return retvalue

    def on(self):
        try:
            autoscale_group.suspend_processes()
            retvalue = self._run_cap_command('maintenance_on')
            if retvalue != 0:
                raise ForsetiDeployException(
                    'maintenance on command did not return 0 as expected, returned: %s' % retvalue
                )
        except Exception as e:
            autoscale_group.resume_processes()
            raise e

    def off(self):
        try:
            autoscale_group.resume_processes()
            retvalue = self._run_cap_command('maintenance_off')
            if retvalue != 0:
                raise ForsetiDeployException(
                    'maintenance off command did not return 0 as expected, returned: %s' % retvalue
                )
        except Exception as e:
            raise e
