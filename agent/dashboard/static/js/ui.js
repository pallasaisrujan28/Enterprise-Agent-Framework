/* UI primitives. Every one returns an HTML string.
 *
 * Views are built from these rather than from hand-written markup, so a change
 * to how a card or a badge looks happens in one place. Keeping the set SMALL is
 * the point — a new primitive is a design decision, not a convenience.
 */

function uiCard(body, options) {
  const opts = options || {};
  const header = opts.title
    ? '<header><h2>' + esc(opts.title) + '</h2>' +
      (opts.action ? '<span>' + opts.action + '</span>' : '') +
      '</header>'
    : '';
  return '<section class="card">' + header + body + '</section>';
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

/* items: [{n, label}] — a view's headline numbers. */
function uiStatBand(items) {
  const cells = items.map(function (item) {
    return '<div><span class="n">' + esc(item.n) + '</span>' +
           '<span class="label">' + esc(item.label) + '</span></div>';
  });
  return '<div class="statband">' + cells.join("") + '</div>';
}

/* columns: [string]; rows: [[cellHtml]] — cells are already-escaped HTML. */
function uiTable(columns, rows, options) {
  const opts = options || {};
  if (!rows.length) {
    return uiNotice("note", esc(opts.empty || "Nothing to show."));
  }
  const head = columns.map(function (c) { return '<th>' + esc(c) + '</th>'; }).join("");
  const body = rows.map(function (row) {
    return '<tr>' + row.join("") + '</tr>';
  }).join("");
  return '<table><thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table>';
}
