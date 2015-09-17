import logging
import apt
import apt.progress
import click
from ips_vagrant.cli import pass_context, Context


@click.command('setup', short_help='Run setup after a fresh Vagrant installation.')
@pass_context
def cli(ctx):
    """Run setup after a fresh Vagrant installation."""
    log = logging.getLogger('ipsv.setup')
    assert isinstance(ctx, Context)

    # Update the system
    click.echo('Updating package cache..')
    cache = apt.Cache()
    cache.update()
    cache.open(None)
    click.echo('Upgrading system packages..')
    cache.upgrade()
    cache.commit(apt.progress.TextFetchProgress(), apt.progress.InstallProgress())

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
