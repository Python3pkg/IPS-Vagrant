import logging
from collections import OrderedDict
import os
import pkgutil

versions = OrderedDict()
path = os.path.join(os.path.dirname(os.path.realpath(__file__)))
for importer, modname, ispkg in pkgutil.iter_modules([path]):
    m = importer.find_module(modname).load_module(modname)
    versions[m.version] = m
versions = OrderedDict(sorted(versions.items(), key=lambda v: v[0]))


def installer(cv, ctx, site):
    """
    Installer factory
    @param  cv: Current version (The version of IPS we are installing)
    @type   cv: tuple
    @return:    Installer instance
    @rtype:     ips_vagrant.installer.latest.Installer
    """
    log = logging.getLogger('ipsv.installer')
    log.info('Loading installer for IPS %s', cv)
    iv = None
    for v in versions:
        if (v is None) or (v >= cv):
            log.debug('Changing installer version to %s', '.'.join(map(str, v)) if v else 'latest')
            iv = v

    log.info('Returning installer version %s', '.'.join(map(str, iv)) if iv else 'latest')
    return versions[iv](ctx, site)
