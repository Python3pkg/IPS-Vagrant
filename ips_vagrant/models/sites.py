# coding: utf-8
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
engine = create_engine('sqlite:///dev/share/sites.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
