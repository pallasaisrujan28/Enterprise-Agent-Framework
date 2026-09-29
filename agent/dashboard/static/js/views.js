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

/* The memory view — the durable graph Graphiti has learned. A read-only window
 * onto facts (semantic), episodes (episodic), and entities. It fetches its own
 * data (unlike the overview, which is a pure function of the topology payload),
 * so the view returns a shell and fills it once /api/memory answers. */
function memoryView() {
  setTimeout(loadMemory, 0);
  return "<h1>Memory</h1>" +
    '<p class="subtitle">Durable, self-updating memory — the facts and episodes ' +
    "the agent has learned from your conversations, held in a temporal knowledge " +
    "graph.</p>" +
    '<div id="memorybody">' + uiNotice("note", "loading memory…") + "</div>";
}

async function loadMemory() {
  var body = document.getElementById("memorybody");
  if (!body) { return; }
  try {
    var m = await getJSON("/api/memory");
    body.innerHTML = renderMemory(m);
  } catch (e) {
    body.innerHTML = uiNotice("failed", "Could not load <code>/api/memory</code>: " + esc(e.message));
  }
}

function renderMemory(m) {
  if (!m.enabled) {
    return uiNotice(
      "note",
      "Memory is off. Start the server with <code>AGENT_MEMORY=on</code> (and the " +
      "<code>neo4j</code> container running) to enable durable memory."
    );
  }
  if (m.error) {
    return uiNotice("failed", "Memory backend error: " + esc(m.error));
  }

  var facts = m.facts || [], eps = m.episodes || [], ents = m.entities || [];

  var factList = facts.length
    ? "<ul class='memlist'>" + facts.map(function (f) {
        var superseded = f.invalid_at
          ? " " + uiBadge("superseded", "partial")
          : "";
        var link = esc(f.source || "?") + " &rarr; " + esc(f.target || "?");
        return "<li><span class='memfact'>" + esc(f.fact || "") + "</span>" + superseded +
          "<span class='tele meta'>" + link + "</span></li>";
      }).join("") + "</ul>"
    : "<p class='label'>No facts yet — chat with the agent and they accumulate.</p>";

  var epList = eps.length
    ? "<ul class='memlist'>" + eps.map(function (e) {
        var when = e.at ? "<span class='tele meta'>" + esc(String(e.at).slice(0, 19)) + "</span>" : "";
        var body = esc((e.content || "").slice(0, 200));
        return "<li><strong>" + esc(e.name || "episode") + "</strong> " + when +
          "<br><span class='label'>" + body + "</span></li>";
      }).join("") + "</ul>"
    : "<p class='label'>No episodes yet.</p>";

  var entList = ents.length
    ? "<ul class='memlist'>" + ents.map(function (n) {
        return "<li><strong>" + esc(n.name || "") + "</strong>" +
          (n.summary ? " — <span class='label'>" + esc(n.summary) + "</span>" : "") + "</li>";
      }).join("") + "</ul>"
    : "<p class='label'>No entities yet.</p>";

  return uiCard(factList, { title: "Facts — semantic memory", action: uiBadge(facts.length + " edges") }) +
    uiCard(epList, { title: "Episodes — episodic memory", action: uiBadge(eps.length) }) +
    uiCard(entList, { title: "Entities", action: uiBadge(ents.length) });
}

/* Connections — external accounts the agent can read from. Sign in ONCE; the
 * token is cached (owner-only) and auto-refreshes, so this is not a per-turn
 * prompt. Status comes from /api/config (a boolean per connector, never a
 * token); the Connect button runs the one-time OAuth flow, which only works on
 * the local dashboard (a deployed instance needs the web OAuth connector). */
function connectionsView() {
  setTimeout(loadConnections, 0);
  return "<h1>Connections</h1>" +
    '<p class="subtitle">External accounts the agent can read from. Sign in once — ' +
    "the token is cached and refreshes itself, so you are not asked again.</p>" +
    '<div id="connbody">' + uiNotice("note", "loading…") + "</div>";
}

async function loadConnections() {
  var body = document.getElementById("connbody");
  if (!body) { return; }
  try {
    var c = await getJSON("/api/config");
    body.innerHTML = renderConnections((c && c.connectors) || {});
    setTimeout(wireConnect, 0);
  } catch (e) {
    body.innerHTML = uiNotice("failed", "Could not load <code>/api/config</code>: " + esc(e.message));
  }
}

function renderConnections(conn) {
  var connected = !!conn.google_calendar || !!conn.gmail;
  var status = connected ? uiBadge("connected", "ok") : uiBadge("not connected", "partial");
  var body = connected
    ? "<p class='label'>Connected (read-only). One sign-in covers both — ask me " +
      "\u201cwhat meetings do I have today?\u201d or \u201cany unread email from X?\u201d</p>"
    : "<button id='connect-gcal' class='btn'>Connect Google</button>" +
      "<p class='label'>One sign-in grants read access to your Calendar and Gmail. " +
      "Opens your browser; local dashboard only, and needs a Desktop OAuth client " +
      "saved at <code>$EAF_HOME/credentials.json</code>.</p>";
  return uiCard(body, { title: "Google (Calendar + Gmail)", action: status });
}

function wireConnect() {
  var b = document.getElementById("connect-gcal");
  if (!b) { return; }
  b.onclick = async function () {
    b.disabled = true;
    b.textContent = "Opening browser…";
    try {
      var r = await fetch("/api/connect/google", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}"
      });
      var j = await r.json();
      alert(j.message || j.error || "done");
    } catch (e) {
      alert("Connect failed: " + e.message);
    }
    loadConnections();
  };
}

var VIEWS = {
  overview: overviewView,
  chat: chatView,
  memory: memoryView,
  connections: connectionsView
};
