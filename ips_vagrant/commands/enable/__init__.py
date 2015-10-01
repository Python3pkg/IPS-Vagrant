import os
import click
import subprocess
from ips_vagrant.cli import Context, pass_context
from ips_vagrant.common import domain_parse
from ips_vagrant.common.progress import Echo
from ips_vagrant.models.sites import Session, Domain, Site


@click.command('enable', short_help='Enable an IPS installation.')
@click.argument('dname', metavar='<domain>')
@click.argument('site', metavar='<site>')
@pass_context
def cli(ctx, dname, site):
    """
    Enable the <site> under the specified <domain>
    """
    assert isinstance(ctx, Context)

    dname = domain_parse(dname).hostname
    domain = Session.query(Domain).filter(Domain.name == dname).first()
    if not domain:
        click.secho('No such domain: {dn}'.format(dn=dname), fg='red', bold=True, err=True)
        return

    site_name = site
    site = Site.get(domain, site_name)
    if not site:
        click.secho('No such site: {site}'.format(site=site_name), fg='red', bold=True, err=True)
        return

    p = Echo('Constructing paths and configuration files...')
    site.enable()
    p.done()

    # Restart Nginx
    p = Echo('Restarting web server...')
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(['service', 'nginx', 'restart'], stdout=FNULL, stderr=subprocess.STDOUT)
    p.done()
