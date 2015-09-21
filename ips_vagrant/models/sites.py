# coding: utf-8
import os
import re
import logging
import sqlahelper
import ips_vagrant
from ConfigParser import ConfigParser
from sqlalchemy import Column, Integer, Text, ForeignKey, text
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


Base = sqlahelper.get_base()
Session = sqlahelper.get_session()
metadata = Base.metadata


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
    def get_or_create(cls, dname):
        """
        Get the requested domain, or create it if it doesn't exist already
        @param  dname:  Domain name
        @type   dname:  str
        @rtype: Domain
        """
        Domain = cls
        dname = dname.hostname if hasattr(dname, 'hostname') else dname
        extras = 'www.{dn}'.format(dn=dname)
        # Fetch the domain entry if it already exists
        logging.getLogger('ipsv.sites.domain').debug('Checking if the domain %s has already been registered', dname)
        domain = Session.query(Domain).filter(Domain.name == dname).first()

        # Otherwise create it now
        if not domain:
            logging.getLogger('ipsv.sites.domain')\
                .debug('Domain name does not yet exist, creating a new database entry')
            domain = Domain(name=dname, extras=extras)
            Session.add(domain)

        return domain

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
    _name = Column(Text, nullable=False)
    slug = Column(Text, nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    root = Column(Text, nullable=False)
    license_key = Column(Text, nullable=False)
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
    domain = relationship("Domain")

    @property
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
        self.slug = re.sub('[^0-9a-zA-Z_-]+', '_', str(value).lower())


_cfg = ConfigParser()
_cfg.read(os.path.join(os.path.dirname(os.path.realpath(ips_vagrant.__file__)), 'config/ipsv.conf'))
engine = create_engine("sqlite:////{path}"
                       .format(path=os.path.join(_cfg.get('Paths', 'Data'), 'sites.db')))
Base.metadata.bind = engine
