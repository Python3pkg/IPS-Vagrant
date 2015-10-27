import os
import click
import logging
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.common import domain_parse
from ips_vagrant.models.sites import Domain, Site, Session


# noinspection PyUnboundLocalVariable
@click.command('mysql', short_help='Connect to the MySQL database for the specified installation.')
@click.argument('site', metavar='<site>')
@click.option('-d', '--domain', 'dname', default='localhost', envvar='DOMAIN', help='Installation domain name.')
@pass_context
def cli(ctx, dname, site):
    """
    Launches a MySQL CLI session for the database of the specified IPS installation.
    """
    assert isinstance(ctx, Context)
    log = logging.getLogger('ipsv.mysql')

    dname = domain_parse(dname).hostname
    domain = Session.query(Domain).filter(Domain.name == dname).first()

    # No such domain
    if not domain:
        click.secho('No such domain: {dn}'.format(dn=dname), fg='red', bold=True, err=True)
        return

    site_name = site
    site = Site.get(domain, site_name)

    # No such site
    if not site:
        click.secho('No such site: {site}'.format(site=site_name), fg='red', bold=True, err=True)
        return

    # Connect to the MySQL database and exit
    log.info('Connecting to MySQL database: {db}'.format(db=site.db_name))
    log.debug('MySQL host: {host}'.format(host=site.db_host))
    log.debug('MySQL username: {user}'.format(user=site.db_user))
    log.debug('MySQL password: {pwd}'.format(pwd=site.db_pass))

    os.execl(
        '/usr/bin/mysql',
        '/usr/bin/mysql',
        '--database={db}'.format(db=site.db_name),
        '--user={user}'.format(user=site.db_user),
        '--password={pwd}'.format(pwd=site.db_pass)
    )
