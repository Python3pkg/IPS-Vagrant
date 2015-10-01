import os
import click
import subprocess
from ips_vagrant.cli import Context, pass_context
from ips_vagrant.common import domain_parse
from ips_vagrant.common.progress import Echo
from ips_vagrant.models.sites import Session, Domain


@click.command('disable', short_help='Disable installations under a domain.')
@click.argument('dname', metavar='<domain>')
@pass_context
def cli(ctx, dname):
    """
    Disable installations under the specified <domain>
    """
    assert isinstance(ctx, Context)

    dname = domain_parse(dname).hostname
    domain = Session.query(Domain).filter(Domain.name == dname).first()
    if not domain:
        click.secho('No such domain: {dn}'.format(dn=dname), fg='red', bold=True, err=True)
        return

    sites = domain.sites
    for site in sites:
        if site.enabled:
            click.secho('Disabling site {sn}'.format(sn=site.name), bold=True)
            site.disable()

    # Restart Nginx
    p = Echo('Restarting web server...')
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(['service', 'nginx', 'restart'], stdout=FNULL, stderr=subprocess.STDOUT)
    p.done()
