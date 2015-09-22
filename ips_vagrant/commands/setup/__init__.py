import os
import apt
import click
import logging
from alembic import command
from alembic.config import Config
from ips_vagrant.common.progress import Echo
from ips_vagrant.cli import pass_context, Context


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
                    'php5-readline', 'php5-apcu']

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
    cache.commit()

    log.debug('Writing setup lock file')
    with open(os.path.join(ctx.config.get('Paths', 'Data'), 'setup.lck'), 'w') as f:
        f.write('1')
