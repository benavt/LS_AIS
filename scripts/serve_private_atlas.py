"""Serve only a verified atlas manifest on loopback or an approved private Tailscale address."""
import argparse
import datetime
import hashlib
import ipaddress
import json
from pathlib import Path
from http.server import ThreadingHTTPServer
import time
from urllib.parse import urlsplit


def private_route(request_path):
    parsed = urlsplit(request_path)
    if not parsed.path.startswith('/LS_AIS/'):
        return None
    relative = parsed.path[len('/LS_AIS'):]
    if relative != '/' and relative.endswith('/'):
        relative += 'index.html'
    return relative + ('?' + parsed.query if parsed.query else '')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--bind', required=True)
    parser.add_argument('--port', type=int, default=18782)
    parser.add_argument('--duration', type=int, default=7200)
    args = parser.parse_args()
    address = ipaddress.ip_address(args.bind)
    if not (address.is_loopback or address in ipaddress.ip_network('100.64.0.0/10')) or not 1 <= args.duration <= 43200:
        parser.error('Select loopback or a private Tailscale address and a bounded preview lifetime')
    from src.analysis.atlas_presentation import handler_for
    site = args.site.resolve()
    manifest = site / 'export-manifest.json'
    rows = json.loads(manifest.read_text())['files']
    overlay = site.parent / ('local-preview' if address.is_loopback else 'private-preview'); overlay.mkdir(exist_ok=False)
    # The shared handler checks every allowlisted file and rechecks changed files
    # before serving. Operational files and directory listings are never routes.
    (overlay / 'presentation.json').write_text(json.dumps(dict(kind='saved-atlas-presentation-overlay',
        source_delivery=str(site), source_files=[], source_manifest_sha256=hashlib.sha256((site.parent / 'delivery-manifest.json').read_bytes()).hexdigest(),
        presentation_files=[], additional_deliveries={})))
    # Treat the exported bundle as one source, including its export receipt.
    rows = [*rows, dict(path='export-manifest.json', bytes=manifest.stat().st_size, sha256=hashlib.sha256(manifest.read_bytes()).hexdigest())]
    receipt = json.loads((overlay / 'presentation.json').read_text())
    receipt['source_files'] = rows
    (overlay / 'presentation.json').write_text(json.dumps(receipt, indent=2) + '\n')
    base = handler_for(overlay)
    class Handler(base):
        def _send(self, head):
            route = private_route(self.path)
            if route is None:
                self.send_error(404)
                return
            self.path = route
            return super()._send(head)
    now = datetime.datetime.now(datetime.timezone.utc)
    result = dict(status='serving', project='LS_AIS', private=True,
        url=f'http://{args.bind}:{args.port}/LS_AIS/', started_at_UTC=now.isoformat(),
        expires_at_UTC=(now + datetime.timedelta(seconds=args.duration)).isoformat(),
        manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(), access=('Local machine only' if address.is_loopback else 'Existing private Tailscale access; host must remain online'))
    with ThreadingHTTPServer((args.bind, args.port), Handler) as server:
        (site.parent / ('local-preview-receipt.json' if address.is_loopback else 'private-preview-receipt.json')).write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result), flush=True)
        server.timeout = 1
        until = time.monotonic() + args.duration
        while time.monotonic() < until:
            server.handle_request()


if __name__ == '__main__':
    main()
