# coding: utf-8
from glob import glob
import os
import re
import logging
import shutil
from sqlalchemy.exc import SQLAlchemyError
import ips_vagrant
from ConfigParser import ConfigParser
from sqlalchemy import create_engine, collate
from sqlalchemy import Column, Integer, Text, ForeignKey, text
from sqlalchemy.orm import relationship, sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from ips_vagrant.common import unparse_version


# Base = sqlahelper.get_base()
# Session = sqlahelper.get_session().config(extension=None)
from ips_vagrant.generators.nginx import ServerBlock

Base = declarative_base()
metadata = Base.metadata

_cfg = ConfigParser()
_cfg.read(os.path.join(os.path.dirname(os.path.realpath(ips_vagrant.__file__)), 'config/ipsv.conf'))
engine = create_engine("sqlite:////{path}"
                       .format(path=os.path.join(_cfg.get('Paths', 'Data'), 'sites.db')))
Base.metadata.bind = engine

session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


class Domain(Base):
    """
    Domain maps
    """
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    extras = Column(Text, nullable=True)
    sites = relationship("Site")

    @classmethod
    def all(cls):
        """
        Return all domains
        @rtype: list of Domain
        """
        Domain = cls
        return Session.query(Domain).all()

    @classmethod
    def get(cls, dname):
        """
        Get the requested domain
        @param  dname:  Domain name
        @type   dname:  str
        @rtype: Domain or None
        """
        Domain = cls
        dname = dname.hostname if hasattr(dname, 'hostname') else dname.lower()
        return Session.query(Domain).filter(Domain.name == dname).first()

    @classmethod
    def get_or_create(cls, dname):
        """
        Get the requested domain, or create it if it doesn't exist already
        @param  dname:  Domain name
        @type   dname:  str
        @rtype: Domain
        """
        Domain = cls
        dname = dname.hostname if hasattr(dname, 'hostname') else dname
        extras = 'www.{dn}'.format(dn=dname) if dname not in ('localhost', ) and not \
            re.match('^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$', dname) else None
        # Fetch the domain entry if it already exists
        logging.getLogger('ipsv.sites.domain').debug('Checking if the domain %s has already been registered', dname)
        domain = Session.query(Domain).filter(Domain.name == dname).first()

        # Otherwise create it now
        if not domain:
            logging.getLogger('ipsv.sites.domain')\
                .debug('Domain name does not yet exist, creating a new database entry')
            domain = Domain(name=dname, extras=extras)
            Session.add(domain)
            Session.commit()

        return domain

    @hybrid_method
    def get_extras(self):
        """
        Get the extra associated domain names (e.g. www.dname.com)
        @rtype: list
        """
        if self.extras:
            return str(self.extras).split(',')

        return []


