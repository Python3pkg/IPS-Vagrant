import click
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.common import domain_parse
from ips_vagrant.models.sites import Domain, Site, Session


@click.command('list', short_help='List all domains, or all installations under a specified <domain>.')
@click.argument('dname', default=False, metavar='<domain>')
@pass_context
def cli(ctx, dname):
    """
    List all domains if no <domain> is provided, otherwise list all sites hosted under <domain>
    """
    assert isinstance(ctx, Context)

    # Print sites
    if dname:
        dname = domain_parse(dname).hostname
        domain = Session.query(Domain).filter(Domain.name == dname).first()

        # No such domain
        if not domain:
            click.secho('No such domain: {dn}'.format(dn=dname), fg='red', bold=True, err=True)
            return

        # Get sites
        sites = Site.all(domain)
        if not sites:
            click.secho('No sites active under domain: {dn}'.format(dn=dname), fg='red', bold=True, err=True)
            return

        # Display site data
        for site in sites:
            prefix = '[DEV] ' if site.in_dev else ''
            click.secho('{pre}{name} ({ver})'.format(pre=prefix, name=site.name, ver=site.version), bold=True)

        return

    # Print domains
    domains = Domain.all()
    for domain in domains:
        # Extra domains
        extras = ''
        if domain.extras:
            extras = ' ({dnames})'.format(dnames=str(domain.extras).replace(',', ', '))

        click.secho('{dname}{extras}'.format(dname=domain.name, extras=extras))
