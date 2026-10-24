/* Mount the Atlas on #atlas from a bundle: data-bundle="<url>" (default: the Broad Street demo), or ?bundle=<url>,
   or a bundle handed over from /verify/ (sessionStorage). The bundle's hash chain is verified in the browser. */
'use strict';
// The site root, from this script's own URL (assets/embed.js): the site works at / and under a prefix (/hypgraph/).
const HG_ROOT = new URL('..', document.currentScript ? document.currentScript.src : location.href);
(async () => {
  const el = document.getElementById('atlas');
  if (!el || !window.HypAtlas) return;
  const params = new URLSearchParams(location.search);
  let bundle = null;
  if (params.get('from') === 'verify') {
    try { bundle = JSON.parse(sessionStorage.getItem('hg-bundle') || 'null'); } catch { bundle = null; }
  }
  const url = params.get('bundle') || el.dataset.bundle || new URL('data/broad-street.bundle.json', HG_ROOT).href;
  try {
    if (!bundle) {
      const r = await fetch(url);
      if (!r.ok) throw new Error(`HTTP ${r.status} for ${url}`);
      bundle = await r.json();
    }
  } catch (e) {
    el.innerHTML = `<div style="padding:24px;font:14px system-ui">Couldn't load the bundle: ${String(e.message).replace(/</g, '&lt;')}</div>`;
    return;
  }
  const theme = window.HG ? window.HG.theme() : 'dark';
  const view = HypAtlas.mount(el, {
    source: HypAtlas.BundleSource(bundle), title: 'ATLAS', theme, hash: el.dataset.hash === 'on',
    onTheme: (t) => {                                    // the explorer's own toggle drives the site's theme
      document.documentElement.dataset.theme = t;
      try { localStorage.setItem('hg-theme', t); } catch { /* private mode */ }
      (window.HG ? window.HG.onTheme : []).forEach((f) => f(t));
    },
  });
  if (window.HG) window.HG.onTheme.push((t) => view.setTheme(t));     // the site's toggle drives the explorer too
})();
