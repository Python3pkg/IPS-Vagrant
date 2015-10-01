# coding=utf-8
import os
import sys
import termios
import click
import progressbar
from array import array
from fcntl import ioctl

_DEFAULT_MAXTERMSIZE = 80


class ProgressBar(progressbar.ProgressBar):
    """
    ProgressBar decorator implementing custom widgets and max term width support
    """
    def __init__(self, maxval=None, label=None, max_term_width=None, fd=sys.stderr):
        """
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
        self.max_term_width = max_term_width or _DEFAULT_MAXTERMSIZE
        widgets = [Label(self.label), progressbar.Bar('#', '[', ']'), ' [', Percentage(), ']']
        super(ProgressBar, self).__init__(maxval, widgets, fd=fd)

    def _format_line(self):
        """
        Joins the widgets and justifies the line
        """
        line = super(ProgressBar, self)._format_line()
        return '\033[1m\033[33m' + line + '\033[0m'

    def _handle_resize(self, signum=None, frame=None):
        """
        Tries to catch resize signals sent from the terminal
        """
        h, w = array('h', ioctl(self.fd, termios.TIOCGWINSZ, '\0' * 8))[:2]
        self.term_width = min([w, self.max_term_width])

    def start(self):
        """
        Hide cursor at start
        """
        os.system('setterm -cursor off')
        super(ProgressBar, self).start()

    def update(self, value=None, label=None):
        """
        Update the progress bar
        @type   value:  int
        @type   label:  str
        """
        if label:
            self.label = label

        super(ProgressBar, self).update(value)

    def finish(self):
        """
        Re-enable cursor on finish
        """
        os.system('setterm -cursor on')
        super(ProgressBar, self).finish()


class Label(progressbar.Widget):
    """
    Static width dynamic progress label
    """
    def __init__(self, label=None, pad_size=30):
        """
        @param  label:      The starting label
        @type   label:      str or None
        @type   pad_size:   int or None
        """
        self._formatted = ''
        self._label = label
        self.pad_size = pad_size
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
        @type   value:      str
        """
        # Fixed width label formatting
        value = value[:self.pad_size] if self.pad_size else value
        try:
            padding = ' ' * (self.pad_size - len(value)) if self.pad_size else ''
        except TypeError:
            padding = ''

        self._formatted = ' {v}{p} '.format(v=value, p=padding)


class Percentage(progressbar.Widget):
    """
    Displays the current percentage as a number with a percent sign.
    @type   pbar:   ProgressBar
    @rtype: str
    """
    def update(self, pbar):
        if pbar.finished:
            return Echo.OK

        return '%3d%%' % pbar.percentage()


class MarkerProgressBar(ProgressBar):
    """
    ProgressBar marker (for when the end count requirement is not known)
    """
    def __init__(self, label, nl=True):
        """
        @param  label:  The progress label
        @type   label:  str
        @param  nl:     Automatically generate a success message with a newline on finish
        @type   nl:     bool
        """
        super(MarkerProgressBar, self).__init__(None, label, None)
        self.nl = nl
        # self.widgets = [Label(self.label, None), progressbar.AnimatedMarker(markers='.oO@* ')]
        self.widgets = [Label(self.label, None), progressbar.AnimatedMarker(markers='←↖↑↗→↘↓↙'.decode('utf8'))]

    def finish(self):
        """
        Update widgets on finish
        """
        os.system('setterm -cursor on')
        if self.nl:
            Echo(self.label).done()


class Echo:
    """
    Echo wrapper, prints a message for a pending task, then automatically reformats it when the task is complete
    """
    OK   = ' OK '
    WARN = 'WARN'
    FAIL = click.style('FAIL', 'red', bold=True)

    def __init__(self, message, color='yellow', bold=True, max_term_width=None):
        """
        @type   message:        str
        @type   color:          str
        @type   bold:           bool
        @type   max_term_width: int or None
        """
        self.max_term_width = max_term_width or _DEFAULT_MAXTERMSIZE
        self.message = ' {msg} '.format(msg=message.strip())
        self.message = self.message[:self.max_term_width - 7]
        self.color = color
        self.bold = bold

        click.secho(self.message, nl=False, fg=color, bold=bold)

    def done(self, status=OK):
        """
        @type   status: str
        """
        padding = ' ' * ((self.max_term_width - 6) - len(self.message))
        suffix = click.style(']', fg=self.color, bold=self.bold)
        message = '{msg}{pad}[{status}{suf}'.format(msg=self.message, pad=padding, status=status, suf=suffix)
        stdout = click.get_text_stream('stdout')
        stdout.write('\r\033[K')
        stdout.flush()
        click.secho(message, fg=self.color, bold=self.bold)
