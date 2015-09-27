from urllib import urlencode
from urlparse import urlparse, parse_qs, urlunparse
from ips_vagrant.installer.latest import Installer as Latest


version = (4, 0, 11)


class Installer(Latest):

    def _check_if_complete(self, url, json_response):
        """
        Check if a request has been completed and return the redirect URL if it has
        @type   url:            str
        @type   json_response:  list or dict
        @rtype: str or bool
        """
        if '__done' in json_response and isinstance(json_response, list):
            mr_parts = list(urlparse(url))
            mr_query = parse_qs(mr_parts[4])
            mr_query['mr'] = '"' + str(json_response[0]) + '"'
            mr_parts[4] = urlencode(mr_query, True)
            mr_link = urlunparse(mr_parts)
            mr_j, mr_r = self._ajax(mr_link)
            self.log.debug('MultipleRedirect link: %s', mr_link)
            return super(Installer, self)._check_if_complete(url, mr_j)

        return False
