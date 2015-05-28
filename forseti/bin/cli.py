#!/usr/bin/env python
"""Forseti is a tool to manage AWS autoscaling groups.

Usage:
    {% for doc in commands_documentation -%}
    forseti {{ doc }}
    {% endfor -%}
    forseti (-h | --help)
    forseti --version

Options:
    {% for doc in options_documentation -%}
    {{ doc }}
    {% endfor -%}
    -h --help             Show this screen.
    --version             Show version.
"""

import sys
from docopt import docopt
from forseti import __version__ as forseti_version
from forseti.configuration import ForsetiConfiguration
from forseti.deployers import (
    DeployAndSnapshotDeployer,
    GoldenInstanceDeployer,
)
from forseti.commands.base import get_all_commands
from forseti.exceptions import ForsetiConfigurationException
from jinja2 import Template
import os.path


def get_configuration_file_path():
    return os.path.abspath(os.path.expanduser('~/.forseti/config.json'))


def read_configuration_file():
    config_path = get_configuration_file_path()
    if not os.path.exists(config_path):
        raise ValueError("Configuration file does not exist at %r" % config_path)

    try:
        return ForsetiConfiguration(config_path)
    except ValueError as exception:
        print "Invalid JSON configuration file %s\n" % config_path
        raise exception


def generate_dosctring():
    commands_documentation = []
    options_documentation = []

    commands = get_all_commands()
    for command_class in commands:
        command = command_class()
        command_doc = command.cli_command_doc()
        if command_doc:
            commands_documentation.append(command_doc)
        comand_options_docs = command.cli_command_options_doc()
        if comand_options_docs:
            options_documentation.append(comand_options_docs)

    return Template(__doc__).render(
        commands_documentation=commands_documentation,
        options_documentation=options_documentation,
        app_name=sys.argv[0]
    )


def commands_arguments_mapper():
    mapper = []
    commands = get_all_commands()
    for command_class in commands:
        command = command_class()
        mapper.append(
            (command.cli_command_name(), command)
        )

    return mapper


def main():
    arguments = docopt(generate_dosctring())
    if arguments['--version']:
        print "Forseti %s" % forseti_version
        return

    configuration = read_configuration_file()

    for cli_command, forseti_command in commands_arguments_mapper():
        if arguments[cli_command]:
            forseti_command.run(configuration, arguments)


if __name__ == '__main__':
    main()
