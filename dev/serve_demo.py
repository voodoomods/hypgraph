"""Dev: build the Broad Street demo into a temp file and serve it (no install needed). python dev/serve_demo.py [port]"""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hypgraph.demos import broad_street  # noqa: E402
from hypgraph.server import serve  # noqa: E402

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
db = Path(tempfile.mkdtemp(prefix="hypgraph-demo-")) / "broad-street.hypgraph"
broad_street.build(path=str(db))
serve(str(db), port=port, writable=True, open_browser=False)
