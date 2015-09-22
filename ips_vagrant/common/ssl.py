import logging
from OpenSSL import crypto


class CertificateFactory:
    """
    SSL Certificate Factory
    """
    def __init__(self, site):
        """
        @param  site:   The Site to create a self-signed SSL certificate for
        @type   site:   ips_vagrant.models.sites.Site
        """
        self.site = site
        self.log = logging.getLogger('ipsv.common.ssl')
        self.log.debug('New Certificate Factory created for site %s', site.name)

    def get(self, bits=2048, type=crypto.TYPE_RSA, digest='sha1'):
        """
        Get a new self-signed certificate
        @type   bits:   int
        @type   digest: str
        @rtype: Certificate
        """
        self.log.debug('Creating a new self-signed SSL certificate')
        # Generate the key and ready our cert
        key = crypto.PKey()
        key.generate_key(type, bits)
        cert = crypto.X509()

        # Fill in some pseudo certificate information with a wildcard common name
        cert.get_subject().C  = 'US'
        cert.get_subject().ST = 'California'
        cert.get_subject().L  = 'Los Angeles'
        cert.get_subject().O  = 'Wright Anything Agency'
        cert.get_subject().OU = 'Law firm / talent agency'
        cert.get_subject().CN = '*.{dn}'.format(dn=self.site.domain.name)

        # Set the serial number, expiration and issued
        cert.set_serial_number(1000)
        cert.gmtime_adj_notBefore(0)
        cert.gmtime_adj_notAfter(315360000)
        cert.set_issuer(cert.get_subject())

        # Map the key and sign our certificate
        cert.set_pubkey(key)
        cert.sign(key, digest)

        # Dump the PEM data and return a certificate container
        _cert = crypto.dump_certificate(crypto.FILETYPE_PEM, cert)
        _key  = crypto.dump_privatekey(crypto.FILETYPE_PEM, key)

        return Certificate(_cert, _key, type, bits, digest)


# noinspection PyShadowingBuiltins
class Certificate:
    """
    Certificate container
    """
    def __init__(self, certificate, key, type, bits, digest):
        self.certificate = certificate
        self.key = key
        self.type = type
        self.bits = bits
        self.digest = digest
