import click
import string
import random
import logging
import json
import requests
from hashlib import md5
from urllib import urlencode
from urlparse import urlparse, urlunparse, parse_qs
from bs4 import BeautifulSoup
from mechanize import Browser
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from ips_vagrant.common import cookiejar, byteify
from ips_vagrant.common.progress import ProgressBar, Echo
from ips_vagrant.installer.dev_tools.latest import DevToolsInstaller

version = None


# noinspection PyMethodMayBeStatic
class Installer(object):

    # License fields
    FIELD_LICENSE_KEY = 'lkey'

    # Server Detail fields
    FIELD_SERVER_SQL_HOST = 'sql_host'
    FIELD_SERVER_SQL_USER = 'sql_user'
    FIELD_SERVER_SQL_PASS = 'sql_pass'
    FIELD_SERVER_SQL_DATABASE = 'sql_database'

    # Admin fields
    FIELD_ADMIN_USER = 'admin_user'
    FIELD_ADMIN_PASS = 'admin_pass1'
    FIELD_ADMIN_PASS_CONFIRM = 'admin_pass2'
    FIELD_ADMIN_EMAIL = 'admin_email'

    def __init__(self, ctx, site, force=False):
        """
        Initialize a new Installer instance
        @type   ctx:    ips_vagrant.cli.Context
        @param  site:   The IPS Site we are installing
        @type   site:   ips_vagrant.models.sites.Site
        @param  force:  Overwrite existing files / databases
        @type   force:  bool
        """
        self.log = logging.getLogger('ipsv.installer')
        self.ctx = ctx
        self.force = force
        self._previous_title = None
        self.url = '{scheme}://{host}/admin/install'.format(
            scheme='https' if site.ssl else 'http', host=site.domain.name
        )
        self.site = site
        self.mysql = create_engine('mysql://root:secret@localhost')

        self._sessions = {}

        self.cookiejar = cookiejar()
        self.cookies = {cookie.name: cookie.value for cookie in self.cookiejar}

        self.browser = Browser()
        self.browser.set_cookiejar(self.cookiejar)

    def _check_title(self, title):
        """
        If we're on the same page, we got an error and need to raise an exception
        @type   title:  str
        @raise  InstallationError:  Title matches the previous page requests title (We're on the same page)
        """
        self.log.info('Installation page loaded: %s', title)
        if self._previous_title and title == self._previous_title:
            raise InstallationError('Unexpected page error')
        self._previous_title = title

    def start(self):
        """
        Start the installation wizard
        """
        self.log.debug('Starting the installation process')
        self.system_check()

    def system_check(self):
        """
        System requirements check
        """
        self.browser.open(self.url)
        self._check_title(self.browser.title())
        p = Echo('Running system check...')
        rsoup = BeautifulSoup(self.browser.response().read(), "html.parser")

        # Check for any errors
        errors = []
        for ul in rsoup.find_all('ul', {'class': 'ipsList_checks'}):
            for li in ul.find_all('li', {'class': 'fail'}):
                errors.append(li.text)

        if errors:
            raise InstallationError(errors)

        # Continue
        continue_link = next(self.browser.links(text_regex='Continue'))
        p.done()
        self.browser.follow_link(continue_link)
        self.license()

    def license(self):
        """
        Submit our license to IPS' servers
        """
        p = Echo('Submitting license key...')
        self._check_title(self.browser.title())
        self.browser.select_form(nr=0)

        # Set the fields
        self.browser.form[self.FIELD_LICENSE_KEY] = '{license}-TESTINSTALL'.format(license=self.site.license_key)
        self.browser.find_control('eula_checkbox').items[0].selected = True  # TODO: User prompt?

        # Submit the request
        self.log.debug('Submitting our license')
        self.browser.submit()
        self.log.debug('Response code: %s', self.browser.response().code)

        p.done()
        self.applications()

    def applications(self):
        """
        Select the applications to install (currently hardcoded to install all applications)
        """
        # Check for license submission errors
        try:
            self._check_title(self.browser.title())
        except InstallationError:
            rsoup = BeautifulSoup(self.browser.response().read(), "html.parser")
            error = rsoup.find('li', id='license_lkey').find('span', {'class': 'ipsType_warning'}).text
            raise InstallationError(error)

        # TODO: Make this configurable
        p = Echo('Setting applications to install...')
        self.browser.select_form(nr=0)
        self.browser.submit()
        p.done()
        self.server_details()

    def server_details(self):
        """
        Input server details (database information, etc.)
        """
        self._check_title(self.browser.title())
        p = Echo('Creating MySQL database...')

        # Create the database
        md5hex = md5(self.site.domain.name + self.site.slug).hexdigest()
        db_name = 'ipsv_{md5}'.format(md5=md5hex)
        # MySQL usernames are limited to 16 characters max
        db_user = 'ipsv_{md5}'.format(md5=md5hex[:11])
        rand_pass = ''.join(random.SystemRandom()
                            .choice(string.ascii_letters + string.digits) for _ in range(random.randint(16, 24)))
        db_pass = rand_pass

        try:
            self.mysql.execute('CREATE DATABASE `{db}`'.format(db=db_name))
        except SQLAlchemyError:
            if not self.force:
                click.confirm('A previous database for this installation already exists.\n'
                              'Would you like to drop it now? The installation will be aborted if you do not',
                              abort=True)
            self.log.info('Dropping existing database: {db}'.format(db=db_name))
            self.mysql.execute('DROP DATABASE IF EXISTS `{db}`'.format(db=db_name))
            self.mysql.execute('DROP USER IF EXISTS `{u}`'.format(u=db_user))
            self.mysql.execute('CREATE DATABASE `{db}`'.format(db=db_name))

        self.mysql.execute("GRANT ALL ON {db}.* TO '{u}'@'localhost' IDENTIFIED BY '{p}'"
                           .format(db=db_name, u=db_user, p=db_pass))

        # Save the database connection information
        self.site.db_host = 'localhost'
        self.site.db_name = db_name
        self.site.db_user = db_user
        self.site.db_pass = db_pass
        self.ctx.db.commit()

        self.log.debug('MySQL Database Name: %s', db_name)
        self.log.debug('MySQL Database User: %s', db_user)
        self.log.debug('MySQL Database Password: %s', db_pass)

        # Set form fields and submit
        self.browser.select_form(nr=0)
        self.browser.form[self.FIELD_SERVER_SQL_HOST] = 'localhost'
        self.browser.form[self.FIELD_SERVER_SQL_USER] = db_user
        self.browser.form[self.FIELD_SERVER_SQL_PASS] = db_pass
        self.browser.form[self.FIELD_SERVER_SQL_DATABASE] = db_name
        self.browser.submit()
        p.done()
        self.admin()

    def admin(self):
        """
        Provide admin login credentials
        """
        self._check_title(self.browser.title())
        self.browser.select_form(nr=0)

        # Get the admin credentials
        prompted = []
        user = self.ctx.config.get('User', 'AdminUser')
        if not user:
            user = click.prompt('Admin display name')
            prompted.append('user')

        password = self.ctx.config.get('User', 'AdminPass')
        if not password:
            password = click.prompt('Admin password', hide_input=True, confirmation_prompt='Confirm admin password')
            prompted.append('password')

        email = self.ctx.config.get('User', 'AdminEmail')
        if not email:
            email = click.prompt('Admin email')
            prompted.append('email')

        self.browser.form[self.FIELD_ADMIN_USER] = user
        self.browser.form[self.FIELD_ADMIN_PASS] = password
        self.browser.form[self.FIELD_ADMIN_PASS_CONFIRM] = password
        self.browser.form[self.FIELD_ADMIN_EMAIL] = email
        p = Echo('Submitting admin information...')
        self.browser.submit()
        p.done()

        if len(prompted) >= 3:
            save = click.confirm('Would you like to save and use these admin credentials for future installations?')
            if save:
                self.log.info('Saving admin login credentials')
                self.ctx.config.set('User', 'AdminUser', user)
                self.ctx.config.set('User', 'AdminPass', password)
                self.ctx.config.set('User', 'AdminEmail', email)
                with open(self.ctx.config_path, 'wb') as cf:
                    self.ctx.config.write(cf)

        self.install()

    def _start_install(self):
        """
        Start the installation
        """
        self._check_title(self.browser.title())
        continue_link = next(self.browser.links(text_regex='Start Installation'))
        self.browser.follow_link(continue_link)

    def _get_mr_link(self):
        """
        Get the MultipleRedirect URL
        @rtype: str
        """
        rsoup = BeautifulSoup(self.browser.response().read(), "html.parser")
        mr_link = rsoup.find('a', {'class': 'button'}).get('href')
        self.log.debug('MultipleRedirect link: %s', mr_link)
        return mr_link

    def _ajax(self, url, method='get', params=None, load_json=True, raise_request=True):
        """
        Perform an Ajax request
        @type   url:        str
        @type   method:     str
        @type   params:     dict or None
        @type   load_json:  bool
        @return:    Tuple with the decoded JSON response and actual response, or just the response if load_json is False
        @rtype:     requests.Response or tuple of (dict or list, requests.Response)
        """
        if 'ajax' in self._sessions:
            ajax = self._sessions['ajax']
        else:
            self.log.debug('Instantiating a new Ajax session')
            ajax = requests.Session()
            ajax.headers.update({'X-Requested-With': 'XMLHttpRequest'})
            ajax.cookies.update(cookiejar())
            ajax.verify = False
            self._sessions['ajax'] = ajax

        response = ajax.request(method, url, params)
        self.log.debug('Ajax response: %s', response.text)
        if raise_request:
            response.raise_for_status()

        if load_json:
            return byteify(json.loads(response.text)), response

        return response

    def _request(self, url, method='get', params=None, raise_request=True):
        """
        Perform a standard HTTP request
        @type   url:            str
        @type   method:         str
        @type   params:         dict or None
        @param  raise_request:  Raise exceptions for HTTP status errors
        @type   raise_request:  bool
        @rtype: requests.Response
        """
        if 'http' in self._sessions:
            http = self._sessions['http']
        else:
            self.log.debug('Instantiating a new HTTP session')
            http = requests.Session()
            http.cookies.update(cookiejar())
            http.verify = False
            self._sessions['http'] = http

        response = http.request(method, url, params)
        self.log.debug('HTTP response code: %s', response.status_code)
        if raise_request:
            response.raise_for_status()

        return response

    def _parse_response(self, url, json_response):
        """
        Parse response data and return the next request URL
        @type   url:            str
        @type   json_response:  list or dict
        @rtype: str
        """
        parts = list(urlparse(url))
        query = parse_qs(parts[4])
        query['mr'] = str(json_response[0]).replace('\'', '"')
        parts[4] = urlencode(query, True)
        return urlunparse(parts)

    def _get_stage(self, json_response):
        """
        Get the current installation stage
        @type   json_response:  list or dict
        @rtype: str
        """
        try:
            return json_response[1]
        except IndexError:
            return 'Installation complete!'

    def _get_progress(self, json_response):
        """
        Get the current installation progress
        @type   json_response:  list or dict
        @rtype: str
        """
        try:
            return round(float(json_response[2]))
        except IndexError:
            return 0

    def _check_if_complete(self, url, json_response):
        """
        Check if a request has been completed and return the redirect URL if it has
        @type   url:            str
        @type   json_response:  list or dict
        @rtype: str or bool
        """
        if 'redirect' in json_response and isinstance(json_response, dict):
            self.log.info('Installation complete')
            return json_response['redirect']

        return False

    def _finalize(self, response):
        """
        Finalize the installation and display a link to the suite
        """
        rsoup = BeautifulSoup(response.text, "html.parser")
        click.echo('------')
        click.secho(rsoup.find('h1', id='elInstaller_welcome').text.strip(), fg='yellow', bold=True)
        click.secho(rsoup.find('p', {'class': 'ipsType_light'}).text.strip(), fg='yellow', dim=True)
        link = rsoup.find('a', {'class': 'ipsButton_primary'}).get('href')
        click.echo(click.style('Go to the suite: ', bold=True) + link + '\n')

    # noinspection PyUnboundLocalVariable
    def install(self):
        """
        Run the actual installation
        """
        self._start_install()
        mr_link = self._get_mr_link()

        # Set up the progress bar
        pbar = ProgressBar(100, 'Running installation...')
        pbar.start()
        mr_j, mr_r = self._ajax(mr_link)

        # Loop until we get a redirect json response
        while True:
            mr_link = self._parse_response(mr_link, mr_j)

            stage = self._get_stage(mr_j)
            progress = self._get_progress(mr_j)
            mr_j, mr_r = self._ajax(mr_link)

            pbar.update(min([progress, 100]), stage)  # NOTE: Response may return progress values above 100

            # If we're done, finalize the installation and break
            redirect = self._check_if_complete(mr_link, mr_j)
            if redirect:
                pbar.finish()
                break

        p = Echo('Finalizing...')
        mr_r = self._request(redirect, raise_request=False)
        p.done()

        # Install developer tools
        if self.site.in_dev:
            DevToolsInstaller(self.ctx, self.site).install()

        # Get the link to our community homepage
        self._finalize(mr_r)


class InstallationError(Exception):
    pass
