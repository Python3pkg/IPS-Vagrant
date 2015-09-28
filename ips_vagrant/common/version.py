from ips_vagrant.common import parse_version


class Version(object):

    def __init__(self, vstring, vid=None):
        self.vstring = vstring
        self.vid = vid
        self.vtuple = parse_version(vstring).version
