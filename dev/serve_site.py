"""Dev: serve site/ on http://127.0.0.1:8770 (run dev/build_site.py first). python dev/serve_site.py [port]"""
import functools
import http.server
import sys
from pathlib import Path

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8770
root = Path(__file__).resolve().parents[1] / "site"
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
http.server.SimpleHTTPRequestHandler.extensions_map.update({".js": "text/javascript", ".json": "application/json",
                                                            ".md": "text/markdown; charset=utf-8",
                                                            ".txt": "text/plain; charset=utf-8"})
print(f"site on http://127.0.0.1:{port}/")
http.server.ThreadingHTTPServer(("127.0.0.1", port), handler).serve_forever()
