import click
import logging
from ips_vagrant.downloaders import IpsManager
from ips_vagrant.cli import pass_context, Context


@click.command('versions', short_help='Displays available IPS and resource versions.')
@click.argument('resource', default='ips', metavar='<resource>')
@pass_context
def cli(ctx, resource):
    """
    Displays all locally cached <resource> versions available for installation.

    \b
    Available resources:
        ips (default)
    """
    log = logging.getLogger('ipsv.setup')
    assert isinstance(ctx, Context)
    
    resource = IpsManager(ctx)
    for r in resource.versions.values():
        click.secho(str(r.version), bold=True)
