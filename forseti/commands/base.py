import inspect
import importlib


from abc import ABCMeta, abstractmethod
from six import add_metaclass


@add_metaclass(ABCMeta)
class BaseForsetiCommand(object):
    @abstractmethod
    def run(self, configuration, cli_arguments):
        raise NotImplementedError

    @abstractmethod
    def cli_command_name(self):
        raise NotImplementedError

    @abstractmethod
    def cli_command_doc(self):
        raise NotImplementedError

    @abstractmethod
    def cli_command_options_doc(self):
        raise NotImplementedError


def get_all_commands():
    module = importlib.import_module("forseti.commands.commands")
    commands = []
    for _, obj in inspect.getmembers(module):
        if (
            inspect.isclass(obj) and
            issubclass(obj, BaseForsetiCommand) and
            not inspect.isabstract(obj)
        ):
            commands.append(obj)

    return commands
