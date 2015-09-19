import os
import re
import click
import logging
from urlparse import urlparse
from sqlalchemy.sql import collate
from ips_vagrant.models.sites import Domain, Site
from ips_vagrant.scraper import Licenses, Version
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.generator.nginx import ServerBlock


@click.command('new', short_help='Creates a new IPS installation.')
@click.option('-n', '--name', prompt='Installation nickname', help='Installation name.')
@click.option('-d', '--domain', 'dname', prompt='Domain name', envvar='DOMAIN', help='Installation domain name.')
@click.option('-l', '--license', 'license_key', envvar='LICENSE', help='License key to use for requests.')
@click.option('--enable/--disable', prompt='Do you want to enable this site after installation?', default=True,
              help='Enable site after installation. Note that this will automatically disable any existing sites '
                   'running on this domain. (Default: True)')
@click.option('--ssl/--no-ssl', envvar='SSL', help='Enable SSL on this installation. (Default: Auto)')
@click.option('--spdy/--no-spdy', envvar='SPDY', default=False,
              help='Enable Google SPDY on this installation. Only applies when SSL is enabled. (Default: False)')
@click.option('--gzip/--no-gzip', envvar='GZIP', default=True, help='Enable GZIP compression. (Default: True)')
@click.option('--cache/--no-cache', envvar='CACHE', default=True,
              help='Use cached version downloads if possible. (Default: True)')
@pass_context
def cli(ctx, name, dname, license_key, enable, ssl, spdy, gzip, cache):
    """Creates a new installation of Invision Power Suite."""
    assert isinstance(ctx, Context)
    login_session = ctx.get_login()
    log = logging.getLogger('ipsv.new')

    # Prompt for our desired license
    def get_license():
        licenses = Licenses(login_session).get()
        user_license = license_key or ctx.config.get('User', 'LicenseKey')

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

    lmeta = get_license()
    version = Version(ctx, login_session, lmeta).get()
    filename = version.filename if version.filename and cache else version.download()

    # Parse the specific domain and make sure it's valid
    log.debug('Parsing domain name: %s', dname)
    dname = dname.lower()
    if not dname.startswith('http://') and not dname.startswith('https://'):
        dname = '{schema}{host}'.format(schema='http://', host=dname)
    dname = urlparse(dname)
    if not dname.hostname:
        raise Exception('Invalid domain provided')

    if not ssl:
        ssl = dname.scheme == 'https'

    # Strip www prefix
    dname = dname.hostname.lstrip('www.') if dname.hostname.startswith('www.') else dname.hostname
    log.debug('Domain name parsed: %s', dname)

    # Fetch the domain entry if it already exists
    log.info('Checking if the domain %s has already been registered', dname)
    domain = ctx.db.query(Domain).filter(Domain.name == dname).first()

    # Otherwise create it now
    if not domain:
        log.info('Domain name does not yet exist, creating a new database entry')
        domain = Domain(name=dname)
        ctx.db.add(domain)
        ctx.db.commit()

    # Make sure this site does not already exist
    site = ctx.db.query(Site).filter(Site.domain == domain).filter(collate(Site.name, 'NOCASE') == name).count()
    if site:
        log.error('Site already exists')
        raise Exception('An installation named "{s}" has already been created for the domain {d}'
                        .format(s=name, d=dname))

    # Construct the HTTP path
    dir_name = re.sub('[^0-9a-zA-Z_-]+', '_', name.lower())
    root = os.path.abspath(os.path.join(ctx.config.get('Paths', 'HttpRoot'), domain.name, dir_name))

    # Create the site database entry
    site = Site(name=name, domain=domain, root=root, license_key=lmeta.license_key, ssl=ssl, spdy=spdy, gzip=gzip,
                enabled=enable)
    ctx.db.add(site)
    ctx.db.commit()

    # Generate our server block configuration
    server_block = ServerBlock(site)

    server_config_path = os.path.join(ctx.config.get('Paths', 'NginxSitesAvailable'), domain.name)
    if not os.path.exists(server_config_path):
        log.debug('Creating new configuration path: %s', server_config_path)
        os.makedirs(server_config_path, 0o755)

    server_config_path = os.path.join(server_config_path, '{fn}.conf'.format(fn=dir_name))
    if os.path.exists(server_config_path):
        log.warn('Server block configuration file already exists, overwriting: %s', server_config_path)
        os.remove(server_config_path)

    log.info('Writing Nginx server block configuration file')
    with open(server_config_path, 'w') as f:
        f.write(server_block.template)
