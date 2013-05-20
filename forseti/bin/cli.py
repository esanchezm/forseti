#!/usr/bin/env python
"""Forseti is a tool to manage AWS autoscaling groups by using golden AMIs.

Usage:
    forseti.py deploy <app> [--ami=<ami-id>]
    forseti.py (-h | --help)
    forseti.py --version

Options:
    --ami=<ami-id> AMI id to be used instead of creating a golden one.
    -h --help      Show this screen.
    --version      Show version.
"""

import json
import sys
from docopt import docopt
from forseti.deployers import TicketeaDeployer
import os.path


def main():
    arguments = docopt(__doc__)

    config_path = os.path.abspath(os.path.expanduser('~/.forseti/config.json'))
    if not os.path.exists(config_path):
        raise ValueError("Configuration file does not exist at %r" % config_path)

    try:
        configuration = json.load(open(config_path))
    except ValueError as exception:
        print "Invalid JSON configuration file %s\n" % config_path
        raise exception

    deployer = TicketeaDeployer(configuration)
    if arguments['deploy']:
        deployer.deploy(arguments['<app>'], ami_id=arguments['--ami'])


if __name__ == '__main__':
    main()
