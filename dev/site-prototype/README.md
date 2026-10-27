# hypgraph.com prototype

The homepage proposed in [docs/site-plan.md](../../docs/site-plan.md), in the HypGraph app's design system. Not
the live site.

```
python dev/site_record.py            # builds the page's own record, re-measures it, checks the copy → data.js
python -m http.server 8790           # from the repo root, then open /dev/site-prototype/
```

- `index.html`, `proto.css`, `proto.js`: the page. Every figure comes from `data.js`.
- `site-record.bundle.json`: the page's own HypGraph record. The lab measures, a reviewer re-measures, and each
  claim is bound to its result. The "This page's own record" tab opens it in the app; any bundle verifier checks it.
- `homepage.md`: the page's copy as `hypgraph check` read it, with the figures filled in.
- `shots/`: light and dark, the fold and the full page (1440 px wide).
- `?theme=light` / `?theme=dark` forces a theme.
