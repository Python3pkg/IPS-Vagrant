import click
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.scraper import Licenses, Version


@click.command('status', short_help='Creates a new IPS installation.')
@pass_context
def cli(ctx):
    """Creates a new installation of Invision Power Suite."""
    assert isinstance(ctx, Context)
    login_session = ctx.get_login()

    # Prompt for our desired license
    def get_license():
        licenses = Licenses(login_session).get()
        user_license = ctx.license or ctx.config.get('User', 'LicenseKey')

        if user_license:
            licenses = {license.license_key: license for license in licenses}
            if user_license in licenses:
                return licenses[user_license]

        opt = ctx.choice([
            (key, '{u} ({k})'.format(u=license.community_url, k=license.license_key))
            for key, license in enumerate(licenses)
        ], 1, 'Which license key would you like to use?')
        license = licenses[opt]

        # Should we save this license?
        if click.confirm('Would you like to save and use this license for future requests?', True):
            ctx.log.debug('Saving license key {k}'.format(k=license.license_key))
            ctx.config.set('User', 'LicenseKey', license.license_key)
            with open(ctx.config_path, 'wb') as configfile:
                ctx.config.write(configfile)

        return license

    version = Version(ctx, login_session, get_license()).get()
    filename = version.filename if version.filename and ctx.cache else version.download()
