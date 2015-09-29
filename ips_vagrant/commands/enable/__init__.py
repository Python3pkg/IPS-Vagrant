import click
from ips_vagrant.cli import Context
from ips_vagrant.common import domain_parse
from ips_vagrant.models.sites import Session, Domain, Site


@click.command('enable', short_help='Enable an IPS installation.')
@click.argument('dname', default=False, metavar='<domain>')
@click.argument('site', default=False, metavar='<site>')
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

    site.enable()
