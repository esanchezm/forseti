from contextlib import contextmanager
import json
from pprint import pformat
import progressbar


class Balloon(progressbar.ProgressBar):
    def __init__(self, message="Waiting", **kwargs):
        widgets = [
            "%s " % message,
            progressbar.AnimatedMarker(markers='.oO@* '),
            progressbar.Timer(format=" %s")
        ]
        super(Balloon, self).__init__(widgets=widgets, maxval=600, **kwargs)
        self.start()


@contextmanager
def balloon_timer(message, **kwargs):
    """
    Context manager which yields a `Balloon` object.

    The balloon object yielded must be updated from outside so the progress bar
    keeps working:

    ```
    with balloon_timer("Testing") as baloon:
        time_elapsed = do_something()
        baloon.update(time_elapsed)
    ```
    """
    balloon = Balloon(message, **kwargs)
    yield balloon
    balloon.finish()


class DefaultFormatter():
    """
    Class to display a variable beautifully
    """

    def display(self, content):
        return pformat(content)


class JsonFormatter():
    """
    Class to display a variable beautifully using a JSON formatter
    """

    def display(self, content):
        return json.dumps(content, sort_keys=False, indent=4, separators=(',', ': '))


class TreeFormatter():
    """
    Class to display a variable beautifully using a tree format.
    Suppose a dictionary:
    `
    {
        'Name' : 'Example',
        'Instances': [{'Status': 'OK', 'Id': '1234'}, {'Status': 'OK', 'Id': '1234'}]
    }
    `
    Will be displayed like this:
    `
    Instances:
        Status: OK
        Id: 1234

        Status: OK
        Id: 1234

    Name: Example

    `
    """

    def _render_dict(self, content, indent=0):
        """
        Returns a dictionary rendered in a tree mode.
        """
        result = ''
        indenting = '    ' * indent
        for key, value in content.iteritems():
            result += "{0}{1}: {2}\n".format(
                indenting,
                str(key),
                self.display(value, indent=indent+1)
            )
        return result

    def _render_list(self, content, indent=0):
        """
        Returns a list rendered in a tree mode.
        """
        result = '[{0}]'.format(len(content))
        for value in content:
            result += "\n"+self.display(value, indent=indent+1)
        return result

    def display(self, content, indent=0):
        if isinstance(content, dict):
            return self._render_dict(content, indent)
        elif isinstance(content, list):
            return self._render_list(content, indent)
        return str(content)
