/**
 * HypGraph Atlas — the research graph explorer. Framework-free, read-only, offline-first.
 *
 *   <link rel="stylesheet" href="atlas.css">
 *   <script src="vendor/cytoscape.min.js"></script>  (+ layout-base, cose-base, cytoscape-fcose for the fcose layout)
 *   <script src="atlas.js"></script>
 *   <div id="atlas"></div>
 *   <script>
 *     HypAtlas.mount(document.getElementById('atlas'), { source: HypAtlas.HttpSource('/api/graph') });
 *     // or, with no server at all:  { source: HypAtlas.BundleSource(bundleJson) }
 *   </script>
 *
 * Views: graph (Cytoscape + fcose) · hypotheses (competing explanations × experiments) · claims (every standing
 * dimension, sortable) · provenance (claim → results → runs → exact files; dependence groups) · work (who is on what,
 * queues, duplicates) · timeline (events per day, replay, feed). Nothing here writes. Standing comes from the engine
 * (Python) — a BundleSource shows the standing the bundle was exported with, and re-verifies its hash chain itself.
 *
 * Options: source (required) · operatorUrl (link for actions that live elsewhere) · fileUrl(path) (opens an artifact)
 * · live (poll for new events; default true for HttpSource) · title (brand line) · theme ('dark' | 'light').
 */
