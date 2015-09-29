import logging
import os
import shutil
from tempfile import mkdtemp
from zipfile import ZipFile
import re
from ips_vagrant.common.progress import Echo
from ips_vagrant.downloaders.dev_tools import DevToolsManager


version = None


class DevToolsInstaller(object):

    def __init__(self, ctx, site):
        """
        Initialize a new Installer instance
        @type   ctx:    ips_vagrant.cli.Context
        @param  site:   The IPS Site we are installing
        @type   site:   ips_vagrant.models.sites.Site
        """
        self.log = logging.getLogger('ipsv.installer.dev_tools')
        self.ctx = ctx
        self.site = site

    def install(self):
        """
        Run the actual installation
        """
        p = Echo('Fetching Developer Tools version information...')
        dev_tools = DevToolsManager(self.ctx, self.site)
        status = p.OK if dev_tools.latest.request else p.FAIL
        p.done(status)
        p = Echo('Fetching the required Developer Tools release...')
        if self.site.version in dev_tools.versions:
            self.log.info('Dev Tools version matched for this IPS version')
            dev_version = dev_tools.versions[self.site.version]
            status = p.OK
        else:
            dev_version = None
            for dv in dev_tools.versions:
                if (dev_version is None) or (dv <= self.site.version):
                    dev_version = dev_tools.versions[dv]
            self.log.warn('No Dev Tools for this IPS release found, using closest match (%s)',
                          dev_version.version.vstring)
            status = p.WARN
        filename = dev_tools.get(dev_version)
        p.done(status)

        # Extract dev files
        p = Echo('Extracting Developer Tools...')
        tmpdir = mkdtemp('ips')
        dev_tools_zip = os.path.join(tmpdir, 'dev_tools.zip')
        dev_tools_dir = os.path.join(tmpdir, 'dev_tools')
        os.mkdir(dev_tools_dir)

        shutil.copyfile(filename, dev_tools_zip)
        with ZipFile(dev_tools_zip) as z:
            namelist = z.namelist()
            if re.match(r'^(\d+)|(dev_[0-9a-zA-Z]{5})/?$', namelist[0]):
                self.log.debug('Developer Tools directory matched: %s', namelist[0])
            else:
                self.log.error('No developer tools directory matched, unable to continue')
                raise Exception('Unrecognized dev tools file format, aborting')

            z.extractall(dev_tools_dir)
            self.log.debug('Developer Tools extracted to: %s', dev_tools_dir)
            dev_tmpdir = os.path.join(dev_tools_dir, namelist[0])
            path = dev_tmpdir
            for dirname, dirnames, filenames in os.walk(dev_tmpdir):
                for filepath in dirnames:
                    site_path = os.path.join(self.site.root, dirname.replace(path, ''), filepath)
                    if not os.path.exists(site_path):
                        self.log.debug('Creating directory: %s', site_path)
                        os.mkdir(site_path, 0o755)

                for filepath in filenames:
                    tmp_path = os.path.join(dirname, filepath)
                    site_path = os.path.join(self.site.root, dirname.replace(path, ''), filepath)
                    shutil.copy(tmp_path, site_path)

            self.log.info('Developer Tools copied to: %s', self.site.root)
        shutil.rmtree(tmpdir)
        p.done()

        p = Echo('Putting IPS into IN_DEV mode...')
        const_path = os.path.join(self.site.root, 'constants.php')
        with open(const_path, 'w+') as f:
            f.write("<?php\n")
            f.write("\n")
            f.write("define( 'IN_DEV', TRUE );")
        p.done()
