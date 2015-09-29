from ips_vagrant.common import parse_version


class Version(object):

    def __init__(self, vstring, vid=None):
        self.vstring = vstring
        self.vid = vid
        self.vtuple = parse_version(vstring).version

    def __repr__(self):
        return "{str} ({id})".format(str=self.vstring, id=self.vid)
