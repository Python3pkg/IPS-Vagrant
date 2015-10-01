import os
import re
import click
import shutil
import logging
import zipfile
import tempfile
import subprocess
from sqlalchemy.sql import collate
from ips_vagrant.common.progress import Echo, MarkerProgressBar
from ips_vagrant.common.version import Version
from ips_vagrant.models.sites import Domain, Site
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.common import domain_parse, choice
from ips_vagrant.common.ssl import CertificateFactory
from ips_vagrant.installer import installer
from ips_vagrant.scrapers import Licenses
from ips_vagrant.downloaders import IpsManager


@click.command('new', short_help='Creates a new IPS installation.')
@click.option('-n', '--name', prompt='Installation nickname', help='Installation name.')
@click.option('-d', '--domain', 'dname', default='localhost', prompt='Domain name', envvar='DOMAIN',
              help='Installation domain name.')
@click.option('-l', '--license', 'license_key', envvar='LICENSE', help='License key to use for requests.')
@click.option('-v', '--version', 'ips_version', envvar='VERSION', help='Manually specify a version to install.')
@click.option('-f', '--force', is_flag=True,
              help='Overwrite any existing files (possibly left over from a broken configuration)')
@click.option('--enable/--disable', prompt='Do you want to enable this site after installation?', default=True,
              help='Enable site after installation. Note that this will automatically disable any existing sites '
                   'running on this domain. (Default: True)')
@click.option('--ssl/--no-ssl', envvar='SSL', help='Enable SSL on this installation. (Default: Auto)', default=None)
@click.option('--spdy/--no-spdy', envvar='SPDY', default=False,
              help='Enable Google SPDY on this installation. Only applies when SSL is enabled. (Default: False)')
@click.option('--gzip/--no-gzip', envvar='GZIP', default=True, help='Enable GZIP compression. (Default: True)')
@click.option('--cache/--no-cache', envvar='CACHE', default=True,
              help='Use cached version downloads if possible. (Default: True)')
@click.option('--install/--no-install', envvar='INSTALL', default=True,
              help='Run the IPS installation automatically after setup. (Default: True)')
@click.option('--dev/--no-dev', envvar='IPSV_IN_DEV', default=False,
              help='Install developer tools and put the site into dev mode after installation. (Default: False)')
