import os
import re
import glob
import click
import shutil
import logging
import zipfile
import tempfile
import subprocess
from sqlalchemy.sql import collate
from ips_vagrant.models.sites import Domain, Site
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.common import domain_parse, choice
from ips_vagrant.generators.nginx import ServerBlock
from ips_vagrant.scraper import Licenses, Version, Installer


@click.command('new', short_help='Creates a new IPS installation.')
@click.option('-n', '--name', prompt='Installation nickname', help='Installation name.')
@click.option('-d', '--domain', 'dname', prompt='Domain name', envvar='DOMAIN', help='Installation domain name.')
@click.option('-l', '--license', 'license_key', envvar='LICENSE', help='License key to use for requests.')
@click.option('-f', '--force', is_flag=True,
              help='Overwrite any existing files (possibly left over from a broken configuration)')
@click.option('--enable/--disable', prompt='Do you want to enable this site after installation?', default=True,
              help='Enable site after installation. Note that this will automatically disable any existing sites '
                   'running on this domain. (Default: True)')
@click.option('--ssl/--no-ssl', envvar='SSL', help='Enable SSL on this installation. (Default: Auto)')
@click.option('--spdy/--no-spdy', envvar='SPDY', default=False,
              help='Enable Google SPDY on this installation. Only applies when SSL is enabled. (Default: False)')
@click.option('--gzip/--no-gzip', envvar='GZIP', default=True, help='Enable GZIP compression. (Default: True)')
@click.option('--cache/--no-cache', envvar='CACHE', default=True,
              help='Use cached version downloads if possible. (Default: True)')
@click.option('--install/--no-install', envvar='INSTALL', default=True,
              help='Run the IPS installation automatically after setup. (Default: True)')
