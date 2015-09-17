import click
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.scraper import Licenses, Version


@click.command('status', short_help='Shows file changes.')
@pass_context
def cli(ctx):
    """Create a new IPS application installation."""
    assert isinstance(ctx, Context)
    login_session = ctx.get_login()

    # Prompt for our desired license
    licenses = Licenses(login_session).get()
    opt = ctx.choice([
        (key, '{u} ({k})'.format(u=license.community_url, k=license.license_key))
        for key, license in enumerate(licenses)
    ], 1, 'Which license key would you like to use?')
    license = licenses[opt]

    version = Version(ctx, login_session, license).get()
    version.download()

