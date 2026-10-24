# Contributing

Thank you. HypGraph is small on purpose, and these rules keep it trustworthy:

1. **The engine stays dependency-free.** `src/hypgraph/` imports only the standard library, except `mcp.py`
   (FastMCP, an optional extra). That lets it run on locked-down lab machines, in classrooms and in the browser.
2. **Standing is never stored.** New status dimensions are derived in `derive.py` from what's in the record. A field
   anyone can set is not a status.
3. **Nothing is updated or deleted.** Corrections are new rows: versions, withdrawals, retractions.
4. **A new rule needs the mistake behind it.** A claim check, a refusal or a ranking change comes with a test that
   reproduces the error it prevents (see `tests/test_engine.py`) and a refusal message that says how to fix it.
5. **The format is a promise.** A change to `schema.py` that older records or other implementations would read
   differently needs a format version and a note in `docs/spec.md`.

## Develop

```bash
pip install -e ".[all]"
pytest
python dev/serve_demo.py        # the Atlas on the demo, http://127.0.0.1:8765
python dev/build_site.py        # regenerate site/ data (bundle, schema, engine files for the playground)
python dev/serve_site.py        # the website, http://127.0.0.1:8770
```

Write plainly. Messages are read by students, scientists and agents, often in the middle of being told "no".
