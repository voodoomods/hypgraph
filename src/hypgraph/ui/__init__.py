"""The Atlas explorer's static files (atlas.js, atlas.css, vendored Cytoscape). A host serves ``static_dir()``."""

from pathlib import Path


def static_dir() -> Path:
    return Path(__file__).parent
