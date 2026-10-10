// Pure geometry + layout helpers used to decide WHAT part of the page is
// screenshotted for the active field. Loaded as a content script, via
// importScripts() in the service worker, and imported directly by tests.
(() => {
  const EXTRA_PADDING = 24;      // extra CSS pixels kept around the context area
  const MIN_W = 320, MIN_H = 120; // never send a crop smaller than this (CSS px)
  const MAX_W = 1200, MAX_H = 400; // never climb to a container larger than this
  const HEADING_GAP = 60;        // include a section heading only for the first row under it
  const CONTROL_SELECTOR = "input, textarea, select, [contenteditable='true'], [role='combobox'], [role='radio'], [role='checkbox']";
  const HEADING_SELECTOR = "h1,h2,h3,h4,h5,h6,legend,[role='heading'],[class*='title'],[class*='heading']";

  const rect = (left, top, width, height) => ({ left, top, width, height });
  const fromDom = r => rect(r.left, r.top, r.width, r.height);

  function union(rects) {
    const list = rects.filter(Boolean);
    const left = Math.min(...list.map(r => r.left));
    const top = Math.min(...list.map(r => r.top));
    const right = Math.max(...list.map(r => r.left + r.width));
    const bottom = Math.max(...list.map(r => r.top + r.height));
    return rect(left, top, right - left, bottom - top);
  }
  const pad = (r, px) => rect(r.left - px, r.top - px, r.width + px * 2, r.height + px * 2);
  function ensureMin(r, minW, minH) {
    const w = Math.max(r.width, minW), h = Math.max(r.height, minH);
    return rect(r.left - (w - r.width) / 2, r.top - (h - r.height) / 2, w, h);
  }
  function clamp(r, vw, vh) {
    const left = Math.max(0, r.left), top = Math.max(0, r.top);
    const right = Math.min(vw, r.left + r.width), bottom = Math.min(vh, r.top + r.height);
    return right - left < 1 || bottom - top < 1 ? null : rect(left, top, right - left, bottom - top);
  }
  // CSS-pixel rect -> integer pixel rect inside a bitmap of (bw x bh).
  function toPixels(r, scaleX, scaleY, bw, bh) {
    const left = Math.max(0, Math.floor(r.left * scaleX)), top = Math.max(0, Math.floor(r.top * scaleY));
    const right = Math.min(bw, Math.ceil((r.left + r.width) * scaleX)), bottom = Math.min(bh, Math.ceil((r.top + r.height) * scaleY));
    return { left, top, width: Math.max(1, right - left), height: Math.max(1, bottom - top) };
  }
  const shrinkFactor = (width, maxWidth) => Math.min(1, maxWidth / Math.max(1, width));

  const isRendered = node => { const r = node.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const controlKey = c => ((c.type || "").toLowerCase() === "radio" && c.name ? `radio:${c.name}` : c);

  // Label, aria-describedby help text and fieldset legend that belong to the control.
  function relatedElements(el, doc, win) {
    const out = [...(el.labels || [])];
    if (el.id) out.push(...doc.querySelectorAll(`label[for="${win.CSS.escape(el.id)}"]`));
    for (const attr of ["aria-labelledby", "aria-describedby"]) {
      for (const id of (el.getAttribute(attr) || "").split(/\s+/).filter(Boolean)) {
        const node = doc.getElementById(id); if (node) out.push(node);
      }
    }
    const legend = el.closest("fieldset")?.querySelector(":scope > legend"); if (legend) out.push(legend);
    return out.filter(isRendered);
  }

  // Nearest section heading above the control (e.g. "Profile Photograph").
  function nearestHeading(el, doc) {
    const stop = el.closest("form") || doc.body;
    for (let node = el; node && node !== stop && node.parentElement; node = node.parentElement) {
      for (let sib = node.previousElementSibling; sib; sib = sib.previousElementSibling) {
        if (sib.matches(HEADING_SELECTOR) && isRendered(sib)) return sib;
      }
    }
    return null;
  }

  // Works out the smallest sensible area around the control: the control, its
  // label/help, the smallest layout container that holds ONLY this control
  // (e.g. the "photo preview + file input" row), and a nearby section heading,
  // plus EXTRA_PADDING. All values are viewport CSS pixels.
  function contextBox(el, win = window) {
    const doc = el.ownerDocument;
    const field = fromDom(el.getBoundingClientRect());
    const limitW = Math.min(MAX_W, win.innerWidth), limitH = Math.min(MAX_H, win.innerHeight * 0.8);
    const parts = [field, ...relatedElements(el, doc, win).map(n => fromDom(n.getBoundingClientRect()))];

    let container = null;
    for (let node = el.parentElement; node && node !== doc.body && node !== doc.documentElement; node = node.parentElement) {
      if (node.matches("form")) break;
      const r = node.getBoundingClientRect();
      if (r.width > limitW || r.height > limitH) break;
      const keys = new Set([...node.querySelectorAll(CONTROL_SELECTOR)].filter(isRendered).map(controlKey));
      if (keys.size > 1) break;
      container = fromDom(r);
    }
    if (container) parts.push(container);

    let area = union(parts);
    const heading = nearestHeading(el, doc);
    if (heading) {
      // Use the heading's text width, not its full-width border/background box.
      const range = doc.createRange(); range.selectNodeContents(heading);
      const textRect = range.getBoundingClientRect();
      const h = fromDom(textRect.width > 0 && textRect.height > 0 ? textRect : heading.getBoundingClientRect());
      const withHeading = union([area, h]);
      if (area.top - (h.top + h.height) <= HEADING_GAP && withHeading.height <= limitH) area = withHeading;
    }
    const wanted = ensureMin(pad(area, EXTRA_PADDING), MIN_W, MIN_H);
    const box = clamp(wanted, win.innerWidth, win.innerHeight);
    const clipped = !box || box.width < wanted.width - 1 || box.height < wanted.height - 1;
    return { box, field, clipped };
  }

  globalThis.SurakshaMitraGeometry = { EXTRA_PADDING, MIN_W, MIN_H, rect, union, pad, ensureMin, clamp, toPixels, shrinkFactor, contextBox };
})();
