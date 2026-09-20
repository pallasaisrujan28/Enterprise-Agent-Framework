/* UI primitives. Every one returns an HTML string.
 *
 * Views are built from these rather than from hand-written markup, so a change
 * to how a card or a badge looks happens in one place. Keeping the set SMALL is
 * the point — a new primitive is a design decision, not a convenience.
 */

/* options: {title, action, cls}. `cls` is appended to the card's class list, for
 * a variant that needs different styling rather than different structure — the
 * chat dock's assistant and refused cards are the only users so far. */
function uiCard(body, options) {
  const opts = options || {};
  const header = opts.title
    ? '<header><h2>' + esc(opts.title) + '</h2>' +
      (opts.action ? '<span>' + opts.action + '</span>' : '') +
      '</header>'
    : '';
  const cls = opts.cls ? ' ' + esc(opts.cls) : '';
  return '<section class="card' + cls + '">' + header + body + '</section>';
}

/* variant is one of the topology's four statuses, or omitted for neutral. */
function uiBadge(text, variant) {
  const attr = variant ? ' data-variant="' + esc(variant) + '"' : '';
  return '<span class="badge"' + attr + '>' + esc(text) + '</span>';
}

/* level: note | ok | warn | failed */
function uiNotice(level, html) {
  return '<div class="notice" data-level="' + esc(level) + '">' + html + '</div>';
}

/* `uiStatBand` and `uiTable` were removed with the overview's stat band and
 * components table. They had no other caller, and an unused primitive is not a
 * primitive — it is dead code that the next person has to read and decide about.
 * Both are three lines to write again from the git history if a view needs them.
 *
 * Note that table STYLING stays in style.css: the chat renders markdown tables,
 * which are real <table> elements built by js/chat.js rather than by a
 * primitive. */
