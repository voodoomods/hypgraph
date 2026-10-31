"""
The notes for a GitHub Release, from CHANGELOG.md: the version's own section, then how to install it and check
what was published. The release job runs it after PyPI has the files; run it yourself to preview.

    python dev/release_notes.py 0.7.11            # print the notes
    python dev/release_notes.py 0.7.11 -o notes.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def section(version: str, changelog: str) -> str:
    """The changelog's section for ``version``: its heading line's title, and everything up to the next heading."""
    m = re.search(rf"^## {re.escape(version)}\b(.*)$", changelog, re.M)
    if not m:
        raise SystemExit(f"CHANGELOG.md has no section for {version}")
    rest = changelog[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    body = rest[: nxt.start()] if nxt else rest
    title = m.group(1).strip(" —-:")
    return (f"**{title[0].upper() + title[1:]}**\n\n" if title else "") + body.strip() + "\n"


def notes(version: str) -> str:
    text = section(version, (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    verification = ("\n  What verifying a record shows: [docs/verification.md](https://github.com/voodoomods/hypgraph/blob/"
                    f"v{version}/docs/verification.md)." if (ROOT / "docs" / "verification.md").is_file() else "")
    walkthrough = ("\n- Before publishing, the release job installed both into fresh environments and ran the documented "
                   "walkthrough\n  (`dev/e2e_install.py`)." if (ROOT / "dev" / "e2e_install.py").is_file() else "")
    return f"""{text}
## Install

```bash
pip install "hypgraph=={version}"            # the engine, the CLI, the HTTP server and the UI; no dependencies
pip install "hypgraph[mcp]=={version}"       # + the MCP server for agents
```

Tested on Python 3.10 to 3.13 on Linux, macOS and Windows. Records and bundles use the `hypgraph/1` format.

## Check what you installed

- The wheel and sdist attached here are the ones published to [PyPI](https://pypi.org/project/hypgraph/{version}/),
  built by this repository's release workflow and uploaded with trusted publishing; PyPI shows their provenance
  attestation.{walkthrough}
- Security model and how to report a vulnerability: [SECURITY.md](https://github.com/voodoomods/hypgraph/blob/v{version}/SECURITY.md).{verification}

Docs: [hypgraph.com](https://hypgraph.com) · record format: [spec](https://hypgraph.com/spec/) · full history:
[CHANGELOG.md](https://github.com/voodoomods/hypgraph/blob/v{version}/CHANGELOG.md)
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("version", help="the version, without the v (0.7.11)")
    ap.add_argument("-o", "--output", default="")
    a = ap.parse_args()
    out = notes(a.version.lstrip("v"))
    if a.output:
        Path(a.output).write_text(out, encoding="utf-8", newline="\n")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
