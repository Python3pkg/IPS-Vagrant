import os
import logging
import requests
import cookielib
from mechanize import Browser


class Login(object):

    # Form constants
    LOGIN_URL = 'https://www.invisionpower.com/clients/index.php?app=core&module=global&section=login'
    TEST_URL = 'https://www.invisionpower.com/clients/index.php?app=nexus&module=clients&section=purchases'
    USERNAME_FIELD = 'ips_username'
    PASSWORD_FIELD = 'ips_password'
    REMEMBER_FIELD = 'rememberMe'

    # Cookie constants
    LOGIN_COOKIE = 'ips_pass_hash'

    def __init__(self, ctx):
        """
        Initialize a new Login Handler instance
        @type   ctx:    ips_vagrant.cli.Context
        """
        # Debug log
        self.log = logging.getLogger('ipsv.login')

        # Ready our CookieJar, loading a saved session if available
        spath = os.path.join(ctx.config.get('Paths', 'Data'), 'session.txt')
        self.cookiejar = cookielib.LWPCookieJar(spath)
        self.cookies = {}

        self.log.debug('Attempting to load session file: %s', spath)
        if os.path.exists(spath):
            try:
                self.cookiejar.load()
                self.cookies = {cookie.name: cookie.value for cookie in self.cookiejar}
                self.log.info('Successfully loaded a saved login session')
            except cookielib.LoadError as e:
                self.log.warn('Session / cookie file exists, but could not be loaded', exc_info=e)

        self.browser = Browser()
        self.browser.set_cookiejar(self.cookiejar)

    def check(self):
        """
        Check if we have an active login session set
        @rtype: bool
        """
        self.log.debug('Testing for a valid login session')
        # If our cookie jar is empty, we obviously don't have a valid login session
        if not len(self.cookiejar):
            return False

        # Test our login session and make sure it's still active
        return requests.get(self.TEST_URL, cookies=self.cookiejar).status_code == 200

    def process(self, username, password, remember=True):
        self.log.debug('Processing login request')

        self.browser.open(self.LOGIN_URL)
        self.log.info('Login page loaded: %s', self.browser.title())

        self.browser.select_form(nr=0)

        # Set the fields
        self.log.debug('Username: %s', username)
        self.log.debug('Password: %s', (password[0] + '*' * (len(password) - 2) + password[-1]))
        self.log.debug('Remember: %s', remember)
        self.browser.form[self.USERNAME_FIELD] = username
        self.browser.form[self.PASSWORD_FIELD] = password
        self.browser.find_control(self.REMEMBER_FIELD).items[0].selected = remember

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

        # Should we save our login session?
        if remember:
            self.log.info('Saving login session to disk')
            self.cookiejar.save()

        self.log.info('Login request successful')
        return self.cookiejar


class BadLoginException(Exception):
    pass
