import os
import logging
import requests
from bs4 import BeautifulSoup
from mechanize import Browser
from .errors import HtmlParserError


class Version(object):
    """
    IPS Versions Scraper
    """
    # noinspection PyShadowingBuiltins
    def __init__(self, ctx, cookiejar, license):
        """
        Initialize a new Login Handler instance
        @type   ctx:        ips_vagrant.cli.Context
        @type   cookiejar:  cookielib.LWPCookieJar
        @type   license:    ips_vagrant.scraper.licenses.LicenseMeta
        """
        self.ctx = ctx
        self.cookiejar = cookiejar
        self.license = license
        self.form = None
        self.log = logging.getLogger('ipsv.scraper.version')

    def get(self):
        """
        Fetch the most recent IPS version(s) available for download
        @return:
        """
        response = requests.get(self.license.license_url, cookies=self.cookiejar)
        self.log.debug('Response code: %s', response.status_code)
        if response.status_code != 200:
            raise HtmlParserError

        soup = BeautifulSoup(response.text, "html.parser")
        script_tpl = soup.find('script', id='download_form')
        self.form = BeautifulSoup(script_tpl.text, "html.parser").find('form')
        return VersionMeta(self)


class VersionMeta(object):
    """
    Version metadata container
    @type   version:    Version
    """
    def __init__(self, version):
        self.form = version.form
        self._version = version
        self.cookiejar = version.cookiejar
        self.filename = None
        self.version = None
        self._action = None
        self._vdir = os.path.join(self._version.ctx.config.get('Paths', 'Data'), 'versions')
        self._browser = Browser()
        self.log = logging.getLogger('ipsv.scraper.version')

        self._parse_form()
        self._check()

    def _parse_form(self):
        self.version = self.form.find('label', {'for': 'version_latest'}).text
        self.log.info('Latest IPS version: %s', self.version)
        self._action = self.form.get('action')

    def _check(self):
        filename = '{fn}.zip'.format(fn=os.path.join(self._vdir, self.version))
        if os.path.isfile(filename):
            self.log.info('Version {v} already downloaded'.format(v=self.version))
            self.filename = filename
            return True

        self.log.info('Version {v} has not been downloaded yet'.format(v=self.version))
        return False

    def download(self):
        # Submit a download request and test the response
        response = requests.post(self._action, {'version': 'latest'}, cookies=self.cookiejar, stream=True)
        if response.status_code != 200:
            self.log.error('Download request failed: %d', response.status_code)
            raise HtmlParserError

        # If we're re-downloading this version, delete the old file
        if self.filename and os.path.isfile(self.filename):
            self.log.info('Removing old version download')
            os.remove(self.filename)

        # Make sure our versions data directory exists
        if not os.path.isdir(os.path.join(self._vdir)):
            self.log.debug('Creating versions data directory')
            os.makedirs(self._vdir, 0o755)

        # Process our file download
        self.filename = os.path.join(self._vdir, '{v}.zip'.format(v=self.version))
        with open(self.filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()

        self.log.info('Version {v} successfully downloaded to {fn}'.format(v=self.version, fn=self.filename))
        return self.filename
