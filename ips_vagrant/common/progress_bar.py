import sys
import termios
import progressbar
from array import array
from fcntl import ioctl


class ProgressBar(progressbar.ProgressBar):
    """
    ProgressBar decorator implementing custom widgets and max term width support
    """
    _DEFAULT_MAXTERMSIZE = 100

    def __init__(self, maxval=None, label=None, max_term_width=None, fd=sys.stderr):
        """
        Initialize a new ProgressBar instance
        @param  maxval:         The maximum progress bar value
        @type   maxval:         str or None
        @param  label:          The progress label (or None to disable the label)
        @type   label:          str or None
        @param  max_term_width: Maximum terminal width allowed, or None for no restriction
        @type   max_term_width: int or None
        @param  fd:             Output stream
        """
        self.max_term_width = max_term_width
        self.label = label
        self.max_term_width = max_term_width or self._DEFAULT_MAXTERMSIZE
        widgets = [Label(self.label), progressbar.Bar('#', '[', ']'), ' [', progressbar.Percentage(), '] ']
        super(ProgressBar, self).__init__(maxval, widgets, fd=fd)

    def _handle_resize(self, signum=None, frame=None):
        """
        Tries to catch resize signals sent from the terminal
        """
        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = min([w, self.max_term_width])

    def update(self, value=None, label=None):
        """
        Update the progress bar
        @type   value:  int
        @type   label:  str
        """
        if label:
            self.label = label

        super(ProgressBar, self).update(value)


class Label(progressbar.Widget):
    """
    Static width dynamic progress label
    """
    def __init__(self, label=None):
        """
        @param  label:  The starting label
        @type   label:  str or None
        """
        self._formatted = ''
        self._label = label
        self.label = label

    def update(self, pbar):
        """
        Handle progress bar updates
        @type   pbar:   ProgressBar
        @rtype: str
        """
        if pbar.label != self._label:
            self.label = pbar.label

        return self.label

    @property
    def label(self):
        """
        Get the formatted label
        @rtype: str
        """
        if not self._label:
            return ''

        return self._formatted

    @label.setter
    def label(self, value):
        """
        Set the label and generate the formatted value
        @type   value:  str
        """
        # Fixed width label formatting
        value = value[:30]
        try:
            padding = ' ' * (30 - len(value))
        except TypeError:
            padding = ''

        self._formatted = ' {v}{p} '.format(v=value, p=padding)