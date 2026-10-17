"""Hand image uploads to the default browser so Lens keeps its own session."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import secrets
import threading
import time


class BrowserUploadBridge:
    lifetime = 600
    max_pending = 32

    def __init__(self):
        self.pending = {}
        self.lock = threading.Lock()
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
                    self.send_error(403)
                    return
                with bridge.lock:
                    bridge._expire()
                    item = bridge.pending.get(self.path)
                if item is None:
                    self.send_error(404, 'Recherche absente ou expiree. Relancez-la depuis TABaTAB.')
                    return
                body, nonce, _expires = item
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Referrer-Policy', 'no-referrer')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Content-Security-Policy',
                                 "default-src 'none'; img-src data:; "
                                 f"script-src 'nonce-{nonce}'; form-action https://*.google.com https://google.com; "
                                 "frame-ancestors 'none'; base-uri 'none'")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        class Server(ThreadingHTTPServer):
            daemon_threads = True

            def service_actions(self):
                with bridge.lock:
                    bridge._expire()

        self.server = Server(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _expire(self):
        now = time.monotonic()
        self.pending = {path: item for path, item in self.pending.items() if item[2] > now}

    def add(self, preview):
        nonce = secrets.token_urlsafe(24)
        route = '/' + secrets.token_urlsafe(32)
        encoded = base64.b64encode(preview).decode('ascii')
        page = f'''<!doctype html>
<html lang="fr"><meta charset="utf-8"><meta name="referrer" content="no-referrer">
<title>TABaTAB — Recherche Google Lens</title>
<h1>Recherche Google Lens</h1>
<p id="status">Envoi de l’image à Google Lens…</p>
<img alt="Image envoyée à Google Lens" width="240" src="data:image/jpeg;base64,{encoded}">
<form id="upload" action="https://lens.google.com/upload?hl=fr" method="post" enctype="multipart/form-data">
<input id="image" type="file" name="encoded_image" accept="image/jpeg" required>
<button type="submit">Rechercher avec Google Lens</button>
</form>
<noscript>Activez JavaScript ou sélectionnez votre image puis cliquez sur Rechercher.</noscript>
<script nonce="{nonce}">
try {{
    const bytes = Uint8Array.from(atob('{encoded}'), c => c.charCodeAt(0));
    const transfer = new DataTransfer();
    transfer.items.add(new File([bytes], 'image.jpg', {{type: 'image/jpeg'}}));
    document.getElementById('image').files = transfer.files;
    document.getElementById('upload').requestSubmit();
}} catch (error) {{
    document.getElementById('status').textContent =
        'Sélectionnez votre image puis cliquez sur Rechercher avec Google Lens.';
}}
</script></html>'''
        with self.lock:
            self._expire()
            while len(self.pending) >= self.max_pending:
                self.pending.pop(next(iter(self.pending)))
            self.pending[route] = (page.encode('utf-8'), nonce, time.monotonic() + self.lifetime)
        return f'http://127.0.0.1:{self.server.server_port}{route}'

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        with self.lock:
            self.pending.clear()


_bridge = None
_bridge_lock = threading.Lock()


def google_browser_upload(preview):
    global _bridge
    with _bridge_lock:
        if _bridge is None:
            _bridge = BrowserUploadBridge()
        return _bridge.add(preview)


def close_browser_uploads():
    global _bridge
    with _bridge_lock:
        if _bridge is not None:
            _bridge.close()
            _bridge = None
