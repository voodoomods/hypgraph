/* The Atlas became HypGraph (hypgraph 0.6). This file loads hypgraph.js in its place, so pages that include atlas.js
   (and call HypAtlas.mount) keep working for one release. New pages: include hypgraph.js and call HypGraph.mount. */
(function () {
  var s = document.currentScript;
  var src = s && s.src ? s.src.replace(/atlas\.js(\?[^#]*)?$/, 'hypgraph.js$1') : 'hypgraph.js';
  document.write('<script src="' + src + '"><\/script>');
})();
