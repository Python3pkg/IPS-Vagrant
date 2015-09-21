import sys
import termios
import progressbar
from array import array
from fcntl import ioctl


class ProgressBar(progressbar.ProgressBar):

    _DEFAULT_MAXTERMSIZE = 100

    def __init__(self, maxval=None, label=None, max_term_width=None, fd=sys.stderr):
        self.max_term_width = max_term_width
        self.label = label
        self.max_term_width = max_term_width or self._DEFAULT_MAXTERMSIZE
        widgets = [Label(self.label), progressbar.Bar('#', '[', ']'), ' [', progressbar.Percentage(), '] ']
        super(ProgressBar, self).__init__(maxval, widgets, fd=fd)

    def _handle_resize(self, signum=None, frame=None):
        """
        Tries to catch resize signals sent from the terminal.
        """
        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = min([w, self.max_term_width])


class Label(progressbar.Widget):
    """
    Displays the current percentage as a number with a percent sign.
    """
    def __init__(self, label=None):
        self._formatted = ''
        self._label = label
        self.label = label

    def update(self, pbar):
        if pbar.label != self._label:
            self.label = pbar.label

        return self.label

    @property
    def label(self):
        if not self._label:
            return ''

        return self._formatted

    @label.setter
    def label(self, value):
        # Fixed width label formatting
        value = value[:30]
        try:
            padding = ' ' * (len(value) - 30)
        except TypeError:
            padding = ''

        self._formatted = ' {v}{p} '.format(v=value, p=padding)
