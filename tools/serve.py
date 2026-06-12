"""Dev server for the web prototype — kills the stale-cache problem for good.

Serves prototype_web/ (the scenarios symlink resolves ../scenarios) with
Cache-Control: no-store on every response, so every browser refresh re-fetches
everything: what you just saved is what you see. No more Cmd+Shift+R roulette.

    python3 tools/serve.py [port]        (default 8023; from game01_demo/)
    → open http://<server>:8023/?scenario=jiebiao
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


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8023
    print(f"serving {DOCROOT} on http://0.0.0.0:{port}/ (no-store: refresh = fresh)")
    http.server.ThreadingHTTPServer(("0.0.0.0", port), NoCacheHandler).serve_forever()
