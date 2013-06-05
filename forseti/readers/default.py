import time
from blessings import Terminal
from forseti.config import ForsetiConfiguration
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

    def __init__(self, aws_properties, *args, **kwargs):
        self.configuration = ForsetiConfiguration(aws_properties)
        self.term = Terminal()
        format = kwargs['format'] or 'tree'
        self.formatter = self.get_formatter(format)

    def get_formatter(self, format):
        if format == 'tree':
            return TreeFormatter()
        if format == 'json':
            return JsonFormatter()
        if format == 'plain':
            return DefaultFormatter()
        raise ForsetiException("Unkwon format %s" % format)

    def _update_status(self, group, max_activities):
        status = group.status()
        status['Activities'] = status['Activities'][:max_activities]
        return status

    def _print_status(self, group, max_activities):
        print self.formatter.display(self._update_status(group, max_activities))
        print self.term.bright_white(datetime.today().strftime("%Y-%m-%d %H:%M:%S"))

    def status(self, application, *args, **kwargs):
        """
        Print the current status of the autoscale group of an application.
        """
        daemon = kwargs['daemon'] or False
        max_activities = kwargs['activities'] or 3
        max_activities = int(max_activities)
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
