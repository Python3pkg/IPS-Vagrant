from collections import OrderedDict
import os
import logging
from zipfile import BadZipfile, ZipFile
import re
import json
from bs4 import BeautifulSoup
from ips_vagrant.downloaders import IpsManager
from ips_vagrant.scrapers.errors import HtmlParserError
from ips_vagrant.common.version import Version
from ips_vagrant.downloaders.downloader import DownloadManager, DownloadMeta


class DevToolsManager(DownloadManager):
    """
    IPS Developer Tools Manager
    """
    FILE_URL = 'https://community.invisionpower.com/files/file/7185-developer-tools/'
    DOWNLOAD_URL = 'https://community.invisionpower.com/files/file/7185-developer-tools/?do=download'

    def __init__(self, ctx, site=None):
        """
        @type   ctx:    ips_vagrant.cli.Context
        @param  site:   The IPS Site we are installing developer tools on
        @type   site:   ips_vagrant.models.sites.Site or None
        """
        super(DevToolsManager, self).__init__(ctx, DevToolsMeta)
        self.log = logging.getLogger('ipsv.downloader.dev_tools')
        self.site = site
        self.path = os.path.join(self.path, 'dev_tools')
        self.ips_versions = OrderedDict()
        self._populate_ips_versions()
        self._setup()

    def _populate_ips_versions(self):
        """
        Populate IPS version data for mapping
        @return:
        """
        # Get a map of version ID's from our most recent IPS version
        ips = IpsManager(self.ctx).latest
        with ZipFile(ips.filepath) as zip:
            namelist = zip.namelist()

            ips_versions_path = os.path.join(namelist[0], 'applications/core/data/versions.json')
            if ips_versions_path not in namelist:
                raise BadZipfile('Missing versions.json file')
            self.ips_versions = json.loads(zip.read(ips_versions_path), object_pairs_hook=OrderedDict)
            self.log.debug("%d version ID's loaded from latest IPS release", len(self.ips_versions))

    def _populate_latest(self):
        """
        Populate version data for the latest release available for download
        """
        if self.site is None:
            self.log.debug('No site specified, not retrieving latest version information')
            return

        response = self.session.get(self.FILE_URL)
        self.log.debug('Response code: %s', response.status_code)
        if response.status_code != 200:
            raise HtmlParserError

        rsoup = BeautifulSoup(response.text, "html.parser")
        version = Version(rsoup.find('span', {'data-role': 'versionTitle'}).text.strip())
        self.log.info('Latest Dev Tools version: %s', version)

        # If we have a cache for this version, just add our url to it
        if version.vtuple in self.versions:
            self.log.debug('Latest IPS version already downloaded, applying URL to cache entry')
            self.versions[version.vtuple].request = ('get', self.DOWNLOAD_URL)
            return

        self.versions[version.vtuple] = DevToolsMeta(self, version, request=('get', self.DOWNLOAD_URL))

    def _read_zip(self, filepath):
        """
        Read an IPS installation zipfile and return the core version number
        @type   filepath:   str
        @rtype: LooseVersion
        """
        with ZipFile(filepath) as zip:
            namelist = zip.namelist()
            if re.match(r'^\d+/?$', namelist[0]):
                self.log.debug('Developer Tools directory matched: %s', namelist[0])
                version_id = namelist[0].strip('/')
            else:
                basename = os.path.basename(filepath)
                match = re.match('^IPS_Developer_Tools_v(\d+).zip$', basename)
                if match:
                    self.log.info('Could not parse dev_tools archive, pulling version id from filename instead')
                    version_id = match.group(1)
                else:
                    self.log.error('No developer tools directory matched, unable to continue')
                    raise BadZipfile('Unrecognized dev tools file format, aborting')

            if version_id not in self.ips_versions:
                raise BadZipfile('Unrecognized version ID (is the dev tools package newer than our latest IPS release?)')
            version = self.ips_versions[version_id]

            self.log.debug('Version matched: %s', version)
            return Version(version, version_id)


class DevToolsMeta(DownloadMeta):
    """
    Developer Tools metadata container
    """
    def __init__(self, *args, **kwargs):
        super(DevToolsMeta, self).__init__(*args, **kwargs)
        self.log = logging.getLogger('ipsv.downloader.dev_tools.meta')
