// Verify bundles with the UI's own verifier (src/hypgraph/ui/hypgraph.js): an implementation independent of the Python
// one, in JavaScript with WebCrypto, so a second check of a bundle doesn't share the first one's code.
//     node dev/js_verify.js src/hypgraph/ui/hypgraph.js a.bundle.json [b.bundle.json …]
//         → JSON {file: {ok, checked, head, problem, unchecked, coverage, warning, anchored}}
// A file may also hold {"bundle": …, "head": "…", "policy": {…}}: verified against that head, trusting that policy.
'use strict';
const fs = require('fs');
globalThis.window = globalThis;
eval(fs.readFileSync(process.argv[2], 'utf8'));                 // defines globalThis.HypGraph
(async () => {
  const out = {};
  for (const f of process.argv.slice(3)) {
    const j = JSON.parse(fs.readFileSync(f, 'utf8'));
    const [b, head, policy] = j.format === undefined && j.bundle ? [j.bundle, j.head || '', j.policy || null] : [j, '', null];
    const v = await globalThis.HypGraph.verifyBundle(b, head, { policy });
    out[f.split(/[\\/]/).pop()] = { ok: v.ok, checked: v.checked, head: v.head, problem: v.problem || '',
      ...(v.ok ? { unchecked: v.unchecked, coverage: v.coverage, warning: v.warning || '', anchored: !!v.anchored } : {}) };
  }
  console.log(JSON.stringify(out));
})();
