from collections import OrderedDict
from glob import glob
import os
import logging
from zipfile import BadZipfile
from abc import abstractmethod, ABCMeta
from mechanize import Browser
from ips_vagrant.common import http_session, unparse_version
from ips_vagrant.scrapers.errors import HtmlParserError


class DownloadManager(object):
    """
    IPS Versions Manager
    """

    __metaclass__ = ABCMeta

    # noinspection PyShadowingBuiltins
    def __init__(self, ctx, meta_class):
        """
        @type   ctx:        ips_vagrant.cli.Context
        @type   license:    ips_vagrant.scraper.licenses.LicenseMeta or None
        """
        self.ctx = ctx
        self.log = logging.getLogger('ipsv.downloader')
        self.session = http_session(ctx.cookiejar)
        self.meta_class = meta_class
        self.meta_name = self.meta_class.__name__

        self.path = os.path.join(self.ctx.config.get('Paths', 'Data'), 'versions')
        self.dev_path = NotImplemented
        self.versions = OrderedDict()

    def _setup(self):
        """
        Run setup tasks after initialization
        """
        self._populate_local()
        try:
            self._populate_latest()
        except Exception as e:
            self.log.exception('Unable to retrieve latest %s version information', self.meta_name)
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
                self.versions[version.vtuple] = self.meta_class(self, version, filepath=archive)
            except BadZipfile as e:
                self.log.warn('Unreadable zip archive in versions directory (%s): %s', e.message, archive)

    @abstractmethod
    def _populate_latest(self):
        """
        Populate version data for the latest release available for download
        """
        pass

    @abstractmethod
    def _read_zip(self, filepath):
        """
        Read an IPS installation zipfile and return the core version number
        @type   filepath:   str
        @rtype: LooseVersion
        """
        pass

    def get(self, version, use_cache=True):
        """
        Get the filepath to the specified version (downloading it in the process if necessary)
        @type   version:    IpsMeta
        @param  use_cache:  Use cached version downloads if available
        @type   use_cache:  bool
        @rtype: str
        """
        self.log.info('Retrieving %s version %s', self.meta_name, version.version)

        if version.filepath:
            if use_cache:
                return version.filepath
            else:
                self.log.info('Ignoring cached %s version: %s', self.meta_name, version.version)
        elif not use_cache:
            self.log.info("We can't ignore the cache of a version that hasn't been downloaded yet")

        version.download()
        return version.filepath

    @property
    def latest(self):
        return self.versions[next(reversed(self.versions))]


class DownloadMeta(object):
    """
    Version metadata container
    """
    def __init__(self, manager, version, filepath=None, request=None, dev=False):
        """
        @type   manaer:     DownloadManager
        @type   version:    ips_vagrant.common.version.Version
        @type   filepath:   str or None
        @type   request:    tuple or None (method, url, params)
        @param  dev:        Indicates a development version
        @type   dev:        bool
        """
        self.manager = manager
        self.filepath = filepath
        self.version = version
        self.request = request
        self.dev = dev
        self.basedir = self.manager.dev_path if dev else self.manager.path
        self.log = logging.getLogger('ipsv.downloader.meta')

        self.session = self.manager.session
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
        if not os.path.isdir(self.basedir):
            self.log.debug('Creating versions data directory')
            os.makedirs(self.basedir, 0o755)

        # Process our file download
        vslug = self.version.vstring.replace(' ', '-')
        self.filepath = self.filepath or os.path.join(self.basedir, '{v}.zip'.format(v=vslug))
        with open(self.filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()

        self.log.info('Version {v} successfully downloaded to {fn}'.format(v=self.version, fn=self.filepath))
