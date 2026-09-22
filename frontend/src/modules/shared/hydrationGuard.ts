/**
 * Hydration guard against browser extensions.
 *
 * Some browser extensions (e.g. Bitdefender Browser Protection) inject
 * marker attributes (`bis_skin_checked`, `bis_register`, `__processed_<uuid>`)
 * into every element of the document before React hydrates. React then diffs
 * the server HTML against this mutated DOM and reports hydration mismatches
 * on completely unrelated components.
 *
 * The fix is not `suppressHydrationWarning` (it would be a per-element patch
 * and would hide real hydration bugs). Instead, this script runs inline in
 * `<head>` — i.e. *before* React hydrates — and:
 *
 *   1. Removes any extension-injected attribute already present.
 *   2. Installs a MutationObserver that keeps removing them, so attributes
 *      injected between the initial pass and hydration (or afterwards) are
 *      stripped too.
 *
 * Only known extension namespaces are touched; every other attribute — and
 * every other hydration mismatch — still behaves normally.
 */
export const EXTENSION_ATTRIBUTE_CLEANUP_SCRIPT = String.raw`
(function () {
  if (typeof window === "undefined" || window.__extensionAttrCleanup) return;
  window.__extensionAttrCleanup = true;

  var RX = /^(bis_|__processed_)/;

  function cleanElement(el) {
    var attrs = el.attributes;
    for (var i = attrs.length - 1; i >= 0; i--) {
      if (RX.test(attrs[i].name)) el.removeAttribute(attrs[i].name);
    }
  }

  function cleanSubtree(root) {
    if (!root || root.nodeType !== 1) return;
    cleanElement(root);
    var all = root.querySelectorAll("*");
    for (var i = 0; i < all.length; i++) cleanElement(all[i]);
  }

  cleanSubtree(document.documentElement);

  new MutationObserver(function (records) {
    for (var r = 0; r < records.length; r++) {
      var m = records[r];
      if (m.type === "attributes" && RX.test(m.attributeName || "")) {
        cleanElement(m.target);
      } else if (m.type === "childList") {
        for (var i = 0; i < m.addedNodes.length; i++) {
          cleanSubtree(m.addedNodes[i]);
        }
      }
    }
  }).observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
  });
})();
`;

declare global {
  interface Window {
    __extensionAttrCleanup?: boolean;
  }
}
