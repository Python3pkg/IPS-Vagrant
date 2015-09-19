from .generator import TemplateGenerator


class ServerBlock(TemplateGenerator):

    def __init__(self, site):
        """
        Initialize a new Nginx Server Block template container
        @param  site:   Site to generate a server block for
        @type   site:   ips_vagrant.models.sites.Site
        """
        super(ServerBlock, self).__init__('nginx/server.tpl')
        self.site = site

    @property
    def template(self):
        if not self._template:
            self._template = self.tpl.render(site=self.site)

        return self._template
