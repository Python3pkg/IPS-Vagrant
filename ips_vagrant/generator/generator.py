from abc import ABCMeta, abstractproperty
from jinja2 import Environment, PackageLoader


class TemplateGenerator(object):

    __metaclass__ = ABCMeta

    def __init__(self, template_path):
        self.env = Environment(loader=PackageLoader('ips_vagrant.generator', 'templates'))
        self.tpl = self.env.get_template(template_path)
        self._template_path = template_path
        self._template = None

    @abstractproperty
    def template(self):
        pass
