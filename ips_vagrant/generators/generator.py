from abc import ABCMeta, abstractproperty
from jinja2 import Environment, PackageLoader


class GeneratorAbstract(object):
    """
    Template file generator
    """
    __metaclass__ = ABCMeta

    def __init__(self, template_path):
        self.env = Environment(loader=PackageLoader('ips_vagrant.generators', 'templates'))
        self.tpl = self.env.get_template(template_path)
        self._template_path = template_path
        self._template = None

    @abstractproperty
    def template(self):
        pass
