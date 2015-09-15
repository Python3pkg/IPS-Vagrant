import logging
from mechanize import Browser
from cookielib import CookieJar


class Login(object):

    # Form constants
    LOGIN_URL = 'https://www.invisionpower.com/clients/index.php?app=core&module=global&section=login'
    USERNAME_FIELD = 'ips_username'
    PASSWORD_FIELD = 'ips_password'
    REMEMBER_FIELD = 'rememberMe'

    # Cookie constants
    LOGIN_COOKIE = 'ips_pass_hash'

    def __init__(self, username, password, remember=True):
        # Debug log
        self.log = logging.getLogger('ipsv.login')

        self.username = username
        self.password = password
        self.remember = remember

        self.cookiejar = CookieJar()
        self.cookies = {}
        self.browser = Browser()
        self.browser.set_cookiejar(self.cookiejar)

    def process(self):
        self.log.debug('Processing login request')

        self.browser.open(self.LOGIN_URL)
        self.log.info('Login page loaded: %s', self.browser.title())

        self.browser.select_form(nr=0)

        # Set the fields
        self.log.debug('Username: %s', self.username)
        self.log.debug('Password: %s', (self.password[0] + '*' * (len(self.password) - 2) + self.password[-1]))
        self.log.debug('Remember: %s', self.remember)
        self.browser.form[self.USERNAME_FIELD] = self.username
        self.browser.form[self.PASSWORD_FIELD] = self.password
        self.browser.find_control(self.REMEMBER_FIELD).items[0].selected=True

        # Submit the request
        self.browser.submit()
        self.log.debug('Response code: %s', self.browser.response().code)

        self.log.debug('== Cookies ==')
        for cookie in self.cookiejar:
            self.log.debug(cookie)
            self.cookies[cookie.name] = cookie.value
        self.log.debug('== End Cookies ==')

        # Make sure we successfully logged in
        if self.LOGIN_COOKIE not in self.cookies:
            raise BadLoginException('No login cookie returned, this probably means an invalid login was provided')

        self.log.info('Login request successful')


class BadLoginException(Exception):
    pass
