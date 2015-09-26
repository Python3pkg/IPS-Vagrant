import logging
import os
import shutil
from tempfile import mkdtemp
from zipfile import ZipFile
import re
from ips_vagrant.common.progress import Echo
from ips_vagrant.downloaders.dev_tools import DevTools


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
        dev_tools = DevTools(self.ctx, self.site).get()
        p.done()
        p = Echo('Downloading the most recent Developer Tools release...')
        filename = dev_tools.filename if dev_tools.filename and self.ctx.cache else dev_tools.download()
        p.done()

        # Extract dev files
        p = Echo('Extracting Developer Tools...')
        tmpdir = mkdtemp('ips')
        dev_tools_zip = os.path.join(tmpdir, 'dev_tools.zip')
        dev_tools_dir = os.path.join(tmpdir, 'dev_tools')
        os.mkdir(dev_tools_dir)

        shutil.copyfile(filename, dev_tools_zip)
        with ZipFile(dev_tools_zip) as z:
            namelist = z.namelist()
            if re.match(r'^\d+/?$', namelist[0]):
                self.log.debug('Developer Tools directory matched: %s', namelist[0])
            else:
                self.log.error('No developer tools directory matched, unable to continue')
                raise Exception('Unrecognized dev tools file format, aborting')

            z.extractall(dev_tools_dir)
            self.log.debug('Developer Tools extracted to: %s', dev_tools_dir)
            dev_tmpdir = os.path.join(dev_tools_dir, namelist[0])
            for filename in os.listdir(dev_tmpdir):
                shutil.copy(os.path.join(dev_tmpdir, filename), os.path.join(self.site.root, filename))

            self.log.info('Developer Tools copied to: %s', self.site.root)
        shutil.rmtree(tmpdir)
        p.done()

        p = Echo('Putting IPS into IN_DEV mode...')
        const_path = os.path.join(self.site.root, 'constants.php')
        with open(const_path, 'w+') as f:
            f.write('<?php')
            f.write('')
            f.write("define( 'IN_DEV', TRUE );")
        p.done()
