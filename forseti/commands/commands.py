import os

from .base import BaseForsetiCommand
from forseti.deployers import (
    DeployAndSnapshotDeployer,
    GoldenInstanceDeployer,
)
from forseti.exceptions import ForsetiDeployException, ForsetiConfigurationException
from forseti.models import EC2AutoScaleGroup
from forseti.readers import DefaultReader


class BaseDeployCommand(BaseForsetiCommand):
    def _get_deployer(self, application, configuration, extra_args=None):
        application_configuration = configuration.get_application_configuration(application)
        if configuration.DEPLOYMENT_STRATEGY not in application_configuration:
            raise ForsetiConfigurationException(
                'Missing %s in application configuration' %
                configuration.DEPLOYMENT_STRATEGY
            )
        strategy = application_configuration[configuration.DEPLOYMENT_STRATEGY]
        extra_args = extra_args or []
        extra_args = ' '.join(extra_args)

        return self._get_deployer_from_strategy(
            strategy,
            application,
            configuration,
            extra_args
        )

    def _get_deployer_from_strategy(
        self, strategy, application, configuration, extra_args=None
    ):
        if strategy == 'deploy_and_snapshot':
            return DeployAndSnapshotDeployer(
                application,
                configuration,
                extra_args
            )
        elif strategy == 'golden_instances':
            return GoldenInstanceDeployer(
                application,
                configuration,
                extra_args
            )

        raise ForsetiConfigurationException(
            'Unknown deployment strategy \'%s\' in application configuration' %
            strategy
        )


class DeployCommand(BaseDeployCommand):
    def cli_command_name(self):
        return "deploy"

    def cli_command_doc(self):
        return ("%s <app> [--ami=<ami-id>] "
                "[-- <args>...]" % self.cli_command_name())

    def cli_command_options_doc(self):
        return ("--ami=<ami-id>        AMI id to be used "
                "instead of creating a golden one.")

    def run(self, configuration, cli_arguments):
        deployer = self._get_deployer(
            cli_arguments['<app>'],
            configuration,
            cli_arguments['<args>']
        )
        deployer.deploy(cli_arguments['--ami'])


class InitCommand(BaseDeployCommand):
    def cli_command_name(self):
        return "init"

    def cli_command_doc(self):
        return ("%s <app> <instance-id> "
                "--deployer=deploy_and_snapshot|golden_instances "
                "[--no-reboot-instance]" %
                self.cli_command_name())

    def cli_command_options_doc(self):
        return """--no-reboot-instance  No reboot instance when creating AMI
    --deployer=deploy_and_snapshot|golden_instances
                          What deployer to use in the new application"""

    def run(self, configuration, cli_arguments):
        deployer = self._get_deployer_from_strategy(
            cli_arguments['--deployer'],
            cli_arguments['<app>'],
            configuration
        )

        deployer.init_application(
            cli_arguments['<instance-id>'],
            cli_arguments['--no-reboot-instance']
        )
        configuration.write()


class CleanUpAutoscaleConfigurationsCommand(BaseDeployCommand):
    def cli_command_name(self):
        return "cleanup_configurations"

    def cli_command_doc(self):
        return "%s [<app>] [--desired_configurations=<desired>]" % \
               self.cli_command_name()

    def cli_command_options_doc(self):
        return """--desired_configurations=<desired> Number of launch configurations you
                          want to leave when doing a cleanup [default: 4]"""

    def run(self, configuration, cli_arguments):
        if cli_arguments['<app>']:
            applications = [cli_arguments['<app>']]
        else:
            applications = configuration.applications.keys()

        for application in applications:
            print "\nApplication: %s" % application
            print "============="
            deployer = self._get_deployer(
                application,
                configuration,
            )
            deployer.cleanup_autoscale_configurations(
                int(cli_arguments['--desired_configurations'])
            )


class RegenerateAutoscalegroupCommand(BaseDeployCommand):
    def cli_command_name(self):
        return "regenerate"

    def cli_command_doc(self):
        return "%s <app>" % self.cli_command_name()

    def cli_command_options_doc(self):
        return None

    def run(self, configuration, cli_arguments):
        deployer = self._get_deployer(
            cli_arguments['<app>'],
            configuration,
        )
        deployer.regenerate()


class StatusCommand(BaseForsetiCommand):
    def cli_command_name(self):
        return "status"

    def cli_command_doc(self):
        return ("%s <app> [--daemon] [--activities=<amount>] "
                "[--format=<format>]" % self.cli_command_name())

    def cli_command_options_doc(self):
        return """--activities=<amount> Number of latest activities to show
    --format=<format>     How to format the status."""

    def run(self, configuration, cli_arguments):
        application = cli_arguments['<app>']
        format = cli_arguments['--format']
        reader = DefaultReader(configuration, format=format)
        daemon = cli_arguments['--daemon']
        activities = cli_arguments['--activities']
        reader.status(application, daemon=daemon, activities=activities)


class ListAutoscaleConfigurationsCommand(BaseForsetiCommand):
    def cli_command_name(self):
        return "list_configurations"

    def cli_command_doc(self):
        return "%s [<app>]" % self.cli_command_name()

    def cli_command_options_doc(self):
        return None

    def run(self, configuration, cli_arguments):
        if cli_arguments['<app>']:
            applications = [cli_arguments['<app>']]
        else:
            applications = configuration.applications.keys()

        reader = DefaultReader(configuration)
        for application in applications:
            print "\nApplication: %s" % application
            print "============="
            reader.list_autoscale_configurations(application)
