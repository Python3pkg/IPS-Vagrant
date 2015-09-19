# coding: utf-8
import os
import ips_vagrant
from ConfigParser import ConfigParser
from sqlalchemy import Column, Integer, Text, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import create_engine


Base = declarative_base()
metadata = Base.metadata


class Domain(Base):
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True)
    name = Column(Text, nullable=False)
    sites = relationship("Site")


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
    enabled = Column(Integer, server_default=text("0"))
    domain = relationship("Domain")


# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
_cfg = ConfigParser()
_cfg.read(os.path.join(os.path.dirname(os.path.realpath(ips_vagrant.__file__)), 'config/ipsv.conf'))
engine = create_engine("sqlite:////{path}"
                       .format(path=os.path.join(_cfg.get('Paths', 'Data'), 'sites.db')))
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
