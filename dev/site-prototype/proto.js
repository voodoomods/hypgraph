/* hypgraph.com prototype: fills every figure from data.js (the homepage's own HypGraph record, built by
   dev/site_record.py), runs the app on a live example or on that record, and verifies bundles in the browser. */
'use strict';
(() => {
  const P = window.PROTO || { facts: {}, standing: {}, overclaims: [], lint: { findings: [] }, data_ok: [] };
  const $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)];
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const root = document.documentElement;
  const theme = () => root.dataset.theme || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');

  // ── figures, from the record ──
  $$('[data-fact]').forEach((el) => { const v = P.facts[el.dataset.fact]; if (v != null) el.textContent = v; });
  const REVIEW = { replicated: ['ok', 'replicated'], checked: ['ok', 'checked'], contested: ['bad', 'contested'],
    objection: ['bad', 'objection'], unchecked: ['', 'unchecked'] };
  $$('[data-claim]').forEach((el) => {
    const st = P.standing[el.dataset.claim]; if (!st) return;
    const [cls, word] = REVIEW[st.review] || ['', st.review || 'unchecked'];
    el.innerHTML = `<button type="button" class="pill ${cls}" data-open-claim="${esc(el.dataset.claim)}" title="${esc(st.summary)}">${esc(st.code)} · ${esc(word)} ↗</button>`;
  });

  // ── the stage: the app on one bundle at a time ──
  const SOURCES = [
    ['scientific', 'Scientific', '../../site/data/examples/scientific.bundle.json'],
    ['software', 'Software', '../../site/data/examples/software.bundle.json'],
    ['trading', 'Trading', '../../site/data/examples/trading.bundle.json'],
    ['knowledge', 'Knowledge', '../../site/data/examples/knowledge.bundle.json'],
    ['optimization', 'Optimization', '../../site/data/examples/optimization.bundle.json'],
    ['page', 'This page’s own record', 'site-record.bundle.json'],
  ];
  const FOOT = {
    page: 'The record behind the figures on this page: each claim bound to the lab’s measurement and re-measured another way by a reviewer. Built by dev/site_record.py.',
    _: 'A HypSwarm run on scripted models (answers computed by the example, replies paced), replayed from its record. The telemetry rides along outside the hash chain.',
  };
  const chips = $('#chips'), app = $('#app');
  let view = null, current = null, bundle = null;
  chips.innerHTML = SOURCES.map(([k, label]) => `<button type="button" data-src="${k}" aria-pressed="false">${esc(label)}</button>`).join('');
  async function show(key, then) {
    const src = SOURCES.find((s) => s[0] === key); if (!src) return;
    chips.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.src === key)));
    $('#stage-foot').textContent = FOOT[key] || FOOT._;
    $('#stage-chain').textContent = 'verifying…'; $('#stage-chain').className = 'pill';
    if (key !== current) {
      if (view) view.destroy();
      current = key;
      bundle = await (await fetch(src[2])).json();
      view = HypGraph.mount(app, { source: HypGraph.BundleSource(bundle), theme: theme(), play: key !== 'page',
        onTheme: (t) => { root.dataset.theme = t; try { localStorage.setItem('hg-proto-theme', t); } catch { /* private */ } } });
      await view.ready;
      const v = await HypGraph.verifyBundle(bundle);
      $('#stage-chain').textContent = v.ok ? `⛓ chain verified · ${v.checked} events` : `✗ chain broken at #${v.broken_at}`;
      $('#stage-chain').className = 'pill ' + (v.ok ? 'ok' : 'bad');
    }
    if (then) then(view);
  }
  chips.addEventListener('click', (e) => { const b = e.target.closest('[data-src]'); if (b) show(b.dataset.src); });
  document.addEventListener('click', (e) => {
    const w = e.target.closest('[data-show]');
    if (w) { e.preventDefault(); $('#product-live').scrollIntoView({ block: 'start' }); show(w.dataset.show); return; }
    const c = e.target.closest('[data-open-claim]');
    if (c) {
      const st = P.standing[c.dataset.openClaim];
      $('#product-live').scrollIntoView({ block: 'start' });
      show('page', (v) => { v.setView('evidence'); if (st) v.show(st.id);
        setTimeout(() => $('#product-live').scrollIntoView({ block: 'start', behavior: 'instant' }), 400); });   // after the drawer takes focus
    }
  });
  show('software');

  // ── verify a bundle, here ──
  $('#verify').addEventListener('click', async () => {
    const out = $('#verify-out'); out.className = 'verify-out'; out.textContent = 'Hashing…';
    const t0 = performance.now(), res = [];
    for (const [k, , url] of SOURCES) {
      const b = await (await fetch(url)).json(); const v = await HypGraph.verifyBundle(b); res.push([k, v]);
    }
    const ms = Math.round(performance.now() - t0), good = res.filter(([, v]) => v.ok).length;
    out.className = 'verify-out' + (good === res.length ? ' ok' : '');
    out.textContent = `${good === res.length ? '✓' : '✗'} ${good} of ${res.length} bundles verified in your browser, ${res.reduce((a, [, v]) => a + (v.checked || 0), 0)} events, ${ms} ms.`;
  });

  // ── the overclaims, as the engine answered them ──
  $('#refusals').innerHTML = P.overclaims.map((o) => `<div class="card ref">
      <div class="bad">${esc(o.claim)}</div>
      <div class="codes">${(o.codes || []).map((c) => `<code>${esc(c)}</code>`).join('')}</div>
      <pre class="msg">${esc(String(o.message || '').replace(/^claim refused:\s*/, '').replace(/\s*\[[A-Z_]+\]/g, ''))}</pre>
      <div class="good"><div class="lbl">Accepted${o.accepted_as ? ' as ' + esc(o.accepted_as) : ''}</div>${esc(o.rewrite)}</div></div>`).join('');

  // ── the page's own record ──
  const rows = Object.entries(P.standing).map(([k, st]) => {
    const [cls, word] = REVIEW[st.review] || ['', st.review || 'unchecked'];
    return `<tr><td><button type="button" class="pill accent" data-open-claim="${esc(k)}">${esc(st.code)} ↗</button></td><td>${esc(st.statement)}<div style="font-size:12.5px;color:var(--ink2);margin-top:2px">${esc(st.summary)}</div></td><td><span class="pill ${cls}">${esc(word)}</span><div style="font-size:12px;color:var(--ink2);margin-top:4px">${esc((st.verdicts || []).join(', '))}</div></td></tr>`;
  }).join('');
  const L = P.lint || { findings: [] };
  const lintRows = (L.findings || []).map((f) => `<li><code>${esc(f.code)}</code> ${esc(f.level)} · ${esc(f.excerpt)} — ${esc(f.message)}</li>`).join('');
  const okRows = (P.data_ok || []).map((d) => `<li>“${esc(d.text)}” — ${esc(d.why)}</li>`).join('');
  const box = $('#record');
  if (box) box.innerHTML = `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>claim</th><th>the claim, and what the record derives about it</th><th>review</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="grid g2" style="margin-top:16px">
      <div class="card"><h3 style="margin:0 0 6px;font-size:16px">The copy, checked against the record</h3>
        <p style="margin:0 0 8px;color:var(--ink2)"><code>hypgraph check homepage.md</code>: ${L.errors ?? '—'} errors, ${L.warnings ?? '—'} warnings.</p>
        ${lintRows ? `<ul style="margin:0;padding-left:18px;color:var(--ink2);font-size:14px">${lintRows}</ul>` : ''}</div>
      <div class="card"><h3 style="margin:0 0 6px;font-size:16px">Phrases true by design</h3>
        <ul style="margin:0;padding-left:18px;color:var(--ink2);font-size:14px">${okRows || '<li>None.</li>'}</ul></div></div>`;

  // ── theme ──
  $('#theme').addEventListener('click', () => {
    const t = theme() === 'dark' ? 'light' : 'dark'; root.dataset.theme = t;
    try { localStorage.setItem('hg-proto-theme', t); } catch { /* private mode */ }
    if (view) view.setTheme(t);
  });
})();
