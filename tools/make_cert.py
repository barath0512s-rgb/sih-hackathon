"""Make the certificate for hub mode over HTTPS.

A browser allows the microphone only on https:// pages or on localhost. The
teacher's laptop is the hub; a tablet on the same Wi-Fi opens
https://<laptop-ip>:5443, so the laptop needs a certificate for its own IP.

This makes, in certs/ (git-ignored, never shared):
  hub-ca.crt / hub-ca.key   a small certificate authority for this laptop only
  hub.crt / hub.key         the server certificate, signed by that CA, valid for
                            localhost, this computer's name and every IPv4
                            address it has right now

The CA is made once and reused. The server certificate is remade every time,
so run this again when the laptop joins a different Wi-Fi and gets a new IP.
run_vaanisetu.bat https does that for you.

On the tablet, either
  - install hub-ca.crt once (open http://<laptop-ip>:5000/hub-ca.crt while the
    plain server runs, or copy the file; Android: Settings > Security >
    Encryption & credentials > Install a certificate > CA certificate), or
  - accept the browser's warning the first time.

Usage:  python tools/make_cert.py [--ip 192.168.1.20 ...]
"""

import argparse
import datetime
import ipaddress
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config  # noqa: E402

from cryptography import x509  # noqa: E402
from cryptography.hazmat.primitives import hashes, serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric import ec  # noqa: E402
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID  # noqa: E402


def local_ipv4():
    """Every IPv4 address of this computer, loopback included."""
    ips = {"127.0.0.1"}
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except OSError:
        pass
    # The address used for the default route; sends nothing.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(ips, key=lambda a: tuple(int(p) for p in a.split(".")))


def _write(path, data):
    path.write_bytes(data)


def _key():
    return ec.generate_private_key(ec.SECP256R1())


def _pem_key(key):
    return key.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())


def _name(cn):
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn),
                      x509.NameAttribute(NameOID.ORGANIZATION_NAME, f"{config.APP_NAME} laptop hub")])


def ensure_ca(cert_dir):
    crt, key = cert_dir / "hub-ca.crt", cert_dir / "hub-ca.key"
    if crt.exists() and key.exists():
        return (x509.load_pem_x509_certificate(crt.read_bytes()),
                serialization.load_pem_private_key(key.read_bytes(), None))
    k = _key()
    now = datetime.datetime.now(datetime.timezone.utc)
    name = _name(f"{config.APP_NAME} hub CA ({socket.gethostname()})")
    c = (x509.CertificateBuilder()
         .subject_name(name).issuer_name(name)
         .public_key(k.public_key())
         .serial_number(x509.random_serial_number())
         .not_valid_before(now - datetime.timedelta(minutes=5))
         .not_valid_after(now + datetime.timedelta(days=3650))
         .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
         .add_extension(x509.KeyUsage(digital_signature=True, key_cert_sign=True, crl_sign=True,
                                      content_commitment=False, key_encipherment=False,
                                      data_encipherment=False, key_agreement=False,
                                      encipher_only=False, decipher_only=False), critical=True)
         .add_extension(x509.SubjectKeyIdentifier.from_public_key(k.public_key()), critical=False)
         # A tablet that trusts this CA must not trust it for real websites:
         # it can only vouch for this laptop's name and private-network addresses.
         .add_extension(x509.NameConstraints(permitted_subtrees=[
             x509.DNSName("localhost"), x509.DNSName(socket.gethostname()),
             *(x509.IPAddress(ipaddress.ip_network(n)) for n in
               ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))],
             excluded_subtrees=None), critical=True)
         .sign(k, hashes.SHA256()))
    _write(key, _pem_key(k))
    _write(crt, c.public_bytes(serialization.Encoding.PEM))
    return c, k


def make_server_cert(cert_dir, extra_ips=()):
    cert_dir.mkdir(exist_ok=True)
    ca, ca_key = ensure_ca(cert_dir)
    # Only addresses the CA may vouch for (see ensure_ca).
    private = [ipaddress.ip_network(n) for n in
               ("127.0.0.0/8", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]
    ips = sorted({i for i in set(local_ipv4()) | set(extra_ips)
                  if any(ipaddress.ip_address(i) in n for n in private)},
                 key=lambda a: tuple(int(p) for p in a.split(".")))
    host = socket.gethostname()
    san = [x509.DNSName("localhost"), x509.DNSName(host)]
    san += [x509.IPAddress(ipaddress.ip_address(i)) for i in ips]
    k = _key()
    now = datetime.datetime.now(datetime.timezone.utc)
    c = (x509.CertificateBuilder()
         .subject_name(_name(host)).issuer_name(ca.subject)
         .public_key(k.public_key())
         .serial_number(x509.random_serial_number())
         .not_valid_before(now - datetime.timedelta(minutes=5))
         # Browsers reject server certificates valid for more than 398 days.
         .not_valid_after(now + datetime.timedelta(days=397))
         .add_extension(x509.SubjectAlternativeName(san), critical=False)
         .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
         .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
         .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
                        critical=False)
         .sign(ca_key, hashes.SHA256()))
    _write(cert_dir / "hub.key", _pem_key(k))
    _write(cert_dir / "hub.crt", c.public_bytes(serialization.Encoding.PEM))
    return ips


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ip", action="append", default=[], help="an extra IPv4 address to include")
    a = ap.parse_args()
    ips = make_server_cert(config.CERT_DIR, a.ip)
    print(f"Certificate written to {config.CERT_DIR}")
    print("Valid for: localhost, " + socket.gethostname() + ", " + ", ".join(ips))
    for ip in ips:
        if ip != "127.0.0.1":
            print(f"  Tablet address: https://{ip}:{config.HTTPS_PORT}")


if __name__ == "__main__":
    main()
