"""Pinned references: one record citing a node of another record, so that records can form a network without
sharing a chain.

A record is one trust boundary: one hash chain, one policy, one board. Another record's claim can still be a line
of support here — as a ``source`` node, which is what a cited outside work already is — provided the reference
says *which version* it read and *what that version hashed to*. The fields on ``source``:

    record    the served record's base URL (what its /api/graph hangs off), e.g. https://mesh/q/demo-a
    node      the node id there
    version   the version that was read
    hash      sha256 of that version's canonical body — the same hash the record's own chain holds for it

``pin`` builds those fields for one of this record's nodes; ``verify_reference`` fetches the cited record and checks
them: the hash still matches (nothing was rewritten), whether the node has been revised since (the pinned version
stands as read, but there is a newer one), and whether it has been withdrawn. A host that holds many records (a
mesh) uses the same functions against its own copies and derives cross-record standing from them. This record never
trusts another record's status; it trusts the hash it pinned."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Callable, Optional

from . import store

if TYPE_CHECKING:
    from .graph import Graph

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_URL = re.compile(r"^https?://[^\s/?#]+[^\s]*$", re.I)
Fetch = Callable[[str], dict]


def body_hash(body: dict) -> str:
    """The hash a record's chain holds for a version: sha256 over the canonical JSON of its body."""
    return store.sha(store.canon(body))


def normalize_record(url: str) -> str:
    """A record URL without a trailing slash, fragment or query; refuses anything that is not http(s)."""
    u = str(url or "").strip()
    if not _URL.match(u):
        raise ValueError(f"record must be the cited record's http(s) URL, not {u!r}")
    p = urllib.parse.urlsplit(u)
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc, p.path.rstrip("/"), "", ""))


def check_fields(body: dict) -> dict:
    """Validate the reference part of a source body (after the generic field cleaning). All four fields or none;
    version a positive integer; hash 64 hex characters; record an http(s) URL. Returns the body with the fields
    normalised."""
    keys = ("record", "node", "version", "hash")
    present = [k for k in keys if body.get(k) not in (None, "", 0)]
    if not present:
        return body
    missing = [k for k in keys if k not in present]
    if missing:
        raise ValueError("a reference to another record names all of record, node, version and hash; missing: "
                         + ", ".join(missing))
    out = dict(body)
    out["record"] = normalize_record(body["record"])
    out["node"] = str(body["node"]).strip()
    v = body["version"]
    try:
        fv = float(v)
    except (TypeError, ValueError):
        raise ValueError(f"version must be a positive whole number, not {v!r}")
    if not fv.is_integer() or fv < 1:
        raise ValueError(f"version must be a positive whole number, not {v!r}")
    out["version"] = int(fv)
    h = str(body["hash"]).strip().lower()
    if not _HEX64.match(h):
        raise ValueError("hash must be the 64-hex sha256 of the cited version's canonical body")
    out["hash"] = h
    return out


def is_reference(body: dict) -> bool:
    return bool(body.get("record")) and bool(body.get("hash"))


def pin(g: "Graph", nid: str, record: str, *, now: str = "") -> dict:
    """Source fields that pin ``nid`` of ``g`` as it stands now, for another record to cite. ``record`` is the URL
    this record is served at. The citation and ``says`` carry the node's own words, so the citing record reads
    without the cited one."""
    s = g.snapshot()
    nid = g.resolve(nid)
    n = s.nodes[nid]
    rec = normalize_record(record)
    brief = g.brief(s, nid)
    title = brief["title"] or n["type"]
    when = now or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"citation": f"{brief['code']} ({n['type']}) in {rec}, version {n['v']}: {title}"[:1000],
            "url": f"{rec}/#node={nid}", "kind": "primary", "retrieved": when,
            "says": str(title)[:1500],
            "record": rec, "node": nid, "version": int(n["v"]), "hash": body_hash(n["body"])}


def references(g: "Graph", inv: str = "") -> list[dict]:
    """Every source in ``g`` that pins a node of another record, with who cites it here. What a host walks to build
    the network between records."""
    s = g.snapshot()
    out = []
    for nid, n in s.nodes.items():
        if n["type"] != "source" or not is_reference(n["body"]) or (inv and n["inv"] != inv):
            continue
        b = n["body"]
        out.append({"id": nid, "code": n["code"], "inv": n["inv"], "record": b["record"], "node": b["node"],
                    "version": b["version"], "hash": b["hash"], "lifecycle": g.state(nid)["lifecycle"],
                    "cited_by": sorted({e["src"] for e in s.inn.get(nid, []) if e["rel"] == "cites"})})
    out.sort(key=lambda r: (r["record"], r["node"], r["id"]))
    return out


def _http_fetch(timeout: float) -> Fetch:
    def fetch(url: str) -> dict:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.load(r)
    return fetch


def verify_reference(fields: dict, *, fetch: Optional[Fetch] = None, timeout: float = 10.0) -> dict:
    """Check a pinned reference against the record it points at.

    ``fetch(url) -> dict`` answers ``GET <record>/api/graph/node/<node>?history=1``; the default is HTTP. A host
    that holds the cited record passes its own reader. Returns::

        {ok, problem, record, node, version, current_version, revised, withdrawn, lifecycle}

    ``ok`` means the pinned version exists there and its body hashes to the pinned hash: what this record read is
    what that record holds. ``revised`` (a newer version exists) and ``withdrawn`` are reported beside it — the
    pin still stands as read, but the citing record's host decides what that means for its standing."""
    try:
        f = check_fields({k: fields.get(k) for k in ("record", "node", "version", "hash")})
    except ValueError as e:
        return {"ok": False, "problem": str(e)}
    if not is_reference(f):
        return {"ok": False, "problem": "not a reference: no record and hash pinned"}
    url = f"{f['record']}/api/graph/node/{urllib.parse.quote(f['node'], safe='')}?history=1"
    out = {"ok": False, "record": f["record"], "node": f["node"], "version": f["version"], "url": url}
    try:
        doc = (fetch or _http_fetch(timeout))(url)
    except urllib.error.HTTPError as e:
        return {**out, "problem": f"the record answered {e.code} for {f['node']}"}
    except Exception as e:  # unreachable, bad JSON, timeout: the reference is unverified, not wrong
        return {**out, "problem": f"could not read the record: {type(e).__name__}"}
    if not isinstance(doc, dict) or "versions" not in doc:
        return {**out, "problem": "the record's answer carries no versions (is it a HypGraph node route with history=1?)"}
    versions = {int(v.get("v", 0)): v for v in doc.get("versions") or [] if isinstance(v, dict)}
    cur = max(versions) if versions else int(doc.get("v") or 0)
    out |= {"current_version": cur, "revised": cur > f["version"], "withdrawn": bool(doc.get("withdrawn")),
            "lifecycle": str((doc.get("state") or {}).get("lifecycle") or ("withdrawn" if doc.get("withdrawn") else ""))}
    ver = versions.get(f["version"])
    if ver is None:
        return {**out, "problem": f"version {f['version']} does not exist there (it has {cur})"}
    body = ver.get("body")
    if isinstance(body, str):
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            return {**out, "problem": "the version's body is not JSON"}
    got = body_hash(body) if isinstance(body, dict) else ""
    if got != f["hash"]:
        return {**out, "problem": f"version {f['version']} hashes to {got[:16]}…, not the pinned {f['hash'][:16]}…"}
    return {**out, "ok": True}


__all__ = ["pin", "references", "verify_reference", "check_fields", "is_reference", "body_hash", "normalize_record"]
