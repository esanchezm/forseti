#!/usr/bin/env python
"""Forseti is a tool to manage AWS autoscaling groups by using golden AMIs.

Usage:
    forseti.py deploy <app>
    forseti.py (-h | --help)
    forseti.py --version

Options:
    -h --help     Show this screen.
    --version     Show version.
"""

import json
import sys
from docopt import docopt
from forseti.deployers import TicketeaDeployer
import os.path


def main():
    arguments = docopt(__doc__)

    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forseti.json')
    try:
        configuration = json.load(open(filepath))
    except ValueError as exception:
        print "Invalid configuration file %s\n" % filepath
        print exception
        sys.exit()

    deployer = TicketeaDeployer(configuration)

    if arguments['deploy']:
        deployer.deploy(arguments['<app>'])


if __name__ == '__main__':
    main()
