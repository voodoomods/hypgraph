/* Mount HypGraph on every [data-hypgraph] element from a bundle: data-bundle="<url>" (default: the Broad Street demo),
   or ?bundle=<url>, or a bundle handed over from /verify/ (sessionStorage). data-hash="on" keeps the view in the URL
   fragment; data-play="on" opens on the Live view and replays the run. The bundle's hash chain is re-verified in the
   browser; its derived views and any telemetry it carries are shown, never trusted. */
'use strict';
// The site root, from this script's own URL (assets/embed.js): the site works at / and under a prefix (/hypgraph/).
const HG_ROOT = new URL('..', document.currentScript ? document.currentScript.src : location.href);
(() => {
  const t = (s, v) => { const x = (window.HG_T || {})[s] || s; return v ? x.replace(/\{(\w+)\}/g, (m, k) => (v[k] != null ? v[k] : m)) : x; };
  const els = document.querySelectorAll('[data-hypgraph]');
  if (!els.length || !window.HypGraph) return;
  const params = new URLSearchParams(location.search);
  const syncTheme = (t) => {                              // the app's own toggle drives the site's theme
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem('hg-theme', t); } catch { /* private mode */ }
    (window.HG ? window.HG.onTheme : []).forEach((f) => f(t));
  };
  els.forEach(async (el) => {
    const main = el.dataset.main === 'on';               // the page's main viewer: it takes ?bundle= and /verify/'s hand-over
    let bundle = null;
    if (main && params.get('from') === 'verify') {
      try { bundle = JSON.parse(sessionStorage.getItem('hg-bundle') || 'null'); } catch { bundle = null; }
    }
    const url = (main && params.get('bundle')) || el.dataset.bundle || new URL('data/broad-street.bundle.json', HG_ROOT).href;
    try {
      if (!bundle) {
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
        bundle = await r.json();
      }
    } catch (e) {
      el.dataset.hgError = 'bundle: ' + e.message;
      el.innerHTML = `<div style="padding:24px;font:14px system-ui">${t('Couldn\'t load the bundle: {e}', { e: String(e.message).replace(/</g, '&lt;') })}</div>`;
      return;
    }
    const theme = document.documentElement.dataset.theme || (window.HG ? window.HG.theme() : 'light');
    // linked records: data-record is this record's own URL; data-records maps the record URLs its pins name to bundles
    let records = {};
    try {
      records = Object.fromEntries(Object.entries(JSON.parse(el.dataset.records || '{}')).map(([k, v]) => [k, new URL(v, HG_ROOT).href]));
    } catch { records = {}; }
    const view = HypGraph.mount(el, {
      source: HypGraph.BundleSource(bundle), theme, hash: el.dataset.hash === 'on', play: el.dataset.play === 'on',
      onTheme: syncTheme, records, recordUrl: el.dataset.record || '', view: el.dataset.view || undefined,
      // the app speaks the page's language; choosing another in the app opens the page in that language
      lang: document.documentElement.lang || 'en', onLang: (code) => { if (window.HG && window.HG.toLang) window.HG.toLang(code); },
    });
    if (window.HG) window.HG.onTheme.push((t) => view.setTheme(t));     // the site's toggle drives the app too
  });
})();
