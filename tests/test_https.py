"""Hub mode over HTTPS: the certificate tools/make_cert.py makes is accepted by
a client that trusts only the hub's CA, and the CA cannot vouch for real sites.

No models needed. Uses a throwaway server on 127.0.0.1, not the app.
"""

import http.server
import ipaddress
import ssl
import threading
import urllib.request

import pytest
from cryptography import x509

from tools.make_cert import make_server_cert


@pytest.fixture(scope="module")
def certs(tmp_path_factory):
    d = tmp_path_factory.mktemp("certs")
    ips = make_server_cert(d)
    return d, ips


def test_certificate_names_this_laptop(certs):
    d, ips = certs
    crt = x509.load_pem_x509_certificate((d / "hub.crt").read_bytes())
    san = crt.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    assert "localhost" in san.get_values_for_type(x509.DNSName)
    assert ipaddress.ip_address("127.0.0.1") in san.get_values_for_type(x509.IPAddress)
    assert "127.0.0.1" in ips
    days = (crt.not_valid_after_utc - crt.not_valid_before_utc).days
    assert days <= 398                       # browsers reject longer server certs


def test_ca_is_limited_to_private_addresses(certs):
    d, _ = certs
    ca = x509.load_pem_x509_certificate((d / "hub-ca.crt").read_bytes())
    nc = ca.extensions.get_extension_for_class(x509.NameConstraints)
    assert nc.critical
    nets = [n.value for n in nc.value.permitted_subtrees if isinstance(n, x509.IPAddress)]
    assert ipaddress.ip_network("192.168.0.0/16") in nets
    assert not any(ipaddress.ip_address("8.8.8.8") in n for n in nets)


def test_ca_is_reused_and_server_cert_is_remade(certs):
    d, _ = certs
    ca_before, crt_before = (d / "hub-ca.crt").read_bytes(), (d / "hub.crt").read_bytes()
    make_server_cert(d)
    assert (d / "hub-ca.crt").read_bytes() == ca_before
    assert (d / "hub.crt").read_bytes() != crt_before


def test_tls_handshake_with_only_the_hub_ca(certs):
    d, _ = certs

    class Ok(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Ok)
    sctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    sctx.load_cert_chain(d / "hub.crt", d / "hub.key")
    srv.socket = sctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        port = srv.server_address[1]
        cctx = ssl.create_default_context(cafile=str(d / "hub-ca.crt"))
        for host in ("127.0.0.1", "localhost"):
            with urllib.request.urlopen(f"https://{host}:{port}/", context=cctx, timeout=5) as r:
                assert r.read() == b"ok"
    finally:
        srv.shutdown()
