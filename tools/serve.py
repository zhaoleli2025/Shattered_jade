"""Dev server for the web prototype — kills the stale-cache problem for good.

Serves prototype_web/ (the scenarios/world symlinks resolve ../) with
Cache-Control: no-store on every response, so every browser refresh re-fetches
everything: what you just saved is what you see.

    python3 tools/serve.py [port]        (default 8765; from game01_demo/)

If the port is busy (a zombie server), the next free one is taken and printed —
ALWAYS read the printed port. Remote use: VS Code → 端口/Ports → Forward a Port
→ type EXACTLY the printed port, then open the printed localhost URL.

For serverless play use the stable editions instead:
    python3 tools/release.py → releases/shattered_jade_full_vX.Y.html
    (one file, map + battles inside — download it and double-click)
"""
import http.server
import os
import sys

DOCROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "prototype_web")


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DOCROOT, **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()


class Server(http.server.ThreadingHTTPServer):
    allow_reuse_address = True   # a freshly killed server can't hold the port


if __name__ == "__main__":
    want = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    srv = None
    for port in range(want, want + 10):
        try:
            srv = Server(("0.0.0.0", port), NoCacheHandler)
            break
        except OSError:
            print(f"port {port} busy — trying {port + 1}")
    if srv is None:
        sys.exit(f"no free port in {want}-{want + 9}")
    print(f"""serving {DOCROOT}
  battles:  http://localhost:{port}/
  the map:  http://localhost:{port}/world.html
remote? VS Code → Ports → Forward → type EXACTLY {port} (a wrong typed port hangs forever)
no-store caching: every refresh is fresh. Ctrl-C to stop.""")
    srv.serve_forever()
