#!/usr/bin/env python
"""Forseti is a tool to manage AWS autoscaling groups by using golden AMIs.

Usage:
    forseti.py deploy <app> [--ami=<ami-id>] [-- <args>...]
    forseti.py status <app> [--daemon] [--activities=<amount>] [--format=<format>]
    forseti.py maintenance <app> (on|off)
    forseti.py (-h | --help)
    forseti.py --version

Options:
    --ami=<ami-id>        AMI id to be used instead of creating a golden one.
    --daemon              Keep running and updating the status
    --activities=<amount> Number of latest activities to show
    --format=<format>     How to format the status.
                          Available values are: plain, json, tree (default)
    -h --help             Show this screen.
    --version             Show version.
    -- <args>...          Extra parameters to be passed to the deploy command
"""

import json
from docopt import docopt
from forseti.configuration_reader import ForsetiConfiguration
from forseti.deployers import (
    DeployAndSnapshotDeployer,
    GoldenInstanceDeployer,
)
from forseti.commands import MaintenanceCommand
from forseti.exceptions import ForsetiConfigurationException
from forseti.readers import DefaultReader
import os.path


def get_deployer(configuration, application, extra_args=None):
    application_configuration = configuration.get_application_configuration(application)
    if not 'deployment_strategy' in application_configuration:
        raise ForsetiConfigurationException(
            'Missing `deployment_strategy` in application configuration'
        )
    strategy = application_configuration['deployment_strategy']
    extra_args = extra_args or []
    extra_args = ' '.join(extra_args)
    if strategy == 'deploy_and_snapshot':
        return DeployAndSnapshotDeployer(configuration, extra_args)
    if strategy == 'golden_instances':
        return GoldenInstanceDeployer(configuration, extra_args)

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
            configuration,
            arguments['<app>'],
            arguments['<args>']
        )
        deployer.deploy(arguments['<app>'], ami_id=arguments['--ami'])
    elif arguments['status']:
        format = arguments['--format']
        reader = DefaultReader(configuration, format=format)
        daemon = arguments['--daemon']
        activities = arguments['--activities']
        reader.status(arguments['<app>'], daemon=daemon, activities=activities)
    elif arguments['maintenance']:
        maintenance = MaintenanceCommand(configuration, arguments['<app>'])
        if arguments['on']:
            maintenance.on()
        else:
            maintenance.off()


if __name__ == '__main__':
    main()