@pass_context
def cli(ctx, name, dname, license_key, force, enable, ssl, spdy, gzip, cache, install):
    """
    Downloads and installs a new instance of the latest Invision Power Suite release.
    """
    assert isinstance(ctx, Context)
    login_session = ctx.get_login()
    log = logging.getLogger('ipsv.new')

    # Prompt for our desired license
    def get_license():
        """
        Prompt the user for a license selection
        @rtype: ips_vagrant.scraper.licenses.LicenseMeta
        """
        licenses = Licenses(login_session).get()
        user_license = license_key or ctx.config.get('User', 'LicenseKey')

        # If we already have a license key saved, skip the prompt and use it instead
        if user_license:
            licenses = {license.license_key: license for license in licenses}
            if user_license in licenses:
                return licenses[user_license]

        # Ask the user to select a license key
        opt = choice([
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

    # Get the latest IPS release
    lmeta = get_license()
    version = Version(ctx, login_session, lmeta).get()
    filename = version.filename if version.filename and cache else version.download()

    # Parse the specific domain and make sure it's valid
    log.debug('Parsing domain name: %s', dname)
    dname = domain_parse(dname)
    if not ssl:
        ssl = dname.scheme == 'https'
    log.debug('Domain name parsed: %s', dname)

    domain = Domain.get_or_create(dname)

    # Make sure this site does not already exist
    site = ctx.db.query(Site).filter(Site.domain == domain).filter(collate(Site.name, 'NOCASE') == name).count()
    if site:
        log.error('Site already exists')
        raise Exception('An installation named "{s}" has already been created for the domain {d}'
                        .format(s=name, d=dname))

    # Construct the HTTP path
    slug = re.sub('[^0-9a-zA-Z_-]+', '_', name.lower())
    root = os.path.abspath(os.path.join(ctx.config.get('Paths', 'HttpRoot'), domain.name, slug))
    if not os.path.exists(root):
        log.debug('Creating HTTP root directory: %s', root)
        os.makedirs(root, 0o755)

    # Create the site database entry
    site = Site(name=name, domain=domain, root=root, license_key=lmeta.license_key, ssl=ssl, spdy=spdy, gzip=gzip,
                enabled=enable)
    ctx.db.add(site)

    # If our new site was enabled, we need to disable any other sites utilizing this domain
    if site.enabled:
        log.debug('Disabling all other sites under the domain %s', domain.name)
        ctx.db.query(Site).filter(Site.id != site.id).filter(Site.domain == domain).update({'enabled': 0})

    # Generate our server block configuration
    server_block = ServerBlock(site)

    server_config_path = os.path.join(ctx.config.get('Paths', 'NginxSitesAvailable'), domain.name)
    if not os.path.exists(server_config_path):
        log.debug('Creating new configuration path: %s', server_config_path)
        os.makedirs(server_config_path, 0o755)

    server_config_path = os.path.join(server_config_path, '{fn}.conf'.format(fn=slug))
    if os.path.exists(server_config_path):
        log.warn('Server block configuration file already exists, overwriting: %s', server_config_path)
        os.remove(server_config_path)

    log.info('Writing Nginx server block configuration file')
    with open(server_config_path, 'w') as f:
        f.write(server_block.template)

    # Create a symlink if this site is being enabled
    if site.enabled:
        sites_enabled_path = ctx.config.get('Paths', 'NginxSitesEnabled')
        symlink_path = os.path.join(sites_enabled_path, '{domain}-{fn}'.format(domain=domain.name,
                                                                               fn=os.path.basename(server_config_path)))
        links = glob.glob(os.path.join(sites_enabled_path, '{domain}-*'.format(domain=domain.name)))
        for link in links:
            if os.path.islink(link):
                log.debug('Removing existing configuration symlink: %s', link)
                os.unlink(link)
            else:
                if not force:
                    log.error('Configuration symlink path already exists, but it is not a symlink')
                    raise Exception('Misconfiguration detected: symlink path already exists, but it is not a symlink '
                                    'and --force was not passed. Unable to continue')
                log.warn('Configuration symlink path already exists, but it is not a symlink. '
                         'Removing anyways since --force was set')
                if os.path.isdir(symlink_path):
                    shutil.rmtree(symlink_path)
                else:
                    os.remove(symlink_path)

        log.info('Enabling Nginx configuration file')
        os.symlink(server_config_path, symlink_path)

        # Restart Nginx
        click.echo('Restarting Nginx')
        subprocess.check_call(['/etc/init.d/nginx', 'restart'])

    # Extract IPS setup files
    tmpdir = tempfile.mkdtemp('ips')
    setup_zip = os.path.join(tmpdir, 'setup.zip')
    setup_dir = os.path.join(tmpdir, 'setup')
    os.mkdir(setup_dir)

    log.info('Extracting setup files')
    shutil.copyfile(filename, setup_zip)
    with zipfile.ZipFile(setup_zip) as z:
        namelist = z.namelist()
        if re.match(r'^ips_\w{5}\/?$', namelist[0]):
            log.debug('Setup directory matched: %s', namelist[0])
        else:
            log.error('No setup directory matched, unable to continue')
            raise Exception('Unrecognized setup file format, aborting')

        z.extractall(setup_dir)
        log.debug('Setup files extracted to: %s', setup_dir)
        setup_tmpdir = os.path.join(setup_dir, namelist[0])
        for filename in os.listdir(setup_tmpdir):
            shutil.move(os.path.join(setup_tmpdir, filename), os.path.join(site.root, filename))

        log.info('Setup files moved to: %s', site.root)
    shutil.rmtree(tmpdir)

    # Apply proper permissions
    writeable_dirs = ['uploads', 'plugins', 'applications', 'datastore']
    
    for wdir in writeable_dirs:
        log.debug('Setting file permissions in %s', wdir)
        os.chmod(os.path.join(site.root, wdir), 0o777)
        for dirname, dirnames, filenames in os.walk(os.path.join(site.root, wdir)):
            for filename in filenames:
                os.chmod(os.path.join(dirname, filename), 0o666)

            for filename in dirnames:
                os.chmod(os.path.join(dirname, filename), 0o777)

    shutil.move(os.path.join(site.root, 'conf_global.dist.php'), os.path.join(site.root, 'conf_global.php'))
    os.chmod(os.path.join(site.root, 'conf_global.php'), 0o777)

    # Run the installation
    installer = Installer(ctx, site)
    installer.start()
