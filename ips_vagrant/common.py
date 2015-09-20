from urlparse import urlparse


def domain_parse(url):
    """
    urlparse wrapper for user input
    @type   url:    str
    @rtype  urlparse.ParseResult
    """
    url = url.lower()
    if not url.startswith('http://') and not url.startswith('https://'):
        url = '{schema}{host}'.format(schema='http://', host=url)
    url = urlparse(url)
    if not url.hostname:
        raise ValueError('Invalid domain provided')

    # Strip www prefix any additional URL data
    url = '{scheme}://{host}'.format(scheme=url.scheme, host=url.hostname.lstrip('www.'))
    return url
