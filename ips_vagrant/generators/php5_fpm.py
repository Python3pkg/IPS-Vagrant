from .generator import GeneratorAbstract


class FpmPoolConfig(GeneratorAbstract):

    def __init__(self):
        """
        Initialize a new php5-fpm pool config template container
        """
        super(FpmPoolConfig, self).__init__('php5-fpm/pool.tpl')

    @property
    def template(self):
        """
        @return:    Parsed template
        @rtype:     str
        """
        if not self._template:
            self._template = self.tpl.render()

        return self._template
