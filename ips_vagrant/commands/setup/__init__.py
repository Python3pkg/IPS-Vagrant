import fileinput
import os
import apt
import shutil
from tempfile import mkstemp
import click
import logging
import subprocess
from alembic import command
from alembic.config import Config
import sys
import re
from ips_vagrant.common.progress import Echo
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.generators.php5_fpm import FpmPoolConfig


@click.command('setup', short_help='Run setup after a fresh Vagrant installation.')
@pass_context
def cli(ctx):
    """
    Run setup after a fresh Vagrant installation.
    """
    log = logging.getLogger('ipsv.setup')
    assert isinstance(ctx, Context)

    lock_path = os.path.join(ctx.config.get('Paths', 'Data'), 'setup.lck')
    if os.path.exists(lock_path):
        raise Exception('Setup is locked, please remove the setup lock file to continue')

    # Create our package directories
    p = Echo('Creating IPS Vagrant system directories...')
    dirs = ['/etc/ipsv', ctx.config.get('Paths', 'Data'), ctx.config.get('Paths', 'Log'),
            ctx.config.get('Paths', 'NginxSitesAvailable'), ctx.config.get('Paths', 'NginxSitesEnabled'),
            ctx.config.get('Paths', 'NginxSSL')]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d, 0o755)
    p.done()

    p = Echo('Copying IPS Vagrant configuration files...')
    with open('/etc/ipsv/ipsv.conf', 'w+') as f:
        ctx.config.write(f)
    p.done()

    # Set up alembic
    alembic_cfg = Config(os.path.join(ctx.basedir, 'alembic.ini'))
    alembic_cfg.set_main_option("script_location", os.path.join(ctx.basedir, 'migrations'))
    alembic_cfg.set_main_option("sqlalchemy.url", "sqlite:////{path}"
                                .format(path=os.path.join(ctx.config.get('Paths', 'Data'), 'sites.db')))

    command.current(alembic_cfg)
    command.downgrade(alembic_cfg, 'base')
    command.upgrade(alembic_cfg, 'head')

    # Update the system
    p = Echo('Updating package cache...')
    cache = apt.Cache()
    cache.update()
    cache.open(None)
    p.done()
    p = Echo('Upgrading system packages...')
    cache.upgrade()
    cache.commit()
    p.done()

    # Install our required packages
    requirements = ['nginx', 'php5-fpm', 'php5-curl', 'php5-gd', 'php5-imagick', 'php5-json', 'php5-mysql',
                    'php5-readline', 'php5-apcu', 'php5-xdebug']

    for requirement in requirements:
        # Make sure the package is available
        p = Echo('Marking package {pkg} for installation'.format(pkg=requirement))
        if requirement not in cache:
            log.warn('Required package {pkg} not available'.format(pkg=requirement))
            p.done(p.FAIL)
            continue

        # Mark the package for installation
        cache[requirement].mark_install()
        p.done()

    log.info('Committing package cache')
    p = Echo('Downloading and installing packages...')
    cache.commit()
    p.done()

    # Disable the default server block
    p = Echo('Configuring Nginx...')
    default_available = os.path.join(ctx.config.get('Paths', 'NginxSitesAvailable'), 'default')
    default_enabled = os.path.join(ctx.config.get('Paths', 'NginxSitesEnabled'), 'default')
    if os.path.isfile(default_available):
        os.remove(default_available)
    if os.path.islink(default_enabled):
        os.unlink(default_enabled)
    p.done()

    # Restart Nginx
    FNULL = open(os.devnull, 'w')
    p = Echo('Restarting Nginx...')
    subprocess.check_call(['service', 'nginx', 'restart'], stdout=FNULL, stderr=subprocess.STDOUT)
    p.done()

    # php.ini configuration
    p = Echo('Configuring php...')
    with open('/etc/php5/fpm/php.ini', 'a') as f:
        f.write('\n[XDebug]')
        f.write('\nxdebug.cli_color=1')

    temp_fh, temp_path = mkstemp()
    with open(temp_path, 'w') as nf:
        with open('/etc/php5/fpm/php.ini') as of:
            # Configuration options we are replacing
            upload_max_filesize = re.compile( '^upload_max_filesize\s+=\s+(\d+[a-zA-Z])\s*$' )
            post_max_size = re.compile( '^post_max_size\s+=\s+(\d+[a-zA-Z])\s*$' )

            for line in of:
                match = upload_max_filesize.match( line ) if upload_max_filesize is not True else False
                if match:
                    nf.write( 'upload_max_filesize = 1000M\n' )
                    upload_max_filesize = True
                    continue

                match = post_max_size.match( line ) if post_max_size is not True else False
                if match:
                    nf.write( 'post_max_size = 1000M\n' )
                    post_max_size = True
                    continue

                nf.write(line)
    os.close(temp_fh)
    os.remove('/etc/php5/fpm/php.ini')
    shutil.move(temp_path, '/etc/php5/fpm/php.ini')
    os.chmod('/etc/php5/fpm/php.ini', 0o644)
    p.done()

    # php5-fpm configuration
    p = Echo('Configuring php5-fpm...')
    if os.path.isfile('/etc/php5/fpm/pool.d/www.conf'):
        os.remove('/etc/php5/fpm/pool.d/www.conf')

    fpm_config = FpmPoolConfig().template
    with open('/etc/php5/fpm/pool.d/ips.conf', 'w') as f:
        f.write(fpm_config)
    p.done()

    # Restart php5-fpm
    p = Echo('Restarting php5-fpm...')
    subprocess.check_call(['service', 'php5-fpm', 'restart'], stdout=FNULL, stderr=subprocess.STDOUT)
    p.done()

    # Copy the man pages and rebuild the manual database
    p = Echo('Writing manual pages...')
    man_path = os.path.join(ctx.basedir, 'man', 'ipsv.1')
    sys_man_path = '/usr/local/share/man/man1'
    if not os.path.exists(sys_man_path):
        os.makedirs(sys_man_path)

    shutil.copyfile(man_path, os.path.join(sys_man_path, 'ipsv.1'))

    subprocess.check_call(['mandb'], stdout=FNULL, stderr=subprocess.STDOUT)

    # Enable the welcome message
    log.debug('Writing welcome message')
    wm_header = '## DO NOT REMOVE :: AUTOMATICALLY GENERATED BY IPSV ##'
    wm_remove = False

    # Remove old profile data
    for line in fileinput.input('/etc/profile', inplace=True):
        # Header / footer match?
        if line == wm_header:
            # Footer match (Stop removing)
            if wm_remove:
                wm_remove = False
                continue

            # Header match (Start removing)
            wm_remove = True
            continue

        # Removing lines?
        if wm_remove:
            continue

        # Print line and continue as normal
        sys.stdout.write(line)

    # Write new profile data
    with open('/etc/profile', 'a') as f:
        f.write("\n" + wm_header + "\n")
        fl_lock_path = os.path.join(ctx.config.get('Paths', 'Data'), 'first_login.lck')
        f.write('if [ ! -f "{lp}" ]; then'.format(lp=fl_lock_path) + "\n")
        f.write('  less "{wp}"'.format(wp=os.path.join(ctx.basedir, 'WELCOME.rst')) + "\n")
        f.write('  sudo touch "{lp}"'.format(lp=fl_lock_path) + "\n")
        f.write('fi' + "\n")
        f.write(wm_header + "\n")
    p.done()

    log.debug('Writing setup lock file')
    with open(os.path.join(ctx.config.get('Paths', 'Data'), 'setup.lck'), 'w') as f:
        f.write('1')
