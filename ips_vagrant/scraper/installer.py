import click
import string
import random
import logging
import json
import requests
from hashlib import md5
from urllib import urlencode
from bs4 import BeautifulSoup
from mechanize import Browser
from sqlalchemy import create_engine
from ips_vagrant.common import cookiejar
from ips_vagrant.common.progress_bar import ProgressBar


class Installer(object):

    def __init__(self, ctx, site):
        """
        Initialize a new Installer instance
        @type   ctx:    ips_vagrant.cli.Context
        @param  site:   The IPS Site we are installing
        @type   site:   ips_vagrant.models.sites.Site
        """
        self.log = logging.getLogger('ipsv.installer')
        self._previous_title = None
        self.url = '{scheme}://{host}/admin/install'.format(
            scheme='https' if site.ssl else 'http', host=site.domain.name
        )
        self.site = site
        self.mysql = create_engine('mysql://root:secret@localhost')

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
        rsoup = BeautifulSoup(self.browser.response().read())

        # Check for any errors
        errors = []
        for ul in rsoup.find_all('ul', {'class': 'ipsList_checks'}):
            for li in ul.find_all('li', {'class': 'fail'}):
                errors.append(li.text)

        if errors:
            raise InstallationError(errors)

        # Continue
        continue_link = next(self.browser.links(text_regex='Continue'))
        self.browser.follow_link(continue_link)
        self.license()

    def license(self):
        """
        Submit our license to IPS' servers
        """
        self._check_title(self.browser.title())
        self.browser.select_form(nr=0)

        # Set the fields
        self.browser.form['lkey'] = '{license}-TESTINSTALL'.format(license=self.site.license_key)
        self.browser.find_control('eula_checkbox').items[0].selected = True  # TODO: User prompt?

        # Submit the request
        self.log.debug('Submitting our license')
        self.browser.submit()
        self.log.debug('Response code: %s', self.browser.response().code)

        self.applications()

    def applications(self):
        """
        Select the applications to install (currently hardcoded to install all applications)
        """
        # Check for license submission errors
        try:
            self._check_title(self.browser.title())
        except InstallationError:
            rsoup = BeautifulSoup(self.browser.response().read())
            error = rsoup.find('li', id='license_lkey').find('span', {'class': 'ipsType_warning'}).text
            raise InstallationError(error)

        # TODO: Make this configurable
        self.browser.select_form(nr=0)
        self.browser.submit()
        self.server_details()

    def server_details(self):
        """
        Input server details (database information, etc.)
        """
        self._check_title(self.browser.title())

        # Create the database
        slug = self.site.slug()
        db_name = 'ipsv_{slug}'.format(slug=slug)[:64]
        # MySQL usernames are limited to 16 characters max
        db_user = 'ipsv_{md5}'.format(md5=md5(self.site.domain.name + slug).hexdigest()[:11])
        rand_pass = ''.join(random.SystemRandom()
                            .choice(string.ascii_letters + string.digits) for _ in range(random.randint(16, 24)))
        db_pass = rand_pass
        self.mysql.execute('DROP DATABASE IF EXISTS `{db}`'.format(db=db_name))
        self.mysql.execute('CREATE DATABASE `{db}`'.format(db=db_name))
        self.mysql.execute("GRANT ALL ON {db}.* TO '{u}'@'localhost' IDENTIFIED BY '{p}'"
                           .format(db=db_name, u=db_user, p=db_pass))

        # Save the database connection information
        self.site.db_host = 'localhost'
        self.site.db_name = db_name
        self.site.db_user = db_user
        self.site.db_pass = db_pass

        # Set form fields and submit
        self.browser.select_form(nr=0)
        self.browser.form['sql_host'] = 'localhost'
        self.browser.form['sql_user'] = db_user
        self.browser.form['sql_pass'] = db_pass
        self.browser.form['sql_database'] = db_name
        self.browser.submit()
        self.admin()

    def admin(self):
        """
        Provide admin login credentials
        """
        self._check_title(self.browser.title())
        self.browser.select_form(nr=0)

        self.browser.form['admin_user'] = click.prompt('Admin display name')
        password = click.prompt('Admin password', confirmation_prompt='Confirm admin password')
        self.browser.form['admin_pass1'] = password
        self.browser.form['admin_pass2'] = password
        self.browser.form['admin_email'] = click.prompt('Admin email')
        self.browser.submit()
        self.install()

    def install(self):
        """
        Run the actual installation
        """
        self._check_title(self.browser.title())
        continue_link = next(self.browser.links(text_regex='Start Installation'))
        self.browser.follow_link(continue_link)

        # Get the MultipleRedirect URL
        rsoup = BeautifulSoup(self.browser.response().read())
        cj = self.browser._ua_handlers['_cookies'].cookiejar  # TODO
        mr_link = rsoup.find('div', {'class': 'ipsMultipleRedirect'})['data-url']
        mr_link += '&' + urlencode({'mr': 'MA=='})
        self.log.debug('MultipleRedirect link: %s', mr_link)

        # Set up the progress bar
        pbar = ProgressBar(100, 'Running installation...')
        pbar.start()

        # Set up our requests session and get begin the installation
        s = requests.Session()
        s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
        s.cookies.update(cj)
        r = s.get(mr_link)
        j = json.loads(r.text)

        # Loop until we get a redirect json response
        while True:
            mr_link += '&' + urlencode({'mr': j[0]})

            try:
                stage = j[1]
            except IndexError:
                stage = 'Installation complete!'

            try:
                progress = round(float(j[2]))
            except IndexError:
                progress = 0

            r = s.get(mr_link)
            j = json.loads(r.text)
            self.log.debug('MultipleRedirect JSON response: %s', str(j))
            pbar.update(min([progress, 100]), stage)  # NOTE: Response may return progress values above 100

            # We're done, finalize the installation and break
            if 'redirect' in j:
                pbar.finish()
                break

        self.log.info('Finalizing installation')
        s.get(j['redirect'])


class InstallationError(Exception):
    pass