'use strict';
(function (global) {
  const VERSION = '0.1.0';
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // ── vocabulary ────────────────────────────────────────────────────
  const TYPES = {
    investigation: { color: '#ffb547', shape: 'star', label: 'Investigation', size: 46 },
    question: { color: '#2fe6d6', shape: 'diamond', label: 'Question', size: 30 },
    hypothesis: { color: '#b18cff', shape: 'hexagon', label: 'Hypothesis', size: 30 },
    claim: { color: '#4ee08a', shape: 'round-rectangle', label: 'Claim', size: 24 },
    experiment: { color: '#ff7ab6', shape: 'round-triangle', label: 'Experiment', size: 28 },
    run: { color: '#4aa8ff', shape: 'barrel', label: 'Run', size: 18 },
    result: { color: '#8ee6ff', shape: 'ellipse', label: 'Result', size: 20 },
    artifact: { color: '#94a3b8', shape: 'rectangle', label: 'Artifact', size: 14 },
    source: { color: '#ffd166', shape: 'tag', label: 'Source', size: 20 },
    review: { color: '#cbd5e1', shape: 'ellipse', label: 'Review', size: 9 },
    decision: { color: '#ff9f43', shape: 'octagon', label: 'Decision', size: 28 },
    task: { color: '#7fb88f', shape: 'vee', label: 'Task', size: 18 },
  };
  const EDGES = {
    supports: { color: '#22c55e', style: 'solid', arrow: 'triangle', label: 'supports' },
    challenges: { color: '#ff4d5e', style: 'solid', arrow: 'tee', label: 'challenges' },
    requires: { color: '#ffb547', style: 'dotted', arrow: 'triangle', label: 'requires (rests on)' },
    derived_from: { color: '#7c8ea3', style: 'solid', arrow: 'triangle', label: 'derived from' },
    produced: { color: '#4aa8ff', style: 'solid', arrow: 'triangle', label: 'produced' },
    uses: { color: '#4aa8ff', style: 'dashed', arrow: 'triangle', label: 'uses (data / code)' },
    tests: { color: '#b18cff', style: 'solid', arrow: 'triangle', label: 'tests' },
    executes: { color: '#ff7ab6', style: 'dashed', arrow: 'triangle', label: 'executes' },
    replicates: { color: '#2fe6d6', style: 'solid', arrow: 'triangle-tee', label: 'replicates' },
    supersedes: { color: '#94a3b8', style: 'dashed', arrow: 'triangle', label: 'supersedes / corrects' },
    corrects: { color: '#94a3b8', style: 'dashed', arrow: 'triangle', label: null },
    reviews: { color: '#cbd5e1', style: 'dotted', arrow: 'circle', label: 'reviews' },
    based_on: { color: '#ff9f43', style: 'dotted', arrow: 'triangle', label: 'based on (decision)' },
    other: { color: '#56657a', style: 'solid', arrow: 'triangle', label: 'other' },
  };
  const STANDING = [
    ['checked', 'checked'], ['unchecked', 'unchecked'], ['needs_revalidation', 'review stale'],
    ['contested', 'contested'], ['at_risk', 'at risk'], ['withdrawn', 'withdrawn'], ['superseded', 'superseded'],
  ];
  const RISKY = ['requires', 'derived_from', 'based_on'];

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
  async function verifyBundle(b) {
    if (!b || b.format !== 'hypgraph/1-bundle') return { ok: false, problem: 'not a hypgraph/1-bundle' };
    let prev = '0'.repeat(64), checked = 0, red = 0;
    const creates = new Map(), revs = new Map(), reviews = new Map(), links = new Map(), withdraws = new Set(), retracts = new Set();
    for (const ev of [...(b.events || [])].sort((x, y) => x.seq - y.seq)) {
      if (ev.redacted) {
        if (ev.prev !== prev) return { ok: false, broken_at: ev.seq, problem: 'chain broken (redacted event)' };
        prev = ev.hash; red += 1; continue;
      }
      if (await sha256(ev.body) !== ev.hash) return { ok: false, broken_at: ev.seq, problem: 'event body does not match its hash' };
      const body = JSON.parse(ev.body);
      if (body.prev !== prev) return { ok: false, broken_at: ev.seq, problem: 'chain broken (prev does not match)' };
      prev = ev.hash; checked += 1;
      const p = body.payload || {};
      if (body.kind === 'create') { creates.set(body.ref, p); revs.set(`${body.ref}#${p.v || 1}`, p.body_sha); }
      else if (body.kind === 'revise') revs.set(`${body.ref}#${p.v}`, p.body_sha);
      else if (body.kind === 'review') { reviews.set(p.review, p); revs.set(`${p.review}#1`, p.body_sha); }
      else if (body.kind === 'link') links.set(Number(p.edge), p);
      else if (body.kind === 'withdraw') withdraws.add(body.ref);
      else if (body.kind === 'retract') retracts.add(Number(p.edge));
    }
    if (b.head && b.head !== prev) return { ok: false, problem: "the chain does not end at the bundle's head" };
    for (const n of b.nodes || []) {
      const c = creates.get(n.id);
      if (n.type === 'review') { if (!reviews.has(n.id)) return { ok: false, problem: `review ${n.id} has no event` }; }
      else if (!c || c.type !== n.type || c.code !== n.code || c.inv !== n.inv) return { ok: false, problem: `node ${n.id} differs from its create event` };
    }
    for (const v of b.versions || []) {
      const want = revs.get(`${v.node}#${v.v}`);
      if (want === undefined) return { ok: false, problem: `version ${v.node} v${v.v} has no event` };
      if (await sha256(v.body) !== want) return { ok: false, problem: `version ${v.node} v${v.v} differs from its event` };
    }
    for (const e of b.edges || []) {
      const want = links.get(Number(e.id));
      if (!want) return { ok: false, problem: `edge ${e.id} has no event` };
      if (want.rel !== e.rel || want.dst !== e.dst || (want.dst_v ?? null) !== (e.dst_v ?? null) || await sha256(e.data) !== want.data_sha)
        return { ok: false, problem: `edge ${e.id} differs from its event` };
    }
    for (const w of b.withdrawals || []) if (!withdraws.has(w.node)) return { ok: false, problem: `withdrawal of ${w.node} has no event` };
    for (const r of b.retractions || []) if (!retracts.has(Number(r.edge))) return { ok: false, problem: `retraction of edge ${r.edge} has no event` };
    const out = { ok: true, checked, head: prev, complete: red === 0, redacted: red, nodes: (b.nodes || []).length, edges: (b.edges || []).length };
    if (red) out.warning = `${red} event(s) outside this investigation are redacted: their content can't be checked.`;
    return out;
  }

  // ── data sources ──────────────────────────────────────────────────
  /** Live: the JSON API of `hypgraph serve`, or any host that serves the same routes (PegasusDMZ's /api/graph). */
  function HttpSource(base = '/api/graph', fetchOpts = {}) {
    const get = async (path) => {
      const r = await fetch(base + path, fetchOpts);
      let body = null;
      try { body = await r.json(); } catch { /* not json */ }
      if (!r.ok) throw new Error((body && (body.detail?.error || body.detail || body.error)) || `HTTP ${r.status}`);
      return body;
    };
    const q = encodeURIComponent;
    return {
      kind: 'http', live: true,
      investigations: () => get('/investigations'),
      subgraph: (inv) => get(`/subgraph?inv=${q(inv)}`),
      node: (id) => get(`/node/${q(id)}?history=1`),
      why: (id) => get(`/why/${q(id)}`),
      impact: (id) => get(`/impact/${q(id)}`),
      events: (after, inv, limit) => get(`/events?after=${after || 0}&inv=${q(inv || '')}&limit=${limit || 500}`),
      next: (inv) => get(`/next?inv=${q(inv)}`),
      work: (inv) => get(`/work?inv=${q(inv)}`),
      cost: (inv) => get(`/cost?inv=${q(inv)}`),
      refusals: (inv) => get(`/refusals?inv=${q(inv)}`),
      verify: () => get('/verify'),
    };
  }

  /** Static: a hypgraph/1-bundle (from `hypgraph export`) — no server, no Python. */
  function BundleSource(bundle) {
    const d = bundle.derived || { by_inv: {}, investigations: [], stats: {} };
    const nodes = new Map(), edges = [];
    Object.values(d.by_inv || {}).forEach((v) => {
      v.subgraph.nodes.forEach((n) => nodes.set(n.id, n));
      v.subgraph.edges.forEach((e) => edges.push(e));
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
      return { center: id, dependents: dep.filter((x) => x.node), edges: edges.filter((e) => seen.has(e.src) && seen.has(e.dst)) };
    };
    let verified = null;
    return {
      kind: 'bundle', live: false, bundle,
      investigations: async () => ({ investigations: d.investigations || [], stats: d.stats || {} }),
      subgraph: async (inv) => d.by_inv[inv].subgraph,
      node: async (id) => {
        const n = nodes.get(id); if (!n) throw new Error(`no node ${id}`);
        const vs = versions.get(id) || [];
        return { ...n, body: vs.length ? vs[vs.length - 1].body : {}, versions: vs, out: out.get(id) || [], in: inn.get(id) || [],
          ...(withdrawn.has(id) ? { withdrawn: withdrawn.get(id) } : {}) };
      },
      why: async (id) => why(id),
      impact: async (id) => impact(id),
      events: async (after, inv) => ({ head, events: evs.filter((e) => e.seq > (after || 0) && (!inv || e.ref === inv || (nodes.get(e.ref) || {}).inv === inv)) }),
      next: async (inv) => d.by_inv[inv].next,
      work: async (inv) => d.by_inv[inv].work,
      cost: async () => null,
      refusals: async () => null,
      verify: async () => (verified = verified || await verifyBundle(bundle)),
    };
  }

  const MARKUP = (o) => `
  <header class="at-bar">
    <div class="at-brand">${esc(o.title || 'ATLAS')} <span>// research graph</span></div>
    <label class="at-inv-wrap" title="Investigation"><span class="at-k">INVESTIGATION</span>
      <select id="at-inv" aria-label="Investigation"></select></label>
    <nav class="at-tabs" role="tablist" aria-label="Views">
      <button role="tab" data-view="graph" class="on" title="Graph (1)">Graph</button>
      <button role="tab" data-view="hypotheses" title="Hypotheses (2)">Hypotheses</button>
      <button role="tab" data-view="claims" title="Claims (3)">Claims</button>
      <button role="tab" data-view="provenance" title="Provenance (4)">Provenance</button>
      <button role="tab" data-view="work" title="Work (5)">Work</button>
      <button role="tab" data-view="timeline" title="Timeline (6)">Timeline</button>
    </nav>
    <div class="at-search">
      <input id="at-q" type="search" placeholder="Search code or words  ( / )" autocomplete="off" aria-label="Search">
      <div class="at-results" id="at-results" hidden></div>
    </div>
    <div class="at-bar-right">
      <span class="at-chip" id="at-chain" title="Hash chain over every write">chain …</span>
      <span class="at-chip at-live" id="at-live" title="Live — polls the event log">LIVE</span>
      <button class="at-btn" id="at-theme" title="Light / dark" aria-label="Toggle theme">◐</button>
      <button class="at-btn" id="at-export" title="Export PNG + JSON" aria-label="Export">⇩</button>
    </div>
  </header>
  <div class="at-body">
    <aside class="at-rail" aria-label="Filters">
      <section class="at-sec"><h3>Node types</h3><div id="at-types" class="at-types"></div></section>
      <section class="at-sec"><h3>Standing</h3><div id="at-standing" class="at-checks"></div></section>
      <section class="at-sec"><h3>Show</h3>
        <label class="at-toggle"><input type="checkbox" id="at-show-reviews"> reviews</label>
        <label class="at-toggle"><input type="checkbox" id="at-show-withdrawn" checked> withdrawn</label>
        <label class="at-toggle"><input type="checkbox" id="at-show-labels" checked> labels</label></section>
      <section class="at-sec"><h3>Edges</h3><div id="at-edge-legend" class="at-legend"></div></section>
      <section class="at-sec"><h3>Ring = review</h3><div class="at-legend">
        <div><i class="ring checked"></i>checked</div><div><i class="ring unchecked"></i>unchecked</div>
        <div><i class="ring needs_revalidation"></i>review stale</div><div><i class="ring contested"></i>contested</div>
        <div><i class="ring at-risk"></i>at risk (glow)</div></div></section>
      <section class="at-sec at-stats" id="at-stats"></section>
    </aside>
    <main class="at-main">
      <section class="at-view on" data-view="graph">
        <div id="at-cy" class="at-cy" aria-label="Graph canvas"></div>
        <div class="at-hud">
          <select id="at-layout" aria-label="Layout"><option value="fcose">force (fcose)</option>
            <option value="breadthfirst">evidence tiers</option><option value="concentric">by degree</option>
            <option value="cose">force (cose)</option></select>
          <label class="at-k" for="at-depth">focus</label>
          <input type="range" id="at-depth" min="1" max="4" value="2" aria-label="Focus depth"><span id="at-depth-v">2</span>
          <button class="at-btn" id="at-fit">Fit</button>
          <button class="at-btn" id="at-why" disabled title="What it rests on (w)">Why</button>
          <button class="at-btn" id="at-impact" disabled title="What rests on it (i)">Impact</button>
          <button class="at-btn" id="at-clear" title="Clear focus (Esc)">Clear</button>
          <span class="at-hint" id="at-hint">click: inspect · double-click: focus · scroll: zoom</span>
        </div>
        <div class="at-tip" id="at-tip" hidden></div>
      </section>
      <section class="at-view" data-view="hypotheses"><div class="at-scroll" id="at-hyp"></div></section>
      <section class="at-view" data-view="claims">
        <div class="at-table-bar"><input id="at-claim-filter" type="search" placeholder="Filter claims…" aria-label="Filter claims">
          <span id="at-claim-count" class="at-k"></span></div>
        <div class="at-scroll"><table class="at-table" id="at-claims"></table></div>
      </section>
      <section class="at-view" data-view="provenance"><div class="at-scroll" id="at-prov"></div></section>
      <section class="at-view" data-view="work"><div class="at-scroll" id="at-work"></div></section>
      <section class="at-view" data-view="timeline">
        <div class="at-tl-top"><button class="at-btn" id="at-tl-play" aria-label="Replay">▶ Replay</button>
          <input type="range" id="at-tl-range" min="0" max="100" value="100" aria-label="Point in time"><span id="at-tl-at" class="at-k"></span></div>
        <svg id="at-tl-chart" class="at-tl-chart" role="img" aria-label="Events per day"></svg>
        <div class="at-scroll at-feed" id="at-tl-feed"></div>
      </section>
    </main>
    <aside class="at-insp" id="at-insp" aria-label="Inspector">
      <div class="at-empty">Select a node to inspect it — its standing, fields, links, versions and provenance.</div>
    </aside>
  </div>
  <div class="at-toast" id="at-toast" hidden></div>`;

  // ── the explorer ──────────────────────────────────────────────────
  function mount(root, opts) {
    opts = opts || {};
    const src = opts.source || HttpSource();
    const OPERATOR = opts.operatorUrl || '';
    root.classList.add('atlas');
    if (!root.dataset.theme) root.dataset.theme = opts.theme || 'dark';
    root.innerHTML = MARKUP(opts);
    const $ = (s) => root.querySelector(s);
    const $$ = (s) => [...root.querySelectorAll(s)];
    const live = opts.live ?? src.live;
    if (!live) $('#at-live').remove();

    const S = {
      inv: '', invs: [], data: { nodes: [], edges: [] }, by: new Map(), view: 'graph', cy: null, sel: null,
      types: new Set(Object.keys(TYPES).filter((t) => t !== 'review')), standing: new Set(STANDING.map((s) => s[0])),
      showReviews: false, showWithdrawn: true, labels: true, head: 0, events: [], until: null, sort: { k: 'code', asc: true },
      details: new Map(),
    };
    async function detail(id) {
      if (!S.details.has(id)) S.details.set(id, await src.node(id));
      return S.details.get(id);
    }
    function toast(msg, ms = 2600) {
      const t = $('#at-toast');
      t.textContent = msg; t.hidden = false;
      clearTimeout(toast._t); toast._t = setTimeout(() => { t.hidden = true; }, ms);
    }

    function standing(n) {
      const st = n.state || {};
      if (st.lifecycle === 'withdrawn') return 'withdrawn';
      if (st.lifecycle === 'superseded') return 'superseded';
      if (st.at_risk) return 'at_risk';
      return (st.review && st.review.state) || 'unchecked';
    }
    const reviewState = (n) => (n.state && n.state.review && n.state.review.state) || 'none';
    const code = (n) => n.code || n.id;
    const day = (iso) => (iso || '').slice(0, 10);
    const count = (i) => Object.values(i.counts || {}).reduce((a, x) => a + x, 0);

    // ── investigations ─────────────────────────────────────────
    async function loadInvestigations() {
      const r = await src.investigations();
      S.invs = r.investigations || [];
      const sel = $('#at-inv');
      sel.innerHTML = S.invs.map((i) => {
        const b = i.body || {};
        return `<option value="${esc(i.id)}">${esc(b.title || i.id)} · ${esc(b.state || 'active')} · ${count(i)}</option>`;
      }).join('') || '<option value="">(no investigations yet)</option>';
      const fromHash = new URLSearchParams(location.hash.slice(1));
      const want = opts.inv || fromHash.get('inv');
      const pick = S.invs.find((i) => i.id === want || i.code === want)
        || S.invs.filter((i) => (i.body || {}).state !== 'archived').sort((a, b) => count(b) - count(a))[0]
        || S.invs[0];
      if (pick) { sel.value = pick.id; await loadInv(pick.id, fromHash.get('node')); }
      const st = r.stats || {};
      $('#at-stats').innerHTML = `graph: ${st.nodes ?? '–'} nodes · ${st.edges ?? '–'} edges<br>events: ${st.seq ?? '–'} · leases: ${st.leases ?? 0}`;
    }

    async function loadInv(inv, focusNode) {
      S.inv = inv; S.details.clear(); S.sel = null;
      $('#at-insp').innerHTML = '<div class="at-empty">Loading…</div>';
      try { S.data = await src.subgraph(inv); } catch (e) {
        $('#at-insp').innerHTML = `<div class="at-empty">Couldn't load the graph: ${esc(e.message)}</div>`; return;
      }
      S.by = new Map(S.data.nodes.map((n) => [n.id, n]));
      S.head = Math.max(S.head, S.data.seq || 0);
      if (opts.hash !== false) history.replaceState(null, '', `#inv=${encodeURIComponent(inv)}`);
      renderRail(); S.events = []; render();
      showInspector(focusNode || inv);
      verifyChain();
    }

    async function verifyChain() {
      const chip = $('#at-chain');
      try {
        const v = await src.verify();
        chip.textContent = v.ok ? `chain ✓ ${v.checked}` : 'chain BROKEN';
        chip.className = 'at-chip ' + (v.ok ? 'ok' : 'bad');
        chip.title = v.ok ? `Hash chain verified over ${v.checked} events${src.kind === 'bundle' ? ' in your browser' : ''}; every version and edge matches its event.${v.warning ? ' ' + v.warning : ''}`
          : `Integrity check failed: ${v.problem || 'at event ' + v.broken_at}`;
      } catch (e) { chip.textContent = 'chain ?'; chip.title = e.message; }
    }

    // ── rail ──────────────────────────────────────────────────
    function renderRail() {
      const counts = {};
      S.data.nodes.forEach((n) => { counts[n.type] = (counts[n.type] || 0) + 1; });
      $('#at-types').innerHTML = Object.entries(TYPES).filter(([t]) => counts[t]).map(([t, v]) => `
        <label><input type="checkbox" data-type="${t}" ${S.types.has(t) ? 'checked' : ''}>
          <span class="sw" style="background:${v.color}"></span>${v.label}<span class="n">${counts[t]}</span></label>`).join('');
      const sc = {};
      S.data.nodes.forEach((n) => { const k = standing(n); sc[k] = (sc[k] || 0) + 1; });
      $('#at-standing').innerHTML = STANDING.map(([k, l]) => `
        <label><input type="checkbox" data-standing="${k}" ${S.standing.has(k) ? 'checked' : ''}>${l}<span class="n">${sc[k] || 0}</span></label>`).join('');
      $('#at-edge-legend').innerHTML = Object.values(EDGES).filter((e) => e.label).map((e) =>
        `<div><i class="ln ${e.style === 'dotted' ? 'dot' : e.style === 'dashed' ? 'dash' : ''}" style="border-color:${e.color}"></i>${e.label}</div>`).join('');
    }
    $('#at-types').addEventListener('change', (ev) => {
      const t = ev.target.dataset.type; if (!t) return;
      ev.target.checked ? S.types.add(t) : S.types.delete(t); render();
    });
    $('#at-standing').addEventListener('change', (ev) => {
      const k = ev.target.dataset.standing; if (!k) return;
      ev.target.checked ? S.standing.add(k) : S.standing.delete(k); render();
    });
    $('#at-show-reviews').addEventListener('change', (ev) => {
      S.showReviews = ev.target.checked;
      ev.target.checked ? S.types.add('review') : S.types.delete('review'); renderRail(); render();
    });
    $('#at-show-withdrawn').addEventListener('change', (ev) => {
      S.showWithdrawn = ev.target.checked;
      ev.target.checked ? S.standing.add('withdrawn') : S.standing.delete('withdrawn'); renderRail(); render();
    });
    $('#at-show-labels').addEventListener('change', (ev) => { S.labels = ev.target.checked; if (S.cy) S.cy.style(cyStyle()).update(); });

    function visible(n) {
      if (!S.types.has(n.type)) return false;
      const k = standing(n);
      // the standing filter governs evidence-bearing nodes, and anything withdrawn or superseded
      const governed = ['claim', 'result', 'hypothesis', 'experiment'].includes(n.type) || k === 'withdrawn' || k === 'superseded';
      if (governed && !S.standing.has(k)) return false;
      if (S.until && n.at > S.until) return false;
      return true;
    }

    // ── views ─────────────────────────────────────────────────
    function setView(v) {
      S.view = v;
      $$('.at-tabs button').forEach((b) => b.classList.toggle('on', b.dataset.view === v));
      $$('.at-view').forEach((s) => s.classList.toggle('on', s.dataset.view === v));
      // Back on the graph with nothing changed: keep the layout and only tell Cytoscape it is visible again.
      if (v === 'graph' && S.cy && S.cyStamp === graphStamp()) { S.cy.resize(); return; }
      render();
    }
    function graphStamp() {
      return JSON.stringify([S.inv, S.data.seq, S.data.nodes.length, [...S.types].sort(), [...S.standing].sort(),
        S.showReviews, S.showWithdrawn, S.labels, S.until, $('#at-layout').value]);
    }
    $('.at-tabs').addEventListener('click', (ev) => { const v = ev.target.dataset.view; if (v) setView(v); });

    function render() {
      if (S.view === 'graph') renderGraph();
      else if (S.view === 'hypotheses') renderHypotheses();
      else if (S.view === 'claims') renderClaims();
      else if (S.view === 'provenance') renderProvenance();
      else if (S.view === 'work') renderWork();
      else if (S.view === 'timeline') renderTimeline();
    }

    // ── graph ─────────────────────────────────────────────────
    function css(name, fallback) { return getComputedStyle(root).getPropertyValue(name).trim() || fallback; }
    function cyStyle() {
      const light = root.dataset.theme === 'light';
      const ink = css('--a-ink', light ? '#0d1321' : '#e6ecf5');
      const ink2 = css('--a-ink3', light ? '#8a96a8' : '#56657a');
      const good = css('--a-good', '#3ddc84'), warn = css('--a-warn', '#ffb547'), bad = css('--a-bad', '#ff4d5e');
      return [
        { selector: 'node', style: {
          'background-color': 'data(color)', shape: 'data(shape)', width: 'data(size)', height: 'data(size)',
          label: S.labels ? 'data(label)' : '', color: ink, 'font-family': css('--a-mono', 'ui-monospace, monospace'), 'font-size': 9,
          'text-valign': 'bottom', 'text-margin-y': 3, 'min-zoomed-font-size': 7, 'border-width': 0,
          'text-outline-color': css('--a-bg', light ? '#f7f8fb' : '#0a0d14'), 'text-outline-width': 2 } },
        { selector: 'node[review = "checked"]', style: { 'border-width': 3, 'border-color': good } },
        { selector: 'node[review = "unchecked"]', style: { 'border-width': 2, 'border-color': ink2, 'border-style': 'dashed' } },
        { selector: 'node[review = "needs_revalidation"]', style: { 'border-width': 3, 'border-color': warn, 'border-style': 'dashed' } },
        { selector: 'node[review = "contested"]', style: { 'border-width': 4, 'border-color': bad } },
        { selector: 'node.risk', style: { 'underlay-color': bad, 'underlay-opacity': 0.35, 'underlay-padding': 7, 'underlay-shape': 'ellipse' } },
        { selector: 'node.withdrawn', style: { opacity: 0.22 } },
        { selector: 'node.superseded', style: { opacity: 0.5 } },
        { selector: 'node.leased', style: { 'underlay-color': '#4aa8ff', 'underlay-opacity': 0.35, 'underlay-padding': 6 } },
        { selector: 'node.revisit', style: { 'underlay-color': warn, 'underlay-opacity': 0.4, 'underlay-padding': 7 } },
        { selector: 'edge', style: {
          width: 1.3, 'line-color': 'data(color)', 'target-arrow-color': 'data(color)', 'target-arrow-shape': 'data(arrow)',
          'line-style': 'data(lstyle)', 'curve-style': 'bezier', 'arrow-scale': 0.7, opacity: 0.75 } },
        { selector: 'node:selected', style: { 'overlay-color': css('--a-accent', '#7cf3ff'), 'overlay-opacity': 0.2, 'overlay-padding': 6 } },
        { selector: '.faded', style: { opacity: 0.07 } },
        { selector: 'edge.path', style: { width: 2.6, opacity: 1 } },
        { selector: 'node.path', style: { opacity: 1 } },
        { selector: 'node.hit', style: { 'overlay-color': warn, 'overlay-opacity': 0.3, 'overlay-padding': 8 } },
      ];
    }

    function elements() {
      const vis = new Set(S.data.nodes.filter(visible).map((n) => n.id));
      const nodes = S.data.nodes.filter((n) => vis.has(n.id)).map((n) => {
        const t = TYPES[n.type] || TYPES.task;
        const st = standing(n);
        const cls = [st === 'withdrawn' ? 'withdrawn' : '', st === 'superseded' ? 'superseded' : '',
          n.state && n.state.at_risk ? 'risk' : '', n.state && n.state.lease ? 'leased' : '',
          n.state && n.state.basis_changed ? 'revisit' : ''].filter(Boolean).join(' ');
        return { group: 'nodes', classes: cls, data: {
          id: n.id, label: code(n), color: t.color, shape: t.shape, review: reviewState(n),
          size: n.type === 'claim' && n.state ? t.size + Math.min(14, 3 * (n.state.independent_lines || 0)) : t.size } };
      });
      const edges = S.data.edges.filter((e) => vis.has(e.src) && vis.has(e.dst)).map((e) => {
        const v = EDGES[e.rel] || EDGES.other;
        return { group: 'edges', data: { id: 'e' + e.id, source: e.src, target: e.dst, rel: e.rel, color: v.color,
          arrow: v.arrow, lstyle: v.style } };
      });
      return nodes.concat(edges);
    }

    function layoutOpts(name, n) {
      const fcose = typeof global.cytoscapeFcose !== 'undefined';
      if (name === 'fcose' && !fcose) name = 'cose';
      if (name === 'fcose') return { name, quality: n > 700 ? 'draft' : 'default', randomize: true, animate: false,
        nodeRepulsion: 7000, idealEdgeLength: 55, gravity: 0.3, nodeSeparation: 60, packComponents: true };
      if (name === 'cose') return { name, animate: false, nodeRepulsion: 9000, idealEdgeLength: 60 };
      if (name === 'breadthfirst') return { name, directed: true, spacingFactor: 0.9, animate: false,
        roots: S.cy.nodes().filter((x) => x.indegree(false) === 0 && x.outdegree(false) > 0) };
      return { name: 'concentric', concentric: (x) => x.degree(), levelWidth: () => 3, animate: false, minNodeSpacing: 8 };
    }

    let pendingFocus = null;
    function renderGraph() {
      if (typeof global.cytoscape === 'undefined') {
        $('#at-cy').innerHTML = '<div class="at-empty" style="padding:20px">Cytoscape is not loaded.</div>'; return;
      }
      if (typeof global.cytoscapeFcose !== 'undefined' && !mount._fcose) { global.cytoscape.use(global.cytoscapeFcose); mount._fcose = true; }
      const els = elements();
      if (!S.cy) {
        S.cy = global.cytoscape({ container: $('#at-cy'), elements: els, style: cyStyle(), wheelSensitivity: 0.25,
          minZoom: 0.05, maxZoom: 4, boxSelectionEnabled: false });
        wireCy();
      } else {
        S.cy.elements().remove(); S.cy.add(els); S.cy.style(cyStyle());
      }
      S.cy.layout(layoutOpts($('#at-layout').value, els.length)).run();
      S.cyStamp = graphStamp();
      if (pendingFocus) { focusOn(pendingFocus); pendingFocus = null; }
      else if (S.sel && S.cy.getElementById(S.sel).length) S.cy.getElementById(S.sel).select();
    }

    function wireCy() {
      const tip = $('#at-tip');
      S.cy.on('tap', 'node', (ev) => showInspector(ev.target.id()));
      S.cy.on('dbltap', 'node', (ev) => focusOn(ev.target.id()));
      S.cy.on('tap', (ev) => { if (ev.target === S.cy) clearFocus(); });
      S.cy.on('mouseover', 'node', (ev) => {
        const n = S.by.get(ev.target.id()); if (!n) return;
        tip.innerHTML = `<b>${esc(code(n))}</b> ${esc(TYPES[n.type]?.label || n.type)}<div>${esc(n.title)}</div>
          <div class="st">${esc((n.state || {}).sentence || '')}</div>`;
        tip.hidden = false;
        const p = ev.renderedPosition; tip.style.left = (p.x + 16) + 'px'; tip.style.top = (p.y + 10) + 'px';
      });
      S.cy.on('mouseout', 'node', () => { tip.hidden = true; });
      S.cy.on('mouseover', 'edge', (ev) => {
        const d = ev.target.data(); const e = S.data.edges.find((x) => 'e' + x.id === d.id);
        tip.innerHTML = `<b>${esc(d.rel)}</b>${e && e.why ? `<div>${esc(e.why)}</div>` : ''}${e ? `<div class="st">by ${esc(e.by)} · ${esc(day(e.at))}</div>` : ''}`;
        tip.hidden = false; const p = ev.renderedPosition || { x: 0, y: 0 };
        tip.style.left = (p.x + 12) + 'px'; tip.style.top = (p.y + 8) + 'px';
      });
      S.cy.on('mouseout', 'edge', () => { tip.hidden = true; });
    }

    function highlight(ids, edgeIds) {
      if (!S.cy) return;
      S.cy.batch(() => {
        S.cy.elements().addClass('faded').removeClass('path');
        ids.forEach((id) => S.cy.getElementById(id).removeClass('faded').addClass('path'));
        (edgeIds || []).forEach((id) => S.cy.getElementById(id).removeClass('faded').addClass('path'));
        if (!edgeIds) S.cy.edges().filter((e) => ids.has(e.source().id()) && ids.has(e.target().id())).removeClass('faded').addClass('path');
      });
      const col = S.cy.collection([...ids].map((id) => S.cy.getElementById(id)).filter((x) => x.length));
      if (col.length) S.cy.animate({ fit: { eles: col, padding: 60 } }, { duration: 300 });
    }
    function clearFocus() { if (S.cy) S.cy.elements().removeClass('faded path hit'); }

    function focusOn(id) {
      if (!S.cy || !S.cy.getElementById(id).length) { pendingFocus = id; return; }
      const depth = +$('#at-depth').value;
      let col = S.cy.getElementById(id);
      for (let i = 0; i < depth; i++) col = col.union(col.neighborhood());
      highlight(new Set(col.nodes().map((x) => x.id())), null);
      S.cy.getElementById(id).select();
    }
    async function whyOrImpact(kind) {
      if (!S.sel) return;
      try {
        const r = await src[kind](S.sel);
        const ids = new Set([S.sel, ...(r.nodes || []).map((n) => n.id), ...(r.dependents || []).map((d) => d.node.id)]);
        if (S.view !== 'graph') setView('graph');
        highlight(ids, (r.edges || []).map((e) => 'e' + e.id));
        toast(kind === 'why' ? `${ids.size - 1} node(s) upstream — what it rests on` : `${ids.size - 1} node(s) rest on it`);
      } catch (e) { toast(e.message); }
    }
    $('#at-depth').addEventListener('input', (ev) => { $('#at-depth-v').textContent = ev.target.value; if (S.sel) focusOn(S.sel); });
    $('#at-fit').addEventListener('click', () => S.cy && S.cy.animate({ fit: { padding: 30 } }, { duration: 250 }));
    $('#at-why').addEventListener('click', () => whyOrImpact('why'));
    $('#at-impact').addEventListener('click', () => whyOrImpact('impact'));
    $('#at-clear').addEventListener('click', clearFocus);
    $('#at-layout').addEventListener('change', () => S.cy && S.cy.layout(layoutOpts($('#at-layout').value, S.cy.elements().length)).run());

    // ── inspector ─────────────────────────────────────────────
    function statClass(v) {
      return { checked: 'st-good', contested: 'st-bad', needs_revalidation: 'st-warn', unchecked: 'st-dim',
        withdrawn: 'st-dim', superseded: 'st-warn', active: 'st-good', published: 'st-good', archived: 'st-dim',
        succeeded: 'st-good', failed: 'st-bad' }[v] || '';
    }
    const nodeLink = (id) => {
      const n = S.by.get(id);
      return `<button class="at-link" data-node="${esc(id)}" title="${esc(n ? n.title : id)}">${esc(n ? code(n) : id)}</button>`;
    };

    async function showInspector(id) {
      if (!id) return;
      S.sel = id;
      ['#at-why', '#at-impact'].forEach((s) => { $(s).disabled = false; });
      const box = $('#at-insp');
      let d;
      try { d = await detail(id); } catch (e) { box.innerHTML = `<div class="at-empty">${esc(e.message)}</div>`; return; }
      if (S.sel !== id) return;
      const st = d.state || {};
      const t = TYPES[d.type] || TYPES.task;
      const dims = [];
      dims.push(['lifecycle', st.lifecycle]);
      if (st.review) dims.push(['review', st.review.state + (st.review.positive.length ? ' · ' + st.review.positive.join(', ') : '')
        + (st.review.open_objections.length ? ' · objection: ' + st.review.open_objections.map((o) => o.by).join(', ') : '')]);
      if (st.execution) dims.push(['execution', st.execution]);
      if (st.outcome) dims.push(['outcome', st.outcome]);
      if (st.evidence) dims.push(['evidence', st.evidence.replace(/_/g, ' ')]);
      if (st.independent_lines !== undefined) dims.push(['lines', String(st.independent_lines)]);
      if (st.basis_changed) dims.push(['revisit', st.basis_changed.map((b) => `${nodeLink(b.node)} v${b.was_v}→v${b.now_v}`).join(' ')]);
      if (st.at_risk) dims.push(['at risk', st.at_risk.map(nodeLink).join(' ')]);
      if (st.rests_on_superseded) dims.push(['older premise', st.rests_on_superseded.map(nodeLink).join(' ')]);
      if (st.lease) dims.push(['being worked', `${esc(st.lease.agent)} until ${esc(st.lease.expires.slice(0, 16).replace('T', ' '))}`]);
      const fields = Object.entries(d.body || {}).filter(([k]) => k !== 'legacy').map(([k, v]) => {
        const val = typeof v === 'string' ? esc(v) : `<pre>${esc(JSON.stringify(v, null, 1))}</pre>`;
        const href = k === 'path' && typeof v === 'string' && opts.fileUrl ? opts.fileUrl(v) : '';
        return `<div class="at-field"><span class="k">${esc(k)}</span>${val}${href ? ` <a class="at-link" target="_blank" rel="noopener" href="${esc(href)}">open</a>` : ''}</div>`;
      }).join('');
      const legacy = d.body && d.body.legacy ? `<div class="at-field"><span class="k">legacy record</span><pre>${esc(JSON.stringify(d.body.legacy, null, 1))}</pre></div>` : '';
      const group = (list, dir) => {
        const by = {};
        list.forEach((e) => { (by[e.rel] = by[e.rel] || []).push(e); });
        return Object.entries(by).map(([rel, es]) => `<div class="at-edge"><span class="rel">${dir === 'out' ? rel + ' →' : '← ' + rel}</span><span>${
          es.slice(0, 30).map((e) => nodeLink(dir === 'out' ? e.dst : e.src)).join(' · ')}${es.length > 30 ? ` +${es.length - 30}` : ''}</span></div>`).join('');
      };
      const versions = (d.versions || []).map((v, i, arr) => {
        const prev = i ? arr[i - 1].body : null;
        const changed = prev ? Object.keys({ ...prev, ...v.body }).filter((k) => JSON.stringify(prev[k]) !== JSON.stringify(v.body[k])) : [];
        return `<div class="at-ver">v${v.v} · ${esc(day(v.at))} · ${esc(v.by)} — ${esc(v.reason || 'created')}${
          changed.length ? ` <span class="ch">changed: ${esc(changed.join(', '))}</span>` : ''}</div>`;
      }).join('');
      box.innerHTML = `
        <div class="at-i-head"><span class="at-i-code">${esc(code(d))}</span>
          <span class="at-badge" style="color:${t.color};border-color:${t.color}">${esc(t.label.toUpperCase())}${d.kind ? ' · ' + esc(d.kind) : ''}</span>
          <span class="at-k">v${d.v} · ${esc(d.by)} · ${esc(day(d.at))}</span></div>
        <div class="at-i-title">${esc(d.title)}</div>
        <div class="at-sentence">${esc(st.sentence || '')}</div>
        <dl class="at-dims">${dims.map(([k, v]) => `<dt>${esc(k)}</dt><dd class="${statClass(String(v).split(' ')[0])}">${String(v).includes('<button') ? v : esc(v)}</dd>`).join('')}</dl>
        <div class="at-actions">
          <button class="at-btn" data-act="focus">Focus</button><button class="at-btn" data-act="why">Why</button>
          <button class="at-btn" data-act="impact">Impact</button><button class="at-btn" data-act="prov">Provenance</button>
          <button class="at-btn" data-act="copy" title="Copy the node id">Copy id</button>
          ${OPERATOR ? `<a class="at-btn" href="${esc(OPERATOR)}" target="_blank" rel="noopener" title="Actions on the record live with the operator">Operator ↗</a>` : ''}
        </div>
        ${d.withdrawn ? `<div class="at-sentence" style="border-color:var(--a-bad)">Withdrawn by ${esc(d.withdrawn.by)} ${esc(day(d.withdrawn.at))}: ${esc(d.withdrawn.why)}</div>` : ''}
        <div class="at-i-sec"><h4>Fields</h4>${fields || '<div class="st-dim">—</div>'}${legacy}</div>
        <div class="at-i-sec"><h4>Links out</h4>${group(d.out || [], 'out') || '<div class="st-dim">none</div>'}</div>
        <div class="at-i-sec"><h4>Links in</h4>${group(d.in || [], 'in') || '<div class="st-dim">none</div>'}</div>
        <div class="at-i-sec"><h4>Versions</h4>${versions || '<div class="st-dim">v1</div>'}</div>`;
      if (S.cy && S.cy.getElementById(id).length) { S.cy.$(':selected').unselect(); S.cy.getElementById(id).select(); }
      if (opts.hash !== false) history.replaceState(null, '', `#inv=${encodeURIComponent(S.inv)}&node=${encodeURIComponent(id)}`);
    }
    $('#at-insp').addEventListener('click', (ev) => {
      const n = ev.target.closest('[data-node]');
      if (n) { showInspector(n.dataset.node); if (S.view === 'graph') focusOn(n.dataset.node); return; }
      const a = ev.target.closest('[data-act]'); if (!a) return;
      const act = a.dataset.act;
      if (act === 'focus') { if (S.view !== 'graph') setView('graph'); focusOn(S.sel); }
      else if (act === 'why' || act === 'impact') whyOrImpact(act);
      else if (act === 'prov') { S.provFor = S.sel; setView('provenance'); }
      else if (act === 'copy') { navigator.clipboard?.writeText(S.sel).then(() => toast('Copied ' + S.sel)); }
    });
    root.addEventListener('click', (ev) => {
      const n = ev.target.closest('.at-view [data-node]');
      if (n) showInspector(n.dataset.node);
    });

    // ── hypotheses ────────────────────────────────────────────
    async function renderHypotheses() {
      const box = $('#at-hyp');
      const nodes = S.data.nodes;
      const hyps = nodes.filter((n) => n.type === 'hypothesis');
      const leads = nodes.filter((n) => n.type === 'claim' && n.kind === 'lead' && n.state.lifecycle === 'active');
      const exps = nodes.filter((n) => n.type === 'experiment');
      const qs = nodes.filter((n) => n.type === 'question');
      if (!hyps.length && !leads.length && !qs.length) {
        box.innerHTML = '<div class="at-empty">No hypotheses, questions or open leads in this investigation yet.</div>'; return;
      }
      box.innerHTML = '<div class="at-empty">Loading hypotheses…</div>';
      const det = await Promise.all(hyps.concat(exps).map((n) => detail(n.id).catch(() => null)));
      const D = new Map(det.filter(Boolean).map((x) => [x.id, x]));
      const card = (n) => {
        const d = D.get(n.id) || { body: {} };
        const preds = (d.body.predictions || []).map((p) => `<li>${esc(p)}</li>`).join('');
        return `<div class="at-card"><h5>${nodeLink(n.id)} ${esc(n.title)}</h5>
          <div class="meta ${statClass(standing(n))}">${esc(n.state.sentence)}</div>${preds ? `<ul>${preds}</ul>` : ''}</div>`;
      };
      let html = '';
      if (qs.length) html += `<div class="at-h2">Questions</div><div class="at-grid">${qs.map((q) =>
        `<div class="at-card"><h5>${nodeLink(q.id)} ${esc(q.title)}</h5><div class="meta">${esc(q.state.sentence)}</div></div>`).join('')}</div>`;
      if (hyps.length) html += `<div class="at-h2">Competing hypotheses (${hyps.length})</div><div class="at-grid">${hyps.map(card).join('')}</div>`;
      const tests = S.data.edges.filter((e) => e.rel === 'tests');
      if (exps.length && hyps.length) {
        const outcome = (x) => {
          const runs = S.data.edges.filter((e) => e.rel === 'executes' && e.dst === x).map((e) => e.src);
          const res = S.data.edges.filter((e) => e.rel === 'produced' && runs.includes(e.src)).map((e) => S.by.get(e.dst)).filter(Boolean);
          return res.length ? res.map((r) => `${code(r)}: ${r.state.outcome || '?'}`).join(', ') : (runs.length ? 'run, no result yet' : 'not run');
        };
        html += `<div class="at-h2">Experiments × hypotheses — expected outcome, then what happened</div>
          <div class="at-table-wrap"><table class="at-table at-matrix"><thead><tr><th>Experiment</th>${hyps.map((h) => `<th>${esc(code(h))}</th>`).join('')}<th>Result</th></tr></thead><tbody>${
          exps.map((x) => `<tr><td>${nodeLink(x.id)} ${esc(x.title.slice(0, 70))}</td>${hyps.map((h) => {
            const t = tests.find((e) => e.src === x.id && e.dst === h.id);
            return `<td class="cell">${t ? `<span class="exp">${esc(t.data.expected || '—')}</span>` : ''}</td>`;
          }).join('')}<td class="cell"><span class="act">${esc(outcome(x.id))}</span></td></tr>`).join('')}</tbody></table></div>`;
      }
      if (leads.length) html += `<div class="at-h2">Open leads (${leads.length}) — angles worth testing, not evidence</div><div class="at-grid">${
        leads.map((n) => `<div class="at-card"><h5>${nodeLink(n.id)} ${esc(n.title)}</h5><div class="meta">${esc(n.state.sentence)}</div></div>`).join('')}</div>`;
      box.innerHTML = html;
    }

    // ── claims ────────────────────────────────────────────────
    const CLAIM_COLS = [
      ['code', 'Code'], ['kind', 'Kind'], ['title', 'Statement'], ['lifecycle', 'Lifecycle'], ['review', 'Review'],
      ['evidence', 'Evidence'], ['lines', 'Lines'], ['risk', 'Risk'], ['by', 'By'], ['at', 'Date'],
    ];
    function claimRow(n) {
      const st = n.state || {};
      return { id: n.id, code: code(n), kind: n.kind || '', title: n.title, lifecycle: st.lifecycle, review: (st.review || {}).state || '',
        evidence: (st.evidence || '').replace(/_/g, ' '), lines: st.independent_lines ?? '', risk: st.at_risk ? 'AT RISK' : st.rests_on_superseded ? 'older premise' : '',
        by: n.by, at: day(n.at) };
    }
    function renderClaims() {
      const q = ($('#at-claim-filter').value || '').toLowerCase();
      const rows = S.data.nodes.filter((n) => n.type === 'claim').map(claimRow)
        .filter((r) => !q || Object.values(r).join(' ').toLowerCase().includes(q));
      const { k, asc } = S.sort;
      const cmp = (x, y) => (typeof x === 'number' && typeof y === 'number' ? x - y
        : String(x ?? '').localeCompare(String(y ?? ''), undefined, { numeric: true, sensitivity: 'base' }));   // C2 before C10
      rows.sort((a, b) => cmp(a[k], b[k]) * (asc ? 1 : -1));
      $('#at-claim-count').textContent = `${rows.length} claim(s)`;
      $('#at-claims').innerHTML = `<thead><tr>${CLAIM_COLS.map(([c, l]) => `<th data-k="${c}" class="${k === c ? 'sorted' + (asc ? ' asc' : '') : ''}">${l}</th>`).join('')}</tr></thead>
        <tbody>${rows.map((r) => `<tr data-node="${esc(r.id)}"><td class="code">${esc(r.code)}</td><td>${esc(r.kind)}</td><td>${esc(r.title)}</td>
          <td class="${statClass(r.lifecycle)}">${esc(r.lifecycle)}</td><td class="${statClass(r.review)}">${esc(r.review)}</td>
          <td>${esc(r.evidence)}</td><td class="num">${esc(r.lines)}</td><td class="${r.risk === 'AT RISK' ? 'st-bad' : 'st-warn'}">${esc(r.risk)}</td>
          <td>${esc(r.by)}</td><td>${esc(r.at)}</td></tr>`).join('')}</tbody>`;
    }
    $('#at-claims').addEventListener('click', (ev) => {
      const th = ev.target.closest('th');
      if (th) { const k = th.dataset.k; S.sort = { k, asc: S.sort.k === k ? !S.sort.asc : true }; renderClaims(); }
    });
    $('#at-claim-filter').addEventListener('input', () => renderClaims());

    // ── provenance ────────────────────────────────────────────
    async function renderProvenance() {
      const box = $('#at-prov');
      const id = S.provFor || S.sel;
      const n = id && S.by.get(id);
      if (!n || !['claim', 'result', 'run', 'hypothesis'].includes(n.type)) {
        box.innerHTML = '<div class="at-empty">Select a claim, result, run or hypothesis (Inspector → Provenance) to trace it to the runs and exact files behind it.</div>';
        return;
      }
      box.innerHTML = '<div class="at-empty">Tracing…</div>';
      let why;
      try { why = await src.why(id); } catch (e) { box.innerHTML = `<div class="at-empty">${esc(e.message)}</div>`; return; }
      const ids = why.nodes.map((x) => x.id);
      const det = new Map((await Promise.all(ids.map((x) => detail(x).catch(() => null)))).filter(Boolean).map((x) => [x.id, x]));
      const col = (type) => why.nodes.filter((x) => x.type === type && x.id !== id);
      const runCard = (r) => {
        const b = (det.get(r.id) || {}).body || {};
        const hashes = (list) => (list || []).slice(0, 8).map((f) => `<div class="at-hash">${esc(f.path || '')} ${f.sha256 ? esc(f.sha256.slice(0, 16)) + '…' : ''}</div>`).join('');
        return `<div class="at-card"><h5>${nodeLink(r.id)} ${esc(b.name || r.title)}</h5>
          <div class="meta ${statClass(b.state)}">${esc(b.kind || '')} · ${esc(b.state || '')} · exit ${esc(b.exit_code ?? '–')} · seed ${esc(b.seed ?? '–')}</div>
          ${b.code && b.code.length ? `<div class="at-k" style="margin-top:6px">code</div>${hashes(b.code)}` : ''}
          ${b.inputs && b.inputs.length ? `<div class="at-k">inputs</div>${hashes(b.inputs)}` : ''}
          ${b.outputs && b.outputs.length ? `<div class="at-k">outputs</div>${hashes(b.outputs)}` : ''}
          ${b.note ? `<div class="meta" style="margin-top:6px">${esc(b.note)}</div>` : ''}</div>`;
      };
      const simple = (x) => `<div class="at-card"><h5>${nodeLink(x.id)} ${esc(x.title.slice(0, 110))}</h5><div class="meta">${esc(x.state.sentence)}</div></div>`;
      const art = (x) => { const b = (det.get(x.id) || {}).body || {};
        return `<div class="at-card"><h5>${nodeLink(x.id)}</h5><div class="at-hash">${esc(b.path || '')}</div><div class="at-hash">sha256 ${esc(b.sha256 || '')}</div></div>`; };
      let groupsHtml = '';
      if (n.type === 'claim' || n.type === 'hypothesis') {
        const support = S.data.edges.filter((e) => e.rel === 'supports' && e.dst === id).map((e) => e.src);
        const rootsOf = (x, seen = new Set()) => {
          if (seen.has(x)) return new Set(); seen.add(x);
          const out = new Set();
          S.data.edges.forEach((e) => {
            if (e.dst === x && e.rel === 'produced') { out.add(e.src); rootsOf(e.src, seen).forEach((y) => out.add(y)); }
            if (e.src === x && (e.rel === 'uses' || e.rel === 'derived_from')) { out.add(e.dst); rootsOf(e.dst, seen).forEach((y) => out.add(y)); }
          });
          return out;
        };
        const groups = [];
        support.forEach((s) => {
          let r = rootsOf(s); if (!r.size) r = new Set(['(no provenance)']);
          const hit = groups.filter((g) => [...g.roots].some((x) => r.has(x)));
          const merged = { lines: [s], roots: r };
          hit.forEach((g) => { merged.lines.push(...g.lines); g.roots.forEach((x) => merged.roots.add(x)); groups.splice(groups.indexOf(g), 1); });
          groups.push(merged);
        });
        const colors = ['#4ee08a', '#4aa8ff', '#ffb547', '#b18cff', '#ff7ab6', '#2fe6d6'];
        groupsHtml = `<div class="at-h2">Independent lines of support: ${groups.length}</div>${groups.map((g, i) =>
          `<div class="at-group" style="border-color:${colors[i % colors.length]}"><div>${g.lines.map(nodeLink).join(' · ')}</div>
           <div class="at-k">share: ${[...g.roots].slice(0, 6).map((x) => x === '(no provenance)' ? 'no recorded run or data' : nodeLink(x)).join(' ')}</div></div>`).join('')
          || '<div class="st-dim">No support linked.</div>'}`;
      }
      if (n.type === 'run') {
        const made = S.data.edges.filter((e) => e.src === id && e.rel === 'produced').map((e) => S.by.get(e.dst)).filter(Boolean);
        await Promise.all([id, ...made.map((m) => m.id)].map((x) => detail(x).then((d) => det.set(x, d)).catch(() => null)));
        groupsHtml = `<div class="at-h2">What the run recorded</div>${runCard({ id, title: n.title })}
          <div class="at-h2">What it produced</div><div class="at-chain">
          <div class="at-col"><h6>Results</h6>${made.filter((m) => m.type === 'result').map(simple).join('') || '<div class="st-dim">—</div>'}</div>
          <div class="at-col"><h6>Files (exact bytes)</h6>${made.filter((m) => m.type === 'artifact').map(art).join('') || '<div class="st-dim">—</div>'}</div></div>`;
      }
      box.innerHTML = `<div class="at-h2">${esc(code(n))} — ${esc(n.title.slice(0, 140))}</div>
        <div class="at-sentence">${esc(n.state.sentence)}</div>${groupsHtml}
        <div class="at-h2">The chain behind it</div>
        <div class="at-chain">
          <div class="at-col"><h6>Claims it rests on</h6>${col('claim').map(simple).join('') || '<div class="st-dim">—</div>'}</div>
          <div class="at-col"><h6>Results</h6>${col('result').map(simple).join('') || '<div class="st-dim">—</div>'}</div>
          <div class="at-col"><h6>Runs</h6>${col('run').map(runCard).join('') || '<div class="st-dim">—</div>'}</div>
          <div class="at-col"><h6>Artifacts (exact bytes)</h6>${col('artifact').map(art).join('') || '<div class="st-dim">—</div>'}</div>
          <div class="at-col"><h6>Sources</h6>${col('source').map(simple).join('') || '<div class="st-dim">—</div>'}</div>
        </div>`;
    }

    // ── work ──────────────────────────────────────────────────
    async function renderWork() {
      const box = $('#at-work');
      let w;
      try { w = await src.work(S.inv); } catch (e) { box.innerHTML = `<div class="at-empty">${esc(e.message)}</div>`; return; }
      let nxt = { ranked: [], untested_hypotheses: [] };
      try { nxt = (await src.next(S.inv)) || nxt; } catch { /* none */ }
      let cost = null;
      try { cost = await src.cost(S.inv); } catch { /* no meter */ }
      let refused = null;
      try { refused = src.refusals ? await src.refusals(S.inv) : null; } catch { /* host without a refusal log */ }
      const list = (rows, empty) => rows.length ? rows.slice(0, 60).map((n) =>
        `<div class="at-edge"><span class="rel">${esc(n.kind || n.type)}</span><span>${nodeLink(n.id)} ${esc(n.title.slice(0, 90))}</span></div>`).join('') : `<div class="st-dim">${empty}</div>`;
      const authors = {};
      S.data.nodes.forEach((n) => { if (n.type !== 'artifact' && n.type !== 'review') authors[n.by] = (authors[n.by] || 0) + 1; });
      const reviewers = {};
      S.data.nodes.filter((n) => n.type === 'review').forEach((n) => { reviewers[n.by] = (reviewers[n.by] || 0) + 1; });
      const bars = (obj) => { const max = Math.max(1, ...Object.values(obj));
        return Object.entries(obj).sort((a, b) => b[1] - a[1]).slice(0, 14).map(([k, v]) =>
          `<div class="at-bar-row"><span>${esc(k)}</span><span class="bar" style="width:${(100 * v / max).toFixed(1)}%"></span><span class="num">${v}</span></div>`).join(''); };
      box.innerHTML = `<div class="at-work-grid">
        <div class="at-card"><h5>Being worked now (${w.leases.length})</h5>${w.leases.length ? w.leases.map((L) =>
          `<div class="at-edge"><span class="rel">${esc(L.agent)}</span><span>${nodeLink(L.node.id)} ${esc(L.node.title.slice(0, 70))}</span></div>`).join('') : '<div class="st-dim">Nobody holds a lease.</div>'}</div>
        <div class="at-card"><h5>Next experiments</h5>${nxt.ranked.length ? nxt.ranked.map((r) =>
          `<div class="at-edge"><span class="rel">score ${r.score}</span><span>${nodeLink(r.experiment.id)} separates ${r.separates}${r.power_check ? ', powered' : ''}${r.duplicate ? ', DUPLICATE' : ''}</span></div>`).join('') : '<div class="st-dim">None planned.</div>'}
          ${nxt.untested_hypotheses.length ? `<div class="at-k" style="margin-top:6px">untested hypotheses</div>${list(nxt.untested_hypotheses, '')}` : ''}</div>
        <div class="at-card"><h5>Review queue (${w.review_queue.length})</h5>${list(w.review_queue, 'Nothing waiting.')}</div>
        <div class="at-card"><h5>Needs revalidation (${w.revalidation.length})</h5>${list(w.revalidation, 'Nothing moved under anyone.')}</div>
        <div class="at-card"><h5>Contested (${w.contested.length})</h5>${list(w.contested, 'No open disputes.')}</div>
        <div class="at-card"><h5>Decisions to revisit (${(w.decisions_to_revisit || []).length})</h5>${list(w.decisions_to_revisit || [], 'None — every decision still rests on what it saw.')}</div>
        <div class="at-card"><h5>Duplicate work (${w.duplicates.length})</h5>${w.duplicates.length ? w.duplicates.map((g) => `<div>${g.map((n) => nodeLink(n.id)).join(' = ')}</div>`).join('') : '<div class="st-dim">No duplicates found.</div>'}</div>
        ${refused ? refusalCard(refused) : ''}
        ${cost && cost.metered !== false && cost.usd !== undefined ? spendCard(cost) : ''}
        <div class="at-card"><h5>Who wrote the record</h5>${bars(authors)}</div>
        <div class="at-card"><h5>Who reviewed it</h5>${Object.keys(reviewers).length ? bars(reviewers) : '<div class="st-dim">No reviews yet.</div>'}</div>
      </div>`;
    }

    // Overclaims the record refused in this investigation: per author, per rule, fixed or still open.
    function refusalCard(r) {
      if (!r.refused) return '<div class="at-card"><h5>Overclaims caught (0)</h5><div class="st-dim">No claim has been refused here.</div></div>';
      const authors = Object.entries(r.by_author || {});
      const max = Math.max(1, ...authors.map(([, v]) => v.refused));
      const rows = authors.slice(0, 10).map(([a, v]) => `<div class="at-bar-row"><span>${esc(a)}</span>`
        + `<span class="bar" style="width:${(100 * v.refused / max).toFixed(1)}%;background:var(--a-warn)"></span>`
        + `<span class="num">${v.fixed}/${v.refused}</span></div>`).join('');
      const codes = Object.entries(r.by_code || {}).slice(0, 6).map(([c, n]) => `<div class="at-edge"><span class="rel">×${n}</span><span>${esc(c)}</span></div>`).join('');
      const latest = (r.recent || []).slice(0, 4).map((x) => `<div class="at-field"><span class="k">${esc(x.author)} · ${esc((x.at || '').slice(0, 10))} · ${esc(x.codes.join(', '))}</span>`
        + `“${esc(x.statement.slice(0, 140))}”${x.fixed_by ? ` <span class="st-good">→ fixed</span>` : ' <span class="st-dim">→ open</span>'}</div>`).join('');
      return `<div class="at-card"><h5>Overclaims caught (${r.refused})</h5>
        <div class="at-k">${r.fixed} came back honest · ${r.refused - r.fixed} open · bars: fixed / refused per author</div>${rows}
        <div class="at-k" style="margin-top:6px">most common</div>${codes}
        <div class="at-k" style="margin-top:6px">latest</div>${latest}</div>`;
    }

    // Spend: from the host's meter (Graph(spend=…)); nobody writes it.
    function spendCard(c) {
      const usd = (v) => '$' + Number(v || 0).toFixed(v >= 10 ? 2 : 3);
      const tok = (v) => v >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : v >= 1e3 ? Math.round(v / 1e3) + 'k' : String(v || 0);
      const rows = (list, key) => { const max = Math.max(1e-9, ...list.map((r) => r.usd || 0));
        return list.slice(0, 10).map((r) => `<div class="at-bar-row"><span>${esc(String(r[key] || '—').split('/').pop())}</span>`
          + `<span class="bar" style="width:${(100 * (r.usd || 0) / max).toFixed(1)}%"></span><span class="num">${usd(r.usd)}</span></div>`).join(''); };
      const cached = c.input_tokens ? Math.round(100 * c.cached_tokens / c.input_tokens) : 0;
      const days = (c.by_day || []).slice(-14);
      const dmax = Math.max(1e-9, ...days.map((d) => d.usd || 0));
      return `<div class="at-card"><h5>Spend ${usd(c.usd)}</h5>
        <div class="at-k">${c.calls} model calls · ${tok(c.input_tokens)} in (${cached}% cached) · ${tok(c.output_tokens)} out
          · ${c.tasks} task(s)${c.unpriced_calls ? ` · ${c.unpriced_calls} unpriced` : ''}</div>
        <div class="at-k">${c.reviews} review verdict(s)${c.usd_per_verdict != null ? ' · ' + usd(c.usd_per_verdict) + ' per verdict' : ''}
          · lab: ${c.lab.runs} run(s), ${c.lab.minutes} min (local)</div>
        <div class="at-k">since the record last moved${c.last_moved ? ' (' + esc(c.last_moved.slice(0, 10)) + ')' : ''}: ${usd(c.since_last_moved.usd)}</div>
        ${days.length ? `<div class="at-spark" title="spend per day">${days.map((d) =>
          `<span title="${esc(d.day)}: ${usd(d.usd)}" style="height:${Math.max(4, 100 * (d.usd || 0) / dmax).toFixed(0)}%"></span>`).join('')}</div>` : ''}
        ${(c.by_agent || []).length ? `<div class="at-k" style="margin-top:6px">by teammate</div>${rows(c.by_agent, 'agent_id')}` : ''}
        ${(c.by_model || []).length ? `<div class="at-k" style="margin-top:6px">by model</div>${rows(c.by_model, 'model')}` : ''}
        ${(c.top_nodes || []).length ? `<div class="at-k" style="margin-top:6px">costliest nodes (shared work — overlapping)</div>`
          + c.top_nodes.slice(0, 6).map((n) => `<div class="at-edge"><span class="rel">${usd(n.usd)}</span><span>${nodeLink(n.id)} ${esc(n.title.slice(0, 70))}</span></div>`).join('') : ''}
      </div>`;
    }

    // ── timeline ──────────────────────────────────────────────
    async function loadEvents() {
      const r = await src.events(0, S.inv, 5000);
      S.events = r.events || []; S.head = Math.max(S.head, r.head || 0);
    }
    async function renderTimeline() {
      if (!S.events.length) { try { await loadEvents(); } catch (e) { $('#at-tl-feed').innerHTML = `<div class="at-empty">${esc(e.message)}</div>`; return; } }
      const days = {};
      S.events.forEach((e) => { const d = day(e.at); (days[d] = days[d] || {})[e.kind] = ((days[d] || {})[e.kind] || 0) + 1; });
      const keys = Object.keys(days).sort();
      const svg = $('#at-tl-chart');
      const W = svg.clientWidth || 800, H = 150, pad = 24;
      const kinds = ['create', 'link', 'review', 'revise', 'withdraw', 'retract', 'lease_take', 'lease_release'];
      const colors = { create: '#4ee08a', link: '#4aa8ff', review: '#ffd166', revise: '#ffb547', withdraw: '#ff4d5e', retract: '#94a3b8', lease_take: '#b18cff', lease_release: '#7c8ea3' };
      const max = Math.max(1, ...keys.map((k) => Object.values(days[k]).reduce((a, b) => a + b, 0)));
      const bw = Math.max(4, (W - 2 * pad) / Math.max(1, keys.length) - 4);
      let out = '';
      keys.forEach((k, i) => {
        let y = H - pad; const x = pad + i * (bw + 4);
        kinds.forEach((kd) => { const v = days[k][kd] || 0; if (!v) return; const h = (H - 2 * pad) * v / max; y -= h;
          out += `<rect x="${x}" y="${y}" width="${bw}" height="${h}" fill="${colors[kd]}"><title>${k} · ${kd}: ${v}</title></rect>`; });
        if (keys.length <= 20 || i % Math.ceil(keys.length / 12) === 0) out += `<text x="${x}" y="${H - 6}" font-size="9" fill="currentColor">${k.length > 7 && keys[0].slice(0, 4) === keys[keys.length - 1].slice(0, 4) ? k.slice(5) : k}</text>`;
      });
      svg.setAttribute('viewBox', `0 0 ${W} ${H}`); svg.style.color = 'var(--a-ink2)'; svg.innerHTML = out;
      const range = $('#at-tl-range');
      range.max = Math.max(0, S.events.length - 1); if (S.until === null) range.value = range.max;
      const feed = S.events.slice(-300).reverse();
      $('#at-tl-feed').innerHTML = feed.map((e) => {
        const n = S.by.get(e.ref);
        return `<div class="ev"><span class="t">${esc(e.at.replace('T', ' ').slice(0, 19))}</span><span>${esc(e.actor)}</span><span>${esc(e.kind)}</span>
          <span>${n ? nodeLink(n.id) + ' ' + esc(n.title.slice(0, 80)) : esc(e.ref)}${e.payload && e.payload.verdict ? ' — ' + esc(e.payload.verdict) : ''}${e.payload && e.payload.rel ? ' — ' + esc(e.payload.rel) : ''}</span></div>`;
      }).join('') || '<div class="at-empty">No events.</div>';
      updateUntilLabel();
    }
    function updateUntilLabel() {
      const i = +$('#at-tl-range').value; const e = S.events[i];
      $('#at-tl-at').textContent = e ? `graph as of ${e.at.replace('T', ' ').slice(0, 16)} (event ${i + 1}/${S.events.length})` : '';
    }
    $('#at-tl-range').addEventListener('input', (ev) => {
      const i = +ev.target.value; const e = S.events[i];
      S.until = (i >= S.events.length - 1) ? null : (e ? e.at : null);
      updateUntilLabel();
    });
    $('#at-tl-range').addEventListener('change', () => toast(S.until ? 'Graph view now shows the record as of that point — open Graph to see it.' : 'Showing the whole record.'));
    $('#at-tl-play').addEventListener('click', async () => {
      if (!S.events.length) await loadEvents();
      setView('graph');
      const times = [...new Set(S.data.nodes.map((n) => n.at).sort())];
      const steps = 40; let i = 0;
      const tick = () => {
        i += 1; S.until = times[Math.min(times.length - 1, Math.floor(times.length * i / steps))];
        if (S.cy) S.cy.batch(() => S.cy.nodes().forEach((x) => { const n = S.by.get(x.id()); x.style('display', n && n.at <= S.until ? 'element' : 'none'); }));
        if (i < steps) setTimeout(tick, 120); else { S.until = null; S.cy && S.cy.nodes().style('display', 'element'); toast('Replay done'); }
      };
      tick();
    });

    // ── search ────────────────────────────────────────────────
    const qbox = $('#at-q'); const results = $('#at-results');
    qbox.addEventListener('input', () => {
      const q = qbox.value.trim().toLowerCase();
      if (!q) { results.hidden = true; clearFocus(); return; }
      const hits = S.data.nodes.filter((n) => code(n).toLowerCase() === q || code(n).toLowerCase().startsWith(q) || (n.title || '').toLowerCase().includes(q)).slice(0, 30);
      results.innerHTML = hits.map((n) => `<button data-node="${esc(n.id)}"><b>${esc(code(n))}</b> ${esc((TYPES[n.type] || {}).label || n.type)} — ${esc(n.title.slice(0, 100))}</button>`).join('') || '<div class="at-empty" style="padding:8px">No match in this investigation.</div>';
      results.hidden = false;
      if (S.cy) { S.cy.nodes().removeClass('hit'); hits.forEach((n) => S.cy.getElementById(n.id).addClass('hit')); }
    });
    results.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-node]'); if (!b) return;
      results.hidden = true; showInspector(b.dataset.node);
      if (S.view !== 'graph') setView('graph'); focusOn(b.dataset.node);
    });
    document.addEventListener('click', (ev) => { if (!ev.target.closest('.at-search')) results.hidden = true; });

    // ── toolbar ───────────────────────────────────────────────
    $('#at-inv').addEventListener('change', (ev) => loadInv(ev.target.value));
    $('#at-theme').addEventListener('click', () => {
      root.dataset.theme = root.dataset.theme === 'light' ? 'dark' : 'light';
      try { localStorage.setItem('atlas-theme', root.dataset.theme); } catch { /* private mode */ }
      if (S.cy) S.cy.style(cyStyle());
      if (opts.onTheme) opts.onTheme(root.dataset.theme);
    });
    try { const t = localStorage.getItem('atlas-theme'); if (t && !opts.theme) root.dataset.theme = t; } catch { /* private mode */ }
    $('#at-export').addEventListener('click', () => {
      const stamp = new Date().toISOString().slice(0, 10);
      if (S.cy) dl(S.cy.png({ full: true, scale: 2, bg: css('--a-bg', '#0a0d14') }), `atlas-${S.inv}-${stamp}.png`);
      const data = src.kind === 'bundle' ? src.bundle : S.data;
      dl(URL.createObjectURL(new Blob([JSON.stringify(data, null, 1)], { type: 'application/json' })),
        src.kind === 'bundle' ? `hypgraph-${S.inv}-${stamp}.json` : `atlas-${S.inv}-${stamp}.json`);
    });
    function dl(href, name) { const a = document.createElement('a'); a.href = href; a.download = name; document.body.appendChild(a); a.click(); a.remove(); }

    // ── keyboard ──────────────────────────────────────────────
    if (opts.hash !== false) {
      global.addEventListener('hashchange', () => {
        const h = new URLSearchParams(location.hash.slice(1));
        const inv = h.get('inv'), node = h.get('node');
        if (inv && inv !== S.inv) {
          if (!S.invs.some((i) => i.id === inv)) { loadInvestigations(); return; }
          $('#at-inv').value = inv; loadInv(inv, node); return;
        }
        if (node && node !== S.sel) { showInspector(node); if (S.view === 'graph') focusOn(node); }
      });
    }
    document.addEventListener('keydown', (ev) => {
      if (!root.isConnected || root.offsetParent === null) return;
      if (ev.target.matches('input, select, textarea')) { if (ev.key === 'Escape') ev.target.blur(); return; }
      if (ev.ctrlKey || ev.metaKey || ev.altKey) return;
      const views = ['graph', 'hypotheses', 'claims', 'provenance', 'work', 'timeline'];
      if (ev.key === '/') { ev.preventDefault(); qbox.focus(); }
      else if (ev.key === 'Escape') { clearFocus(); results.hidden = true; }
      else if (/^[1-6]$/.test(ev.key)) setView(views[+ev.key - 1]);
      else if (ev.key === 'f' && S.sel) focusOn(S.sel);
      else if (ev.key === 'w' && S.sel) whyOrImpact('why');
      else if (ev.key === 'i' && S.sel) whyOrImpact('impact');
    });

    // ── live: poll the event log ──────────────────────────────
    let reloadTimer = null;
    async function poll() {
      try {
        const r = await src.events(S.head, '', 500);
        $('#at-live').classList.remove('off');
        const mine = (r.events || []).filter((e) => !S.inv || S.by.has(e.ref) || e.ref === S.inv || (e.payload && e.payload.inv === S.inv));
        if (r.events && r.events.length) S.head = r.head;
        if (mine.length) {
          toast(`${mine.length} new change(s) in this investigation`);
          clearTimeout(reloadTimer);
          reloadTimer = setTimeout(async () => {
            const keep = S.sel;
            S.data = await src.subgraph(S.inv);
            S.by = new Map(S.data.nodes.map((n) => [n.id, n])); S.details.clear(); S.events = [];
            renderRail(); render(); if (keep) showInspector(keep);
          }, 800);
        }
      } catch { const l = $('#at-live'); if (l) l.classList.add('off'); }
      setTimeout(poll, opts.pollMs || 15000);
    }

    const ready = loadInvestigations().then(() => { if (live) setTimeout(poll, opts.pollMs || 15000); }).catch((e) => {
      $('#at-insp').innerHTML = `<div class="at-empty">Couldn't reach the research graph: ${esc(e.message)}</div>`;
    });
    const setTheme = (t) => { root.dataset.theme = t; if (S.cy) S.cy.style(cyStyle()); };
    return { ready, state: S, show: showInspector, setView, focus: focusOn, setTheme, source: src };
  }

  global.HypAtlas = { mount, HttpSource, BundleSource, verifyBundle, sha256, TYPES, EDGES, version: VERSION };
})(typeof window !== 'undefined' ? window : globalThis);
