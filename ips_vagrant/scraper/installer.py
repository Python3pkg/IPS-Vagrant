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


class Installer(object):

    def __init__(self, ctx, site):
        """
        Initialize a new Installer instance
        @type   ctx:    ips_vagrant.cli.Context
        @type   site:   ips_vagrant.models.sites.Site
        """
        # Debug log
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
        self.log.info('Installation page loaded: %s', title)
        if self._previous_title and title == self._previous_title:
            raise InstallationError('Unexpected page error')

    def start(self):
        """
        Check if we have an active login session set
        @rtype: bool
        """
        self.log.debug('Starting the installation process')
        self.system_check()

    def system_check(self):
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
        self._check_title(self.browser.title())
        self.browser.select_form(nr=0)

        # Set the fields
        self.browser.form['lkey'] = '{license}-TESTINSTALL'.format(license=self.site.license_key)
        self.browser.find_control('eula_checkbox').items[0].selected = True

        # Submit the request
        self.log.debug('Submitting our license')
        self.browser.submit()
        self.log.debug('Response code: %s', self.browser.response().code)

        self.applications()

    def applications(self):
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

        self.site.db_host = 'localhost'
        self.site.db_name = db_name
        self.site.db_user = db_user
        self.site.db_pass = db_pass

        self.browser.select_form(nr=0)
        self.browser.form['sql_host'] = 'localhost'
        self.browser.form['sql_user'] = db_user
        self.browser.form['sql_pass'] = db_pass
        self.browser.form['sql_database'] = db_name
        self.browser.submit()
        self.admin()

    def admin(self):
        self._check_title(self.browser.title())
        self.browser.select_form(nr=0)

        self.browser.form['admin_user'] = 'makoto'  # click.prompt('Admin display name')
        password = 'makoto'  # click.prompt('Admin password', confirmation_prompt='Confirm admin password')
        self.browser.form['admin_pass1'] = password
        self.browser.form['admin_pass2'] = password
        self.browser.form['admin_email'] = 'makoto@makoto.io'  # click.prompt('Admin email')
        self.browser.submit()
        self.install()

    def install(self):
        self._check_title(self.browser.title())
        continue_link = next(self.browser.links(text_regex='Start Installation'))
        self.browser.follow_link(continue_link)

        rsoup = BeautifulSoup(self.browser.response().read())
        cj = self.browser._ua_handlers['_cookies'].cookiejar
        mr_link = rsoup.find('div', {'class': 'ipsMultipleRedirect'})['data-url']
        # mr_link = mr_link.encode('UTF-8')
        mr_link += '&' + urlencode({'mr': 'MA=='})
        self.log.debug('MultipleRedirect link: %s', mr_link)

        s = requests.Session()
        s.headers.update({'X-Requested-With': 'XMLHttpRequest'})
        s.cookies.update(cj)
        r = s.get(mr_link)
        j = json.loads(r.text)

        while True:
            mr_link += '&' + urlencode({'mr': j[0]})

            try:
                stage = j[1]
            except IndexError:
                stage = 'Complete'

            try:
                progress = j[2]
            except IndexError:
                progress = 0

            r = s.get(mr_link)
            j = json.loads(r.text)
            self.log.debug('MultipleRedirect JSON response: %s', str(j))

            if 'redirect' in j:
                break

        self.log.info('Finalizing installation')
        r = s.get(j['redirect'])

        with open('output.html', 'w') as f:
            f.write(r.text)


class InstallationError(Exception):
    pass
