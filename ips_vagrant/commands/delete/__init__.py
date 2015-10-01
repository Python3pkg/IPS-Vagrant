import os
import shutil
import click
import subprocess
from ips_vagrant.cli import pass_context, Context
from ips_vagrant.common import domain_parse
from ips_vagrant.models.sites import Domain, Site, Session


@click.command('list', short_help='Delete a single site or ALL sites under a domain.')
@click.argument('dname', metavar='<domain>')
@click.argument('site', default=False, metavar='<site>')
@click.option('--remove-code/--preserve-code', 'delete_code', help='Deletes project code (HTTP files) with the site '
                                                                   'entry. (Default: Preserve)')
@click.option('--no-safety-prompt', 'no_prompt', is_flag=True, help='Skip the safety confirmation prompt(s). '
                                                                    'USE WITH CAUTION!')
@pass_context
def cli(ctx, dname, site, delete_code, no_prompt):
    """
    Deletes a single site if both <domain> and <site> are specified, or ALL sites under a domain if only the <domain>
    is specified.
    """
    assert isinstance(ctx, Context)

    # Get the domain
    dname = domain_parse(dname)
    domain = Domain.get(dname)
    if not domain:
        click.secho('No such domain: {dn}'.format(dn=domain.name), fg='red', bold=True, err=True)
        return

    domain_sites = {site.name.lower(): site for site in domain.sites}

    # Single site?
    if site:
        if site.lower() not in domain_sites:
            click.secho('No such site "{sn}" under the domain {dn}'.format(sn=site, dn=domain.name))
        site = domain_sites[site.lower()]

        delete_single(site, domain, delete_code, no_prompt)
        return

    # Delete the entire domain
    delete_all(domain, delete_code, no_prompt)


def delete_single(site, domain, delete_code=False, no_prompt=False):
    """
    Delete a single site
    @type   site:           Site
    @type   domain:         Domain
    @type   delete_code:    bool
    @type   no_prompt:      bool
    """
    click.secho('Deleting installation "{sn}" hosted on the domain {dn}'.format(sn=site.name, dn=domain.name),
                fg='yellow', bold=True)
    if not no_prompt:
        if delete_code:
            warn_text = click.style('WARNING! THIS WILL PERMANENTLY DELETE THIS SITE AND ALL OF THE ASSOCIATED '
                                    'PROJECT CODE FILES!\nTHIS MEANS ALL DATA FILES, INCLUDING ANY CREATED CUSTOM '
                                    'APPLICATIONS AND PLUGINS WILL BE PERMANENTLY AND IRREVOCABLY ERASED!',
                                    fg='red', bold=True)
            click.echo(warn_text)
            prompt_text = click.style('In order to continue, please re-input the site name', fg='white', bold=True)
            prompt = click.prompt(prompt_text)

            # If our prompt doesn't match, abort
            if prompt != site.name:
                click.secho('Site name did not match, site will not be deleted. Aborting.', fg='red', bold=True)
                raise click.Abort('Site name prompt did not match')

        else:
            prompt_text = click.style('Are you sure you want to delete this site entry? Your project files will '
                                      'still be preserved.', fg='white', bold=True)
            click.confirm(prompt_text, abort=True)

    site.delete()

    if delete_code:
        _remove_code(site)

    # If this is the only site left in the domain, remove the domain now as well
    domain_sites = [ds for ds in domain.sites if ds.id != site.id]
    if not len(domain_sites):
        Session.delete(domain)

    Session.commit()
    click.secho('{sn} removed'.format(sn=site.name), fg='yellow', bold=True)

    # Restart Nginx
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(['service', 'nginx', 'restart'], stdout=FNULL, stderr=subprocess.STDOUT)


def delete_all(domain, delete_code=False, no_prompt=False):
    """
    Delete all sites under a domain
    @type   domain:         Domain
    @type   delete_code:    bool
    @type   no_prompt:      bool
    """
    click.secho('All of the following installations hosted on the domain {dn} will be deleted:'
                .format(dn=domain.name), fg='yellow', bold=True)

    sites = domain.sites
    for site in sites:
        click.secho('{sn} ({v})'.format(sn=site.name, v=site.version), fg='red', bold=True)
    click.secho('------', fg='white', bold=True)
    click.echo()

    if not no_prompt:
        if delete_code:
            warn_text = click.style('WARNING! THIS WILL PERMANENTLY DELETE ALL OF THE ABOVE SITES AND ALL OF THEIR '
                                    'PROJECT CODE FILES!\nTHIS MEANS ALL DATA FILES, INCLUDING ANY CREATED CUSTOM '
                                    'APPLICATIONS AND PLUGINS, WILL BE PERMANENTLY AND IRREVOCABLY ERASED!',
                                    fg='red', bold=True)
            click.echo(warn_text)
            prompt_text = click.style('In order to continue, please re-input the domain name', fg='white', bold=True)
            prompt = click.prompt(prompt_text)

            # If our prompt doesn't match, abort
            if prompt != domain.name:
                click.secho('Domain name did not match, domain will not be deleted. Aborting.', fg='red', bold=True)
                raise click.Abort('Domain name prompt did not match')

        else:
            prompt_text = click.style('Are you sure you want to delete this domain and all its associated sites? '
                                      'Your project files will still be preserved.', fg='white', bold=True)
            click.confirm(prompt_text, abort=True)

    for site in sites:
        Session.delete(site)
        if delete_code:
            _remove_code(site)
        click.secho('{sn} removed'.format(sn=site.name), fg='yellow', bold=True)

    Session.delete(domain)
    Session.commit()

    # Restart Nginx
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(['service', 'nginx', 'restart'], stdout=FNULL, stderr=subprocess.STDOUT)


def _remove_code(site):
    """
    Delete project files
    @type   site:   Site
    """
    def handle_error(function, path, excinfo):
        click.secho('Failed to remove path ({em}): {p}'.format(em=excinfo.message, p=path), err=True, fg='red')

    if os.path.exists(site.root):
        shutil.rmtree(site.root, onerror=handle_error)