@pass_context
def cli(ctx, name, dname, license_key, ips_version, force, enable, ssl, spdy, gzip, cache, install, dev):
    """
    Downloads and installs a new instance of the latest Invision Power Suite release.
    """
    assert isinstance(ctx, Context)
    login_session = ctx.get_login()
    log = logging.getLogger('ipsv.new')
    ctx.cache = cache

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
    p = Echo('Fetching IPS version information...')
    ips = IpsManager(ctx, lmeta)
    p.done()
    if ips_version:
        if ips_version == 'latest_dev':
            v = ips.dev_version
            if not v:
                click.secho('There is no IPS development release available for download', err=True, fg='red', bold=True)
                raise Exception('There is no IPS development release available for download')
            p = Echo('Downloading IPS development release {vs}...'.format(vs=v.version.vstring))
        else:
            ips_version = Version(ips_version)
            v = ips.versions[ips_version.vtuple]
            p = Echo('Fetching IPS version {iv}'.format(iv=ips_version.vstring))
    else:
        v = ips.latest
        p = Echo('Downloading IPS release {vs}...'.format(vs=v.version.vstring))
    filename = ips.get(v, cache)
    p.done()

    # Parse the specific domain and make sure it's valid
    log.debug('Parsing domain name: %s', dname)
    dname = domain_parse(dname)
    if ssl is None:
        ssl = dname.scheme == 'https'
    log.debug('Domain name parsed: %s', dname)

    domain = Domain.get_or_create(dname)

    # Make sure this site does not already exist
    p = Echo('Constructing site data...')
    site = ctx.db.query(Site).filter(Site.domain == domain).filter(collate(Site.name, 'NOCASE') == name).count()
    if site:
        p.done(p.FAIL)
        log.error('Site already exists')
        click.secho('An installation named "{s}" has already been created for the domain {d}'
                    .format(s=name, d=dname.hostname),
                    err=True, fg='red', bold=True)
        raise click.Abort

    # Create the site database entry
    site = Site(name=name, domain=domain, license_key=lmeta.license_key, version=v.version.vstring, ssl=ssl, spdy=spdy,
                gzip=gzip, enabled=enable, in_dev=dev)

    status = p.OK
    if os.path.exists(site.root):
        if not force:
            p.done(p.FAIL)
            click.secho("Installation path already exists and --force was not passed:\n{p}".format(p=site.root),
                        err=True, fg='red', bold=True)
            log.info('Aborting installation, path already exists: {p}'.format(p=site.root))
            raise click.Abort

        log.warn('Overwriting existing installation path: {p}'.format(p=site.root))
        status = p.WARN

    ctx.db.add(site)
    ctx.db.commit()
    p.done(status)

    # Construct the HTTP path
    p = Echo('Constructing paths and configuration files...')
    site.write_nginx_config()
    p.done()

    # Generate SSL certificates if enabled
    if ssl:
        p = Echo('Generating SSL certificate...')
        ssl_path = os.path.join(ctx.config.get('Paths', 'NginxSSL'), domain.name)
        if not os.path.exists(ssl_path):
            log.debug('Creating new SSL path: %s', ssl_path)
            os.makedirs(ssl_path, 0o755)

        sc = CertificateFactory(site).get()
        site.ssl_key = sc.key
        site.ssl_certificate = sc.certificate

        with open(os.path.join(ssl_path, '{s}.key'.format(s=site.slug)), 'w') as f:
            f.write(sc.key)
        with open(os.path.join(ssl_path, '{s}.pem').format(s=site.slug), 'w') as f:
            f.write(sc.certificate)
        p.done()

    # Create a symlink if this site is being enabled
    if site.enabled:
        site.enable(force)

        # Restart Nginx
        p = Echo('Restarting web server...')
        FNULL = open(os.devnull, 'w')
        subprocess.check_call(['service', 'nginx', 'restart'], stdout=FNULL, stderr=subprocess.STDOUT)
        p.done()

    # Extract IPS setup files
    p = Echo('Extracting setup files to tmp...')
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
        p.done()
        p = MarkerProgressBar('Copying setup files...')
        setup_tmpdir = os.path.join(setup_dir, namelist[0])
        for dirname, dirnames, filenames in p(os.walk(setup_tmpdir)):
            for filepath in dirnames:
                site_path = os.path.join(site.root, dirname.replace(setup_tmpdir, ''), filepath)
                if not os.path.exists(site_path):
                    log.debug('Creating directory: %s', site_path)
                    os.mkdir(site_path, 0o755)

            for filepath in filenames:
                tmp_path = os.path.join(dirname, filepath)
                site_path = os.path.join(site.root, dirname.replace(setup_tmpdir, ''), filepath)
                shutil.copy(tmp_path, site_path)

        log.info('Setup files copied to: %s', site.root)
    shutil.rmtree(tmpdir)

    # Apply proper permissions
    # p = MarkerProgressBar('Setting file permissions...')
    writeable_dirs = ['uploads', 'plugins', 'applications', 'datastore']
    
    for wdir in writeable_dirs:
        log.debug('Setting file permissions in %s', wdir)
        os.chmod(os.path.join(site.root, wdir), 0o777)
        p = MarkerProgressBar('Setting file permissions...', nl=False)
        for dirname, dirnames, filenames in p(os.walk(os.path.join(site.root, wdir))):
            for filename in filenames:
                os.chmod(os.path.join(dirname, filename), 0o666)

            for filename in dirnames:
                os.chmod(os.path.join(dirname, filename), 0o777)
    Echo('Setting file permissions...').done()

    shutil.move(os.path.join(site.root, 'conf_global.dist.php'), os.path.join(site.root, 'conf_global.php'))
    os.chmod(os.path.join(site.root, 'conf_global.php'), 0o777)

    # Run the installation
    if install:
        p = Echo('Initializing installer...')
        i = installer(v.version, ctx, site, force)
        p.done()
        i.start()
    else:
        click.echo('------')
        click.secho('IPS is now ready to be installed. To proceed with the installation, follow the link below',
                    fg='yellow', bold=True)
        click.echo('{schema}://{host}'.format(schema='https' if site.ssl else 'http', host=site.domain.name))
