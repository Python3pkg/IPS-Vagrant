from collections import OrderedDict
import json
import os
import logging
from zipfile import ZipFile, BadZipfile
import re
from bs4 import BeautifulSoup
from ips_vagrant.common.version import Version
from ips_vagrant.downloaders.downloader import DownloadManager, DownloadMeta


class IpsManager(DownloadManager):
    """
    IPS Versions Manager
    """
    # noinspection PyShadowingBuiltins
    def __init__(self, ctx, license=None):
        """
        @type   ctx:        ips_vagrant.cli.Context
        @type   license:    ips_vagrant.scraper.licenses.LicenseMeta or None
        """
        super(IpsManager, self).__init__(ctx, IpsMeta)
        self.log = logging.getLogger('ipsv.downloader.ips')
        self.license = license
        self.path = os.path.join(self.path, 'ips')
        self.dev_path = os.path.join(self.path, 'dev')
        self.dev_version = None
        self._setup()

    def _populate_latest(self):
        """
        Popular version data for the latest release available for download
        """
        if self.license is None:
            self.log.debug('No license specified, not retrieving latest version information')
            return

        # Submit a request to the client area
        response = self.session.get(self.license.license_url)
        self.log.debug('Response code: %s', response.status_code)
        response.raise_for_status()

        # Load our license page
        soup = BeautifulSoup(response.text, "html.parser")
        script_tpl = soup.find('script', id='download_form')
        form = BeautifulSoup(script_tpl.text, "html.parser").find('form')

        # Parse the response for a download link to the latest IPS release
        version = Version(form.find('label', {'for': 'version_latest'}).text)
        self.log.info('Latest IPS version: %s', version.vstring)
        url = form.get('action')

        # Parse the response for a download link to the latest development release
        dev_version = Version(form.find('label', {'for': 'version_dev'}).text)
        if dev_version:
            self.log.info('Latest IPS development version: %s', version.vstring)
            dev_url = form.get('action')
            self.dev_version = IpsMeta(self, dev_version, request=('post', dev_url, {'version': 'latestdev'}), dev=True)

        # If we have a cache for this version, just add our url to it
        if version.vtuple in self.versions:
            self.log.debug('Latest IPS version already downloaded, applying URL to cache entry')
            self.versions[version.vtuple].request = ('post', url, {'version': 'latest'})
            return

        self.versions[version.vtuple] = IpsMeta(self, version, request=('post', url, {'version': 'latest'}))

    def _read_zip(self, filepath):
        """
        Read an IPS installation zipfile and return the core version number
        @type   filepath:   str
        @rtype: Version
        """
        with ZipFile(filepath) as zip:
            namelist = zip.namelist()
            if re.match(r'^ips_\w{5}/?$', namelist[0]):
                self.log.debug('Setup directory matched: %s', namelist[0])
            else:
                self.log.error('No setup directory matched')
                raise BadZipfile('Unrecognized setup file format')

            versions_path = os.path.join(namelist[0], 'applications/core/data/versions.json')
            if versions_path not in namelist:
                raise BadZipfile('Missing versions.json file')
            versions = json.loads(zip.read(versions_path), object_pairs_hook=OrderedDict)
            vid = next(reversed(versions))
            version = versions[vid]

            self.log.debug('Version matched: %s', version)
            return Version(version, vid)


class IpsMeta(DownloadMeta):
    """
    Version metadata container
    """
    def __init__(self, *args, **kwargs):
        super(IpsMeta, self).__init__(*args, **kwargs)
        self.log = logging.getLogger('ipsv.downloader.ips.meta')
