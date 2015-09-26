import os
import logging
import requests
from bs4 import BeautifulSoup
from ips_vagrant.scrapers.errors import HtmlParserError
from ips_vagrant.common import cookiejar


class DevTools(object):
    """
    IPS Developer Tools Scraper
    """
    FILE_URL = 'https://community.invisionpower.com/files/file/7185-developer-tools/'
    DOWNLOAD_URL = 'https://community.invisionpower.com/files/file/7185-developer-tools/?do=download'

    def __init__(self, ctx, site):
        """
        @type   ctx:    ips_vagrant.cli.Context
        @param  site:   The IPS Site we are installing developer tools on
        @type   site:   ips_vagrant.models.sites.Site
        """
        self.log = logging.getLogger('ipsv.scraper.dev_tools')
        self.ctx = ctx

        self.cookiejar = cookiejar()
        self.cookies = {cookie.name: cookie.value for cookie in self.cookiejar}

        self.session = requests.Session()
        self.session.cookies.update(self.cookiejar)
        self.session.headers.update({'User-Agent': 'ipsv/0.1.0'})

    def get(self):
        """
        Return metadata on the most recent Developer Tools release
        @rtype: DevToolsMeta
        """
        r = self.session.get(self.FILE_URL)
        self.log.debug('Response code: %s', r.status_code)
        if r.status_code != 200:
            raise HtmlParserError

        rsoup = BeautifulSoup(r.text, "html.parser")
        version = rsoup.find('span', {'data-role': 'versionTitle'}).text.strip()
        return DevToolsMeta(self, version)


class DevToolsMeta(object):
    """
    Developer Tools metadata container
    @type   dev_tools:  DevTools
    @type   version:    str
    """
    def __init__(self, dev_tools, version):
        self._dev_tools = dev_tools
        self.version = version
        self.filename = None
        self.session = dev_tools.session
        self._vdir = os.path.join(self._dev_tools.ctx.config.get('Paths', 'Data'), 'versions', 'dev_tools')
        self.log = logging.getLogger('ipsv.scraper.version')

        self.check()

    def check(self):
        """
        Check if we have already downloaded this version (and save its path if we have)
        @type:  bool
        """
        filename = '{fn}.zip'.format(fn=os.path.join(self._vdir, self.version))
        if os.path.isfile(filename):
            self.log.info('Developer Tools {v} already downloaded'.format(v=self.version))
            self.filename = filename
            return True

        self.log.info('Developer Tools {v} has not been downloaded yet'.format(v=self.version))
        return False

    def download(self):
        """
        Download the latest developer tools release
        @return:    Download file path
        @rtype:     str
        """
        # Submit a download request and test the response
        response = self.session.get(self._dev_tools.DOWNLOAD_URL, stream=True)
        if response.status_code != 200:
            self.log.error('Download request failed: %d', response.status_code)
            raise HtmlParserError

        # If we're re-downloading this version, delete the old file
        if self.filename and os.path.isfile(self.filename):
            self.log.info('Removing old dev tools download')
            os.remove(self.filename)

        # Make sure our versions data directory exists
        if not os.path.isdir(os.path.join(self._vdir)):
            self.log.debug('Creating dev tools versions data directory')
            os.makedirs(self._vdir, 0o755)

        # Process our file download
        self.filename = os.path.join(self._vdir, '{v}.zip'.format(v=self.version))
        with open(self.filename, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()

        self.log.info('Developer tools {v} successfully downloaded to {fn}'.format(v=self.version, fn=self.filename))
        return self.filename
