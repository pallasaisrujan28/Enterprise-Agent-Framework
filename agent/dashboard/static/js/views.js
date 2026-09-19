/* The views, and the router that picks one.
 *
 * VIEWS[route](data) returns the HTML for #view. Adding a screen is a key here.
 */

function overviewView(data) {
  const counts = data.counts;
  const total = data.nodes.length;

  const band = uiStatBand([
    { n: counts.built, label: "built" },
    { n: counts.partial, label: "partial" },
    { n: counts.broken, label: "broken" },
    { n: counts.missing, label: "missing" },
    { n: total, label: "components" }
  ]);

  /* Stated rather than implied. A reader should know that a green box on this
   * chart may be a claim nobody checked. */
  const probed = data.nodes.filter(function (n) { return n.evidence === "probed"; }).length;
  const honesty = uiNotice(
    "note",
    "This chart is rendered from <code>/api/topology</code>, not drawn by hand, so " +
    "a component cannot appear here without a status and a reason. " +
    "<strong>" + esc(probed) + " of " + esc(total) + "</strong> statuses were " +
    "verified at runtime; the rest are claims recorded in " +
    "<code>agent/dashboard/topology.py</code>."
  );

  const chart = uiCard('<div id="chart">' + archSVG(data) + "</div>", {
    title: "Architecture",
    action: uiBadge(data.generated_at + " UTC")
  });

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
    uiTable(["status", "component", "group", "what is actually true"], rows),
    { title: "Components", action: uiBadge("worst first") }
  );

  return "<h1>Overview</h1>" +
    '<p class="subtitle">What exists, what is half-built, and what is only a plan.</p>' +
    band + honesty + chart + table + footerNote();
}

function chatView() {
  return "<h1>Chat</h1>" +
    '<p class="subtitle">Not implemented.</p>' +
    uiNotice(
      "warn",
      "There is no chat endpoint yet. It is tracked as <strong>KAN-9</strong> and needs " +
      "<code>POST /api/chat/stream</code> plus the orchestrator's own entry point — " +
      "this view will call the same path the CLI does, never a private one."
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