class Site(Base):
    """
    IPS installation
    """
    __tablename__ = 'sites'

    id = Column(Integer, primary_key=True)
    _name = Column('name', Text, nullable=False)
    slug = Column(Text, nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    root = Column(Text, nullable=False)
    license_key = Column(Text, nullable=False)
    _version = Column('version', Text, nullable=False)
    ssl = Column(Integer, server_default=text("0"))
    ssl_key = Column(Text, nullable=True)
    ssl_certificate = Column(Text, nullable=True)
    spdy = Column(Integer, server_default=text("0"))
    gzip = Column(Integer, server_default=text("1"))
    db_host = Column(Text, nullable=True)
    db_name = Column(Text, nullable=True)
    db_user = Column(Text, nullable=True)
    db_pass = Column(Text, nullable=True)
    enabled = Column(Integer, server_default=text("0"))
    in_dev = Column(Integer, nullable=True, server_default=text("0"))
    domain = relationship("Domain")

    @classmethod
    def all(cls, domain=None):
        """
        Return all sites
        @param  domain: The domain to filter by
        @type   domain: Domain
        @rtype: list of Site
        """
        Site = cls
        site = Session.query(Site)
        if domain:
            site.filter(Site.domain == domain)
        return site.all()

    @classmethod
    def get(cls, domain, name):
        """
        Get the requested site entry
        @param  domain: Domain name
        @type   domain: Domain
        @param  name:   Site name
        @type   name:   str
        @rtype: Domain
        """
        Site = cls
        return Session.query(Site).filter(Site.domain == domain).filter(collate(Site.name, 'NOCASE') == name).first()

    def delete(self, drop_database=True):
        """
        Delete the site entry
        @param  drop_database:  Drop the sites associated MySQL database
        @type   drop_database:  bool
        """
        self.disable()
        Session.delete(self)

        if drop_database and self.db_name:
            mysql = create_engine('mysql://root:secret@localhost')
            mysql.execute('DROP DATABASE IF EXISTS `{db}`'.format(db=self.db_name))
            try:
                mysql.execute('DROP USER `{u}`'.format(u=self.db_user))
            except SQLAlchemyError:
                pass

    @hybrid_property
    def name(self):
        """
        Get the sites name
        @rtype: str
        """
        return self._name

    @name.setter
    def name(self, value):
        """
        Generate the Site's slug (for file paths, URL's, etc.)
        """
        self._name = value
        self.slug = re.sub('[^0-9a-zA-Z_-]+', '_', str(value).lower())
        self.root = os.path.abspath(os.path.join(_cfg.get('Paths', 'HttpRoot'), self.domain.name, self.slug))

    @hybrid_property
    def version(self):
        """
        Get the sites IPS version
        @rtype: str
        """
        return self._version

    @version.setter
    def version(self, value):
        """
        Save the Site's version from a string or version tuple
        @type   value:  tuple or str
        """
        if isinstance(value, tuple):
            value = unparse_version(value)

        self._version = value

    def enable(self, force=False):
        """
        Enable this site
        """
        log = logging.getLogger('ipsv.models.sites.site')
        log.debug('Disabling all other sites under the domain %s', self.domain.name)
        Session.query(Site).filter(Site.id != self.id).filter(Site.domain == self.domain).update({'enabled': 0})

        sites_enabled_path = _cfg.get('Paths', 'NginxSitesEnabled')
        server_config_path = os.path.join(_cfg.get('Paths', 'NginxSitesAvailable'), self.domain.name)
        server_config_path = os.path.join(server_config_path, '{fn}.conf'.format(fn=self.slug))
        symlink_path = os.path.join(sites_enabled_path, '{domain}-{fn}'.format(domain=self.domain.name,
                                                                               fn=os.path.basename(server_config_path)))
        links = glob(os.path.join(sites_enabled_path, '{domain}-*'.format(domain=self.domain.name)))
        for link in links:
            if os.path.islink(link):
                log.debug('Removing existing configuration symlink: %s', link)
                os.unlink(link)
            else:
                if not force:
                    log.error('Configuration symlink path already exists, but it is not a symlink')
                    raise Exception('Misconfiguration detected: symlink path already exists, but it is not a symlink '
                                    'and --force was not passed. Unable to continue')
                log.warn('Configuration symlink path already exists, but it is not a symlink. Removing anyways '
                         'since --force was set')
                if os.path.isdir(symlink_path):
                    shutil.rmtree(symlink_path)
                else:
                    os.remove(symlink_path)

        log.info('Enabling Nginx configuration file')
        os.symlink(server_config_path, symlink_path)

        self.enabled = 1
        Session.commit()

    def disable(self):
        """
        Disable this site
        """
        log = logging.getLogger('ipsv.models.sites.site')
        sites_enabled_path = _cfg.get('Paths', 'NginxSitesEnabled')
        symlink_path = os.path.join(sites_enabled_path, '{domain}-{fn}.conf'.format(domain=self.domain.name,
                                                                                    fn=self.slug))
        log.debug('Symlink path: %s', symlink_path)
        if os.path.islink(symlink_path):
            log.info('Removing configuration symlink: %s', symlink_path)
            os.unlink(symlink_path)

        self.enabled = 0
        Session.commit()

    def write_nginx_config(self):
        """
        Write the Nginx configuration file for this Site
        """
        log = logging.getLogger('ipsv.models.sites.site')
        if not os.path.exists(self.root):
            log.debug('Creating HTTP root directory: %s', self.root)
            os.makedirs(self.root, 0o755)

        # Generate our server block configuration
        server_block = ServerBlock(self)

        server_config_path = os.path.join(_cfg.get('Paths', 'NginxSitesAvailable'), self.domain.name)
        if not os.path.exists(server_config_path):
            log.debug('Creating new configuration path: %s', server_config_path)
            os.makedirs(server_config_path, 0o755)

        server_config_path = os.path.join(server_config_path, '{fn}.conf'.format(fn=self.slug))
        if os.path.exists(server_config_path):
            log.info('Server block configuration file already exists, overwriting: %s', server_config_path)
            os.remove(server_config_path)

        log.info('Writing Nginx server block configuration file')
        with open(server_config_path, 'w') as f:
            f.write(server_block.template)
