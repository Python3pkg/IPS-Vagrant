import os
import sys
import click
import logging
from ConfigParser import ConfigParser
from ips_vagrant.scraper import Login

CONTEXT_SETTINGS = dict(auto_envvar_prefix='IPSV', max_content_width=120)


class Context(object):
    """
    CLI Context
    """
    def __init__(self):
        self.cookiejar = None
        self.config = None
        self.config_path = None
        self.log = None
        self.license = None
        self.cache = None
        self.basedir = os.path.join(os.path.dirname(os.path.realpath(__file__)))
        self._load_config()

        self._login = Login(self)

    def _load_config(self):
        self.config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'config', 'ipsv.conf')
        self.config = ConfigParser()
        self.config.read(self.config_path)

    def get_login(self, use_session=True):
        # Should we try and return an existing login session?
        if use_session and self._login.check():
            self.cookiejar = self._login.cookiejar
            return self.cookiejar

        # Prompt the user for their login credentials
        username = click.prompt('Username')
        password = click.prompt('Password', hide_input=True)
        remember = click.confirm('Save login session?', True)

        # Process the login
        cookiejar = self._login.process(username, password, remember)
        if remember:
            self.cookiejar = cookiejar

        return cookiejar

    def choice(self, opts, default=1, text='Please make a choice'):
        opts_len = len(opts)
        opts_enum = enumerate(opts, 1)
        opts = list(opts)

        for key, opt in opts_enum:
            click.echo('[{k}] {o}'.format(k=key, o=opt[1] if isinstance(opt, tuple) else opt))

        click.echo('-' * 12)
        opt = click.prompt(text, default, type=click.IntRange(1, opts_len))
        opt = opts[opt - 1]
        return opt[0] if isinstance(opt, tuple) else opt


# noinspection PyAbstractClass
class IpsvCLI(click.MultiCommand):
    """
    IPS Vagrant Commandline Interface
    """
    def list_commands(self, ctx):
        """
        List CLI commands
        @type   ctx:    Context
        @rtype: list
        """
        rv = []
        for filename in os.listdir(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'commands')):
            if filename.endswith('.py') and filename.startswith('cmd_'):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        """
        Get a bound command method
        @type   ctx:    Context
        @param  name:   Command name
        @type   name:   str

        @rtype: object
        """
        try:
            name = name.encode('ascii', 'replace')
            mod = __import__('ips_vagrant.commands.cmd_' + name,
                             None, None, ['cli'])
        except ImportError:
            return
        return mod.cli


pass_context = click.make_pass_decorator(Context, ensure=True)


@click.command(cls=IpsvCLI, context_settings=CONTEXT_SETTINGS)
@click.option('-v', '--verbose', count=True, help='-v|vv|vvv Increase the verbosity of messages: 1 for normal output, '
                                                  '2 for more verbose output and 3 for debug')
@click.option('--license', envvar='LICENSE', help='License key to use for requests')
@click.option('--cache/--no-cache', default=True, help='Use cached version downloads if possible (Default: True)')
@pass_context
def cli(ctx, verbose, license, cache):
    """
    IPS Vagrant Management Utility
    """
    # Set up the logger
    verbose = verbose if (verbose <= 3) else 3
    log_levels = {1: logging.WARN, 2: logging.INFO, 3: logging.DEBUG}
    log_level = log_levels[verbose]

    ctx.license = license
    ctx.cache = cache

    ctx.log = logging.getLogger('ipsv')
    ctx.log.setLevel(log_level)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    ctx.log.addHandler(ch)
