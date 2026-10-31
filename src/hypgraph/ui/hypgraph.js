/**
 * HypGraph — the research record, every profile, live. Framework-free, read-only, offline-first; no build step.
 *
 *   <link rel="stylesheet" href="hypgraph.css">
 *   <script src="vendor/cytoscape.min.js"></script>  (+ layout-base, cose-base, cytoscape-fcose for the fcose layout)
 *   <script src="hypgraph.js"></script>
 *   <div id="app" style="height:100vh"></div>
 *   <script>
 *     HypGraph.mount(document.getElementById('app'), { source: HypGraph.HttpSource('/api/graph'), hash: true });
 *     // or, with no server at all:  { source: HypGraph.BundleSource(bundleJson) }
 *   </script>
 *
 * Views (docs/ui-plan.md): Overview · Live (with the swarm as swimlanes) · Pipeline · Graph · Evidence · Work orders · Audit log · Report, each in
 * the investigation's profile's own words (Requirement, Thesis, Solution…). Nothing here writes. Standing, stages and
 * gates come from the engine; a BundleSource shows what the bundle was exported with and re-verifies its hash chain
 * in the browser. An HttpSource follows the record live (GET /stream), falling back to polling on older hosts, and
 * hides what a host's API doesn't serve.
 *
 * Options: source (required) · theme ('light' | 'dark'; the OS's choice by default) · embed (on a page of its own:
 * it grows to its content and scrolls nothing inside, the feed shows the latest 15 events) · hash (keep the view in
 * location.hash) · title · live ·
 * play (open on the Live view and replay the run from its first event; also `#view=live&play=1`, and skipped when
 * the visitor asks for reduced motion) · onTheme(t) · operatorUrl · fileUrl(path) ·
 * lang (the host page's language; the UI speaks en, es, fr, de, zh-Hans and picks ?lang=, then lang, then the
 * visitor's saved choice, then the browser's) · langSwitch (false hides the language menu) · onLang(code) (the visitor
 * picked one) · stringsUrl (where hypgraph.i18n.js is, if not beside this script). Keys: 1–8 views · ⌘K / Ctrl+K or / search · Esc close · t theme.
 * `HypAtlas` is kept as an alias of `HypGraph` for one release.
 */
