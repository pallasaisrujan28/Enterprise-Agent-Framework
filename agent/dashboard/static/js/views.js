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

/* The overview is the CHART, and nothing else.
 *
 * It used to carry a stat band, a paragraph explaining where the data came from,
 * and a table repeating every node's detail underneath. Each was defensible on
 * its own and together they buried the one thing the page is for — you had to
 * scroll past three blocks of prose to reach the diagram, and then past the
 * diagram to find a table saying the same thing in words.
 *
 * The information is not lost: every node's full detail is one click away in the
 * panel below the chart, which is where it is actually wanted — next to the box
 * you are asking about, not in a list of twenty-two.
 */
function overviewView(data) {
  const chart = uiCard(
    '<div id="chart">' + archSVG(data) + "</div>",
    {
      title: "Architecture — click any box",
      action: uiBadge(data.generated_at + " UTC")
    }
  );

  return "<h1>Overview</h1>" + chart + detailPanel(data);
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
    );
}

var VIEWS = {
  overview: overviewView,
  chat: chatView
};
