// Verify bundles with the UI's own verifier (src/hypgraph/ui/hypgraph.js): an implementation independent of the Python
// one, in JavaScript with WebCrypto, so a second check of a bundle doesn't share the first one's code.
//     node dev/js_verify.js src/hypgraph/ui/hypgraph.js a.bundle.json [b.bundle.json …]   → JSON {file: {ok, checked, head, problem, unchecked}}
'use strict';
const fs = require('fs');
globalThis.window = globalThis;
eval(fs.readFileSync(process.argv[2], 'utf8'));                 // defines globalThis.HypGraph
(async () => {
  const out = {};
  for (const f of process.argv.slice(3)) {
    const v = await globalThis.HypGraph.verifyBundle(JSON.parse(fs.readFileSync(f, 'utf8')));
    out[f.split(/[\\/]/).pop()] = { ok: v.ok, checked: v.checked, head: v.head, problem: v.problem || '',
      ...(v.ok ? { unchecked: v.unchecked } : {}) };
  }
  console.log(JSON.stringify(out));
})();