'use strict';
(function (global) {
  const VERSION = '0.6.0';
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const RISKY = ['requires', 'derived_from', 'based_on'];
  const SAME_TYPE = ['supersedes', 'corrects'];      // schema.SAME_TYPE: a replacement of the same type
  // bundle.REPLACEABLE: the types a supersedes / corrects link can point at (schema.RELS); no other type is superseded
  const REPLACEABLE = ['artifact', 'claim', 'decision', 'experiment', 'hypothesis', 'question', 'result', 'run', 'source', 'task'];
  const cap = (t) => (t ? t[0].toUpperCase() + t.slice(1) : '');

  // ── hashing (WebCrypto, with a small fallback for insecure contexts) ─────
  async function sha256(text) {
    const bytes = new TextEncoder().encode(text);
    if (global.crypto && global.crypto.subtle) {
      const d = await global.crypto.subtle.digest('SHA-256', bytes);
      return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, '0')).join('');
    }
    return sha256Fallback(bytes);
  }
  function sha256Fallback(bytes) {
    const K = new Uint32Array([0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
      0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
      0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da, 0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
      0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb,
      0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
      0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f,
      0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2]);
    const H = new Uint32Array([0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]);
    const l = bytes.length, n = ((l + 9 + 63) >> 6) << 6, m = new Uint8Array(n);
    m.set(bytes); m[l] = 0x80;
    const dv = new DataView(m.buffer); dv.setUint32(n - 4, l * 8); dv.setUint32(n - 8, Math.floor(l / 0x20000000));
    const w = new Uint32Array(64), r = (x, k) => (x >>> k) | (x << (32 - k));
    for (let o = 0; o < n; o += 64) {
      for (let i = 0; i < 16; i++) w[i] = dv.getUint32(o + 4 * i);
      for (let i = 16; i < 64; i++) {
        const s0 = r(w[i - 15], 7) ^ r(w[i - 15], 18) ^ (w[i - 15] >>> 3), s1 = r(w[i - 2], 17) ^ r(w[i - 2], 19) ^ (w[i - 2] >>> 10);
        w[i] = (w[i - 16] + s0 + w[i - 7] + s1) >>> 0;
      }
      let [a, b, c, d, e, f, g, h] = H;
      for (let i = 0; i < 64; i++) {
        const t1 = (h + (r(e, 6) ^ r(e, 11) ^ r(e, 25)) + ((e & f) ^ (~e & g)) + K[i] + w[i]) >>> 0;
        const t2 = ((r(a, 2) ^ r(a, 13) ^ r(a, 22)) + ((a & b) ^ (a & c) ^ (b & c))) >>> 0;
        h = g; g = f; f = e; e = (d + t1) >>> 0; d = c; c = b; b = a; a = (t1 + t2) >>> 0;
      }
      H[0] += a; H[1] += b; H[2] += c; H[3] += d; H[4] += e; H[5] += f; H[6] += g; H[7] += h;
    }
    return [...H].map((x) => x.toString(16).padStart(8, '0')).join('');
  }

  /** Verify a hypgraph/1-bundle string-for-string — the same checks as hypgraph.verify_bundle in Python. */
  // ── verifying a bundle: the same checks as hypgraph.bundle.verify_bundle / store.check_rows (keep them in step) ──
  const ROW_TABLES = ['nodes', 'versions', 'edges', 'withdrawals', 'retractions', 'leases'];
  const STANDING_NOTE = 'standing (review state, support, at-risk, the sentence) is what the exporting engine derived: the '
    + 'chain doesn\'t cover it. Re-derive it from the verified rows with `hypgraph verify --standing`.';
  const cp = (s, n) => Array.from(String(s)).slice(0, n).join('');            // Python's s[:n]: code points, not UTF-16
  const same = (a, b) => {                                                     // JSON values, as Python's ==
    if (a === b) return true;
    if (a == null || b == null) return (a ?? null) === (b ?? null);
    if (typeof a !== 'object' || typeof b !== 'object') return false;
    if (Array.isArray(a) !== Array.isArray(b)) return false;
    const ka = Object.keys(a), kb = Object.keys(b);
    return ka.length === kb.length && ka.every((k) => Object.prototype.hasOwnProperty.call(b, k) && same(a[k], b[k]));
  };

  const label = (t, k) => t === 'versions' ? `version ${String(k).replace(/#(\d+)$/, ' v$1')}`   // as store._label names rows
    : ({ nodes: 'node ', edges: 'link ', withdrawals: 'withdrawal of ', retractions: 'retraction of link ' })[t] + k;

  /** What the tables must hold, read from the events alone; then both directions against the rows. */
  async function checkRows(events, tables, importer) {
    const want = Object.fromEntries(ROW_TABLES.map((t) => [t, new Map()])), leases = [], unchecked = {};
    const put = (t, key, checks) => {
      if (want[t].has(key)) return `two events write ${label(t, key)}`;
      want[t].set(key, checks); return '';
    };
    const who = (actor, p, strict) => {
      if ('as' in p) return actor === importer ? ['eq', p.as] : ['bad', `only the ${importer} credits another author`];
      if (strict || actor !== importer) return ['eq', actor];
      return ['any', 'nodes.created_by'];
    };
    for (const ev of events) {
      const k = ev.kind, ref = ev.ref, p = ev.payload || {}, at = ev.at, actor = ev.actor;
      let problem = '';
      if (k === 'create') {
        const strict = 'reason_sha' in p;
        problem = put('nodes', ref, [['type', 'eq', p.type], ['code', 'eq', p.code], ['inv', 'eq', p.inv],
          ['created_at', 'eq', at], ['created_by', ...who(actor, p, strict)]])
          || put('versions', `${ref}#${Number(p.v ?? 1)}`, [['at', 'eq', at], ['by', 'eq', actor], ['body', 'sha', p.body_sha],
            strict ? ['reason', 'sha', p.reason_sha] : ['reason', 'unchecked', 'versions.reason']]);
      } else if (k === 'revise') {
        problem = put('versions', `${ref}#${Number(p.v)}`, [['at', 'eq', at], ['by', 'eq', actor], ['body', 'sha', p.body_sha],
          'reason_sha' in p ? ['reason', 'sha', p.reason_sha] : ['reason', 'head', String(p.reason ?? '')]]);
      } else if (k === 'review') {
        const strict = 'code' in p;
        problem = put('nodes', p.review, [['type', 'eq', 'review'], ['created_at', 'eq', at],
          strict ? ['code', 'eq', p.code] : ['code', 'unchecked', 'nodes.code'],
          strict ? ['inv', 'eq', p.inv] : ['inv', 'inv_of', ref], ['created_by', ...who(actor, p, strict)]])
          || put('versions', `${p.review}#1`, [['at', 'eq', at], ['by', 'eq', actor], ['reason', 'eq', ''], ['body', 'sha', p.body_sha]]);
      } else if (k === 'link') {
        problem = put('edges', Number(p.edge), [['src', 'eq', ref], ['rel', 'eq', p.rel], ['dst', 'eq', p.dst],
          ['dst_v', 'eq', p.dst_v], ['data', 'sha', p.data_sha], ['at', 'eq', at], ['by', 'eq', actor],
          'src_v' in p ? ['src_v', 'eq', p.src_v] : ['src_v', 'unchecked', 'edges.src_v'],
          'why_sha' in p ? ['why', 'sha', p.why_sha] : ['why', 'unchecked', 'edges.why']]);
      } else if (k === 'withdraw') {
        const strict = 'why_sha' in p;
        problem = put('withdrawals', ref, [['at', 'eq', at], ['by', ...who(actor, p, strict)],
          strict ? ['why', 'sha', p.why_sha] : ['why', 'head', String(p.why ?? '')]]);
      } else if (k === 'retract') {
        problem = put('retractions', Number(p.edge), [['at', 'eq', at], ['by', 'eq', actor],
          'why_sha' in p ? ['why', 'sha', p.why_sha] : ['why', 'unchecked', 'retractions.why']]);
      } else if (k === 'lease_take' || k === 'lease_release') {
        const note = 'note_sha' in p ? ['note', 'sha', p.note_sha] : 'note' in p ? ['note', 'eq', cp(p.note, 300)]
          : ['note', 'unchecked', 'leases.note'];
        leases.push([['node', 'eq', ref], ['agent', 'eq', p.for || actor], ['task', 'eq', p.task], ['kind', 'eq', k.slice(6)],
          ['at', 'eq', at], ['expires', 'eq', p.expires ?? ''], note]);
      }
      if (problem) return { problem };
    }
    const invOf = new Map();
    want.nodes.forEach((checks, id) => checks.forEach(([f, how, v]) => { if (f === 'inv' && how === 'eq') invOf.set(id, v); }));
    const mismatch = async (row, checks) => {
      for (const [field, how, v] of checks) {
        const got = row[field];
        let ok;
        if (how === 'eq') ok = same(got, v);
        else if (how === 'sha') ok = typeof got === 'string' && await sha256(got) === v;
        else if (how === 'head') ok = typeof got === 'string' && cp(got, 300) === v;
        else if (how === 'inv_of') ok = same(got, invOf.get(v));
        else if (how === 'bad') return v;
        else { if (got != null && got !== '') unchecked[v] = (unchecked[v] || 0) + 1; ok = true; }
        if (!ok) return field;
      }
      return '';
    };
    const keys = { nodes: (r) => r.id, versions: (r) => `${r.node}#${Number(r.v)}`, edges: (r) => Number(r.id),
      withdrawals: (r) => r.node, retractions: (r) => Number(r.edge) };
    for (const [t, key] of Object.entries(keys)) {
      const have = new Map();
      for (const r of tables[t] || []) {
        const k = key(r);
        if (have.has(k)) return { problem: `${label(t, k)} appears twice` };
        have.set(k, r);
      }
      for (const [k, r] of have) {
        if (!want[t].has(k)) return { problem: `${label(t, k)} has no event` };
        const bad = await mismatch(r, want[t].get(k));
        if (bad) return { problem: `${label(t, k)} differs from its event (${bad})` };
      }
      for (const k of want[t].keys()) if (!have.has(k)) return { problem: `${label(t, k)} is missing: its event says it was written` };
    }
    const rows = [...(tables.leases || [])].sort((a, b) => Number(a.id) - Number(b.id));
    if (new Set(rows.map((r) => Number(r.id))).size !== rows.length) return { problem: 'a lease id appears twice' };
    if (rows.length !== leases.length) return { problem: `${rows.length} lease rows for ${leases.length} lease events` };
    for (let i = 0; i < rows.length; i++) {
      const bad = await mismatch(rows[i], leases[i]);
      if (bad) return { problem: `lease ${rows[i].id} differs from its event (${bad})` };
    }
    return { unchecked };
  }

  const titleOf = (b) => cp(b.statement || b.title || b.text || b.aim || b.summary || b.choice || b.citation || b.name
    || b.path || b.verdict || '', 300);

  /** The investigation a bundle says it is scoped to ('' for the whole record). Not covered by the chain. */
  const scopeOf = (b) => (b.scope && typeof b.scope === 'object' && !Array.isArray(b.scope) ? String(b.scope.inv || '') : '');

  /** The scope must be the one shape export() writes (bundle.py _scope_problem): it names an investigation node, the
   *  bundle holds only that investigation's nodes, and only a scoped bundle redacts events. */
  function scopeProblem(b, tables, redacted) {
    const inv = scopeOf(b);
    if (!inv) return redacted ? `the bundle has no scope but ${redacted} redacted event(s): only an export of one investigation redacts events, so this is a cut of the record presented as the whole of it` : '';
    const n = tables.nodes.find((x) => x.id === inv);
    if (!n) return `the bundle's scope names ${inv}, which the record doesn't hold`;
    if (n.type !== 'investigation') return `the bundle's scope names ${n.code || inv}, a ${n.type}, not an investigation: a scope is always an investigation`;
    const other = tables.nodes.filter((x) => x.id !== inv && x.inv !== inv);
    if (other.length) return `the bundle's scope is ${n.code || inv}, but it holds ${other.length} node(s) of other investigations (${other[0].code || other[0].id} first): an export of one investigation holds only its own`;
    return '';
  }

  /** The derived views are presentation; every fact in them the rows fix must agree with the verified rows. A
   *  lifecycle is checked against the current rule only; one that matches only 0.3's rule goes on `historical` as
   *  [name, shown, current] (bundle.py _derived_problem): not a problem, not checked either. A scoped bundle with
   *  redacted events may show a replaceable node superseded from another investigation: it goes on `unconfirmed`. */
  function derivedProblem(b, tables, historical = null, unconfirmed = null, redacted = 0) {
    const d = b.derived;
    if (d == null) return '';
    if (typeof d !== 'object') return 'derived is not an object';
    const nodes = new Map(tables.nodes.map((n) => [n.id, n])), latest = new Map();
    tables.versions.forEach((v) => { if (v.v > ((latest.get(v.node) || [0])[0])) latest.set(v.node, [v.v, JSON.parse(v.body)]); });
    const withdrawn = new Set(tables.withdrawals.map((w) => w.node)), retracted = new Set(tables.retractions.map((r) => Number(r.edge)));
    const live = new Map(tables.edges.filter((e) => !retracted.has(Number(e.id))).map((e) => [Number(e.id), e]));
    const scope = scopeOf(b);
    const invs = new Set(scope ? [scope] : [...nodes.values()].filter((n) => n.type === 'investigation').map((n) => n.id));
    const replaced = new Map();
    live.forEach((e) => { if (SAME_TYPE.includes(e.rel)) (replaced.get(e.dst) || replaced.set(e.dst, []).get(e.dst)).push(e.src); });
    // derive.lifecycle on the verified rows; since 0.4 a superseded replacement still replaces (chains), 0.3 counted an active one
    const lifecycle = (nid, chains, seen = new Set()) => {
      if (withdrawn.has(nid)) return 'withdrawn';
      const counts = chains ? ['active', 'superseded'] : ['active'];
      for (const s of replaced.get(nid) || []) if (!seen.has(s) && counts.includes(lifecycle(s, chains, new Set([...seen, nid])))) return 'superseded';
      if (nodes.get(nid).type === 'investigation') return ((latest.get(nid) || [0, {}])[1]).state || 'active';
      return 'active';
    };
    const facts = (x, where) => {
      if (!x || typeof x !== 'object' || typeof x.id !== 'string') return `${where} shows a node without its id`;
      const n = nodes.get(x.id);
      if (!n) return `${where} shows ${x.id}, which the record doesn't hold`;
      const name = n.code || n.id;
      const [v, body] = latest.get(n.id) || [0, {}];
      const want = { type: n.type, code: n.code, inv: n.inv, by: n.created_by, at: n.created_at, v, title: titleOf(body),
        kind: body.kind || body.verdict || '' };
      for (const [k, w] of Object.entries(want)) {
        if (!(k in x)) return `${where} shows ${name} without its ${k}`;
        if (!same(x[k], w)) return `${where} shows ${name} with ${k} ${JSON.stringify(x[k])}; the record has ${JSON.stringify(w)}`;
      }
      const st = x.state;
      if (!st || typeof st !== 'object' || !('lifecycle' in st)) return `${where} shows ${name} without its lifecycle`;
      const w = lifecycle(n.id, true), shown = st.lifecycle;
      if (shown === w) return '';
      if (shown === 'superseded' && scope && redacted && !withdrawn.has(n.id) && REPLACEABLE.includes(n.type)) {
        // a replacement in another investigation is among the redacted events: possible, not confirmable
        if (unconfirmed && !unconfirmed.includes(name)) unconfirmed.push(name);
        return '';
      }
      if (shown === lifecycle(n.id, false)) {
        if (historical && !historical.some(([a, s, c]) => a === name && s === shown && c === w)) historical.push([name, shown, w]);
        return '';
      }
      return `${where} shows ${name} as ${JSON.stringify(shown)}; the record makes it ${JSON.stringify(w)}`;
    };
    const byInv = d.by_inv;
    const keys = byInv && typeof byInv === 'object' && !Array.isArray(byInv) ? Object.keys(byInv) : null;
    if (!keys || keys.length !== invs.size || !keys.every((k) => invs.has(k))) return "the views don't cover the record's investigations";
    const listed = d.investigations;
    if (!Array.isArray(listed)) return 'the investigation list is missing';
    for (const x of listed) {
      if (x && typeof x === 'object' && typeof x.id === 'string' && !invs.has(x.id)) return `the investigation list shows ${x.id}, which isn't in the bundle's scope`;
      const p = facts(x, 'the investigation list'); if (p) return p;
    }
    const listedIds = listed.map((x) => x.id), listedSet = new Set(listedIds);
    if (listedIds.length !== listedSet.size || listedSet.size !== invs.size || ![...invs].every((i) => listedSet.has(i))) return "the investigation list doesn't show the record's investigations";
    for (const [inv, v] of Object.entries(byInv)) {
      const sg = (v || {}).subgraph || {}, shown = sg.nodes || [], name = (nodes.get(inv) || {}).code || inv;
      for (const x of shown) { const p = facts(x, `the graph of ${name}`); if (p) return p; }
      const mine = new Set([...nodes.values()].filter((n) => n.inv === inv || n.id === inv).map((n) => n.id));
      const ids = shown.map((x) => x.id), idset = new Set(ids);
      const covers = idset.size === mine.size && [...mine].every((i) => idset.has(i));
      if (ids.length !== idset.size || (!covers && !(mine.size > ids.length && ids.length >= 5000))) return `the graph of ${name} doesn't show the nodes the record holds`;
      const want = new Map([...live].filter(([, e]) => idset.has(e.src) && idset.has(e.dst)));
      const got = sg.edges || [];
      if (!got.every((e) => e && typeof e === 'object' && Number.isInteger(e.id))) return `the graph of ${name} shows a link without its id`;
      if (got.length !== want.size || new Set(got.map((e) => e.id)).size !== got.length || !got.every((e) => want.has(e.id))) return `the graph of ${name} doesn't show the live links the record holds`;
      for (const e of got) {
        const r = want.get(e.id);
        for (const k of ['src', 'src_v', 'rel', 'dst', 'dst_v', 'at', 'by', 'why', 'data']) {
          if (!(k in e)) return `the graph shows link ${e.id} without its ${k}`;
          if (k !== 'data' && !same(e[k], r[k])) return `the graph shows link ${e.id} with ${k} ${JSON.stringify(e[k])}; the record has ${JSON.stringify(r[k])}`;
        }
        if (!same(e.data, JSON.parse(r.data))) return `the graph shows link ${e.id} with other data than the record`;
      }
    }
    return '';
  }

  /** Check a bundle in the browser: the chain, then the rows against the events both ways, then the derived views
   *  against the rows. Standing isn't covered (see STANDING_NOTE). With `head`, also that the chain ends at it. */
  // the bundle's policy isn't covered by the chain: the verifier trusts only what its caller supplies (bundle.py)
  const POLICY_DEFAULT = { reviewers: [], instrument: 'lab', operator: 'operator', importer: 'importer', system: 'system',
    max_creates_per_minute: 60, extra_reserved: [] };
  const normPolicy = (p) => {
    const o = { ...POLICY_DEFAULT };
    for (const k of Object.keys(o)) if (p && p[k] !== undefined) o[k] = p[k];
    for (const k of ['reviewers', 'extra_reserved']) o[k] = [...new Set(o[k] || [])].sort();
    return o;
  };
  function policyProblem(b, policy) {
    const stated = normPolicy(b.policy || {});
    for (const k of Object.keys(policy || {})) {
      if (!(k in stated)) continue;
      const want = normPolicy({ [k]: policy[k] })[k];
      if (!same(stated[k], want)) return `the bundle states ${k} ${JSON.stringify(stated[k])}; the policy you trust has ${JSON.stringify(want)}`;
    }
    return '';
  }

  const MALFORMED = 'the bundle is malformed: a field is missing or of the wrong kind';
  async function verifyBundle(b, head = '', opts = {}) {
    try { return await verifyBundleRaw(b, head, opts); } catch (e) {
      if (e instanceof TypeError || e instanceof SyntaxError || e instanceof RangeError) return { ok: false, problem: MALFORMED };
      throw e;
    }
  }

  async function verifyBundleRaw(b, head = '', opts = {}) {
    if (!b || b.format !== 'hypgraph/1-bundle') return { ok: false, problem: 'not a hypgraph/1-bundle' };
    const policy = opts.policy || null;
    const pp = policyProblem(b, policy);
    if (pp) return { ok: false, problem: pp };
    let prev = '0'.repeat(64), checked = 0, red = 0;
    const events = [], seqs = new Set();
    for (const ev of [...(b.events || [])].sort((x, y) => x.seq - y.seq)) {
      if (seqs.has(ev.seq)) return { ok: false, broken_at: ev.seq, problem: 'two events share a sequence number' };
      seqs.add(ev.seq);
      if (ev.redacted) {
        if (ev.prev !== prev) return { ok: false, broken_at: ev.seq, problem: 'chain broken (redacted event)' };
        prev = ev.hash; red += 1; continue;
      }
      if (await sha256(ev.body) !== ev.hash) return { ok: false, broken_at: ev.seq, problem: 'event body does not match its hash' };
      let body = null;
      try { body = JSON.parse(ev.body); } catch { /* not JSON */ }
      if (!body || typeof body !== 'object' || Array.isArray(body)) return { ok: false, broken_at: ev.seq, problem: "event body isn't a JSON object" };
      if (body.prev !== prev) return { ok: false, broken_at: ev.seq, problem: 'chain broken (prev does not match)' };
      prev = ev.hash; checked += 1;
      events.push(body);
    }
    const order = [...seqs].sort((x, y) => x - y);
    if (!order.every((q, i) => q === i + 1)) return { ok: false, problem: "the events aren't numbered 1 to n: sequence numbers were changed, or events dropped from the start or the middle" };
    if (b.head && b.head !== prev) return { ok: false, problem: "the chain does not end at the bundle's head" };
    const tables = Object.fromEntries(ROW_TABLES.map((t) => [t, b[t] || []]));
    const importer = String((policy || {}).importer || 'importer'), stated = String((b.policy || {}).importer || 'importer');
    const rows = await checkRows(events, tables, importer);
    if (rows.problem) return { ok: false, problem: rows.problem + (stated !== importer ? ` (the bundle names ${stated} as its importer, which the chain doesn't cover; if you trust that, verify with --importer ${stated})` : '') };
    const sp = scopeProblem(b, tables, red);
    if (sp) return { ok: false, problem: sp };
    const historical = [], unconfirmed = [];
    const dp = derivedProblem(b, tables, historical, unconfirmed, red);
    if (dp) return { ok: false, problem: `the derived views contradict the verified record: ${dp}` };
    const partial = Object.keys(rows.unchecked).length > 0 || red > 0;
    const out = { ok: true, checked, head: prev, complete: red === 0, redacted: red, nodes: tables.nodes.length,
      edges: tables.edges.length, unchecked: rows.unchecked, coverage: partial ? 'partial' : 'complete',
      views: b.derived == null ? 'none' : historical.length ? 'historical' : unconfirmed.length ? 'unconfirmed' : 'checked',
      policy: { trusted: Object.keys(policy || {}).sort(), importer }, standing: { checked: false, note: STANDING_NOTE } };
    const notes = [];
    if (red) notes.push(`${red} event(s) are redacted. The bundle says they lie outside this investigation, but a redacted event keeps only its hash, so that can't be checked: a change hidden among them (a withdrawal, say) would not show. Only the full record, verified against the published head, rules that out.`);
    if (stated !== importer) notes.push(`The bundle names ${stated} as its importer; the chain doesn't cover that, so ${importer} was used.`);
    const listed = (names) => names.slice(0, 8).join('; ') + (names.length > 8 ? `; and ${names.length - 8} more` : '');
    if (historical.length) {
      const shown = listed(historical.map(([a, s, c]) => `${a} shown ${s}, the current rule makes it ${c}`));
      notes.push(`The views are not checked: ${historical.length} lifecycle(s) follow hypgraph 0.3's rule, not the current one (${shown}). A bundle exported by 0.3 shows them so, but the chain doesn't record which version exported a bundle, so this can't be told from an edited view. Go by the current rule.`);
    }
    if (unconfirmed.length) notes.push(`The views are not checked: ${unconfirmed.length} node(s) are shown superseded with no replacement in this bundle (${listed(unconfirmed)}). A replacement in another investigation would be among the redacted events, which keep only their hashes, so this can't be confirmed here: the rows make them active. Only the full record, verified against the published head, settles it.`);
    if (notes.length) out.warning = notes.join(' ');
    return anchored(out, head);
  }

  /** A verification held against a head published elsewhere: the full hash or its first 16+ hex characters. */
  function anchored(res, head) {
    const want = String(head || '').trim().toLowerCase();
    if (!want || !res.ok) return res;
    if (want.length < 16 || !/^[0-9a-f]+$/.test(want)) return { ...res, ok: false, problem: "the anchor must be the head's hash, or at least its first 16 hex characters" };
    if (!String(res.head || '').startsWith(want)) return { ...res, ok: false, anchored: false, problem: `the chain ends at ${String(res.head).slice(0, 16)}…, not at the anchored head ${want.slice(0, 16)}…: this is not the record that was published (rewritten, cut short, or another record)` };
    return { ...res, anchored: true };
  }

  // ── data sources ──────────────────────────────────────────────────
  const settle = async (p) => { try { return await p; } catch { return null; } };   // a route a host doesn't serve → null

  /** Live: the JSON API of `hypgraph serve`, or any host that serves the same routes under its own prefix. */
  function HttpSource(base = '/api/graph', fetchOpts = {}) {
    const get = async (path) => {
      const r = await fetch(base + path, fetchOpts);
      let body = null;
      try { body = await r.json(); } catch { /* not json */ }
      if (!r.ok) throw new Error((body && (body.detail?.error || body.detail || body.error)) || `HTTP ${r.status}`);
      return body;
    };
    const q = encodeURIComponent;
    const src = {
      kind: 'http', live: true, base,
      investigations: () => get('/investigations'),
      node: (id) => get(`/node/${q(id)}?history=1`),
      why: (id) => get(`/why/${q(id)}`),
      impact: (id) => get(`/impact/${q(id)}`),
      events: (after, inv, limit) => get(`/events?after=${after || 0}&inv=${q(inv || '')}&limit=${limit || 5000}`),
      exportUrl: (inv) => `${base}/export?inv=${q(inv)}`,
      async load(inv) {
        const [subgraph, stages, board, completion, orders, report, profile, events, verify, refusals, node, telemetry] = await Promise.all([
          get(`/subgraph?inv=${q(inv)}`), settle(get(`/stages?inv=${q(inv)}`)), settle(get(`/board?inv=${q(inv)}`)),
          settle(get(`/completion?inv=${q(inv)}`)), settle(get(`/orders?inv=${q(inv)}`)), settle(get(`/report?inv=${q(inv)}`)),
          settle(get(`/profile?inv=${q(inv)}`)), settle(src.events(0, inv, 5000)), settle(get('/verify')),
          settle(get(`/refusals?inv=${q(inv)}`)), settle(src.node(inv)), settle(get(`/telemetry?inv=${q(inv)}&limit=10000`))]);
        return { subgraph, stages: stages && stages.stages, board: board && board.board, completion,
          orders: orders && orders.orders, report, profile, events, verify, refusals, node, telemetry };
      },
      /** Follow the record and the swarm's telemetry: Server-Sent Events from /stream, or polling /events and
       *  /telemetry where a host has no stream. */
      follow(inv, after, onEvent, onState, onTel, telAfter) {
        let es = null, timer = null, closed = false, head = after || 0, toff = telAfter || 0;
        const poll = async () => {
          if (closed) return;
          try {
            const out = await src.events(head, inv, 500);
            (out.events || []).forEach((e) => { head = Math.max(head, e.seq); onEvent(e); });
            if (onTel) {
              const t = await settle(get(`/telemetry?inv=${q(inv)}&after=${toff}`));
              if (t) { (t.events || []).forEach(onTel); toff = t.next || toff; }
            }
            onState('polling');
          } catch { onState('offline'); }
          timer = setTimeout(poll, 5000);
        };
        if (typeof EventSource === 'function') {
          let opened = false;
          es = new EventSource(`${base}/stream?inv=${q(inv)}&after=${head}&after_telemetry=${toff}`);
          es.onopen = () => { opened = true; onState('live'); };
          es.addEventListener('record', (m) => { try { const e = JSON.parse(m.data); head = Math.max(head, e.seq); onEvent(e); } catch { /* skip */ } });
          es.addEventListener('telemetry', (m) => { try { if (onTel) onTel(JSON.parse(m.data)); } catch { /* skip */ } });
          es.onerror = () => {
            if (!opened) { es.close(); es = null; poll(); }       // no stream route here: poll instead
            else onState('reconnecting');                          // EventSource retries by itself (Last-Event-ID)
          };
        } else poll();
        return () => { closed = true; if (es) es.close(); clearTimeout(timer); };
      },
    };
    return src;
  }

  /** Static: a hypgraph/1-bundle (from `hypgraph export`) — no server, no Python. */
  function BundleSource(bundle) {
    const d = bundle.derived || { by_inv: {}, investigations: [], stats: {} };
    const nodes = new Map(), edges = [];
    Object.values(d.by_inv || {}).forEach((v) => {
      ((v.subgraph || {}).nodes || []).forEach((n) => nodes.set(n.id, n));
      ((v.subgraph || {}).edges || []).forEach((e) => edges.push(e));
    });
    const out = new Map(), inn = new Map();
    edges.forEach((e) => { (out.get(e.src) || out.set(e.src, []).get(e.src)).push(e); (inn.get(e.dst) || inn.set(e.dst, []).get(e.dst)).push(e); });
    const versions = new Map();
    (bundle.versions || []).forEach((v) => { (versions.get(v.node) || versions.set(v.node, []).get(v.node)).push({ ...v, body: JSON.parse(v.body) }); });
    versions.forEach((list) => list.sort((a, b) => a.v - b.v));
    const withdrawn = new Map((bundle.withdrawals || []).map((w) => [w.node, w]));
    const evs = (bundle.events || []).filter((e) => !e.redacted).map((e) => { const b = JSON.parse(e.body); return { seq: e.seq, at: b.at, actor: b.actor, kind: b.kind, ref: b.ref, payload: b.payload }; });
    const head = evs.length ? evs[evs.length - 1].seq : 0;
    const why = (id) => {
      const outRels = ['derived_from', 'requires', 'based_on', 'executes', 'uses', 'cites', 'tests'], inRels = ['supports', 'produced'];
      const seen = new Set([id]); let frontier = [id]; const es = [];
      while (frontier.length && seen.size < 300) {
        const nxt = [];
        frontier.forEach((x) => {
          const ups = (out.get(x) || []).filter((e) => outRels.includes(e.rel)).map((e) => [e, e.dst])
            .concat((inn.get(x) || []).filter((e) => inRels.includes(e.rel)).map((e) => [e, e.src]));
          ups.forEach(([e, y]) => { es.push(e); if (!seen.has(y)) { seen.add(y); nxt.push(y); } });
        });
        frontier = nxt;
      }
      return { center: id, nodes: [...seen].map((x) => nodes.get(x)).filter(Boolean), edges: es };
    };
    const impact = (id) => {
      const step = (x) => (inn.get(x) || []).filter((e) => RISKY.includes(e.rel)).map((e) => [e.src, e.rel])
        .concat((out.get(x) || []).filter((e) => e.rel === 'produced').map((e) => [e.dst, 'produced']))
        .concat((out.get(x) || []).filter((e) => e.rel === 'supports').map((e) => [e.dst, 'supports']));
      const seen = new Set([id]), dep = []; let frontier = [[id, 0]];
      while (frontier.length && dep.length < 500) {
        const nxt = [];
        frontier.forEach(([x, k]) => step(x).forEach(([y, rel]) => { if (!seen.has(y)) { seen.add(y); dep.push({ node: nodes.get(y), rel, depth: k + 1 }); nxt.push([y, k + 1]); } }));
        frontier = nxt;
      }
      return { center: id, dependents: dep.filter((x) => x.node) };
    };
    const node = async (id) => {
      const n = nodes.get(id); if (!n) throw new Error(`no node ${id}`);
      const vs = versions.get(id) || [];
      return { ...n, body: vs.length ? vs[vs.length - 1].body : {}, versions: vs, out: out.get(id) || [], in: inn.get(id) || [],
        ...(withdrawn.has(id) ? { withdrawn: withdrawn.get(id) } : {}) };
    };
    let verified = null;
    const evsOf = (inv) => evs.filter((e) => !inv || e.ref === inv || (nodes.get(e.ref) || {}).inv === inv);
    return {
      kind: 'bundle', live: false, bundle,
      investigations: async () => ({ investigations: d.investigations || [], stats: d.stats || {} }),
      node, why: async (id) => why(id), impact: async (id) => impact(id),
      events: async (after, inv) => ({ head, events: evsOf(inv).filter((e) => e.seq > (after || 0)) }),
      async load(inv) {
        const v = d.by_inv[inv] || {};
        verified = verified || await verifyBundle(bundle);
        let invNode = null;
        try { invNode = await node(inv); } catch { invNode = (d.investigations || []).find((x) => x.id === inv) || null; }
        return { subgraph: v.subgraph || { nodes: [], edges: [] }, stages: v.stages || null, board: v.board || null,
          completion: v.completion || null, orders: v.orders || null, report: v.report || null, profile: v.profile || null,
          events: { head, events: evsOf(inv) }, verify: verified, refusals: null, node: invNode,
          telemetry: v.telemetry || (bundle.telemetry ? { events: (bundle.telemetry.events || bundle.telemetry).filter((t) => !t.inv || t.inv === inv) } : null) };
      },
    };
  }

  // ── the model: one investigation, from either source ──────────────
  function makeModel(inv, raw) {
    const nodes = (raw.subgraph && raw.subgraph.nodes) || [], edges = (raw.subgraph && raw.subgraph.edges) || [];
    const byId = new Map(nodes.map((n) => [n.id, n])), byCode = new Map(nodes.filter((n) => n.code).map((n) => [n.code, n]));
    const profile = raw.profile || { id: '', name: '', labels: {}, workflow: null };
    const body = (raw.node && raw.node.body) || {};
    const events = ((raw.events && raw.events.events) || []).slice().sort((a, b) => a.seq - b.seq);
    return {
      inv, nodes, edges, byId, byCode, profile, events, raw,
      head: (raw.events && raw.events.head) || (events.length ? events[events.length - 1].seq : 0),
      code: (raw.node && raw.node.code) || (byId.get(inv) || {}).code || 'INV', title: body.title || (raw.node && raw.node.title) || (byId.get(inv) || {}).title || inv,
      objective: body.objective || '', pid: profile.id || body.profile || '',
      stages: raw.stages, board: raw.board, completion: raw.completion, orders: raw.orders, report: raw.report,
      verify: raw.verify, refusals: raw.refusals,
      tel: ((raw.telemetry && raw.telemetry.events) || []).slice().sort((a, b) => a.ts - b.ts),
      telNext: (raw.telemetry && raw.telemetry.next) || 0, telSource: raw.telemetry ? (raw.telemetry.exists !== false) : false,
      L: (t) => (profile.labels && profile.labels[t]) || cap(t),
      codeOf: (id) => ((byId.get(id) || {}).code) || id,
    };
  }
  const st = (n) => (n && n.state) || {};
  const reviewOf = (n) => ((st(n).review || {}).state) || '';
  const staleOf = (n) => { const s = st(n).stale; return Array.isArray(s) ? s : (s ? [String(s)] : []); };
  const TYPE_COLOR = { investigation: '#f79009', question: '#0b6bcb', hypothesis: '#7a5af8', claim: '#12b76a', experiment: '#ee46bc',
    run: '#2e90fa', result: '#06aed4', artifact: '#98a2b3', source: '#eaaa08', review: '#cbd5e1', decision: '#f97066', task: '#667085' };
  const PROFILE_COLOR = { scientific: '#0b6bcb', software: '#5925dc', trading: '#b54708', knowledge: '#067647', optimization: '#c11574' };
  const VIEWS = [['overview', '▦', 'Overview'], ['live', '◉', 'Live'], ['pipeline', '⇶', 'Pipeline'], ['graph', '⬡', 'Graph'],
    ['evidence', '☰', 'Evidence'], ['orders', '▤', 'Work orders'], ['audit', '⛓', 'Audit log'], ['report', '❐', 'Report']];
  const LOGO = '<svg viewBox="0 0 64 64" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#0a0d14"/><g fill="none" stroke-linecap="round" stroke-width="3"><path d="M18 44 L32 20 L46 44" stroke="#7cf3ff"/><path d="M18 44 L46 44" stroke="#b18cff" stroke-dasharray="3 5"/></g><circle cx="32" cy="20" r="6" fill="#4ee08a"/><circle cx="18" cy="44" r="5" fill="#7cf3ff"/><circle cx="46" cy="44" r="5" fill="none" stroke="#ff4d5e" stroke-width="3"/></svg>';

  // the pill shows the standing in the UI's language (T); standingKey stays English: filters, CSV and tests use it
  function standingPill(n, T) {
    if (!n) return '';
    const s = st(n), rv = reviewOf(n), stale = staleOf(n);
    // no lifecycle: say so rather than default it (a withdrawn claim must never read as active)
    if (s.lifecycle == null) return `<span class="pill warn" title="${esc(T('st.unknown.tip'))}"><span class="d"></span>${esc(T('st.unknown'))}</span>`;
    if (s.lifecycle === 'withdrawn') return `<span class="pill bad"><span class="d"></span>${esc(T('st.withdrawn'))}</span>`;
    if (s.lifecycle === 'superseded') return `<span class="pill neutral">${esc(T('st.superseded'))}</span>`;
    if (stale.length) return `<span class="pill warn" title="${esc(stale[0])}"><span class="d"></span>${esc(T('st.stale'))}</span>`;
    if (s.at_risk) return `<span class="pill warn"><span class="d"></span>${esc(T('st.at_risk'))}</span>`;
    if (rv === 'contested') return `<span class="pill bad"><span class="d"></span>${esc(T('st.contested'))}</span>`;
    if (rv === 'checked') return `<span class="pill ok"><span class="d"></span>${esc(T('st.checked'))}</span>`;
    if (rv === 'unchecked') return `<span class="pill neutral">${esc(T('st.unchecked'))}</span>`;
    if (rv === 'needs_revalidation') return `<span class="pill warn">${esc(T('st.needs_revalidation'))}</span>`;
    return `<span class="pill neutral">${esc(T.word('life.', s.lifecycle))}</span>`;
  }
  const standingKey = (n) => { const s = st(n), rv = reviewOf(n); return s.lifecycle == null ? 'unknown' : s.lifecycle === 'withdrawn' ? 'withdrawn' : s.lifecycle === 'superseded' ? 'superseded'
    : staleOf(n).length ? 'stale' : s.at_risk ? 'at risk' : rv || s.lifecycle; };
  const STANDINGS = { checked: 'st.checked', unchecked: 'st.unchecked', contested: 'st.contested', stale: 'st.stale', 'at risk': 'st.at_risk',
    superseded: 'st.superseded', withdrawn: 'st.withdrawn' };

  function csv(rows) { return rows.map((r) => r.map((c) => { const s = String(c ?? ''); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }).join(',')).join('\n'); }
  function download(name, text, type = 'text/plain') {
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([text], { type })); a.download = name;
    document.body.appendChild(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }
  function md(src) {                                     // the report's markdown: headings, tables, lists, emphasis
    const lines = String(src || '').split('\n'); let out = '', i = 0;
    const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>').replace(/(^|[\s(])_(.+?)_(?=[\s).,;:]|$)/g, '$1<i>$2</i>').replace(/`(.+?)`/g, '<code>$1</code>');
    while (i < lines.length) {
      const l = lines[i];
      if (/^#{1,6} /.test(l)) { const h = Math.min(l.match(/^#+/)[0].length + 1, 4); out += `<h${h}>${inline(l.replace(/^#+ /, ''))}</h${h}>`; i++; continue; }
      if (l.startsWith('|')) {
        const rows = []; while (i < lines.length && lines[i].startsWith('|')) rows.push(lines[i++]);
        const cells = (r) => r.replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
        out += '<table><thead><tr>' + cells(rows[0]).map((c) => `<th scope="col">${inline(c)}</th>`).join('') + '</tr></thead><tbody>' +
          rows.slice(2).map((r) => '<tr>' + cells(r).map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') + '</tbody></table>';
        continue;
      }
      if (/^[-*] /.test(l)) { out += '<ul>'; while (i < lines.length && /^[-*] /.test(lines[i])) out += `<li>${inline(lines[i++].slice(2))}</li>`; out += '</ul>'; continue; }
      if (l.trim()) out += `<p>${inline(l)}</p>`;
      i++;
    }
    return out;
  }

  // ── words: every string the UI shows, English first (the source); hypgraph.i18n.js adds the other languages ──
  // What the record and the engine say (statements, sentences, gate reasons, the report, the verifier's problems and
  // warnings) is shown as written, in English, in every language: audits and agents parse it. i18n/glossary.json
  // fixes the terms. Placeholders: {name}. Nouns for node types (and the profiles' labels) come from `nouns`.
  const LANGS = { en: 'English', es: 'Español', fr: 'Français', de: 'Deutsch', 'zh-Hans': '简体中文' };
  const EN = /* strings:en */{
    "search": "Search the record", "search.aria": "Search the record (Ctrl+K)", "theme.aria": "Switch theme", "theme.tip": "Theme (t)",
    "lang.aria": "Language", "loading": "Loading the record…", "drawer.aria": "Details", "pal.aria": "Search",
    "pal.placeholder": "Jump to a view, investigation, node or question…", "pal.view": "view · {n}", "pal.investigation": "investigation",
    "pal.none": "No match.",
    "view.overview": "Overview", "view.live": "Live", "view.pipeline": "Pipeline", "view.graph": "Graph", "view.evidence": "Evidence",
    "view.orders": "Work orders", "view.audit": "Audit log", "view.report": "Report",
    "nav.investigation": "Investigation", "nav.investigations": "Investigations", "nav.open": "{n} open", "no_profile": "no profile",
    "st.unknown": "unknown", "st.unknown.tip": "this view gives no lifecycle for it", "st.withdrawn": "withdrawn",
    "st.superseded": "superseded", "st.stale": "stale", "st.at_risk": "at risk", "st.contested": "contested", "st.checked": "checked",
    "st.unchecked": "unchecked", "st.needs_revalidation": "re-check", "life.active": "active", "life.closed": "closed",
    "life.published": "published",
    "chain.ok": "⛓ verified · {n}", "chain.ok.tip": "hash chain and every row re-verified: {n} events, head {head}…",
    "chain.partial": "partial coverage", "chain.partial.tip": "Not every row field is vouched for by its event",
    "chain.partial.redacted": "{n} event(s) outside this investigation are redacted", "chain.exported": "standing as exported",
    "chain.views": "views not checked", "chain.bad": "⛓ does not verify", "chain.bad.at": "⛓ does not verify at #{n}",
    "stream.live": "live", "stream.polling": "polling", "stream.polling.tip": "this host has no event stream; checking every 5 s",
    "stream.reconnecting": "reconnecting", "stream.offline": "offline",
    "exported": "{what} as exported with the bundle, not verified: the chain covers the record's rows, not what an engine derived from them. Re-derive it with <code>hypgraph verify --standing</code>.",
    "exp.overview": "Completion and the counts below are", "exp.pipeline": "Stages and gates are", "exp.evidence": "Standing is",
    "exp.orders": "Order status is", "exp.report": "This report is",
    "stage.aria": "stage {i} of {of}", "gate.met": "met", "gate.not_met": "not met", "gate.current": "current", "optional": "optional",
    "alert.noverify": "The record does not verify: {problem}", "alert.noverify.at": "The record does not verify at event #{n}: {problem}",
    "alert.stale": "{n} node(s) rest on evidence that changed: {codes}", "alert.contested": "{n} {noun}(s) contested: {codes}",
    "alert.at_risk": "{n} node(s) at risk — a premise fell: {codes}", "alert.lease": "{task} held by {who} past its lease",
    "alert.returned": "{n} work order(s) returned, waiting on the record: {codes}", "alert.refused": "{n} overclaim(s) refused by the record",
    "lvl.bad": "action", "lvl.warn": "check", "lvl.info": "note", "raised.tip": "raised {n} times", "open": "open",
    "alerts.none": "Nothing needs attention.",
    "tel.repeat.refused": "{seat}'s {tool} was refused 3 times in a row: {error}",
    "tel.repeat.failed": "{seat}'s {tool} was failed 3 times in a row: {error}",
    "tel.loop": "{seat} called {tool} with the same arguments 3 times in a row — a loop?",
    "tel.model_failed": "{n} model call(s) failed: {error}", "tel.budget": "the run has used {pct} % of its budget",
    "tr.model_failed": "model call failed", "tr.model": "model {model} · {tok} tokens", "tr.model_name": "model {model}", "tr.refused": "{tool} refused by the record",
    "tr.tool_failed": "tool {tool} failed", "tr.tool": "tool {tool}", "tr.took": "took {order}", "tr.finished": "finished {order} · {calls}",
    "tr.scheduler": "scheduler: {event}", "tr.run_started": "run started · {title}", "tr.run_ended": "run ended · {stopped} · {n} calls",
    "who.run": "run", "who.scheduler": "scheduler", "calls.n": "{n} call(s)", "calls.one": "{n} call", "calls.many": "{n} calls",
    "trace.none": "No work orders in the telemetry yet.", "trace.in_flight": "in flight", "trace.running": "running",
    "trace.order": "Work order", "trace.no_calls": "No calls yet.",
    "os.open": "open", "os.overdue": "overdue", "os.returned": "returned", "os.accepted": "accepted", "os.cancelled": "cancelled",
    "os.reworked": "reworked", "os.ended": "ended",
    "fly.calling": "calling {model}", "fly.the_model": "the model", "fly.running": "running {tool}", "fly.on": "on {order}",
    "refused.n": "{n} refused", "lanes.none": "Nobody has started yet.", "lanes.scheduler": "scheduler",
    "lanes.scheduler.sub": "reworks · escalations", "lg.in_flight": "in flight", "lg.model_call": "model call", "lg.tool_call": "tool call",
    "lg.refused": "refused by the record", "lg.failed": "failed", "lg.rework": "rework · escalation",
    "kpi.settled": "{Ns} settled", "kpi.complete": "investigation complete", "kpi.in_progress": "in progress", "kpi.checked": "{Ns} checked",
    "kpi.checked.sub": "by an independent reviewer", "kpi.stale": "Stale evidence", "kpi.stale.yes": "rests on changed files or pages",
    "kpi.stale.no": "nothing rests on changed inputs", "kpi.contested": "Contested", "kpi.contested.yes": "open objections",
    "kpi.contested.no": "no open objections", "kpi.orders.sub": "accepted by the record", "kpi.spend": "Spend",
    "kpi.spend.calls": "{n} model calls", "kpi.spend.tel": "{n} model calls · from telemetry", "kpi.spend.none": "not metered",
    "pill.complete": "Complete", "pill.in_progress": "In progress", "plural": "{Ns}",
    "ov.through": "through the {name} workflow · {stages}", "col.stage": "Stage", "col.status": "Status",
    "stage.of": "stage {i} of {of}", "q.settled": "settled", "q.contested": "contested", "q.open": "open",
    "ov.no_questions": "No questions in this investigation yet.", "ov.attention": "Needs attention", "ov.completion": "Completion",
    "ov.kernel": "kernel", "ov.recent": "Recent activity", "ov.no_events": "No events.",
    "pl.no_workflow": "This investigation has no workflow profile, so its questions have no stages. Start an investigation with a <code>@2</code> profile (scientific, software, trading, knowledge, optimization) to see them move through its workflow.",
    "pl.no_stages": "This host doesn't serve the workflow stages (<code>/api/graph/stages</code>, hypgraph ≥ 0.5).",
    "pl.lede": "Each {noun} moves through the {name} workflow. The stage is derived from the record, never set by hand, and each gate says what would meet it.",
    "ev.lede": "Every {claim}, {result} and source with its derived standing: checked, stale, contested, at risk.",
    "csv": "Export CSV", "ev.filter": "Filter by code, text or author", "ev.filter.aria": "Filter evidence", "ev.standing": "Standing",
    "ev.any": "any standing", "ev.shown": "{n} shown", "col.code": "Code", "col.type": "Type", "col.statement": "Statement",
    "col.author": "Author", "col.standing": "Standing", "rerun": "re-run", "ev.none": "Nothing matches.",
    "or.none": "This host doesn't serve work orders (<code>/api/graph/orders</code>).", "none": "none",
    "or.lede": "What the harness asked each seat to do, the record's predicates for done, and how each order ended.",
    "or.col.open": "Open", "or.col.returned": "Returned", "or.col.accepted": "Accepted", "or.col.cancelled": "Cancelled · reworked",
    "or.done_when": "done when {preds}",
    "au.lede": "The record's append-only event log. Every write is hash-chained, and the chain is re-verified when the record is read.",
    "au.verified": "⛓ Verified: {n} events, head {head}, and every row against its event",
    "au.not_covered": "not covered (written before events vouched for them): {fields}", "au.noverify": "⛓ The record does not verify: {problem}",
    "au.actor": "Actor", "au.every_actor": "every actor", "au.event": "Event", "au.every_event": "every event", "au.n": "{n} events",
    "au.seq": "Seq", "au.time": "Time (UTC)", "au.what": "What happened",
    "rp.default": "Facts from the record", "rp.print": "Print · PDF", "rp.md": "Download Markdown", "rp.bundle": "Export bundle",
    "rp.lede": "The facts of the record, generated by the engine that serves or exported it. Interpretation belongs below them.",
    "rp.none": "This host doesn't serve the report.",
    "gr.lede": "The {name} record as a graph: what rests on what. Select a node for its standing, history and provenance.",
    "gr.lede.plain": "The record as a graph: what rests on what. Select a node for its standing, history and provenance.",
    "gr.png": "Export PNG", "gr.json": "Export JSON", "gr.aria": "Graph of {n} nodes", "gr.lg.bad": "at risk · contested",
    "gr.lg.gone": "superseded · withdrawn", "gr.needs": "The graph needs vendor/cytoscape.min.js.",
    "lv.replaying": "Replaying", "lv.running": "Running", "lv.paused": "Paused", "lv.ended": "Run ended · {how}", "lv.failed": "failed",
    "lv.done": "done", "lv.complete": "Complete", "lv.watching": "Watching", "lv.recorded": "Recorded",
    "lv.issued": "Work orders issued", "lv.picked": "Picked up", "lv.returned": "Returned", "lv.reviews": "Reviews",
    "lv.tel": "telemetry · {n} events", "lv.tel.carried": "telemetry · {n} events · not hash-chained",
    "lv.tel.tip": "the swarm's telemetry: model and tool calls, work orders, decisions",
    "lv.tel.tip.carried": "the swarm's telemetry: model and tool calls, work orders, decisions — carried in the bundle as observation; the hash chain does not cover it and nothing derived rests on it",
    "lv.tel.none": "telemetry: not connected",
    "lv.tel.none.tip": "Run the swarm with hypswarm ≥ 0.1.0a7 (telemetry on by default for a record file): model and tool calls, tokens and cost per seat appear here.",
    "lv.k.calls": "Model calls", "lv.k.tokens": "Tokens", "lv.k.cached": "{n} cached", "lv.k.tools": "Tool calls",
    "lv.k.refused": "{n} refused by the record", "lv.k.errors": "Errors", "lv.k.budget": "Budget", "lv.k.of": "of {x}",
    "lv.k.of_calls": "of {n} calls", "lv.k.nocap": "no cap",
    "lv.lede": "Everything the swarm does, as it happens: every model and tool call, who holds which work order, what each seat writes, every review, the record growing.",
    "lv.lede.recorded": " This is the run's recorded log; play it back.",
    "lv.event_of": "event {cur} of {n}", "lv.start.aria": "Back to the start", "lv.pause": "❚❚ Pause", "lv.play": "▶ Play",
    "lv.speed": "Speed", "lv.scrub": "Point in the run", "lv.follow": "Follow live", "lv.jump": "Jump to end", "lv.timeline": "Timeline",
    "lv.timeline.sub": "who held what, when — every call a tick; click an order for its trace", "lv.alerts": "Alerts",
    "lv.seats": "Seats", "lv.seats.sub": "who is working on what", "lv.growing": "The record, growing",
    "lv.graph.aria": "The record as of event {n}", "lv.stream": "Event stream", "lv.stream.sub": "newest first", "lv.show": "Show",
    "lv.feed.all": "record + telemetry", "lv.feed.record": "record", "lv.feed.tel": "telemetry", "lv.trace": "Trace",
    "lv.trace.sub": "where a work order's time went: each model and tool call", "nothing_yet": "Nothing yet.",
    "seat.scheduler": "scheduler", "seat.instrument": "instrument", "seat.refused.tip": "writes the record refused; each refusal says what to fix",
    "err.one": "{n} error", "err.many": "{n} errors", "seat.working": "working {code}", "seat.calls": "{n} call(s) · {tok} tokens",
    "seat.writes.tip": "record writes",
    "say.issued": "issued work order {code}", "say.opened": "opened {noun} {code}", "say.wrote": "wrote {noun} {code}",
    "say.linked": "linked {a} {rel} {b}", "say.reviewed": "reviewed {code} — {verdict}", "say.revised": "revised {code}",
    "say.picked": "{who} picked up {code}", "say.returned": "returned {code}", "say.withdrew": "withdrew {code}",
    "say.retracted": "retracted a link {edge}",
    "dr.close": "Close details", "dr.standing": "Standing", "dr.checked_by": "checked by {who}", "dr.objections": "open objections: {list}",
    "dr.written": "Written", "dr.by": "by", "dr.at": "at", "dr.versions": "versions", "dr.fields": "Fields", "dr.rests_on": "Rests on",
    "dr.nothing": "nothing", "dr.rests_on_it": "What rests on it", "dr.provenance": "Provenance",
    "dr.provenance.sub": "· everything it rests on, to the files", "dr.if_fell": "If it fell", "dr.if_fell.sub": "· what would be at risk",
    "dr.complete": "complete", "dr.settled_by": "settled by {who}", "dr.next": "next: {x}", "dr.gates": "Gates", "dr.met_by": "met by {list}",
    "dr.answered": "Answered by", "dr.no_answer": "No claim answers it yet.",
    "noverify.banner": "This record does not verify: {problem}. What follows is shown as it arrived, unverified.",
    "empty.none": "This record has no investigations yet.",
    "empty.live": " Start a swarm against it and it appears here as soon as it begins.",
    "empty.demo": " <code>hypgraph demo</code> builds one to explore.", "err.read": "Couldn't read the record: {msg}"
  }/* /strings:en */;
  const TABLES = { en: EN };
  /** Add languages, { es: {...}, fr: {...} } — hypgraph.i18n.js calls this; a host may add its own. */
  function addStrings(tables) {
    Object.entries(tables || {}).forEach(([k, t]) => { if (k !== 'en' && t && typeof t === 'object') TABLES[k] = t; });
  }
  if (global.HypGraphStrings) addStrings(global.HypGraphStrings);        // hypgraph.i18n.js was loaded first
  /** A BCP 47 tag as one of LANGS, or ''. zh, zh-CN, zh-SG and zh-Hans… are Simplified Chinese; zh-TW, zh-HK, zh-Hant aren't. */
  function matchLang(tag) {
    const t = String(tag || '').trim().replace(/_/g, '-').toLowerCase();
    if (!t) return '';
    if (t === 'zh' || t.startsWith('zh-hans') || /^zh-(cn|sg|my)$/.test(t)) return 'zh-Hans';
    const base = t.split('-')[0];
    return base !== 'zh' && LANGS[base] ? base : '';
  }
  /** The language to speak: ?lang=, then the host page's own (opts.lang), then the visitor's saved choice, then the
   *  browser's languages in order; English when none is one the UI speaks. */
  function pickLang({ query = '', host = '', saved = '', languages = [] } = {}) {
    for (const c of [query, host, saved, ...(languages || [])]) { const m = matchLang(c); if (m) return m; }
    return 'en';
  }
  const fill = (s, v) => String(s).replace(/\{(\w+)\}/g, (m, k) => (v && v[k] != null ? String(v[k]) : m));
  /** T(key, vars) in one language, falling back to English; T.word(prefix, value) for a data value the table may name;
   *  T.noun(label) the singular and plural of a node type's (or a profile's) display noun. */
  function translator(lang) {
    const t = TABLES[lang] || EN, nouns = t.nouns || {};
    const T = (k, v) => fill(t[k] ?? EN[k] ?? k, v);
    T.lang = TABLES[lang] ? lang : 'en';
    T.word = (prefix, value) => { const k = prefix + value; return t[k] ?? EN[k] ?? String(value ?? ''); };
    T.noun = (label) => {
      const [N, Ns] = T.lang === 'en' ? [label, label + 's'] : nouns[label] || [label, label];
      const low = (x) => (T.lang === 'de' ? x : x.toLowerCase());        // German nouns keep their capital
      return { N, Ns, noun: low(N), nouns: low(Ns) };
    };
    return T;
  }
  // hypgraph.i18n.js is fetched only when a page asks for a language other than English, from beside this script
  const SELF_SRC = (typeof document !== 'undefined' && document.currentScript && document.currentScript.src) || '';
  const loadingStrings = {};
  function loadStrings(lang, url) {
    if (lang === 'en' || TABLES[lang]) return Promise.resolve(true);
    const src = url || (SELF_SRC ? new URL('hypgraph.i18n.js', SELF_SRC).href : '');
    if (!src || typeof document === 'undefined') return Promise.resolve(false);
    loadingStrings[src] = loadingStrings[src] || new Promise((done) => {
      const s = document.createElement('script');
      s.src = src; s.async = true;
      s.onload = () => done(true);
      s.onerror = () => { delete loadingStrings[src]; done(false); };
      (document.head || document.documentElement).appendChild(s);
    });
    return loadingStrings[src].then(() => !!TABLES[lang]);
  }
  const LANG_KEY = 'hypgraph-lang';
  const savedLang = () => { try { return global.localStorage.getItem(LANG_KEY) || ''; } catch { return ''; } };

  // ── the app ───────────────────────────────────────────────────────
  function mount(root, opts) {
    opts = opts || {};
    const src = opts.source || HttpSource();
    root.classList.add('hg');
    const prefersDark = () => !!(global.matchMedia && global.matchMedia('(prefers-color-scheme: dark)').matches);
    if (!root.dataset.theme) root.dataset.theme = opts.theme || (prefersDark() ? 'dark' : 'light');
    if (opts.embed) root.classList.add('hg-embed');   // on a page of its own, not the workbench: short feeds, no scroll trap
    // the language: ?lang=, the host's (opts.lang), the visitor's saved choice, the browser's — English by default
    let T = translator('en');
    const wantLang = pickLang({ query: (global.location && new URLSearchParams(global.location.search).get('lang')) || '',
      host: opts.lang || '', saved: savedLang(),
      languages: global.navigator ? (global.navigator.languages && global.navigator.languages.length ? global.navigator.languages : [global.navigator.language]) : [] });
    const brand = opts.title && !/^atlas$/i.test(opts.title) ? esc(opts.title) : 'Hyp<b>Graph</b>';
    const langSwitch = opts.langSwitch === false ? '' : `<select class="select hg-lang" id="hg-lang">${Object.entries(LANGS).map(([k, name]) =>
      `<option value="${k}" lang="${k}">${esc(name)}</option>`).join('')}</select>`;
    root.innerHTML = `<div class="hg-app">
      <header class="hg-top"><div class="hg-brand">${LOGO}<span>${brand}</span></div>
        <div class="hg-crumb" id="hg-crumb"></div><div class="sp"></div><span id="hg-status"></span><span id="hg-chain"></span>
        <button class="hg-search" id="hg-search" type="button">⌕ <span id="hg-search-t"></span><kbd>⌘K</kbd></button>
        ${langSwitch}<button class="btn" id="hg-theme" type="button">◐</button></header>
      <nav class="hg-nav" id="hg-nav" aria-label="HypGraph"></nav>
      <main class="hg-main" id="hg-main" tabindex="-1"><div class="empty" id="hg-loading"></div></main></div>
      <aside class="hg-drawer" id="hg-drawer" aria-hidden="true"></aside>
      <div class="hg-pal" id="hg-pal" role="dialog"><div class="box"><input id="hg-pal-q">
        <ul id="hg-pal-list" role="listbox"></ul></div></div>`;
    const $ = (s) => root.querySelector(s);
    function chrome() {                                    // the frame's own words, in the current language
      root.setAttribute('lang', T.lang);
      $('#hg-search').setAttribute('aria-label', T('search.aria')); $('#hg-search-t').textContent = T('search');
      $('#hg-theme').setAttribute('aria-label', T('theme.aria')); $('#hg-theme').title = T('theme.tip');
      const sel = $('#hg-lang');
      if (sel) { sel.value = T.lang; sel.setAttribute('aria-label', T('lang.aria')); sel.title = T('lang.aria'); }
      const ld = $('#hg-loading'); if (ld) ld.textContent = T('loading');
      $('#hg-drawer').setAttribute('aria-label', T('drawer.aria')); $('#hg-pal').setAttribute('aria-label', T('pal.aria'));
      $('#hg-pal-q').placeholder = T('pal.placeholder'); $('#hg-pal-q').setAttribute('aria-label', T('pal.aria'));
    }
    chrome();
    /** Speak `lang` (fetching its strings if need be; English if they can't be had). save: the visitor chose it. */
    async function setLang(lang, save) {
      const want = matchLang(lang) || 'en';
      const ok = await loadStrings(want, opts.stringsUrl);
      if (!ok) root.dataset.hgLangError = want; else delete root.dataset.hgLangError;
      T = translator(ok ? want : 'en');
      chrome();
      if (save) {
        try { global.localStorage.setItem(LANG_KEY, T.lang); } catch { /* private mode */ }
        try {                                                             // a ?lang= in the address would win on reload
          const u = new URL(global.location.href);
          if (u.searchParams.has('lang')) { u.searchParams.set('lang', T.lang); global.history.replaceState(global.history.state, '', u); }
        } catch { /* sandboxed frame */ }
        if (opts.onLang) opts.onLang(T.lang);
      }
      if (S.m) render();
      if (S.drawer && S.drawer.q) openQuestion(S.drawer.q); else if (S.drawer && S.drawer.node) openNode(S.drawer.node);
      return T.lang;
    }
    const nounOf = (t) => T.noun(S.m.L(t));                // a node type in the profile's words, in this language
    const TL = (t) => nounOf(t).N;
    const live = opts.live ?? src.live;
    const S = { invs: [], inv: '', m: null, view: 'overview', cursor: null, playing: false, speed: 4, timer: null, stream: 'off',
      lastEventAt: 0, follow: null, cy: null, drawer: null, ev: { q: '', types: new Set(['claim', 'result', 'hypothesis', 'source', 'decision']), standing: '' },
      sort: { k: 'code', asc: true }, audit: { actor: '', kind: '' }, graphTypes: null, palIdx: 0, profiles: new Map() };
    const fail = (e) => { root.dataset.hgError = String((e && e.message) || e); };

    // ── loading ──
    async function loadInvestigations() {
      const out = await src.investigations();
      S.invs = (out.investigations || []).filter((i) => i && i.id);
      await Promise.all(S.invs.slice(0, 40).map(async (i) => {
        try { const n = await src.node(i.id); S.profiles.set(i.id, String(((n && n.body) || {}).profile || '')); } catch { S.profiles.set(i.id, ''); }
      }));
    }
    async function openInv(inv, keep) {
      S.inv = inv; S.telSeen = null;
      const raw = await src.load(inv);
      S.m = makeModel(inv, raw);
      if (!keep) { S.cursor = null; stopPlay(); }
      if (S.follow) S.follow();
      S.follow = null;
      if (live && src.follow) S.follow = src.follow(inv, S.m.head, onLiveEvent, (s) => { S.stream = s; status(); }, onTel, S.m.telNext);
      render();
    }
    let refreshTimer = null;
    function onLiveEvent(e) {
      if (!S.m || S.m.events.some((x) => x.seq === e.seq)) return;
      S.m.events.push(e); S.m.head = Math.max(S.m.head, e.seq); S.lastEventAt = Date.now();
      if (S.view === 'live') renderSoon();
      clearTimeout(refreshTimer);                          // the derived views (stages, standing) follow a moment later
      refreshTimer = setTimeout(async () => {
        try {
          const raw = await src.load(S.inv);
          const evs = S.m.events, tel = S.m.tel; S.m = makeModel(S.inv, raw);
          if (evs.length > S.m.events.length) S.m.events = evs;
          if (tel.length > S.m.tel.length) S.m.tel = tel;
          render();
        } catch { /* keep what we have */ }
      }, 1200);
    }
    const telKey = (t) => `${t.kind}|${t.span || ''}|${t.ts}|${t.event || ''}`;
    function onTel(t) {
      if (!S.m) return;
      if (!S.telSeen) S.telSeen = new Set(S.m.tel.map(telKey));
      const k = telKey(t);
      if (S.telSeen.has(k)) return;
      S.telSeen.add(k); S.m.tel.push(t); S.m.telSource = true; S.lastEventAt = Date.now();
      if (S.view === 'live' || S.view === 'overview') renderSoon();
    }
    let soon = null;
    const renderSoon = () => { if (!soon) soon = setTimeout(() => { soon = null; render(); }, 250); };

    // ── chrome ──
    function nav() {
      const m = S.m;
      const n = { evidence: m.nodes.filter((x) => S.ev.types.has(x.type) && !(x.type === 'decision' && x.by === 'harness')).length,
        orders: (m.orders || []).length, audit: m.events.length, pipeline: (m.stages || []).length };
      const open = (m.orders || []).filter((o) => ['open', 'overdue'].includes(o.status)).length;
      let h = `<h2>${esc(T('nav.investigation'))}</h2>` + VIEWS.map(([k, ico]) =>
        `<button type="button" data-v="${k}" ${S.view === k ? 'aria-current="page"' : ''}><span class="ico" aria-hidden="true">${ico}</span>${esc(T('view.' + k))}` +
        (k === 'live' ? (open ? `<span class="n">${esc(T('nav.open', { n: open }))}</span>` : '') : n[k] != null ? `<span class="n">${n[k]}</span>` : '') + '</button>').join('');
      if (S.invs.length > 1) {
        h += `<h2>${esc(T('nav.investigations'))}</h2>` + S.invs.map((i) => {
          const pid = S.profiles.get(i.id) || '', fam = pid.split('@')[0];
          return `<button type="button" data-inv="${esc(i.id)}" ${i.id === S.inv ? 'aria-current="true"' : ''}><div class="inv">
            <span class="dot" style="background:${PROFILE_COLOR[fam] || 'var(--ink3)'}"></span><div><div class="t">${esc(i.title || i.code)}</div>
            <div class="s">${esc(pid || T('no_profile'))} · ${esc(i.code)}</div></div></div></button>`;
        }).join('');
      }
      $('#hg-nav').innerHTML = h;
    }
    function status() {
      const m = S.m;
      if (!m) return;
      $('#hg-crumb').innerHTML = `<span class="t">${esc(m.code)} · ${esc(m.title)}</span>` +
        (m.pid ? `<span class="pill accent" title="${esc(m.profile.about || '')}">${esc(m.pid)}</span>` : `<span class="pill neutral">${esc(T('no_profile'))}</span>`);
      const v = m.verify;
      // the verifier's own problem, warning and note are shown verbatim (English): only the frame around them is translated
      $('#hg-chain').innerHTML = !v ? '' : v.ok ? `<span class="pill ok" title="${esc(T('chain.ok.tip', { n: v.checked, head: String(v.head || '').slice(0, 12) }))}">${esc(T('chain.ok', { n: v.checked }))}</span>` +
          (v.coverage === 'partial' ? ` <span class="pill warn" title="${esc(T('chain.partial.tip') + (Object.keys(v.unchecked || {}).length ? ': ' + Object.entries(v.unchecked || {}).map(([f, n]) => `${f} ×${n}`).join(', ') : '') + (v.redacted ? '; ' + T('chain.partial.redacted', { n: v.redacted }) : ''))}">${esc(T('chain.partial'))}</span>` : '') +
          (v.views === 'historical' || v.views === 'unconfirmed' ? ` <span class="pill warn" title="${esc(v.warning || '')}">${esc(T('chain.views'))}</span>` : '') +
          (v.standing && !v.standing.checked ? ` <span class="pill neutral" title="${esc(v.standing.note || '')}">${esc(T('chain.exported'))}</span>` : '')
        : `<span class="pill bad" title="${esc(v.problem || '')}">${esc(v.broken_at ? T('chain.bad.at', { n: v.broken_at }) : T('chain.bad'))}</span>`;
      const s = !live ? '' : S.stream === 'live' ? `<span class="pill ok"><span class="d"></span>${esc(T('stream.live'))}</span>`
        : S.stream === 'polling' ? `<span class="pill neutral" title="${esc(T('stream.polling.tip'))}">${esc(T('stream.polling'))}</span>`
        : S.stream === 'reconnecting' ? `<span class="pill warn">${esc(T('stream.reconnecting'))}</span>` : S.stream === 'offline' ? `<span class="pill bad">${esc(T('stream.offline'))}</span>` : '';
      $('#hg-status').innerHTML = s;
    }
    // a bundle's standing, stages, orders and report are what its exporter derived: the chain covers the rows, not these
    const asExported = (what) => {
      const v = S.m && S.m.verify;
      return v && v.ok && v.standing && !v.standing.checked ? `<div class="note" data-exported>${T('exported', { what: esc(T(what)) })}</div>` : '';
    };
    const head = (h, p, acts = '') => `<div class="head"><div><h1>${h}</h1>${p ? `<p>${p}</p>` : ''}</div>${acts ? `<div class="acts">${acts}</div>` : ''}</div>`;

    // ── stage helpers ──
    function stageBar(sq) {
      const stages = (S.m.profile.workflow && S.m.profile.workflow.stages) || [];
      if (!stages.length || !sq) return '';
      return `<div class="bar" role="img" aria-label="${esc(T('stage.aria', { i: sq.index, of: sq.of }))}">` + stages.map((s, i) => {
        const g = (sq.gates || []).find((x) => x.stage === s.name);
        const c = g && g.met ? 'met' : i === sq.index - 1 ? 'cur' : s.optional ? 'opt' : '';
        return `<span class="${c}" title="${esc(s.name)}${g ? ' — ' + esc(g.met ? T('gate.met') : g.why || T('gate.not_met')) : ''}"></span>`;
      }).join('') + '</div>';
    }
    const isBookkeeping = (n) => n.type === 'decision' && n.by === 'harness';

    function alerts() {
      const m = S.m, out = [];
      const claims = m.nodes.filter((n) => n.type === 'claim');
      const stale = m.nodes.filter((n) => ['claim', 'result', 'source', 'decision'].includes(n.type) && staleOf(n).length && st(n).lifecycle === 'active');
      if (m.verify && !m.verify.ok) out.push(['bad', m.verify.broken_at ? T('alert.noverify.at', { n: m.verify.broken_at, problem: m.verify.problem || '' }) : T('alert.noverify', { problem: m.verify.problem || '' })]);
      if (stale.length) out.push(['warn', T('alert.stale', { n: stale.length, codes: stale.slice(0, 6).map((n) => n.code).join(', ') }), stale[0].code]);
      const contested = claims.filter((c) => reviewOf(c) === 'contested');
      if (contested.length) out.push(['bad', T('alert.contested', { n: contested.length, ...nounOf('claim'), codes: contested.map((n) => n.code).join(', ') }), contested[0].code]);
      const risk = m.nodes.filter((n) => st(n).at_risk && st(n).lifecycle === 'active');
      if (risk.length) out.push(['warn', T('alert.at_risk', { n: risk.length, codes: risk.slice(0, 6).map((n) => n.code).join(', ') }), risk[0].code]);
      const now = Date.now(), held = new Map();
      m.events.forEach((e) => { const p = e.payload || {};
        if (e.kind === 'lease_take') held.set(p.task, { who: p.for, until: Date.parse(p.expires || '') });
        if (e.kind === 'lease_release') held.delete(p.task); });
      held.forEach((h, task) => { if (h.until && h.until < now) out.push(['warn', T('alert.lease', { task: m.codeOf(task), who: h.who })]); });
      const returned = (m.orders || []).filter((o) => o.status === 'returned');
      if (returned.length) out.push(['info', T('alert.returned', { n: returned.length, codes: returned.map((o) => o.code).join(', ') })]);
      const r = m.refusals && (m.refusals.refused ?? m.refusals.total);
      if (r) out.push(['info', T('alert.refused', { n: r })]);
      if (m.tel.length) out.push(...telAlerts(m.tel));
      return out;
    }
    const alertList = (items) => {
      const seen = new Map();                            // the same alert raised four times is one line, ×4
      items.forEach(([lvl, txt, code]) => { const k = lvl + '|' + txt, h = seen.get(k); if (h) h.n++; else seen.set(k, { lvl, txt, code, n: 1 }); });
      const rows = [...seen.values()];
      return rows.length ? `<ul class="alerts">${rows.map(({ lvl, txt, code, n }) =>
        `<li><span class="pill ${lvl}">${esc(T(lvl === 'bad' ? 'lvl.bad' : lvl === 'warn' ? 'lvl.warn' : 'lvl.info'))}</span><span>${esc(txt)}${n > 1 ? ` <span class="pill neutral" title="${esc(T('raised.tip', { n }))}">×${n}</span>` : ''}${code ? ` <button class="btn" type="button" data-n="${esc(code)}" style="padding:1px 8px">${esc(T('open'))}</button>` : ''}</span></li>`).join('')}</ul>`
        : `<div class="dim">${esc(T('alerts.none'))}</div>`;
    };

    // ── telemetry (what the swarm did that the record can't see) ──
    function telUpTo() {                                   // the telemetry the current replay position has reached
      const m = S.m;
      if (S.cursor == null) return m.tel;
      const ev = m.events[Math.max(0, Math.min(S.cursor, m.events.length) - 1)];
      if (!ev || S.cursor === 0) return [];
      const cut = Date.parse(ev.at) / 1000 + 0.999;
      return m.tel.filter((t) => t.ts <= cut);
    }
    // a tool call the record refused (an overclaim, a missing gate) is the record doing its job, not a failure
    const refusedCall = (t) => t.kind === 'tool_end' && t.ok === false && /^refused|\brefused:/.test(String(t.error || ''));
    const failed = (t) => t.ok === false && !refusedCall(t);
    function telStats(tel) {
      const ends = tel.filter((t) => t.kind === 'model_end'), tools = tel.filter((t) => t.kind === 'tool_end');
      const sum = (xs, k) => xs.reduce((a, t) => a + (Number(t[k]) || 0), 0);
      const run = tel.find((t) => t.kind === 'run_start'), b = (run && run.budget) || {};
      const usd = sum(ends, 'usd'), calls = ends.reduce((a, t) => a + (Number(t.calls) || 1), 0);
      const used = b.max_usd ? usd / b.max_usd : b.max_calls ? calls / b.max_calls : null;
      return { calls, tin: sum(ends, 'in'), tout: sum(ends, 'out'), cached: sum(ends, 'cached'), usd, tools: tools.length,
        errors: ends.filter(failed).length + tools.filter(failed).length, refused: tools.filter(refusedCall).length, budget: b, used,
        run, ended: tel.find((t) => t.kind === 'run_end') };
    }
    function openSpans(tel) {                               // spans started and not ended: what is in flight
      const open = new Map();
      tel.forEach((t) => { if (t.kind.endsWith('_start')) open.set(t.span, t); else if (t.kind.endsWith('_end')) open.delete(t.span); });
      return [...open.values()];
    }
    const fmtUsd = (x) => !x ? '$0' : x >= 0.01 ? '$' + x.toFixed(2) : x >= 0.0001 ? '$' + x.toFixed(4) : '<$0.0001';
    const fmtN = (x) => x >= 10000 ? (x / 1000).toFixed(1) + 'k' : String(x);
    function telAlerts(tel) {
      const out = [], last = new Map(), runs = new Map();
      tel.forEach((t) => {
        if (t.kind !== 'tool_end' && t.kind !== 'tool_start') return;
        const key = `${t.seat}|${t.tool}`;
        if (t.kind === 'tool_end') {
          const n = t.ok === false ? (last.get(key) || 0) + 1 : 0;
          last.set(key, n);
          if (n === 3) out.push(['warn', T(refusedCall(t) ? 'tel.repeat.refused' : 'tel.repeat.failed', { seat: t.seat, tool: t.tool, error: String(t.error || '').slice(0, 90) })]);
        } else {
          const sig = `${t.seat}|${t.tool}|${JSON.stringify(t.args || {})}`, r = runs.get(t.seat) || { sig: '', n: 0 };
          r.n = r.sig === sig ? r.n + 1 : 1; r.sig = sig; runs.set(t.seat, r);
          if (r.n === 3) out.push(['warn', T('tel.loop', { seat: t.seat, tool: t.tool })]);
        }
      });
      const errs = tel.filter((t) => t.kind === 'model_end' && t.ok === false);
      if (errs.length) out.push(['bad', T('tel.model_failed', { n: errs.length, error: String(errs[errs.length - 1].error || '').slice(0, 100) })]);
      const st = telStats(tel);
      if (st.used != null && st.used >= 0.8 && !st.ended) out.push(['warn', T('tel.budget', { pct: Math.round(st.used * 100) })]);
      return out;
    }
    function telRow(t) {
      const c = (x) => `<span class="code">${esc(x)}</span>`, d = (x) => `<span class="dim">${esc(x)}</span>`;
      const tm = String(t.at || '').slice(11, 19);
      let what;
      switch (t.kind) {
        case 'model_end': what = t.ok === false ? `<span class="tel-bad">${esc(T('tr.model_failed'))}</span> ${d(String(t.error || '').slice(0, 120))}`
          : `${T('tr.model', { model: d(t.model || ''), tok: `${fmtN(t.in || 0)}→${fmtN(t.out || 0)}` })}${t.usd ? ' · ' + fmtUsd(t.usd) : ''} · ${t.s}s${(t.tool_calls || []).length ? ' → ' + t.tool_calls.map(esc).join(', ') : ''}`; break;
        case 'tool_end': what = refusedCall(t) ? `<span class="tel-warn">${T('tr.refused', { tool: esc(t.tool) })}</span> ${d(String(t.error || '').replace(/^refused:?\s*/, '').replace(/\b(\w+ refused):\s*\1:\s*/g, '$1: ').slice(0, 140))}`
          : t.ok === false ? `<span class="tel-bad">${T('tr.tool_failed', { tool: esc(t.tool) })}</span> ${d(String(t.error || '').slice(0, 120))}` : `${T('tr.tool', { tool: c(t.tool) })} · ${t.s}s`; break;
        case 'order_start': what = `${T('tr.took', { order: c(t.order) })} ${d('· ' + (t.model || ''))}`; break;
        case 'order_end': what = `${T('tr.finished', { order: c(t.order), calls: esc(T('calls.n', { n: t.calls || 0 })) })}${t.stopped ? ' ' + d('· ' + t.stopped) : ''}`; break;
        case 'decision': what = `${T('tr.scheduler', { event: esc(t.event) })}${t.order ? ' ' + c(t.order) : ''}${t.why || t.missing ? ' ' + d('— ' + String(t.why || t.missing).slice(0, 100)) : ''}`; break;
        case 'run_start': what = T('tr.run_started', { title: esc(t.title || '') }); break;
        case 'run_end': what = `${T('tr.run_ended', { stopped: esc(t.stopped || ''), n: t.calls || 0 })}${t.usd ? ' · ' + fmtUsd(t.usd) : ''}`; break;
        default: return '';
      }
      return `<div class="ev tel"><span class="seq">${esc(tm)}</span><span class="who">${esc(t.seat || T(t.kind.startsWith('run') ? 'who.run' : 'who.scheduler'))}</span><span>${what}</span></div>`;
    }
    function trace(tel) {
      const orders = tel.filter((t) => t.kind === 'order_start');
      if (!orders.length) return `<div class="empty">${esc(T('trace.none'))}</div>`;
      const pick = orders.find((o) => o.order === S.traceOrder) || orders[orders.length - 1];
      const kids = tel.filter((t) => t.parent === pick.span && (t.kind === 'model_end' || t.kind === 'tool_end' || t.kind === 'model_start' || t.kind === 'tool_start'));
      const ended = new Map(kids.filter((t) => t.kind.endsWith('_end')).map((t) => [t.span, t]));
      const startOf = new Map(kids.filter((t) => t.kind.endsWith('_start')).map((t) => [t.span, t]));
      const oend = tel.find((t) => t.kind === 'order_end' && t.span === pick.span);
      // "now" is the wall clock while following live, and the replay position while replaying
      const now = S.cursor == null ? Date.now() / 1000 : (tel.length ? tel[tel.length - 1].ts : pick.ts);
      const t0 = pick.ts, t1 = oend ? oend.ts : Math.max(t0 + 0.001, now);
      const span = Math.max(t1 - t0, 0.001);
      const rows = [...startOf.values()].map((s) => {
        const e = ended.get(s.span), dur = e ? Math.max(e.s || (e.ts - s.ts), 0) : Math.max(now - s.ts, 0);
        const left = ((s.ts - t0) / span) * 100, width = Math.max((dur / span) * 100, 0.6);
        const kind = s.kind.split('_')[0], bad = e && e.ok === false ? (refusedCall(e) ? ' refused' : ' bad') : '';
        const label = kind === 'model' ? `${T('tr.model_name', { model: s.model || '' })}${e ? ` · ${fmtN(e.in || 0)}→${fmtN(e.out || 0)}${e.usd ? ' · ' + fmtUsd(e.usd) : ''}` : ' · ' + T('trace.in_flight')}`
          : `${s.tool}${e ? '' : ' · ' + T('trace.running')}`;
        return `<div class="tr"><span class="tl">${esc(label)}</span><span class="tb"><i class="${kind}${bad}${e ? '' : ' open'}" style="left:${left.toFixed(2)}%;width:${Math.min(width, 100 - left).toFixed(2)}%"></i></span><span class="ts">${dur.toFixed(2)}s</span></div>`;
      }).join('');
      return `<div class="toolbar" style="margin:0 0 8px"><label class="dim" for="hg-trace-order">${esc(T('trace.order'))}</label>
        <select class="select" id="hg-trace-order">${orders.map((o) => `<option value="${esc(o.order)}" ${o === pick ? 'selected' : ''}>${esc(o.order)} · ${esc(o.seat)}</option>`).join('')}</select>
        <span class="dim">${esc(pick.model || '')} · ${(t1 - t0).toFixed(1)}s${oend ? ` · ${esc(T('calls.n', { n: oend.calls || 0 }))}${oend.stopped ? ' · ' + esc(oend.stopped) : ''}` : ' · ' + esc(T('trace.running'))}</span></div>
        <div class="trace">${rows || `<div class="dim">${esc(T('trace.no_calls'))}</div>`}</div>`;
    }

    function lanes(tel, running) {                     // the swarm as swimlanes: seats as rows, orders as bars, calls as ticks
      const m = S.m, all = m.tel, following = S.cursor == null;
      if (!all.length) return '';
      const run = all.find((t) => t.kind === 'run_start'), end = all.find((t) => t.kind === 'run_end');
      const seen = tel.length ? tel[tel.length - 1].ts : (run ? run.ts : all[0].ts);
      const now = following && running ? Date.now() / 1000 : seen;       // the replay position, or the wall clock
      const t0 = run ? run.ts : all[0].ts;
      const t1 = Math.max(end ? end.ts : Math.max(all[all.length - 1].ts, now), t0 + 1);   // a fixed axis while replaying
      const span = t1 - t0, x = (ts) => Math.min(100, Math.max(0, ((ts - t0) / span) * 100));
      const fmtT = (s) => s >= 3600 ? `${Math.floor(s / 3600)}h${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}` : `${Math.floor(s / 60)}:${String(Math.floor(Math.max(s, 0) % 60)).padStart(2, '0')}`;
      const starts = tel.filter((t) => t.kind === 'order_start');
      if (!starts.length) return `<div class="empty">${esc(T('lanes.none'))}</div>`;
      const status = new Map((m.orders || []).map((o) => [o.code, o.status]));
      const ends = new Map(tel.filter((t) => t.kind === 'order_end').map((t) => [t.span, t]));
      const startOf = new Map(tel.filter((t) => t.kind === 'model_start' || t.kind === 'tool_start').map((t) => [t.span, t]));
      const calls = tel.filter((t) => t.kind === 'model_end' || t.kind === 'tool_end');
      const open = openSpans(tel).filter((t) => t.kind === 'model_start' || t.kind === 'tool_start');
      const seats = [...new Set(starts.map((o) => o.seat).concat(calls.map((t) => t.seat)).filter(Boolean))];   // in the order they first took work; a seat that only made calls (the lead's report) still gets its row
      const head = (following && running) || S.playing || !following ? `<u class="playhead" style="left:${x(now).toFixed(2)}%" title="${esc(fmtT(now - t0))}"></u>` : '';
      const rows = seats.map((seat) => {
        const bars = starts.filter((o) => o.seat === seat).map((o) => {
          const e = ends.get(o.span), st = e ? (status.get(o.order) || 'ended') : 'open';   // until it ends, the viewer doesn't know how it ends
          const a = x(o.ts), b = x(e ? e.ts : now);
          const cls = st === 'accepted' ? 'ok' : st === 'reworked' ? 'warn' : st === 'cancelled' ? 'off' : st === 'returned' ? 'info' : e ? 'done' : 'open';
          const title = `${o.order} · ${seat}${o.model ? ' · ' + o.model : ''}\n${e ? `${Number(e.s || e.ts - o.ts).toFixed(1)}s · ${T('calls.n', { n: e.calls || 0 })}${e.stopped ? ' · ' + e.stopped : ''}` : T('trace.in_flight')}\n${T.word('os.', st)}`;
          return `<button type="button" class="ord ${cls}" data-act="lv-trace" data-order="${esc(o.order)}" style="left:${a.toFixed(2)}%;width:${Math.max(b - a, 0.4).toFixed(2)}%" title="${esc(title)}">${esc(o.order)}</button>`;
        }).join('');
        const ticks = calls.filter((t) => t.seat === seat).map((t) => {
          const s = startOf.get(t.span), ts = s ? s.ts : t.ts - (Number(t.s) || 0);
          const a = x(ts), w = Math.max(((Number(t.s) || 0) / span) * 100, 0.15);
          const kind = t.kind === 'model_end' ? (t.ok === false ? 'bad' : 'model') : refusedCall(t) ? 'refused' : failed(t) ? 'bad' : 'tool';
          const title = t.kind === 'model_end' ? `${T('tr.model', { model: t.model || '', tok: `${fmtN(t.in || 0)}→${fmtN(t.out || 0)}` })}${t.usd ? ' · ' + fmtUsd(t.usd) : ''} · ${t.s}s${t.ok === false ? '\n' + String(t.error || '').slice(0, 120) : ''}`
            : `${t.tool} · ${t.s}s${t.ok === false ? '\n' + String(t.error || '').replace(/^refused:?\s*/, '').slice(0, 120) : ''}`;
          return `<u class="tick ${kind}" style="left:${a.toFixed(2)}%;width:${Math.min(w, 100 - a).toFixed(2)}%" title="${esc(title)}"></u>`;
        }).join('');
        const flying = open.filter((t) => t.seat === seat).map((t) => `<u class="tick open ${t.kind === 'model_start' ? 'model' : 'tool'}" style="left:${x(t.ts).toFixed(2)}%;width:${Math.max(x(now) - x(t.ts), 0.15).toFixed(2)}%" title="${esc(t.kind === 'model_start' ? T('fly.calling', { model: t.model || T('fly.the_model') }) : T('fly.running', { tool: t.tool }))}"></u>`).join('');
        const mine = calls.filter((t) => t.seat === seat), n = mine.filter((t) => t.kind === 'model_end').length;
        const usd = mine.reduce((a, t) => a + (Number(t.usd) || 0), 0), refs = mine.filter(refusedCall).length;
        return `<div class="lane-row"><div class="lane-lbl"><b>${esc(seat)}</b><span class="dim">${esc(T(n === 1 ? 'calls.one' : 'calls.many', { n }))}${usd ? ' · ' + fmtUsd(usd) : ''}${refs ? ` · <span class="tel-warn">${esc(T('refused.n', { n: refs }))}</span>` : ''}</span></div><div class="lane">${bars}${ticks}${flying}${head}</div></div>`;
      }).join('');
      const marks = tel.filter((t) => t.kind === 'decision' && /rework|escalat|cancel|moot/.test(String(t.event || ''))).map((t) =>
        `<u class="mark" style="left:${x(t.ts).toFixed(2)}%" title="${esc(`${T('tr.scheduler', { event: t.event })}${t.order ? ' ' + t.order : ''}${t.why || t.missing ? ' — ' + String(t.why || t.missing).slice(0, 100) : ''}`)}"></u>`).join('');
      const sched = marks ? `<div class="lane-row"><div class="lane-lbl"><b>${esc(T('lanes.scheduler'))}</b><span class="dim">${esc(T('lanes.scheduler.sub'))}</span></div><div class="lane">${marks}${head}</div></div>` : '';
      const step = [5, 10, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600].find((s) => span / s <= 8) || 3600;
      let ax = '';
      for (let s = 0; s <= span; s += step) ax += `<span style="left:${((s / span) * 100).toFixed(2)}%">${fmtT(s)}</span>`;
      return `<div class="lanes">${rows}${sched}<div class="lane-row axis"><div class="lane-lbl"></div><div class="lane">${ax}</div></div></div>
        <div class="legend dim"><i class="ord ok"></i> ${esc(T('os.accepted'))} <i class="ord warn"></i> ${esc(T('os.reworked'))} <i class="ord info"></i> ${esc(T('os.returned'))} <i class="ord off"></i> ${esc(T('os.cancelled'))} <i class="ord open"></i> ${esc(T('lg.in_flight'))}
          <span class="gap"></span><u class="tick model"></u> ${esc(T('lg.model_call'))} <u class="tick tool"></u> ${esc(T('lg.tool_call'))} <u class="tick refused"></u> ${esc(T('lg.refused'))} <u class="tick bad"></u> ${esc(T('lg.failed'))} <u class="mark"></u> ${esc(T('lg.rework'))}</div>`;
    }

    // ── views ──
    function vOverview() {
      const m = S.m, qs = m.board || [], claims = m.nodes.filter((n) => n.type === 'claim');
      const settled = qs.filter((q) => q.status === 'settled').length, checked = claims.filter((c) => reviewOf(c) === 'checked').length;
      const stale = m.nodes.filter((n) => staleOf(n).length && st(n).lifecycle === 'active').length;
      const contested = claims.filter((c) => reviewOf(c) === 'contested').length;
      const orders = m.orders || [], done = orders.filter((o) => o.status === 'accepted').length;
      const sp = (m.report && m.report.spend) || {};
      const comp = m.completion;
      const kp = [[T('kpi.settled', nounOf('question')), `${settled}/${qs.length}`, comp ? T(comp.complete ? 'kpi.complete' : 'kpi.in_progress') : '', ''],
        [T('kpi.checked', nounOf('claim')), `${checked}/${claims.length}`, T('kpi.checked.sub'), ''],
        [T('kpi.stale'), stale, T(stale ? 'kpi.stale.yes' : 'kpi.stale.no'), stale ? 'warn' : ''],
        [T('kpi.contested'), contested, T(contested ? 'kpi.contested.yes' : 'kpi.contested.no'), contested ? 'bad' : ''],
        [T('view.orders'), `${done}/${orders.length}`, T('kpi.orders.sub'), ''],
        sp.metered ? [T('kpi.spend'), '$' + Number(sp.usd || 0).toFixed(3), T('kpi.spend.calls', { n: sp.calls }), '']
          : m.tel.length ? (() => { const t = telStats(m.tel); return [T('kpi.spend'), fmtUsd(t.usd), T('kpi.spend.tel', { n: t.calls }), '']; })()
          : [T('kpi.spend'), '—', T('kpi.spend.none'), '']];
      const stagesBy = new Map((m.stages || []).map((x) => [x.code, x]));
      const wf = m.profile.workflow;
      return head(esc(m.title), esc(m.objective), comp ? `<span class="pill ${comp.complete ? 'ok' : 'warn'}"><span class="d"></span>${esc(T(comp.complete ? 'pill.complete' : 'pill.in_progress'))}</span>` : '') + asExported('exp.overview') +
        `<div class="grid kpis">${kp.map(([k, v, s, c]) => `<div class="card kpi ${c}"><div class="k">${esc(k)}</div><div class="v">${v}</div><div class="s">${esc(s)}</div></div>`).join('')}</div>
        <div class="grid two" style="margin-top:14px">
          <div class="card"><h3>${esc(T('plural', nounOf('question')))} ${wf ? `<span class="sub">${esc(T('ov.through', { name: m.profile.name, stages: wf.stages.map((s) => s.name).join(' → ') }))}</span>` : ''}</h3>
            ${qs.length ? `<table><thead><tr><th scope="col" style="width:56px"></th><th scope="col">${esc(TL('question'))}</th>${wf ? `<th scope="col" style="width:210px">${esc(T('col.stage'))}</th>` : ''}<th scope="col" style="width:110px">${esc(T('col.status'))}</th></tr></thead><tbody>
            ${qs.map((q) => { const sq = stagesBy.get(q.code);
              return `<tr class="click" data-q="${esc(q.code)}" tabindex="0"><td class="code">${esc(q.code)}</td><td>${esc(q.text)}</td>
                ${wf ? `<td>${stageBar(sq)}<div class="dim" style="margin-top:4px">${sq ? `${esc(sq.stage)} · ${esc(T('stage.of', { i: sq.index, of: sq.of }))}` : ''}</div></td>` : ''}
                <td>${q.status === 'settled' ? `<span class="pill ok"><span class="d"></span>${esc(T('q.settled'))}</span>` : q.status === 'contested' ? `<span class="pill bad">${esc(T('q.contested'))}</span>` : `<span class="pill neutral">${esc(T.word('q.', q.status))}</span>`}</td></tr>`; }).join('')}
            </tbody></table>` : `<div class="empty">${esc(T('ov.no_questions'))}</div>`}</div>
          <div class="grid" style="align-content:start">
            <div class="card"><h3>${esc(T('ov.attention'))}</h3><div class="body">${alertList(alerts())}</div></div>
            ${comp ? `<div class="card"><h3>${esc(T('ov.completion'))} <span class="sub">${esc(comp.profile || m.pid || T('ov.kernel'))}</span></h3><div class="body">
              ${(comp.criteria || []).map((c) => `<div class="gate" style="margin-bottom:8px"><span class="m ${c.met ? 'met' : 'no'}" aria-hidden="true">${c.met ? '✓' : '·'}</span>
              <div><b>${esc(String(c.name).replace(/_/g, ' '))}</b> <span class="sr">${esc(T(c.met ? 'gate.met' : 'gate.not_met'))}</span><div class="dim">${esc(c.why)}</div></div></div>`).join('')}</div></div>` : ''}
            <div class="card"><h3>${esc(T('ov.recent'))} <span class="r"><button class="btn" type="button" data-v="audit">${esc(T('view.audit'))}</button></span></h3><div>${m.events.slice(-6).reverse().map((e) => evRow(e)).join('') || `<div class="empty">${esc(T('ov.no_events'))}</div>`}</div></div>
          </div></div>`;
    }

    function vPipeline() {
      const m = S.m, wf = m.profile.workflow;
      if (!wf) return head(esc(T('view.pipeline')), '') + `<div class="note">${T('pl.no_workflow')}</div>`;
      if (!m.stages) return head(esc(T('view.pipeline')), '') + `<div class="note warn">${T('pl.no_stages')}</div>`;
      const stages = wf.stages, cols = `56px repeat(${stages.length}, minmax(120px, 1fr))`;
      const qs = new Map((m.board || []).map((q) => [q.code, q]));
      return head(esc(T('view.pipeline')), esc(T('pl.lede', { ...nounOf('question'), name: m.profile.name }))) + asExported('exp.pipeline') +
        `<div class="card" style="overflow:auto"><div class="lane" style="grid-template-columns:${cols};border-bottom:1px solid var(--line);background:var(--surface2)">
          <div style="min-height:auto"></div>${stages.map((s, i) => `<div style="min-height:auto"><b>${i + 1}. ${esc(s.name)}</b>${s.optional ? ` <span class="pill neutral">${esc(T('optional'))}</span>` : ''}<div class="dim" style="margin-top:2px">${esc(s.holds)}</div></div>`).join('')}</div>
          ${m.stages.map((sq) => `<div class="lane click" data-q="${esc(sq.code)}" tabindex="0" role="button" aria-label="${esc(sq.code)} ${esc((qs.get(sq.code) || {}).text || '')}" style="grid-template-columns:${cols};border-bottom:1px solid var(--line);cursor:pointer">
            <div class="code">${esc(sq.code)}</div>${stages.map((s, i) => { const g = (sq.gates || []).find((x) => x.stage === s.name);
              const c = g && g.met ? 'met' : i === sq.index - 1 ? 'cur' : 'no';
              return `<div><div class="gate"><span class="m ${c}" aria-hidden="true">${c === 'met' ? '✓' : c === 'cur' ? '●' : ''}</span>
                <div><span class="mono">${esc(g ? g.gate : s.gate)}</span><span class="sr">${esc(T(c === 'met' ? 'gate.met' : c === 'cur' ? 'gate.current' : 'gate.not_met'))}</span>
                ${g && g.evidence && g.evidence.length ? `<div class="dim">${g.evidence.slice(0, 3).map(esc).join(', ')}</div>` : ''}
                ${g && !g.met && i === sq.index - 1 ? `<div class="why">${esc(g.why)}</div>` : ''}</div></div></div>`; }).join('')}</div>`).join('')}
        </div>`;
    }

    function evidenceRows() {
      const m = S.m, q = S.ev.q.toLowerCase();
      let rows = m.nodes.filter((n) => S.ev.types.has(n.type) && !isBookkeeping(n));
      if (S.ev.standing) rows = rows.filter((n) => standingKey(n) === S.ev.standing);
      if (q) rows = rows.filter((n) => `${n.code} ${n.title} ${n.by}`.toLowerCase().includes(q));
      const k = S.sort.k, dir = S.sort.asc ? 1 : -1;
      const key = (n) => k === 'type' ? TL(n.type) : k === 'statement' ? n.title : k === 'author' ? n.by : k === 'standing' ? standingKey(n)
        : (n.code || '').replace(/\d+/, (d) => d.padStart(6, '0'));
      return rows.sort((a, b) => String(key(a)).localeCompare(String(key(b))) * dir);
    }
    function vEvidence() {
      const m = S.m, rows = evidenceRows();
      const types = ['claim', 'result', 'hypothesis', 'source', 'decision', 'experiment', 'run', 'artifact'].filter((t) => m.nodes.some((n) => n.type === t));
      const th = (k, label, w) => `<th scope="col" ${w ? `style="width:${w}"` : ''} aria-sort="${S.sort.k === k ? (S.sort.asc ? 'ascending' : 'descending') : 'none'}"><button type="button" data-sort="${k}">${esc(T(label))}${S.sort.k === k ? (S.sort.asc ? ' ↑' : ' ↓') : ''}</button></th>`;
      return head(esc(T('view.evidence')), esc(T('ev.lede', { claim: nounOf('claim').noun, result: nounOf('result').noun })), `<button class="btn" type="button" data-act="csv-evidence">${esc(T('csv'))}</button>`) + asExported('exp.evidence') +
        `<div class="toolbar"><input class="input" id="hg-ev-q" placeholder="${esc(T('ev.filter'))}" value="${esc(S.ev.q)}" aria-label="${esc(T('ev.filter.aria'))}">
          ${types.map((t) => `<button type="button" class="chip" data-evtype="${t}" aria-pressed="${S.ev.types.has(t)}">${esc(TL(t))}</button>`).join('')}
          <select class="select" id="hg-ev-st" aria-label="${esc(T('ev.standing'))}"><option value="">${esc(T('ev.any'))}</option>${Object.entries(STANDINGS).map(([s, k]) => `<option value="${s}" ${S.ev.standing === s ? 'selected' : ''}>${esc(T(k))}</option>`).join('')}</select>
          <span class="dim">${esc(T('ev.shown', { n: rows.length }))}</span></div>
        <div class="card"><table><thead><tr>${th('code', 'col.code', '70px')}${th('type', 'col.type', '140px')}${th('statement', 'col.statement')}${th('author', 'col.author', '120px')}${th('standing', 'col.standing', '120px')}</tr></thead><tbody>
        ${rows.map((n) => `<tr class="click" data-n="${esc(n.id)}" tabindex="0"><td class="code">${esc(n.code)}</td><td>${esc(TL(n.type))}</td><td>${esc(n.title)}</td>
          <td class="dim">${esc(n.by)}${n.by === 'instrument' || n.by === 'lab' ? ` <span class="pill info">${esc(T('rerun'))}</span>` : ''}</td><td>${standingPill(n, T)}</td></tr>`).join('') || `<tr><td colspan="5" class="empty">${esc(T('ev.none'))}</td></tr>`}
        </tbody></table></div>`;
    }

    function vOrders() {
      const m = S.m, os = m.orders;
      if (!os) return head(esc(T('view.orders')), '') + `<div class="note warn">${T('or.none')}</div>`;
      const col = (name, list) => `<div class="col"><h3>${esc(T(name))}<b>${list.length}</b></h3>${list.map(orderCard).join('') || `<div class="dim" style="padding:6px">${esc(T('none'))}</div>`}</div>`;
      return head(esc(T('view.orders')), esc(T('or.lede')), `<button class="btn" type="button" data-act="csv-orders">${esc(T('csv'))}</button>`) + asExported('exp.orders') +
        `<div class="kanban">${col('or.col.open', os.filter((o) => ['open', 'overdue'].includes(o.status)))}${col('or.col.returned', os.filter((o) => o.status === 'returned'))}
        ${col('or.col.accepted', os.filter((o) => o.status === 'accepted'))}${col('or.col.cancelled', os.filter((o) => ['cancelled', 'reworked'].includes(o.status)))}</div>`;
    }
    function orderCard(o) {
      const what = String(o.objective || '').split(': ').slice(-1)[0];
      return `<div class="order"><div class="r"><span class="code">${esc(o.code)}</span><span class="pill neutral">${esc(o.assignee)}</span>
        ${o.status === 'overdue' ? `<span class="pill warn">${esc(T('os.overdue'))}</span>` : ''}<button type="button" class="btn" data-q="${esc(o.target)}" style="margin-left:auto;padding:0 7px">${esc(o.target)}</button></div>
        <div>${esc(what.slice(0, 160))}</div>${o.done_when ? `<div class="dim mono" style="margin-top:4px">${T('or.done_when', { preds: o.done_when.map((p) => esc(p.p)).join(' · ') })}</div>` : ''}
        ${o.returned_note ? `<div class="dim" style="margin-top:3px">“${esc(String(o.returned_note).slice(0, 140))}”</div>` : ''}</div>`;
    }

    function auditRows() { return S.m.events.filter((e) => (!S.audit.actor || e.actor === S.audit.actor) && (!S.audit.kind || e.kind === S.audit.kind)); }
    function vAudit() {
      const m = S.m, rows = auditRows(), v = m.verify;
      const actors = [...new Set(m.events.map((e) => e.actor))].sort(), kinds = [...new Set(m.events.map((e) => e.kind))].sort();
      return head(esc(T('view.audit')), esc(T('au.lede')), `<button class="btn" type="button" data-act="csv-audit">${esc(T('csv'))}</button>`) +
        (v ? `<div class="note ${v.ok ? '' : 'warn'}">${v.ok ? `${T('au.verified', { n: v.checked, head: `<code>${esc(String(v.head || '').slice(0, 16))}…</code>` })}${Object.keys(v.unchecked || {}).length ? ' · ' + T('au.not_covered', { fields: esc(Object.entries(v.unchecked || {}).map(([f, n]) => `${f} ×${n}`).join(', ')) }) : ''}${v.warning ? ' · ' + esc(v.warning) : ''}${v.standing && !v.standing.checked ? ' · ' + esc(v.standing.note) : ''}` : T('au.noverify', { problem: esc(v.problem || '') })}</div>` : '') +
        `<div class="toolbar"><select class="select" id="hg-au-actor" aria-label="${esc(T('au.actor'))}"><option value="">${esc(T('au.every_actor'))}</option>${actors.map((a) => `<option ${S.audit.actor === a ? 'selected' : ''}>${esc(a)}</option>`).join('')}</select>
          <select class="select" id="hg-au-kind" aria-label="${esc(T('au.event'))}"><option value="">${esc(T('au.every_event'))}</option>${kinds.map((k) => `<option ${S.audit.kind === k ? 'selected' : ''}>${esc(k)}</option>`).join('')}</select><span class="dim">${esc(T('au.n', { n: rows.length }))}</span></div>
        <div class="card"><table><thead><tr><th scope="col" style="width:60px">${esc(T('au.seq'))}</th><th scope="col" style="width:170px">${esc(T('au.time'))}</th><th scope="col" style="width:120px">${esc(T('au.actor'))}</th><th scope="col" style="width:120px">${esc(T('au.event'))}</th><th scope="col">${esc(T('au.what'))}</th></tr></thead><tbody>
        ${rows.slice().reverse().slice(0, 2000).map((e) => `<tr><td class="mono dim">${e.seq}</td><td class="mono dim">${esc(String(e.at || '').replace('T', ' ').slice(0, 19))}</td>
          <td>${esc(e.actor)}</td><td><span class="pill neutral">${esc(e.kind)}</span></td><td>${say(e)}</td></tr>`).join('')}</tbody></table></div>`;
    }

    function vReport() {
      const m = S.m, name = (m.profile.workflow && m.profile.workflow.report) || T('rp.default');
      const acts = `<button class="btn" type="button" data-act="print">${esc(T('rp.print'))}</button><button class="btn" type="button" data-act="md">${esc(T('rp.md'))}</button>` +
        (src.exportUrl ? `<a class="btn" href="${esc(src.exportUrl(S.inv))}" download>${esc(T('rp.bundle'))}</a>` : src.bundle ? `<button class="btn" type="button" data-act="bundle">${esc(T('rp.bundle'))}</button>` : '');
      // the report is the engine's text, shown as generated (English)
      return head(esc(name), esc(T('rp.lede')), acts) + asExported('exp.report') +
        `<div class="card"><div class="body md">${m.report ? md(m.report.markdown) : `<div class="empty">${esc(T('rp.none'))}</div>`}</div></div>`;
    }

    function vGraph() {
      const m = S.m, types = [...new Set(m.nodes.map((n) => n.type))].filter((t) => t !== 'review');
      if (!S.graphTypes) S.graphTypes = new Set(types.filter((t) => t !== 'task'));
      return head(esc(T('view.graph')), esc(m.profile.name ? T('gr.lede', { name: m.profile.name }) : T('gr.lede.plain')),
        `<button class="btn" type="button" data-act="png">${esc(T('gr.png'))}</button><button class="btn" type="button" data-act="json">${esc(T('gr.json'))}</button>`) +
        `<div class="toolbar">${types.map((t) => `<button type="button" class="chip" data-gtype="${t}" aria-pressed="${S.graphTypes.has(t)}"><i style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${TYPE_COLOR[t] || '#98a2b3'};margin-right:5px"></i>${esc(TL(t))}</button>`).join('')}</div>
        <div class="card"><div class="graph big" id="hg-graph" role="img" aria-label="${esc(T('gr.aria', { n: m.nodes.length }))}"></div><div class="legend">
          <span><i style="border:2px solid var(--ok)"></i>${esc(T('st.checked'))}</span><span><i style="border:2px dashed var(--warn)"></i>${esc(T('st.stale'))}</span><span><i style="border:2px solid var(--bad)"></i>${esc(T('gr.lg.bad'))}</span><span><i style="background:var(--line2)"></i>${esc(T('gr.lg.gone'))}</span></div></div>`;
    }

    // ── live ──
    function vLive() {
      const m = S.m, n = m.events.length, cur = S.cursor == null ? n : Math.min(S.cursor, n), seen = m.events.slice(0, cur);
      const following = S.cursor == null, last = seen[seen.length - 1];
      const ranTo = telUpTo(), runEnd = ranTo.filter((t) => t.kind === 'run_end').pop(), runStart = ranTo.filter((t) => t.kind === 'run_start').pop();
      const runOpen = runStart && (!runEnd || runEnd.ts < runStart.ts);   // telemetry says whether a run is under way
      const running = S.playing || (following && live && (runOpen || (!runStart && S.stream === 'live' && Date.now() - S.lastEventAt < 30000)));
      const state = S.playing ? T('lv.replaying') : running ? T('lv.running') : !following ? T('lv.paused')
        : runEnd && runEnd === ranTo.filter((t) => t.kind.startsWith('run_')).pop() ? T('lv.ended', { how: runEnd.stopped || T(runEnd.ok === false ? 'lv.failed' : 'lv.done') })
        : m.completion && m.completion.complete ? T('lv.complete') : live ? T('lv.watching') : T('lv.recorded');
      const c = (f) => seen.filter(f).length;
      const kp = [[T('lv.issued'), c((e) => e.kind === 'create' && (e.payload || {}).type === 'task')], [T('lv.picked'), c((e) => e.kind === 'lease_take')],
        [T('lv.returned'), c((e) => e.kind === 'lease_release')], [T('plural', nounOf('result')), c((e) => e.kind === 'create' && (e.payload || {}).type === 'result')],
        [T('plural', nounOf('claim')), c((e) => e.kind === 'create' && (e.payload || {}).type === 'claim')], [T('lv.reviews'), c((e) => e.kind === 'review')]];
      const tel = telUpTo(), ts = telStats(tel);
      const carried = src.kind === 'bundle';                // telemetry handed over in a bundle sits outside its hash chain
      const telPill = m.tel.length ? `<span class="pill ok" title="${esc(T(carried ? 'lv.tel.tip.carried' : 'lv.tel.tip'))}">${esc(T(carried ? 'lv.tel.carried' : 'lv.tel', { n: m.tel.length }))}</span>`
        : `<span class="pill neutral" title="${esc(T('lv.tel.none.tip'))}">${esc(T('lv.tel.none'))}</span>`;
      const tk = m.tel.length ? [[T('lv.k.calls'), ts.calls, ''], [T('lv.k.tokens'), `${fmtN(ts.tin)} → ${fmtN(ts.tout)}`, ts.cached ? T('lv.k.cached', { n: fmtN(ts.cached) }) : ''],
        [T('kpi.spend'), fmtUsd(ts.usd), ''], [T('lv.k.tools'), ts.tools, ts.refused ? T('lv.k.refused', { n: ts.refused }) : ''],
        [T('lv.k.errors'), ts.errors, '', ts.errors ? 'bad' : ''],
        [T('lv.k.budget'), ts.used == null ? '—' : `${Math.round(ts.used * 100)} %`, ts.budget.max_usd ? T('lv.k.of', { x: fmtUsd(ts.budget.max_usd) }) : ts.budget.max_calls ? T('lv.k.of_calls', { n: ts.budget.max_calls }) : T('lv.k.nocap'), ts.used >= 0.8 ? 'warn' : '']] : [];
      return head(esc(T('view.live')), esc(T('lv.lede') + (live ? '' : T('lv.lede.recorded'))), telPill) +
        `<div class="card" style="margin-bottom:14px"><div class="live-head">
          <span class="pulse ${running ? '' : 'off'}" aria-hidden="true"></span><b>${esc(state)}</b>
          <span class="dim">${esc(T('lv.event_of', { cur, n }))}${last ? ' · ' + esc(String(last.at || '').slice(11, 19)) + ' UTC' : ''}</span>
          <button class="btn" type="button" data-act="lv-start" aria-label="${esc(T('lv.start.aria'))}">⏮</button>
          <button class="btn" type="button" data-act="lv-play">${esc(T(S.playing ? 'lv.pause' : 'lv.play'))}</button>
          <select class="select" id="hg-lv-speed" aria-label="${esc(T('lv.speed'))}">${[1, 4, 12, 40].map((x) => `<option value="${x}" ${S.speed === x ? 'selected' : ''}>${x}×</option>`).join('')}</select>
          <input class="scrub" type="range" id="hg-lv-scrub" min="0" max="${n}" value="${cur}" aria-label="${esc(T('lv.scrub'))}">
          <button class="btn" type="button" data-act="lv-live" ${following ? 'disabled' : ''}>${esc(T(live ? 'lv.follow' : 'lv.jump'))}</button></div></div>
        ${tk.length ? `<div class="grid kpis" style="margin-bottom:10px">${tk.map(([k, v, s, c]) => `<div class="card kpi ${c || ''}"><div class="k">${esc(k)}</div><div class="v">${v}</div>${s ? `<div class="s">${esc(s)}</div>` : ''}</div>`).join('')}</div>` : ''}
        <div class="grid kpis" style="margin-bottom:14px">${kp.map(([k, v]) => `<div class="card kpi"><div class="k">${esc(k)}</div><div class="v">${v}</div></div>`).join('')}</div>
        ${m.tel.length ? `<div class="card" style="margin-bottom:14px"><h3>${esc(T('lv.timeline'))} <span class="sub">${esc(T('lv.timeline.sub'))}</span></h3><div class="body">${lanes(tel, running)}</div></div>` : ''}
        ${m.tel.length ? (() => { const a = telAlerts(tel); return a.length ? `<div class="card" style="margin-bottom:14px"><h3>${esc(T('lv.alerts'))}</h3><div class="body">${alertList(a)}</div></div>` : ''; })() : ''}
        <div class="grid live">
          <div class="card"><h3>${esc(T('lv.seats'))} <span class="sub">${esc(T('lv.seats.sub'))}</span></h3>${seats(seen, tel)}</div>
          <div class="card"><h3>${esc(T('lv.growing'))}</h3><div class="graph" id="hg-live-graph" role="img" aria-label="${esc(T('lv.graph.aria', { n: cur }))}"></div></div>
          <div class="card"><h3>${esc(T('lv.stream'))} <span class="sub">${esc(T('lv.stream.sub'))}</span>
            ${m.tel.length ? `<span class="r"><select class="select" id="hg-lv-feed" aria-label="${esc(T('lv.show'))}">${[['all', 'lv.feed.all'], ['record', 'lv.feed.record'], ['telemetry', 'lv.feed.tel']].map(([v, l]) => `<option value="${v}" ${S.feed === v ? 'selected' : ''}>${esc(T(l))}</option>`).join('')}</select></span>` : ''}</h3>
            <div class="feed" aria-live="polite">${feed(seen, tel, running)}</div></div>
        </div>
        ${m.tel.length ? `<div class="card" style="margin-top:14px"><h3>${esc(T('lv.trace'))} <span class="sub">${esc(T('lv.trace.sub'))}</span></h3><div class="body">${trace(tel)}</div></div>` : ''}`;
    }
    function feed(seen, tel, running) {
      const mode = S.feed || 'all', cap = opts.embed ? 15 : 400;
      const rec = mode === 'telemetry' ? [] : seen.slice(-cap).map((e) => ({ ts: Date.parse(e.at) / 1000, e }));
      const tl = mode === 'record' ? [] : tel.filter((t) => !t.kind.endsWith('_start') || t.kind === 'order_start' || t.kind === 'run_start').slice(-cap).map((t) => ({ ts: t.ts, t }));
      const all = rec.concat(tl).sort((a, b) => b.ts - a.ts || ((b.e ? b.e.seq : 0) - (a.e ? a.e.seq : 0))).slice(0, cap);
      return all.map((x, i) => x.e ? evRow(x.e, i === 0 && (S.playing || running)) : telRow(x.t)).join('') || `<div class="empty">${esc(T('nothing_yet'))}</div>`;
    }
    function seats(seen, tel) {
      const m = S.m, by = {};
      seen.forEach((e) => {
        const p = e.payload || {}, who = e.kind === 'lease_take' ? p.for : e.actor;
        if (!who) return;
        const s = by[who] || (by[who] = { writes: 0, holding: null, last: '' });
        if (e.kind === 'lease_take') s.holding = m.codeOf(p.task);
        if (e.kind === 'lease_release') s.holding = null;
        if (['create', 'revise', 'link', 'review', 'withdraw'].includes(e.kind)) s.writes++;
        s.last = say(e, true);
      });
      const ends = (tel || []).filter((t) => t.kind === 'model_end' || t.kind === 'tool_end');
      ends.forEach((t) => { if (t.seat && !by[t.seat]) by[t.seat] = { writes: 0, holding: null, last: '' }; });
      const open = openSpans(tel || []), now = Date.now() / 1000, following = S.cursor == null;
      const names = Object.keys(by).sort((a, b) => (a === 'harness') - (b === 'harness') || a.localeCompare(b));
      return names.map((w) => { const s = by[w];
        const mine = ends.filter((t) => t.seat === w), calls = mine.filter((t) => t.kind === 'model_end');
        const usd = calls.reduce((a, t) => a + (Number(t.usd) || 0), 0), tok = calls.reduce((a, t) => a + (Number(t.in) || 0) + (Number(t.out) || 0), 0);
        const errs = mine.filter(failed).length, refs = mine.filter(refusedCall).length;
        const fly = open.filter((t) => t.seat === w && (t.kind === 'model_start' || t.kind === 'tool_start')).pop();
        const flying = fly ? `<span class="fly"></span>${fly.kind === 'model_start' ? esc(T('fly.calling', { model: fly.model || T('fly.the_model') })) : esc(T('fly.running', { tool: fly.tool }))}${following ? ` · ${Math.max(0, now - fly.ts).toFixed(1)}s` : ''}${fly.order ? ' ' + T('fly.on', { order: `<span class="code">${esc(fly.order)}</span>` }) : ''}` : '';
        return `<div class="seat ${s.holding || fly ? 'busy' : ''}"><div class="av" aria-hidden="true">${esc(w.slice(0, 2).toUpperCase())}</div>
          <div><div class="nm">${esc(w)}${w === 'harness' ? ` <span class="pill neutral">${esc(T('seat.scheduler'))}</span>` : (w === 'instrument' || w === 'lab') ? ` <span class="pill info">${esc(T('seat.instrument'))}</span>` : ''}${refs ? ` <span class="pill warn" title="${esc(T('seat.refused.tip'))}">${esc(T('refused.n', { n: refs }))}</span>` : ''}${errs ? ` <span class="pill bad">${esc(T(errs > 1 ? 'err.many' : 'err.one', { n: errs }))}</span>` : ''}</div>
          <div class="doing">${flying || (s.holding ? T('seat.working', { code: `<span class="code">${esc(s.holding)}</span>` }) : esc(s.last))}</div>
          ${calls.length ? `<div class="dim" style="font-size:11.5px">${esc(T('seat.calls', { n: calls.length, tok: fmtN(tok) }))}${usd ? ' · ' + fmtUsd(usd) : ''}</div>` : ''}</div>
          <span class="mono dim" title="${esc(T('seat.writes.tip'))}">${s.writes}</span></div>`; }).join('')
        || `<div class="empty">${esc(T('lanes.none'))}</div>`;
    }
    function say(e, plain) {
      const m = S.m, p = e.payload || {}, c = (x) => plain ? x : `<span class="code">${esc(x)}</span>`, d = (x) => plain ? x : `<span class="dim">${esc(x)}</span>`;
      const ref = m.codeOf(e.ref);                       // the vars arrive escaped (c, d) or, plain, as text
      switch (e.kind) {
        case 'create': return p.type === 'task' ? T('say.issued', { code: c(p.code || ref) })
          : T(p.type === 'investigation' ? 'say.opened' : 'say.wrote', { noun: plain ? nounOf(p.type).noun : esc(nounOf(p.type).noun), code: c(p.code || ref) });
        case 'link': return T('say.linked', { a: c(ref), rel: d(p.rel || ''), b: c(m.codeOf(p.dst)) });
        case 'review': return T('say.reviewed', { code: c(ref), verdict: plain ? p.verdict : '<b>' + esc(p.verdict) + '</b>' });
        case 'revise': return T('say.revised', { code: c(ref) }) + (p.reason ? ' ' + d('(' + p.reason + ')') : '');
        case 'lease_take': return T('say.picked', { who: plain ? p.for || e.actor : esc(p.for || e.actor), code: c(m.codeOf(p.task)) });
        case 'lease_release': return T('say.returned', { code: c(m.codeOf(p.task)) }) + (p.note ? ' ' + d('— ' + String(p.note).slice(0, 100)) : '');
        case 'withdraw': return T('say.withdrew', { code: c(ref) }) + (p.why ? ' ' + d('— ' + p.why) : '');
        case 'retract': return T('say.retracted', { edge: d('#' + (p.edge || '')) });
        default: return `${plain ? e.kind : esc(e.kind)} ${c(ref)}`;
      }
    }
    function evRow(e, fresh) {
      const p = e.payload || {};
      return `<div class="ev ${fresh ? 'fresh' : ''}"><span class="seq">#${e.seq}</span><span class="who">${esc(e.kind === 'lease_take' ? (p.for || e.actor) : e.actor)}</span><span>${say(e)}</span></div>`;
    }
    function stopPlay() { S.playing = false; clearInterval(S.timer); S.timer = null; }
    function replayFromStart() {                          // open on the Live view, playing the run from its first event
      if (S.view !== 'live') setView('live');
      const still = global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches;
      if (!S.m.events.length || still) return;            // reduced motion: the finished run, with Play one click away
      S.cursor = 0; play();
    }
    function play() {
      const n = S.m.events.length;
      if (S.cursor == null || S.cursor >= n) S.cursor = 0;
      S.playing = true; clearInterval(S.timer);
      S.timer = setInterval(() => { if (S.cursor >= S.m.events.length) { stopPlay(); render(); return; } S.cursor++; render(); }, 1000 / S.speed);
      render();
    }

    // ── graph ──
    function graphInto(el, nodes, edges, fit) {
      if (!el || !global.cytoscape) { if (el) el.innerHTML = `<div class="empty">${esc(T('gr.needs'))}</div>`; return null; }
      const css = getComputedStyle(root), tok = (k) => css.getPropertyValue(k).trim();
      const shown = nodes.filter((n) => n.type !== 'review');
      const ids = new Set(shown.map((n) => n.id));
      const ring = (n) => staleOf(n).length ? 'stale' : (st(n).at_risk || reviewOf(n) === 'contested') ? 'bad' : reviewOf(n) === 'checked' ? 'ok' : '';
      const cy = global.cytoscape({ container: el, wheelSensitivity: 0.25, boxSelectionEnabled: false,
        elements: [...shown.map((n) => ({ data: { id: n.id, label: n.code || '', type: n.type, color: TYPE_COLOR[n.type] || '#98a2b3', ring: ring(n),
          gone: ['superseded', 'withdrawn'].includes(st(n).lifecycle) ? 'y' : '' } })),
          ...edges.filter((e) => ids.has(e.src) && ids.has(e.dst)).map((e, i) => ({ data: { id: `e${i}-${e.src}-${e.dst}`, source: e.src, target: e.dst, rel: e.rel } }))],
        style: [
          { selector: 'node', style: { 'background-color': 'data(color)', label: 'data(label)', 'font-size': 9, color: tok('--ink2'), 'text-valign': 'bottom',
            'text-margin-y': 3, width: 16, height: 16, 'font-family': 'ui-monospace, monospace' } },
          { selector: 'node[type="investigation"]', style: { width: 26, height: 26, shape: 'star' } },
          { selector: 'node[type="question"]', style: { width: 22, height: 22, shape: 'diamond' } },
          { selector: 'node[type="claim"]', style: { shape: 'round-rectangle', width: 20 } },
          { selector: 'node[type="hypothesis"]', style: { shape: 'hexagon', width: 20, height: 18 } },
          { selector: 'node[type="experiment"]', style: { shape: 'round-triangle' } },
          { selector: 'node[type="artifact"]', style: { shape: 'rectangle', width: 12, height: 12 } },
          { selector: 'node[type="source"]', style: { shape: 'tag' } },
          { selector: 'node[type="decision"]', style: { shape: 'octagon' } },
          { selector: 'node[type="task"]', style: { shape: 'tag', width: 12, height: 12, opacity: 0.65 } },
          { selector: 'node[ring="ok"]', style: { 'border-width': 2, 'border-color': tok('--ok') } },
          { selector: 'node[ring="stale"]', style: { 'border-width': 2, 'border-style': 'dashed', 'border-color': tok('--warn') } },
          { selector: 'node[ring="bad"]', style: { 'border-width': 2, 'border-color': tok('--bad') } },
          { selector: 'node[gone="y"]', style: { opacity: 0.35 } },
          { selector: 'edge', style: { width: 1, 'line-color': tok('--line2'), 'target-arrow-shape': 'triangle', 'target-arrow-color': tok('--line2'), 'curve-style': 'bezier', 'arrow-scale': 0.6 } },
          { selector: 'edge[rel="supersedes"]', style: { 'line-style': 'dashed', 'line-color': tok('--warn'), 'target-arrow-color': tok('--warn') } },
          { selector: 'edge[rel="challenges"]', style: { 'line-color': tok('--bad'), 'target-arrow-color': tok('--bad') } },
          { selector: ':selected', style: { 'overlay-color': tok('--accent'), 'overlay-opacity': 0.22, 'overlay-padding': 5 } },
        ] });
      try { cy.layout({ name: hasFcose() ? 'fcose' : 'cose', animate: false, randomize: true, nodeRepulsion: 6500, idealEdgeLength: 60, fit: fit !== false, padding: 24 }).run(); }
      catch { cy.layout({ name: 'cose', animate: false }).run(); }
      cy.on('tap', 'node', (ev) => openNode(ev.target.id()));
      return cy;
    }
    let fcoseKnown = null;
    function hasFcose() {
      if (fcoseKnown != null) return fcoseKnown;
      try { const t = global.cytoscape({ headless: true }); t.layout({ name: 'fcose' }); fcoseKnown = true; } catch { fcoseKnown = false; }
      return fcoseKnown;
    }

    // ── drawer ──
    function drawer(title, sub, body) {
      const d = $('#hg-drawer');
      d.innerHTML = `<header><div style="flex:1;min-width:0"><h2>${title}</h2><div class="dim" style="margin-top:4px">${sub}</div></div>
        <button class="btn" type="button" data-act="close" aria-label="${esc(T('dr.close'))}">✕</button></header>${body}`;
      d.classList.add('open'); d.setAttribute('aria-hidden', 'false');
      const b = d.querySelector('[data-act="close"]'); if (b) b.focus({ preventScroll: true });
    }
    function closeDrawer() { const d = $('#hg-drawer'); d.classList.remove('open'); d.setAttribute('aria-hidden', 'true'); S.drawer = null; syncHash(); }
    const nodeLink = (id, rel) => { const n = S.m.byId.get(id); return `<div class="link"><button type="button" data-n="${esc(id)}"><span class="code">${esc((n && n.code) || id)}</span></button>
      ${rel ? `<span class="dim">${esc(rel)}</span>` : ''}<span class="ink2" style="min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(n ? (TL(n.type) + ' · ' + (n.title || '')) : '')}</span></div>`; };
    async function openNode(idOrCode) {
      const m = S.m, n = m.byId.get(idOrCode) || m.byCode.get(idOrCode);
      if (!n) return;
      if (n.type === 'question') return openQuestion(n.code);
      S.drawer = { node: n.id }; syncHash();
      const s = st(n), rv = s.review || {};
      const skeleton = (det, why, imp) => {
        const body = (det && det.body) || {};
        const fields = Object.entries(body).filter(([k, v]) => v !== '' && v != null && !['title'].includes(k)).slice(0, 14);
        return `
        <section><h4>${esc(T('dr.standing'))}</h4>${standingPill(n, T)} <span style="margin-left:6px">${esc(s.sentence || '')}</span>
          ${staleOf(n).length ? `<div class="why">${esc(staleOf(n).join('; '))}</div>` : ''}
          ${rv.positive && rv.positive.length ? `<div class="dim" style="margin-top:6px">${esc(T('dr.checked_by', { who: rv.positive.join(', ') }))}</div>` : ''}
          ${rv.open_objections && rv.open_objections.length ? `<div class="why">${esc(T('dr.objections', { list: rv.open_objections.join(', ') }))}</div>` : ''}</section>
        <section><h4>${esc(T('dr.written'))}</h4><div class="kv"><span class="k">${esc(T('dr.by'))}</span><span>${esc(n.by)}</span><span class="k">${esc(T('dr.at'))}</span><span class="mono">${esc(String(n.at || '').replace('T', ' ').slice(0, 19))}</span>
          ${det && det.versions && det.versions.length > 1 ? `<span class="k">${esc(T('dr.versions'))}</span><span>${det.versions.map((v) => `v${v.v}${v.reason ? ' (' + esc(v.reason) + ')' : ''}`).join(' · ')}</span>` : ''}</div></section>
        ${fields.length ? `<section><h4>${esc(T('dr.fields'))}</h4><div class="kv">${fields.map(([k, v]) => `<span class="k">${esc(k)}</span><span style="overflow-wrap:anywhere">${esc(typeof v === 'object' ? JSON.stringify(v) : v).slice(0, 600)}</span>`).join('')}</div></section>` : ''}
        <section><h4>${esc(T('dr.rests_on'))}</h4>${det ? (det.out || []).map((e) => nodeLink(e.dst, e.rel)).join('') || `<div class="dim">${esc(T('dr.nothing'))}</div>` : '<div class="dim">…</div>'}</section>
        <section><h4>${esc(T('dr.rests_on_it'))}</h4>${det ? (det.in || []).map((e) => nodeLink(e.src, e.rel)).join('') || `<div class="dim">${esc(T('dr.nothing'))}</div>` : '<div class="dim">…</div>'}</section>
        ${why && why.nodes && why.nodes.length > 1 ? `<section><h4>${esc(T('dr.provenance'))} <span class="dim">${esc(T('dr.provenance.sub'))}</span></h4>${why.nodes.filter((x) => x.id !== n.id).slice(0, 40).map((x) => nodeLink(x.id)).join('')}</section>` : ''}
        ${imp && imp.dependents && imp.dependents.length ? `<section><h4>${esc(T('dr.if_fell'))} <span class="dim">${esc(T('dr.if_fell.sub'))}</span></h4>${imp.dependents.slice(0, 40).map((x) => nodeLink(x.node.id, x.rel)).join('')}</section>` : ''}`;
      };
      const title = `<span class="code">${esc(n.code)}</span><span class="pill neutral">${esc(TL(n.type))}</span>`;
      drawer(title, esc(n.title), skeleton(null));
      const [det, why, imp] = await Promise.all([settle(src.node(n.id)), settle(src.why(n.id)), settle(src.impact(n.id))]);
      if (S.drawer && S.drawer.node === n.id) drawer(title, esc(n.title), skeleton(det, why, imp));
    }
    function openQuestion(code) {
      const m = S.m, sq = (m.stages || []).find((x) => x.code === code), q = (m.board || []).find((x) => x.code === code) || {};
      const qn = m.byCode.get(code);
      S.drawer = { q: code }; syncHash();
      const orders = (m.orders || []).filter((o) => o.target === code);
      drawer(`<span class="code">${esc(code)}</span><span class="pill neutral">${esc(TL('question'))}</span>`, esc(q.text || (qn && qn.title) || ''), `
        ${sq && sq.workflow !== false ? `<section><h4>${esc(T('col.stage'))}</h4>${stageBar(sq)}<div style="margin-top:6px"><b>${esc(sq.stage)}</b> · ${esc(T('stage.of', { i: sq.index, of: sq.of }))}
          ${sq.complete ? ` <span class="pill ok">${esc(T('dr.complete'))}</span>` : ''}${sq.settled_by ? ` <span class="pill info">${esc(T('dr.settled_by', { who: sq.settled_by }))}</span>` : ''}${sq.next ? `<div class="dim">${esc(T('dr.next', { x: sq.next }))}</div>` : ''}</div></section>
        <section><h4>${esc(T('dr.gates'))}</h4>${(sq.gates || []).map((g) => `<div class="gate" style="margin-bottom:9px"><span class="m ${g.met ? 'met' : 'no'}" aria-hidden="true">${g.met ? '✓' : ''}</span>
          <div><b>${esc(g.stage)}</b> <span class="mono dim">${esc(g.gate)}</span>${g.optional ? ` <span class="pill neutral">${esc(T('optional'))}</span>` : ''} <span class="sr">${esc(T(g.met ? 'gate.met' : 'gate.not_met'))}</span>
          <div class="dim">${g.met ? T('dr.met_by', { list: (g.evidence || []).map(esc).join(', ') }) : esc(g.why)}${g.who ? ' · ' + esc(g.who) : ''}</div></div></div>`).join('')}</section>` : ''}
        <section><h4>${esc(T('dr.answered'))}</h4>${(q.answers || []).map((c) => { const n = m.byCode.get(c);
          return `<div style="margin-bottom:8px"><button type="button" class="btn" data-n="${esc(n ? n.id : c)}" style="padding:1px 8px">${esc(c)}</button> ${standingPill(n, T)}<div style="margin-top:3px">${esc((n || {}).title || '')}</div></div>`; }).join('') || `<div class="dim">${esc(T('dr.no_answer'))}</div>`}</section>
        ${orders.length ? `<section><h4>${esc(T('view.orders'))}</h4>${orders.map((o) => `<div class="link"><span class="code">${esc(o.code)}</span><span class="pill neutral">${esc(T.word('os.', o.status))}</span><span class="dim">${esc(o.assignee)}</span></div>`).join('')}</section>` : ''}`);
    }

    // ── palette ──
    function palItems(q) {
      const m = S.m, x = q.trim().toLowerCase(), items = [];
      VIEWS.forEach(([k], i) => items.push({ label: T('view.' + k), kind: T('pal.view', { n: i + 1 }), run: () => setView(k) }));
      S.invs.forEach((i) => items.push({ label: `${i.code} · ${i.title}`, kind: S.profiles.get(i.id) || T('pal.investigation'), run: () => select(i.id) }));
      if (m) m.nodes.filter((n) => n.type !== 'review').forEach((n) => items.push({ label: `${n.code} · ${n.title || ''}`, kind: TL(n.type), run: () => openNode(n.id) }));
      return (x ? items.filter((it) => it.label.toLowerCase().includes(x) || it.kind.toLowerCase().includes(x)) : items).slice(0, 60);
    }
    function palOpen() { $('#hg-pal').classList.add('open'); const i = $('#hg-pal-q'); i.value = ''; S.palIdx = 0; palDraw(); i.focus(); }
    function palClose() { $('#hg-pal').classList.remove('open'); }
    function palDraw() {
      const its = palItems($('#hg-pal-q').value);
      S.palIdx = Math.max(0, Math.min(S.palIdx, its.length - 1));
      $('#hg-pal-list').innerHTML = its.map((it, i) => `<li role="option" data-pi="${i}" aria-selected="${i === S.palIdx}"><span>${esc(it.label)}</span><span class="k">${esc(it.kind)}</span></li>`).join('') || `<li class="dim">${esc(T('pal.none'))}</li>`;
      S.palCurrent = its;
    }

    // ── render ──
    const V = { overview: vOverview, live: vLive, pipeline: vPipeline, graph: vGraph, evidence: vEvidence, orders: vOrders, audit: vAudit, report: vReport };
    function render() {
      if (!S.m) return;
      try {
        status(); nav();
        const main = $('#hg-main'), y = main.scrollTop;
        const v = S.m.verify;               // a record that doesn't verify is shown as it arrived, and says so
        main.innerHTML = (v && !v.ok ? `<div class="note warn" role="alert">${esc(T('noverify.banner', { problem: v.problem || '' }))}</div>` : '') + V[S.view]();
        if (S.view === 'live') main.scrollTop = y;
        root.dataset.hgView = S.view; root.dataset.hgReady = '1';
        if (S.cy) { try { S.cy.destroy(); } catch { /* gone */ } S.cy = null; }
        // the scheduler's own decisions (accepting work orders) are work-order bookkeeping: shown with the work orders
        if (S.view === 'graph') S.cy = graphInto($('#hg-graph'), S.m.nodes.filter((n) => S.graphTypes.has(n.type) && (S.graphTypes.has('task') || !isBookkeeping(n))), S.m.edges);
        if (S.view === 'live') {
          const made = new Set(S.m.events.slice(0, S.cursor == null ? S.m.events.length : S.cursor).filter((e) => e.kind === 'create').map((e) => e.ref));
          S.cy = graphInto($('#hg-live-graph'), S.m.nodes.filter((n) => made.has(n.id) && n.type !== 'task' && !isBookkeeping(n)).slice(0, 400), S.m.edges);
        }
        syncHash();
      } catch (e) { fail(e); throw e; }
    }
    function setView(v) { if (!V[v]) return; if (v !== 'live') stopPlay(); S.view = v; render(); $('#hg-main').focus({ preventScroll: true }); }
    async function select(inv) { if (inv === S.inv) return; closeDrawer(); await openInv(inv); }
    function syncHash() {
      if (!opts.hash || !S.m) return;
      const p = new URLSearchParams({ view: S.view, inv: S.m.code !== 'INV' && S.invs.length > 1 ? S.inv : '' });
      if (!p.get('inv')) p.delete('inv');
      if (S.drawer && S.drawer.q) p.set('q', S.drawer.q);
      if (S.drawer && S.drawer.node) p.set('node', S.m.codeOf(S.drawer.node));
      if (S.view === 'live' && S.cursor != null) p.set('at', S.cursor);
      const h = '#' + p.toString();
      if (location.hash !== h) history.replaceState(null, '', h);
    }
    function setTheme(t) { root.dataset.theme = t; if (S.m) render(); }

    // ── events (delegated) ──
    root.addEventListener('click', (ev) => {
      const t = ev.target.closest('[data-v],[data-inv],[data-q],[data-n],[data-act],[data-sort],[data-evtype],[data-gtype],[data-pi]');
      if (!t || !root.contains(t)) { if (ev.target.id === 'hg-pal') palClose(); return; }
      if (t.dataset.v) return setView(t.dataset.v);
      if (t.dataset.inv) return select(t.dataset.inv);
      if (t.dataset.q) return openQuestion(t.dataset.q);
      if (t.dataset.n) return openNode(t.dataset.n);
      if (t.dataset.pi != null) { const it = S.palCurrent[+t.dataset.pi]; palClose(); if (it) it.run(); return; }
      if (t.dataset.sort) { S.sort = { k: t.dataset.sort, asc: S.sort.k === t.dataset.sort ? !S.sort.asc : true }; return render(); }
      if (t.dataset.evtype) { const x = t.dataset.evtype; S.ev.types.has(x) ? S.ev.types.delete(x) : S.ev.types.add(x); return render(); }
      if (t.dataset.gtype) { const x = t.dataset.gtype; S.graphTypes.has(x) ? S.graphTypes.delete(x) : S.graphTypes.add(x); return render(); }
      const a = t.dataset.act, m = S.m, slug = (m.code || 'inv').toLowerCase();
      if (a === 'close') return closeDrawer();
      if (a === 'lv-play') return S.playing ? (stopPlay(), render()) : play();
      if (a === 'lv-start') { stopPlay(); S.cursor = 0; return render(); }
      if (a === 'lv-live') { stopPlay(); S.cursor = null; return render(); }
      if (a === 'lv-trace') { S.traceOrder = t.dataset.order || ''; render(); const el = $('#hg-trace-order'); if (el) el.scrollIntoView({ block: 'center', behavior: 'smooth' }); return; }
      if (a === 'print') return global.print();
      if (a === 'md') return download(`${slug}-report.md`, (m.report && m.report.markdown) || '', 'text/markdown');
      if (a === 'bundle') return download(`${slug}.bundle.json`, JSON.stringify(src.bundle), 'application/json');
      if (a === 'json') return download(`${slug}-graph.json`, JSON.stringify({ nodes: m.nodes, edges: m.edges }, null, 1), 'application/json');
      if (a === 'png' && S.cy) { const u = S.cy.png({ full: true, scale: 2, bg: getComputedStyle(root).getPropertyValue('--surface') }); const l = document.createElement('a'); l.href = u; l.download = `${slug}-graph.png`; l.click(); return; }
      if (a === 'csv-evidence') return download(`${slug}-evidence.csv`, csv([['code', 'type', 'statement', 'author', 'standing'], ...evidenceRows().map((n) => [n.code, TL(n.type), n.title, n.by, standingKey(n)])]), 'text/csv');
      if (a === 'csv-orders') return download(`${slug}-work-orders.csv`, csv([['code', 'status', 'assignee', 'target', 'issued', 'objective'], ...(m.orders || []).map((o) => [o.code, o.status, o.assignee, o.target, o.issued, o.objective])]), 'text/csv');
      if (a === 'csv-audit') return download(`${slug}-audit.csv`, csv([['seq', 'at', 'actor', 'kind', 'ref', 'what'], ...auditRows().map((e) => [e.seq, e.at, e.actor, e.kind, m.codeOf(e.ref), say(e, true)])]), 'text/csv');
    });
    root.addEventListener('input', (ev) => {
      const id = ev.target.id;
      if (id === 'hg-ev-q') { S.ev.q = ev.target.value; const pos = ev.target.selectionStart; render(); const i = $('#hg-ev-q'); if (i) { i.focus(); i.setSelectionRange(pos, pos); } }
      if (id === 'hg-lv-scrub') { stopPlay(); const v = +ev.target.value; S.cursor = v >= S.m.events.length ? null : v; render(); }
      if (id === 'hg-pal-q') { S.palIdx = 0; palDraw(); }
    });
    root.addEventListener('change', (ev) => {
      const id = ev.target.id;
      if (id === 'hg-ev-st') { S.ev.standing = ev.target.value; render(); }
      if (id === 'hg-au-actor') { S.audit.actor = ev.target.value; render(); }
      if (id === 'hg-au-kind') { S.audit.kind = ev.target.value; render(); }
      if (id === 'hg-lv-speed') { S.speed = +ev.target.value; if (S.playing) play(); }
      if (id === 'hg-lv-feed') { S.feed = ev.target.value; render(); }
      if (id === 'hg-trace-order') { S.traceOrder = ev.target.value; render(); }
      if (id === 'hg-lang') setLang(ev.target.value, true);
    });
    const typing = (el) => el && (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA' || el.isContentEditable);
    root.addEventListener('keydown', (ev) => {
      const palOpenNow = $('#hg-pal').classList.contains('open');
      if (palOpenNow) {
        if (ev.key === 'Escape') { ev.preventDefault(); return palClose(); }
        if (ev.key === 'ArrowDown') { ev.preventDefault(); S.palIdx++; return palDraw(); }
        if (ev.key === 'ArrowUp') { ev.preventDefault(); S.palIdx = Math.max(0, S.palIdx - 1); return palDraw(); }
        if (ev.key === 'Enter') { ev.preventDefault(); const it = (S.palCurrent || [])[S.palIdx]; palClose(); if (it) it.run(); return; }
        return;
      }
      if ((ev.key === 'k' || ev.key === 'K') && (ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); return palOpen(); }
      if (ev.key === 'Escape') return closeDrawer();
      if ((ev.key === 'Enter' || ev.key === ' ') && ev.target.matches && ev.target.matches('tr.click, .lane.click')) { ev.preventDefault(); return ev.target.click(); }
      if (typing(ev.target) || ev.metaKey || ev.ctrlKey || ev.altKey) return;
      if (ev.key === '/') { ev.preventDefault(); return palOpen(); }
      if (/^[1-8]$/.test(ev.key)) return setView(VIEWS[+ev.key - 1][0]);
      if (ev.key === 't') { const t = root.dataset.theme === 'dark' ? 'light' : 'dark'; setTheme(t); if (opts.onTheme) opts.onTheme(t); }
    });
    $('#hg-search').addEventListener('click', palOpen);
    $('#hg-theme').addEventListener('click', () => { const t = root.dataset.theme === 'dark' ? 'light' : 'dark'; setTheme(t); if (opts.onTheme) opts.onTheme(t); });
    if (!root.hasAttribute('tabindex')) root.tabIndex = -1;

    if (live) setInterval(async () => {                    // investigations a swarm starts later appear in the nav
      if (!S.m || document.hidden) return;
      const before = S.invs.length;
      try { await loadInvestigations(); } catch { return; }
      if (S.invs.length !== before) nav();
    }, 10000);
    setInterval(() => {                                    // in-flight calls show their elapsed time while live
      if (S.view === 'live' && S.cursor == null && S.m && S.m.tel.length && openSpans(S.m.tel).length && !document.hidden) render();
    }, 1000);

    // ── start ──
    const fromHash = () => (opts.hash ? new URLSearchParams(location.hash.slice(1)) : new URLSearchParams());
    const ready = (async () => {
      try {
        await Promise.all([setLang(wantLang), loadInvestigations()]);
        if (!S.invs.length) {
          $('#hg-main').innerHTML = `<div class="empty">${esc(T('empty.none'))}${live ? esc(T('empty.live')) : T('empty.demo')}</div>`;
          root.dataset.hgReady = '1';
          if (!live) return;
          await new Promise((resolve) => {                 // a swarm started after the page: open it when it begins
            const t = setInterval(async () => {
              try { await loadInvestigations(); } catch { return; }
              if (S.invs.length) { clearInterval(t); resolve(); }
            }, 3000);
          });
        }
        const h = fromHash();
        const want = h.get('inv'), pick = S.invs.find((i) => i.id === want || i.code === want || S.profiles.get(i.id) === want) || S.invs[0];
        if (h.get('view') && V[h.get('view')]) S.view = h.get('view');
        await openInv(pick.id);
        if (h.get('at') && S.view === 'live') { S.cursor = Math.min(+h.get('at'), S.m.events.length); render(); }
        else if (opts.play || h.get('play')) replayFromStart();
        if (h.get('q')) openQuestion(h.get('q'));
        else if (h.get('node')) openNode(h.get('node'));
      } catch (e) {
        fail(e);
        $('#hg-main').innerHTML = `<div class="empty">${esc(T('err.read', { msg: e.message }))}</div>`;
      }
    })();
    if (opts.hash && global.addEventListener) {          // a link, Back or Forward changes the fragment: follow it
      global.addEventListener('hashchange', async () => {
        if (!S.m) return;
        const h = fromHash(), want = h.get('inv');
        const pick = want && S.invs.find((i) => i.id === want || i.code === want || S.profiles.get(i.id) === want);
        if (pick && pick.id !== S.inv) await openInv(pick.id);
        if (h.get('view') && V[h.get('view')] && h.get('view') !== S.view) setView(h.get('view'));
        if (h.get('at') && S.view === 'live') { stopPlay(); S.cursor = Math.min(+h.get('at'), S.m.events.length); render(); }
        else if (h.get('play')) replayFromStart();
        if (h.get('q')) openQuestion(h.get('q'));
        else if (h.get('node')) openNode(h.get('node'));
      });
    }
    global.addEventListener && global.addEventListener('error', (e) => { if (e && e.filename && /hypgraph\.js/.test(e.filename)) fail(e.message); });
    return { ready, state: S, setView, setTheme, setLang, lang: () => T.lang, select, show: openNode, focus: openNode, question: openQuestion, source: src,
      destroy: () => { if (S.follow) S.follow(); stopPlay(); if (S.cy) S.cy.destroy(); root.innerHTML = ''; } };
  }

  const API = { mount, HttpSource, BundleSource, verifyBundle, anchored, sha256, version: VERSION, TYPE_COLOR,
    languages: { ...LANGS }, pickLang, matchLang, addStrings };
  global.HypGraph = API;
  global.HypAtlas = global.HypAtlas || API;        // the Atlas's name, kept for one release
})(typeof window !== 'undefined' ? window : globalThis);
