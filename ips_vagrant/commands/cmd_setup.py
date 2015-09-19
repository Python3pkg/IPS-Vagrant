import os
import logging
import apt
import click
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.context import EnvironmentContext
from ips_vagrant.cli import pass_context, Context


@click.command('setup', short_help='Run setup after a fresh Vagrant installation.')
@pass_context
def cli(ctx):
    """Run setup after a fresh Vagrant installation."""
    log = logging.getLogger('ipsv.setup')
    assert isinstance(ctx, Context)

    # Set up alembic
    config = Config(os.path.join(ctx.basedir, 'alembic.ini'))
    config.set_main_option("sqlalchemy.url", "sqlite:////{path}"
                           .format(path=os.path.join(ctx.config.get('Paths', 'Data'), 'sites.db')))
    script = ScriptDirectory.from_config(config)

    with EnvironmentContext(
        config,
        script,
    ):
        script.run_env()

    # Create our package directories
    click.echo('Creating IPS Vagrant system directories..')
    dirs = ['/etc/ipsv', ctx.config.get('Paths', 'Data'), ctx.config.get('Paths', 'Log')]
    for d in dirs:
        if not os.path.exists(d):
            os.makedirs(d, 0o755)

    click.echo('Copying IPS Vagrant configuration files..')
    with open('/etc/ipsv/ipsv.conf', 'w+') as f:
        ctx.config.write(f)

    # Update the system
    click.echo('Updating package cache..')
    cache = apt.Cache()
    cache.update()
    cache.open(None)
    click.echo('Upgrading system packages..')
    cache.upgrade()
    cache.commit()

    # Install our required packages
    requirements = ['nginx', 'php5-fpm', 'php5-curl', 'php5-gd', 'php5-imagick', 'php5-json', 'php5-mysql',
                    'php5-readline', 'php5-apcu']

    for requirement in requirements:
        # Make sure the package is available
        if requirement not in cache:
            log.warn('Required package {pkg} not available'.format(pkg=requirement))
            continue

        # Mark the package for installation
        click.echo('Marking package {pkg} for installation'.format(pkg=requirement))
        cache[requirement].mark_install()

    log.info('Committing package cache')
    cache.commit()
