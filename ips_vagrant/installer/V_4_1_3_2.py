import click

from ips_vagrant.common.progress import ProgressBar, Echo
from ips_vagrant.installer.dev_tools.latest import DevToolsInstaller
from ips_vagrant.installer.latest import Installer as Latest


version = (4, 1, 3, 2)


class Installer(Latest):

    def start(self):
        """
        Start the installation wizard
        """
        self.log.debug('Starting the installation process')

        self.browser.open(self.url)

        self.system_check()

    def admin(self):
        """
        Provide admin login credentials
        """
        self._check_title(self.browser.title())
        self.browser.select_form(nr=0)

        # Get the admin credentials
        prompted = []
        user = self.ctx.config.get('User', 'AdminUser')
        if not user:
            user = click.prompt('Admin display name')
            prompted.append('user')

        password = self.ctx.config.get('User', 'AdminPass')
        if not password:
            password = click.prompt('Admin password', hide_input=True, confirmation_prompt='Confirm admin password')
            prompted.append('password')

        email = self.ctx.config.get('User', 'AdminEmail')
        if not email:
            email = click.prompt('Admin email')
            prompted.append('email')

        self.browser.form[self.FIELD_ADMIN_USER] = user
        self.browser.form[self.FIELD_ADMIN_PASS] = password
        self.browser.form[self.FIELD_ADMIN_PASS_CONFIRM] = password
        self.browser.form[self.FIELD_ADMIN_EMAIL] = email
        p = Echo('Submitting admin information...')
        self.browser.submit()
        p.done()

        if len(prompted) >= 3:
            save = click.confirm('Would you like to save and use these admin credentials for future installations?')
            if save:
                self.log.info('Saving admin login credentials')
                self.ctx.config.set('User', 'AdminUser', user)
                self.ctx.config.set('User', 'AdminPass', password)
                self.ctx.config.set('User', 'AdminEmail', email)
                with open(self.ctx.config_path, 'wb') as cf:
                    self.ctx.config.write(cf)

        self.install()

    def _start_install(self):
        """
        Start the installation
        """
        self._check_title(self.browser.title())
        continue_link = next(self.browser.links(text_regex='Start Installation'))
        self.browser.follow_link(continue_link)

    # noinspection PyUnboundLocalVariable
    def install(self):
        """
        Run the actual installation
        """
        self._start_install()
        mr_link = self._get_mr_link()

        # Set up the progress bar
        pbar = ProgressBar(100, 'Running installation...')
        pbar.start()
        mr_j, mr_r = self._ajax(mr_link)

        # Loop until we get a redirect json response
        while True:
            mr_link = self._parse_response(mr_link, mr_j)

            stage = self._get_stage(mr_j)
            progress = self._get_progress(mr_j)
            mr_j, mr_r = self._ajax(mr_link)

            pbar.update(min([progress, 100]), stage)  # NOTE: Response may return progress values above 100

            # If we're done, finalize the installation and break
            redirect = self._check_if_complete(mr_link, mr_j)
            if redirect:
                pbar.finish()
                break

        p = Echo('Finalizing...')
        mr_r = self._request(redirect, raise_request=False)
        p.done()

        # Install developer tools
        if self.site.in_dev:
            DevToolsInstaller(self.ctx, self.site).install()

        # Get the link to our community homepage
        self._finalize(mr_r)
