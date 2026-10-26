# HypGraph UI prototype

A clickable prototype of the redesigned HypGraph UI (plan: `docs/ui-plan.md`), on real records — one per `@2`
profile, from HypSwarm's scripted examples 01–05. Not shipped; `src/hypgraph/ui/` is unchanged.

    python dev/ui_prototype_data.py <record> …        # rebuild data.js from records
    python -m http.server 8790                         # from the repo root, then open
    http://localhost:8790/dev/ui-prototype/index.html#view=live&inv=knowledge@2

Deep links: `#view=overview|live|pipeline|graph|evidence|orders|audit|report&inv=<profile or code>&q=Q1&at=<event>&theme=dark`.
`shots/` holds 1440×900 captures of each view.
