# coding: utf-8
import os
import re
import logging
import sqlahelper
import ips_vagrant
from ConfigParser import ConfigParser
from sqlalchemy import Column, Integer, Text, ForeignKey, text
# from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine


# Base = declarative_base()
Base = sqlahelper.get_base()
Session = sqlahelper.get_session()
metadata = Base.metadata


class Domain(Base):
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    sites = relationship("Site")

    @classmethod
    def get_or_create(cls, dname):
        Domain = cls
        dname = dname.hostname if hasattr(dname, 'hostname') else dname
        # Fetch the domain entry if it already exists
        logging.getLogger('ipsv.sites.domain').debug('Checking if the domain %s has already been registered', dname)
        domain = Session.query(Domain).filter(Domain.name == dname).first()

        # Otherwise create it now
        if not domain:
            logging.getLogger('ipsv.sites.domain')\
                .debug('Domain name does not yet exist, creating a new database entry')
            domain = Domain(name=dname)
            Session.add(domain)

        return domain


class Site(Base):
    __tablename__ = 'sites'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    domain_id = Column(Integer, ForeignKey('domains.id'), nullable=False)
    root = Column(Text, nullable=False)
    license_key = Column(Text, nullable=False)
    ssl = Column(Integer, server_default=text("0"))
    spdy = Column(Integer, server_default=text("0"))
    gzip = Column(Integer, server_default=text("1"))
    db_host = Column(Text, nullable=True)
    db_name = Column(Text, nullable=True)
    db_user = Column(Text, nullable=True)
    db_pass = Column(Text, nullable=True)
    enabled = Column(Integer, server_default=text("0"))
    domain = relationship("Domain")

    def slug(self):
        return re.sub('[^0-9a-zA-Z_-]+', '_', str(self.name).lower())


# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
_cfg = ConfigParser()
_cfg.read(os.path.join(os.path.dirname(os.path.realpath(ips_vagrant.__file__)), 'config/ipsv.conf'))
engine = create_engine("sqlite:////{path}"
                       .format(path=os.path.join(_cfg.get('Paths', 'Data'), 'sites.db')))
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine
