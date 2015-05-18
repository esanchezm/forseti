#!/usr/bin/env python
"""Forseti is a tool to manage AWS autoscaling groups.

Usage:
    forseti.py deploy <app> [--ami=<ami-id>] [-- <args>...]
    forseti.py status <app> [--daemon] [--activities=<amount>] [--format=<format>]
    forseti.py list_configurations [<app>]
    forseti.py cleanup_configurations [<app>] [--desired_configurations=<desired>]
    forseti.py regenerate <app>
    forseti.py maintenance <app> (on|off)
    forseti.py (-h | --help)
    forseti.py --version

Options:
    --ami=<ami-id>        AMI id to be used instead of creating a golden one.
    --daemon              Keep running and updating the status
    --activities=<amount> Number of latest activities to show
    --desired_configurations=<desired> Number of launch configurations you
                          want to leave when doing a cleanup [default: 4]
    --format=<format>     How to format the status.
                          Available values are: plain, json, tree (default)
    -h --help             Show this screen.
    --version             Show version.
    -- <args>...          Extra parameters to be passed to the deploy command
"""

import json
from docopt import docopt
from forseti import __version__ as forseti_version
from forseti.configuration import ForsetiConfiguration
from forseti.deployers import (
    DeployAndSnapshotDeployer,
    GoldenInstanceDeployer,
)
from forseti.commands import MaintenanceCommand
from forseti.exceptions import ForsetiConfigurationException
from forseti.readers import DefaultReader
import os.path


def get_deployer(application, configuration, extra_args=None):
    application_configuration = configuration.get_application_configuration(application)
    if configuration.DEPLOYMENT_STRATEGY not in application_configuration:
        raise ForsetiConfigurationException(
            'Missing %s in application configuration' %
            configuration.DEPLOYMENT_STRATEGY
        )
    strategy = application_configuration[configuration.DEPLOYMENT_STRATEGY]
    extra_args = extra_args or []
    extra_args = ' '.join(extra_args)

    return get_deployer_from_strategy(
        strategy,
        application,
        configuration,
        extra_args=None
    )


def get_deployer_from_strategy(strategy, application, configuration, extra_args=None):
    if strategy == 'deploy_and_snapshot':
        return DeployAndSnapshotDeployer(application, configuration, extra_args)
    if strategy == 'golden_instances':
        return GoldenInstanceDeployer(application, configuration, extra_args)

    raise ForsetiConfigurationException(
        'Unknown deployment strategy \'%s\' in application configuration' % strategy
    )


def main():
    arguments = docopt(__doc__)

    config_path = os.path.abspath(os.path.expanduser('~/.forseti/config.json'))
    if not os.path.exists(config_path):
        raise ValueError("Configuration file does not exist at %r" % config_path)

    try:
        configuration = ForsetiConfiguration(json.load(open(config_path)))
    except ValueError as exception:
        print "Invalid JSON configuration file %s\n" % config_path
        raise exception

    if arguments['deploy']:
        deployer = get_deployer(
            arguments['<app>'],
            configuration,
            arguments['<args>']
        )
        deployer.deploy(arguments['--ami'])
    elif arguments['status']:
        format = arguments['--format']
        reader = DefaultReader(configuration, format=format)
        daemon = arguments['--daemon']
        activities = arguments['--activities']
        reader.status(arguments['<app>'], daemon=daemon, activities=activities)
    elif arguments['list_configurations']:
        if arguments['<app>']:
            applications = [arguments['<app>']]
        else:
            applications = configuration.applications.keys()

        for application in applications:
            print "\nApplication: %s" % application
            print "============="
            deployer = get_deployer(
                application,
                configuration,
            )
            deployer.list_autoscale_configurations()
    elif arguments['cleanup_configurations']:
        if arguments['<app>']:
            applications = [arguments['<app>']]
        else:
            applications = configuration.applications.keys()

        for application in applications:
            print "\nApplication: %s" % application
            print "============="
            deployer = get_deployer(
                application,
                configuration,
            )
            deployer.cleanup_autoscale_configurations(
                int(arguments['--desired_configurations'])
            )
    elif arguments['regenerate']:
        deployer = get_deployer(
            arguments['<app>'],
            configuration,
        )
        deployer.regenerate()
    elif arguments['maintenance']:
        maintenance = MaintenanceCommand(configuration, arguments['<app>'])
        if arguments['on']:
            maintenance.on()
        else:
            maintenance.off()
    elif arguments['--version']:
        print "Forseti %s" % forseti_version


if __name__ == '__main__':
    main()
