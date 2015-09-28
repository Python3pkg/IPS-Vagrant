import importlib
import logging
from collections import OrderedDict
import os
import pkgutil


versions = OrderedDict()
path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
_modnames = [name for __, name, ispkg in pkgutil.iter_modules([path]) if not ispkg]
for modname in _modnames:
    m = importlib.import_module('ips_vagrant.installer.dev_tools.{name}'.format(name=modname))
    versions[getattr(m, 'version')] = getattr(m, 'DevToolsInstaller')
versions = OrderedDict(sorted(versions.items(), key=lambda v: v[0]))


def dev_tools_installer(cv, ctx, site):
    """
    Installer factory
    @param  cv: Current version (The version of Developer Tools we are installing)
    @type   cv: ips_vagrant.common.version.Version
    @return:    Installer instance
    @rtype:     ips_vagrant.installer.dev_tools.latest.DevToolsInstaller
    """
    log = logging.getLogger('ipsv.installer.dev_tools')
    log.info('Loading installer for Dev Tools %s', cv)
    iv = None
    for v in versions:
        vstring = '.'.join(map(str, v)) if v else 'latest'
        # cvstring = '.'.join(map(str, cv)) if cv else 'latest'
        log.debug('Checking if version %s >= %s', vstring, cv.vstring)
        if (v is None) or (v >= cv):
            log.debug('Changing installer version to %s', vstring)
            iv = v

    log.info('Returning installer version %s', '.'.join(map(str, iv)) if iv else 'latest')
    return versions[iv](ctx, site)
