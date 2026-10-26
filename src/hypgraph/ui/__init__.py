"""The HypGraph UI's static files (hypgraph.js, hypgraph.css, index.html, vendored Cytoscape; atlas.js and atlas.css
are one-release shims for pages that still include the Atlas). A host serves ``static_dir()``."""

from pathlib import Path


def static_dir() -> Path:
    return Path(__file__).parent
