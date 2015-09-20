import logging
from bs4 import BeautifulSoup
from mechanize import Browser
from ips_vagrant.common import cookiejar


class Installer(object):

    def __init__(self, ctx, site):
        """
        Initialize a new Login Handler instance
        @type   ctx:    ips_vagrant.cli.Context
        @type   site:   ips_vagrant.models.sites.Site
        """
        # Debug log
        self.log = logging.getLogger('ipsv.installer')
        self.url = '{scheme}://{host}/admin/install'.format(
            scheme='https' if site.ssl else 'http', host=site.domain.name
        )
        self.site = site

        self.cookiejar = cookiejar()
        self.cookies = {cookie.name: cookie.value for cookie in self.cookiejar}

        self.browser = Browser()
        self.browser.set_cookiejar(self.cookiejar)

    def start(self):
        """
        Check if we have an active login session set
        @rtype: bool
        """
        self.log.debug('Starting the installation process')
        self.submit_license()

    def submit_license(self):
        self.browser.open(self.url)
        self.log.info('Installation page loaded: %s', self.browser.title())

        self.browser.select_form(nr=0)

        # Set the fields
        self.browser.form['lkey'] = '{license}-TESTINSTALL'.format(license=self.site.license_key)
        self.browser.find_control('eula_checkbox').items[0].selected = True

        # Submit the request
        self.log.debug('Submitting our license')
        self.browser.submit()
        self.log.debug('Response code: %s', self.browser.response().code)

        # Check our response
        rsoup = BeautifulSoup(self.browser.response().read())

        # If we're still on the license page, get our error
        if rsoup.find('h1', {'class': 'ipsType_pageTitle'}).text == 'Step: License':
            error = rsoup.find('li', id='license_lkey').find('span', {'class': 'ipsType_warning'}).text
            raise InstallationError(error)


class InstallationError(Exception):
    pass
