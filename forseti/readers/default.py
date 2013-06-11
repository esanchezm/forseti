import time
from blessings import Terminal
from forseti.configuration_reader import ForsetiConfiguration
from forseti.exceptions import ForsetiException
from forseti.models import EC2AutoScaleGroup
from forseti.utils import (
    DefaultFormatter,
    JsonFormatter,
    TreeFormatter
)
from datetime import datetime


class DefaultReader(object):
    """Deployer for ticketea's infrastructure"""

    # FIXME: These values could be defined in forseti models
    COLORED_VALUES = {
        'OutOfService': 'red',
        'InService': 'green',
        'Healthy': 'green',
        'UnHealthy': 'red',
        'Terminating': 'yellow',
    }

    def __init__(self, aws_properties, *args, **kwargs):
        self.configuration = ForsetiConfiguration(aws_properties)
        self.term = Terminal()
        format = kwargs['format'] or 'tree'
        self.formatter = self.get_formatter(format)

    def get_formatter(self, format):
        """
        Get the formatter object based on a format string.
        'tree' will return a `TreeFormatter`
        'json' will return a `JsonFormatter`
        'plain' will return a `DefaultFormatter`
        Any other value will raise a `ForsetiException`
        """
        if format == 'tree':
            return TreeFormatter()
        if format == 'json':
            return JsonFormatter()
        if format == 'plain':
            return DefaultFormatter()
        raise ForsetiException("Unknown format %s" % format)

    def _color_value(self, value):
        """
        Add color to a value of a autoscale group status dictionary. If
        the value is defined in `COLORED_VALUES` then the color is added.
        """
        if value in self.COLORED_VALUES.keys():
            color = self.COLORED_VALUES[value]
            return getattr(self.term, color) + value + self.term.normal
        return value

    def _color_dictionary_list(self, array):
        """
        Add color to a list of dictionaries. Each key is coloured in blue
        and each value is colored using `_color_value`
        """
        coloured_list = []
        for content in array:
            coloured_content = {}
            for key, value in content.iteritems():
                key = '{t.blue}{0}{t.normal}'.format(key, t=self.term)
                coloured_content[key] = self._color_value(value)
            coloured_list.append(coloured_content)

        return coloured_list

    def _color_status(self, status):
        """
        Color the autoscale group `status` by setting a blue color to the
        keys and calling `_color_value` on each value. A new dictionary is
        returned.
        """
        coloured_status = {}
        for key, value in status.iteritems():
            if isinstance(value, list):
                value = self._color_dictionary_list(value)
            key = '{t.blue}{0}{t.normal}'.format(key, t=self.term)
            coloured_status[key] = self._color_value(value)
        return coloured_status

    def _get_updated_status(self, group, max_activities):
        """
        Updates the autoscale group status and limit the activities to
        `max_activities`
        """
        status = group.status()
        status['Activities'] = status['Activities'][:max_activities]
        return status

    def _print_status(self, group, max_activities, color=True):
        """
        Print the status and the current date.
        If `color` is `True` the output will be coloured by
        `_color_status`
        """
        status = self._get_updated_status(group, max_activities)
        if color:
            status = self._color_status(status)
        print self.formatter.display(status)
        print self.term.bright_white(datetime.today().strftime("%Y-%m-%d %H:%M:%S"))

    def status(self, application, daemon=False, activities=3, *args, **kwargs):
        """
        Print the current status of the autoscale group of an application.
        """
        # activities can be read from args and must be converted.
        max_activities = int(activities) if activities else 3
        group = EC2AutoScaleGroup(
            self.configuration.get_autoscale_group(application),
            application,
            self.configuration.get_autoscale_group_configuration(application)
        )

        if not daemon:
            return self._print_status(group, max_activities)

        # Daemon case will print the status in a fullscreen terminal forever
        running = True
        while running:
            try:
                with self.term.fullscreen():
                    self._print_status(group, max_activities)
                    time.sleep(1)
            except (KeyboardInterrupt, SystemExit):
                running = False
            finally:
                self.term.exit_fullscreen()
