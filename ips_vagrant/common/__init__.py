from distutils.version import StrictVersion, LooseVersion
import os
import click
import logging
import cookielib
import requests
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
    return cfg


def choice(opts, default=1, text='Please make a choice.'):
    """
    Prompt the user to select an option
    @param  opts:   List of tuples containing options in (key, value) format - value is optional
    @type   opts:   list of tuple
    @param  text:   Prompt text
    @type   text:   str
    """
    opts_len = len(opts)
    opts_enum = enumerate(opts, 1)
    opts = list(opts)

    for key, opt in opts_enum:
        click.echo('[{k}] {o}'.format(k=key, o=opt[1] if isinstance(opt, tuple) else opt))

    click.echo('-' * 12)
    opt = click.prompt(text, default, type=click.IntRange(1, opts_len))
    opt = opts[opt - 1]
    return opt[0] if isinstance(opt, tuple) else opt


def styled_status(enabled, bold=True):
    """
    Generate a styled status string
    @param  enabled:    Enabled / Disabled boolean
    @type   enabled:    bool
    @param  bold:       Display status in bold format
    @type   bold:       bool
    @rtype: str
    """
    return click.style('Enabled' if enabled else 'Disabled', 'green' if enabled else 'red', bold=bold)


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


def http_session(cookies=None):
    """
    Generate a Requests session
    @param  cookies:    Cookies to load. None loads the app default CookieJar. False disables cookie loading.
    @type   cookies:    dict, cookielib.LWPCookieJar, None or False
    @rtype  requests.Session
    """
    session = requests.Session()
    if cookies is not False:
        session.cookies.update(cookies or cookiejar())
    session.headers.update({'User-Agent': 'ipsv/{v}'.format(v=ips_vagrant.__version__)})

    return session


def cookiejar(name='session'):
    """
    Ready the CookieJar, loading a saved session if available
    @rtype: cookielib.LWPCookieJar
    """
    log = logging.getLogger('ipsv.common.cookiejar')
    spath = os.path.join(config().get('Paths', 'Data'), '{n}.txt'.format(n=name))
    cj = cookielib.LWPCookieJar(spath)
    log.debug('Attempting to load session file: %s', spath)
    if os.path.exists(spath):
        try:
            cj.load()
            log.info('Successfully loaded a saved session / cookie file')
        except cookielib.LoadError as e:
            log.warn('Session / cookie file exists, but could not be loaded', exc_info=e)

    return cj


def parse_version(vstring):
    """
    StrictVersion / LooseVersion decorator method
    @type   vstring:    str
    @return:    StrictVersion if possible, otherwise LooseVersion
    @rtype:     StrictVersion or LooseVersion
    """
    try:
        version = StrictVersion(vstring)
    except ValueError:
        logging.getLogger('ipvs.common.debug').info('Strict parsing failed, falling back to LooseVersion instead')
        version = LooseVersion(vstring)
        version.version = tuple(version.version)

    return version


def unparse_version(vtuple):
    """
    Return the textual representation of a version tuple
    @type   vtuple: tuple
    @rtype: str
    """
    return '.'.join(map(str, vtuple))


def byteify(input):
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input
