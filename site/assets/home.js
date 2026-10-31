/* hypgraph.com homepage: fills every figure from site-data.js (the page's own HypGraph record, built by
   dev/site_record.py), runs the app on a live example, Broad Street or that record, and verifies bundles here. */
'use strict';
// the site root, from this script's own URL: the page may be a translation one folder down (es/, fr/ …)
const HG_HOME = new URL('..', document.currentScript ? document.currentScript.src : location.href);
(() => {
  const t = (s, v) => { const x = (window.HG_T || {})[s] || s; return v ? x.replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? v[k] : m)) : x; };
  const at = (p) => new URL(p, HG_HOME).href;
  const P = window.SITE_DATA || { facts: {}, standing: {}, overclaims: [], lint: { findings: [] }, data_ok: [] };
  const $ = (s) => document.querySelector(s), $$ = (s) => [...document.querySelectorAll(s)];
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const root = document.documentElement;
  const theme = () => (window.HG ? window.HG.theme() : root.dataset.theme || 'light');

  // ── figures, from the record ──
  // a figure reads in the page's language: "188 of 188", "5 of 5 bundles", "no" dependencies
  const said = (v) => {
    const m = /^([\d,]+) of ([\d,]+)( bundles)?$/.exec(v);
    if (m) return t(m[3] ? '{k} of {n} bundles' : '{k} of {n}', { k: m[1], n: m[2] });
    return v === 'no' ? t('no') : v;
  };
  $$('[data-fact]').forEach((el) => { const v = P.facts[el.dataset.fact]; if (v != null) el.textContent = said(v); });
  const REVIEW = { replicated: ['ok', t('replicated')], checked: ['ok', t('checked')], contested: ['bad', t('contested')],
    objection: ['bad', t('objection')], unchecked: ['', t('unchecked')] };
  const badge = (k) => {
    const st = P.standing[k]; if (!st) return '';
    const [cls, word] = REVIEW[st.review] || ['', st.review || t('unchecked')];
    return `<button type="button" class="pill ${cls}" data-open-claim="${esc(k)}" title="${esc(st.summary)}">${esc(st.code)} · ${esc(word)} ↗</button>`;
  };
  $$('[data-claim]').forEach((el) => { el.innerHTML = badge(el.dataset.claim); });

  // ── the stage: the app on one bundle at a time ──
  const EXAMPLES = ['scientific', 'software', 'trading', 'knowledge', 'optimization'];
  const LABEL = { scientific: t('Scientific'), software: t('Software'), trading: t('Trading'), knowledge: t('Knowledge'), optimization: t('Optimization') };
  const SOURCES = EXAMPLES.map((k) => [k, LABEL[k], `data/examples/${k}.bundle.json`])
    .concat([['broad-street', 'Broad Street, 1854', 'data/broad-street.bundle.json'], ['page', t('This page’s record'), 'data/site-record.bundle.json']]);
  const FOOT = {
    page: t('The record behind the figures on this page: each claim bound to the lab’s measurement and re-measured another way by a reviewer.'),
    'broad-street': t('A teaching reconstruction of Snow’s cholera investigation (figures from his 1855 account), as one verifiable record.'),
    _: t('A HypSwarm run on scripted models (answers computed by the example, replies paced), replayed from its record. Its telemetry rides along outside the hash chain.'),
  };
  const tabs = $('#stage-tabs'), app = $('#app');
  let view = null, current = null;
  tabs.innerHTML = SOURCES.map(([k, label]) => `<button type="button" data-src="${k}" aria-pressed="false">${esc(label)}</button>`).join('');
  async function show(key, then) {
    const src = SOURCES.find((s) => s[0] === key); if (!src || !window.HypGraph) return;
    tabs.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.src === key)));
    $('#stage-foot').textContent = FOOT[key] || FOOT._;
    if (key !== current) {
      $('#stage-chain').textContent = t('verifying…'); $('#stage-chain').className = 'pill';
      if (view) view.destroy();
      current = key;
      const bundle = await (await fetch(at(src[2]))).json();
      view = HypGraph.mount(app, { source: HypGraph.BundleSource(bundle), theme: theme(), play: EXAMPLES.includes(key), embed: true,
        lang: root.lang || 'en', langSwitch: false,
        onTheme: (t) => { root.dataset.theme = t; try { localStorage.setItem('hg-theme', t); } catch { /* private */ } (window.HG ? window.HG.onTheme : []).forEach((f) => f(t)); } });
      await view.ready;
      const v = await HypGraph.verifyBundle(bundle);
      $('#stage-chain').textContent = v.ok ? t('⛓ chain verified · {n} events', { n: v.checked }) : t('✗ chain broken at #{n}', { n: v.broken_at });
      $('#stage-chain').className = 'pill ' + (v.ok ? 'ok' : 'bad');
    }
    if (then) then(view);
  }
  if (window.HG) window.HG.onTheme.push((t) => { if (view) view.setTheme(t); });
  tabs.addEventListener('click', (e) => { const b = e.target.closest('[data-src]'); if (b) show(b.dataset.src); });
  document.addEventListener('click', (e) => {
    const w = e.target.closest('[data-show]');
    if (w) { e.preventDefault(); $('#product').scrollIntoView({ block: 'start' }); show(w.dataset.show); return; }
    const c = e.target.closest('[data-open-claim]');
    if (c) {
      const st = P.standing[c.dataset.openClaim];
      $('#product').scrollIntoView({ block: 'start' });
      show('page', (v) => { v.setView('evidence'); if (st) v.show(st.id);
        setTimeout(() => $('#product').scrollIntoView({ block: 'start', behavior: 'instant' }), 400); });   // after the drawer takes focus
    }
  });
  show('software');

  // ── verify, here: the example records the claim is about, and this page's own record on its own line ──
  $('#verify').addEventListener('click', async () => {
    const out = $('#verify-out'); out.className = 'verify-out'; out.textContent = t('Hashing…');
    const check = async (url) => HypGraph.verifyBundle(await (await fetch(at(url))).json());
    const t0 = performance.now();
    const ex = await Promise.all(EXAMPLES.map((k) => check(`data/examples/${k}.bundle.json`)));
    const ms = Math.round(performance.now() - t0), good = ex.filter((v) => v.ok).length;
    const own = await check('data/site-record.bundle.json');
    out.className = 'verify-out' + (good === ex.length && own.ok ? ' ok' : '');
    out.innerHTML = `${good === ex.length ? '✓' : '✗'} ${esc(t('{k} of {n} example records verified in your browser — {e} events, {ms} ms.', { k: good, n: ex.length, e: ex.reduce((a, v) => a + (v.checked || 0), 0), ms }))}`
      + `<br>${own.ok ? '✓' : '✗'} ${esc(own.ok ? t('This page’s own record: {n} events, chain intact.', { n: own.checked || 0 }) : t('This page’s own record: {n} events', { n: own.checked || 0 }) + ' — ' + (own.problem || 'broken') + '.')}`;
  });

  // ── the overclaims, as the engine answered them ──
  $('#refusals').innerHTML = (P.overclaims || []).map((o) => `<div class="card ref">
      <div class="bad">${esc(o.claim)}</div>
      <div class="codes">${(o.codes || []).map((c) => `<code>${esc(c)}</code>`).join('')}</div>
      <pre class="msg">${esc(String(o.message || '').replace(/^claim refused:\s*/, '').replace(/\s*\[[A-Z_]+\]/g, ''))}</pre>
      <div class="good"><div class="lbl">${esc(o.accepted_as ? t('Accepted as {what}', { what: o.accepted_as }) : t('Accepted'))}</div>${esc(o.rewrite)}</div></div>`).join('');

  // ── the page's own record ──
  const rows = Object.entries(P.standing).map(([k, st]) => {
    const [cls, word] = REVIEW[st.review] || ['', st.review || t('unchecked')];
    return `<tr><td>${badge(k)}</td><td>${esc(st.statement)}<div style="font-size:12.5px;color:var(--ink2);margin-top:2px">${esc(st.summary)}</div></td><td><span class="pill ${cls}">${esc(word)}</span><div style="font-size:12px;color:var(--ink2);margin-top:4px">${esc((st.verdicts || []).join(', '))}</div></td></tr>`;
  }).join('');
  const L = P.lint || { findings: [] };
  const lintRows = (L.findings || []).map((f) => `<li><code>${esc(f.code)}</code> ${esc(f.level)} · ${esc(f.excerpt)} — ${esc(f.message)}</li>`).join('');
  const okRows = (P.data_ok || []).map((d) => `<li>“${esc(d.text)}” — ${esc(d.why)}</li>`).join('');
  $('#record-claims').innerHTML = `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>${esc(t('claim'))}</th><th>${esc(t('the claim, and what the record derives about it'))}</th><th>${esc(t('review'))}</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="grid2" style="margin-top:16px">
      <div class="card"><h3>${esc(t('The text of this page, checked against the record'))}</h3>
        <p>${t('<code>hypgraph check</code> on <a href="{href}">the page as read</a>: {e} errors, {w} warnings.', { href: at('data/homepage-checked.md'), e: L.errors ?? '—', w: L.warnings ?? '—' })}</p>
        ${lintRows ? `<ul style="margin:8px 0 0;padding-left:18px;color:var(--ink2);font-size:14px">${lintRows}</ul>` : ''}</div>
      <div class="card"><h3>${esc(t('Phrases true by design'))}</h3>
        <ul style="margin:0;padding-left:18px;color:var(--ink2);font-size:14px">${okRows || `<li>${esc(t('None.'))}</li>`}</ul></div></div>
    <p class="note">${t('Built {at} · chain head <code>{head}…</code>', { at: esc(String(P.built || '').replace('T', ' ').replace('Z', ' UTC')), head: esc(String(P.head || '').slice(0, 16)) })}</p>`;
})();
