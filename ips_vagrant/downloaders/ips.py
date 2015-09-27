from collections import OrderedDict
from glob import glob
import json
import os
import logging
from zipfile import ZipFile, BadZipfile
import re
from bs4 import BeautifulSoup
from mechanize import Browser
from ips_vagrant.common import http_session, parse_version, unparse_version
from ips_vagrant.scrapers.errors import HtmlParserError


class IpsManager(object):
    """
    IPS Versions Manager
    """
    # noinspection PyShadowingBuiltins
    def __init__(self, ctx, license=None):
        """
        @type   ctx:        ips_vagrant.cli.Context
        @type   license:    ips_vagrant.scraper.licenses.LicenseMeta or None
        """
        self.ctx = ctx
        self.log = logging.getLogger('ipsv.scraper.version')
        self.session = http_session(ctx.cookiejar)
        self.license = license

        self.path = os.path.join(self.ctx.config.get('Paths', 'Data'), 'versions', 'ips')
        self.versions = OrderedDict()

        self._populate_local()
        self._populate_latest()
        self._sort()

    def _sort(self):
        """
        Sort versions by their version number
        """
        self.versions = OrderedDict(sorted(self.versions.items(), key=lambda v: v[0]))

    def _populate_local(self):
        """
        Populate version data for local archives
        """
        archives = glob(os.path.join(self.path, '*.zip'))
        for archive in archives:
            try:
                version = self._read_zip(archive)
                self.versions[version.version] = IpsMeta(self, version.version, filepath=archive)
            except BadZipfile as e:
                self.log.warn('Unreadable zip archive in IPS versions directory (%s): %s', e.message, archive)

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
        version = parse_version(form.find('label', {'for': 'version_latest'}).text)
        self.log.info('Latest IPS version: %s', version)
        url = form.get('action')

        # If we have a cache for this version, just add our url to it
        if version.version in self.versions:
            self.log.debug('Latest IPS version already downloaded, applying URL to cache entry')
            self.versions[version.version].request = ('post', url, {'version': 'latest'})
            return

        self.versions[version.version] = IpsMeta(self, version.version, request=('post', url, {'version': 'latest'}))

    def _read_zip(self, filepath):
        """
        Read an IPS installation zipfile and return the core version number
        @type   filepath:   str
        @rtype: LooseVersion
        """
        with ZipFile(filepath) as zip:
            namelist = zip.namelist()
            if re.match(r'^ips_\w{5}\/?$', namelist[0]):
                self.log.debug('Setup directory matched: %s', namelist[0])
            else:
                self.log.error('No setup directory matched')
                raise BadZipfile('Unrecognized setup file format')

            versions_path = os.path.join(namelist[0], 'applications/core/data/versions.json')
            if versions_path not in namelist:
                raise BadZipfile('Missing versions.json file')
            versions = json.loads(zip.read(versions_path), object_pairs_hook=OrderedDict)
            version = versions[next(reversed(versions))]

            self.log.debug('Version matched: %s', version)
            return parse_version(version)

    def get(self, version, use_cache=True):
        """
        Get the filepath to the specified version (downloading it in the process if necessary)
        @type   version:    IpsMeta
        @param  use_cache:  Use cached version downloads if available
        @type   use_cache:  bool
        @rtype: str
        """
        self.log.info('Retrieving version %s', version.version)

        if version.filepath:
            if use_cache:
                return version.filepath
            else:
                self.log.info('Ignoring cached version: %s', version.version)
        elif not use_cache:
            self.log.info("We can't ignore the cache of a version that hasn't been downloaded yet")

        version.download()
        return version.filepath

    @property
    def latest(self):
        return self.versions[next(reversed(self.versions))]


class IpsMeta(object):
    """
    Version metadata container
    """
    def __init__(self, ips_manager, version, filepath=None, request=None):
        """
        @type   ips_manager:    IpsManager
        @type   version:        LooseVersion
        @type   filepath:       str or None
        @type   request:        tuple or None (method, url, params)
        """
        self.ips_manager = ips_manager
        self.filepath = filepath
        self.version = version
        self.request = request
        self.log = logging.getLogger('ipsv.scraper.version')

        self.session = self.ips_manager.session
        self._browser = Browser()

    def download(self):
        """
        Download the latest IPS release
        @return:    Download file path
        @rtype:     str
        """
        # Submit a download request and test the response
        self.log.debug('Submitting request: %s', self.request)
        response = self.session.request(*self.request, stream=True)
        if response.status_code != 200:
            self.log.error('Download request failed: %d', response.status_code)
            raise HtmlParserError

        # If we're re-downloading this version, delete the old file
        if self.filepath and os.path.isfile(self.filepath):
            self.log.info('Removing old version download')
            os.remove(self.filepath)

        # Make sure our versions data directory exists
        if not os.path.isdir(os.path.join(self.ips_manager.path)):
            self.log.debug('Creating versions data directory')
            os.makedirs(self.ips_manager.path, 0o755)

        # Process our file download
        self.filepath = self.filepath or os.path.join(self.ips_manager.path, '{v}.zip'
                                                      .format(v=unparse_version(self.version)))
        with open(self.filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()

        self.log.info('Version {v} successfully downloaded to {fn}'.format(v=self.version, fn=self.filepath))
        self.filepath = self.filepath
