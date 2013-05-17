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
from forseti.forseti import Forseti
import os.path


if __name__ == '__main__':
    arguments = docopt(__doc__)

    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'forseti.json')
    try:
        configuration = json.load(open(filepath))
    except ValueError as exception:
        print "Invalid configuration file %s\n" % filepath
        print exception
        sys.exit()

    forseti = Forseti(configuration)

    if arguments['deploy']:
        forseti.deploy(arguments['<app>'])
