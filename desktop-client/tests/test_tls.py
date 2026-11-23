import http.server
import shutil
import ssl
import subprocess
import threading
from pathlib import Path

import pytest

from jarvis_client.api import ApiClient, ClientError


def test_real_tls_handshake_rejects_untrusted_local_certificate(tmp_path, vault):
    openssl = shutil.which("openssl") or r"C:\Program Files\Git\usr\bin\openssl.exe"
    if not Path(openssl).is_file():
        pytest.skip("OpenSSL unavailable for ephemeral TLS certificate")
    key, certificate = tmp_path / "temporary.key", tmp_path / "temporary.crt"
    generated = subprocess.run([openssl, "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", str(key), "-out", str(certificate), "-subj", "/CN=localhost", "-days", "1"], capture_output=True, timeout=20)
    assert generated.returncode == 0
    observed = []
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            observed.append(self.path)
            self.send_response(200)
            self.end_headers()
        def log_message(self, *args):
            pass
    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(str(certificate), str(key))
    server.socket = context.wrap_socket(server.socket, server_side=True)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    api = ApiClient("https://127.0.0.1:" + str(server.server_port), vault)
    try:
        with pytest.raises(ClientError, match="TLS"):
            api.probe()
        assert not observed  # certificate was rejected before any HTTP/token exchange
    finally:
        api.close()
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
