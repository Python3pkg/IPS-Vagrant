import re
import logging
import requests
from bs4 import BeautifulSoup
from .errors import HtmlParserError


class Licenses(object):
    """
    IPS License Data Scraper
    """
    URL = 'https://www.invisionpower.com/clients/index.php?app=nexus&module=clients&section=purchases'

    def __init__(self, login_session):
        """
        Initialize a License Scraper instance
        @type   login_session:  cookielib.CookieJar
        """
        self.cookiejar = login_session
        self.log = logging.getLogger('ipsv.scraper.licenses')

    def get(self):
        """
        Fetch all licenses associated with our account
        @rtype: list of LicenseMeta
        """
        response = requests.get(self.URL, cookies=self.cookiejar)
        self.log.debug('Response code: %s', response.status_code)
        if response.status_code != 200:
            raise HtmlParserError

        soup = BeautifulSoup(response.text, "html.parser")
        com_pattern = re.compile('\((.+)\)')

        package_list = soup.find('ul', {'id': 'package_list'})
        package_items = package_list.find_all('li')

        licenses = []
        for item in package_items:
            div = item.find('div', {'class': 'product_info'})
            a = div.find('a')
            licenses.append(
                LicenseMeta(
                    div.find('span', {'class': 'desc'}).text,
                    a.get('href'),
                    com_pattern.search(a.text).group(1)
                )
            )

        return licenses


class LicenseMeta(object):
    """
    License metadata container
    """
    def __init__(self, license_key, license_url, community_url):
        """
        Initialize a LicenseMeta instance
        @type   license_key:    str
        @param  license_url:    URL to the license information page
        @type   license_url:    str
        @param  community_url:  URL to the licenses associated community
        @type   community_url:  str
        """
        self.license_key = license_key
        self.license_url = license_url
        self.community_url = community_url

        self.log = logging.getLogger('ipsv.scraper.licenses')

        if not all((self.license_key, self.license_url, self.community_url)):
            raise HtmlParserError

        self.log.info('License: {lk} ; License URL: {lu} ; Community URL: {cu}'
                      .format(lk=self.license_key, lu=license_url, cu=self.community_url))
