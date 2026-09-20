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

/* `#chat` used to be a page saying chat did not exist. It exists now, and it is
 * in the dock rather than a page, so this route just points at it — an old
 * bookmark should not land on a blank screen. */
function chatView() {
  return "<h1>Chat</h1>" +
    '<p class="subtitle">The chat is docked on the right, on every page.</p>' +
    uiNotice(
      "note",
      "It sits beside the architecture on purpose: each turn reports which skills " +
      "triggered and what the obligation gate decided, and those are boxes on the " +
      "chart. If the dock is collapsed, the <strong>Chat</strong> button at the " +
      "bottom right reopens it."
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
