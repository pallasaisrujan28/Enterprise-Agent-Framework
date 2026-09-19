/* The views, and the router that picks one.
 *
 * VIEWS[route](data) returns the HTML for #view. Adding a screen is a key here.
 */

/* Which box the reader last clicked. Kept in a global rather than the URL so a
 * refresh does not reopen a panel the reader has moved on from. */
var SELECTED = null;

function showNode(id) {
  SELECTED = SELECTED === id ? null : id;
  render();
}

function detailPanel(data) {
  if (!SELECTED) {
    return '<div id="detail">' + uiNotice(
      "note",
      "Click any box for the full story behind its status."
    ) + "</div>";
  }
  const node = data.nodes.filter(function (n) { return n.id === SELECTED; })[0];
  if (!node) { return ""; }

  const evidence = node.evidence === "probed"
    ? "Checked at runtime."
    : "Recorded claim — nothing verified this automatically.";

  return '<div id="detail">' + uiCard(
    "<p>" + esc(node.detail) + "</p>" +
    '<p class="label">' + esc(evidence) + "</p>",
    {
      title: node.label,
      action: uiBadge(node.status, node.status) + " " + uiBadge(node.group)
    }
  ) + "</div>";
}

function overviewView(data) {
  const counts = data.counts;
  const total = data.nodes.length;
  const probed = data.nodes.filter(function (n) { return n.evidence === "probed"; }).length;

  const band = uiStatBand([
    { n: counts.built, label: "built" },
    { n: counts.partial, label: "partial" },
    { n: counts.broken, label: "broken" },
    { n: counts.missing, label: "missing" },
    { n: probed + "/" + total, label: "verified" }
  ]);

  const chart = uiCard(
    '<div id="chart">' + archSVG(data) + "</div>",
    {
      title: "Architecture — click any box",
      action: uiBadge(data.generated_at + " UTC")
    }
  );

  /* Stated rather than implied: a green box on this chart may be a claim that
   * nothing checked. Saying so is what stops the chart becoming decoration. */
  const honesty = uiNotice(
    "note",
    "Rendered from <code>/api/topology</code> — a component cannot appear here " +
    "without a status and a reason. <strong>" + esc(probed) + " of " + esc(total) +
    "</strong> statuses were verified at runtime; the rest are claims recorded in " +
    "<code>agent/dashboard/topology.py</code>. Dashed boxes are not built yet."
  );

  const order = { broken: 0, partial: 1, missing: 2, built: 3 };
  const rows = data.nodes
    .slice()
    .sort(function (a, b) {
      if (order[a.status] !== order[b.status]) { return order[a.status] - order[b.status]; }
      return a.label.localeCompare(b.label);
    })
    .map(function (node) {
      return [
        "<td>" + uiBadge(node.status, node.status) + "</td>",
        "<td>" + esc(node.label) + "</td>",
        '<td class="label">' + esc(node.group) + "</td>",
        '<td class="detail">' + esc(node.detail) + "</td>"
      ];
    });

  const table = uiCard(
    uiTable(["status", "component", "band", "what is actually true"], rows),
    { title: "Components", action: uiBadge("worst first") }
  );

  return "<h1>Overview</h1>" +
    '<p class="subtitle">Four lanes, top to bottom. The harness runs one turn; ' +
    'the tool path is how a tool gets chosen, narrowed and run; memory is what ' +
    'survives the turn; ops is the offline loop. Faint lines are long-range.</p>' +
    band + honesty + chart + detailPanel(data) + table + footerNote();
}

function chatView() {
  return "<h1>Chat</h1>" +
    '<p class="subtitle">Not implemented.</p>' +
    uiNotice(
      "warn",
      "There is no chat endpoint yet — <strong>KAN-9</strong>. It needs a model behind " +
      "the proxy seam (KAN-11) and credentials through the resolver (KAN-10) first, " +
      "because a chat box streaming a hardcoded reply would be a stub presented as " +
      "working. When it lands it will call the same entry point the CLI uses."
    ) + footerNote();
}

function footerNote() {
  return "<footer>" +
    "Static files are re-read from disk on every request, so a hard reload shows a CSS or JS " +
    "edit. Python is held in memory — after changing <code>agent/dashboard/</code> you must " +
    "restart <code>agent dashboard</code>." +
    "</footer>";
}

var VIEWS = {
  overview: overviewView,
  chat: chatView
};
