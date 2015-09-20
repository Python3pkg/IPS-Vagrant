import os
import logging
import cookielib
import ips_vagrant
from urlparse import urlparse
from ConfigParser import ConfigParser


def config():
    """
    Load system configuration
    @rtype: ConfigParser
    """
    cfg = ConfigParser()
    cfg.read(os.path.join(os.path.dirname(os.path.realpath(ips_vagrant.__file__)), 'config/ipsv.conf'))


def domain_parse(url):
    """
    urlparse wrapper for user input
    @type   url:    str
    @rtype: urlparse.ParseResult
    """
    url = url.lower()
    if not url.startswith('http://') and not url.startswith('https://'):
        url = '{schema}{host}'.format(schema='http://', host=url)
    url = urlparse(url)
    if not url.hostname:
        raise ValueError('Invalid domain provided')

    # Strip www prefix any additional URL data
    url = urlparse('{scheme}://{host}'.format(scheme=url.scheme, host=url.hostname.lstrip('www.')))
    return url


def cookiejar():
    """
    Ready the CookieJar, loading a saved session if available
    @rtype: cookielib.LWPCookieJar
    """
    log = logging.getLogger('ipsv.common.cookiejar')
    spath = os.path.join(config().get('Paths', 'Data'), 'session.txt')
    cj = cookielib.LWPCookieJar(spath)
    log.debug('Attempting to load session file: %s', spath)
    if os.path.exists(spath):
        try:
            cj.load()
            log.info('Successfully loaded a saved login session')
        except cookielib.LoadError as e:
            log.warn('Session / cookie file exists, but could not be loaded', exc_info=e)

    return cj
