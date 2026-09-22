/* The chat dock — send a message, watch the turn run.
 *
 * Structure follows waku's dock, which is the part of its UI worth borrowing:
 * chat sits beside whatever page you are on rather than being a page, so a turn
 * can be sent while looking at the architecture it runs through. The transport
 * is the same shape too — a POST that answers with SSE frames, read with
 * fetch + a stream reader, because EventSource can only issue a GET and a
 * message does not belong in a URL.
 *
 * THE ONE RULE THAT MATTERS HERE
 * Streamed text is a DRAFT. The obligation gate has not seen it yet — it cannot
 * have, it needs a finished answer. So the streamed text is labelled as a draft
 * while it arrives, and if the server sends `supersedes_draft` the draft is
 * REPLACED, never appended to. Leaving a refused draft on screen with a refusal
 * underneath it would show the user the exact answer the gate withheld.
 */

/* Every turn in this conversation. The dock is a pure function of this array. */
var CHAT = [];
var SESSION = "default";
var CONFIG = null;

/* The model this conversation uses, or "" for whatever the server defaults to. */
var MODEL_OVERRIDE = "";

/* ── markdown, a deliberately small subset ─────────────────────────────────
 * Escaped FIRST, then patterns applied to the escaped text, so nothing the
 * model emits can become markup. A real markdown library is a dependency and a
 * larger attack surface than the six constructs a chat reply actually uses.
 */
function mdToHtml(text) {
  var html = esc(text);

  /* Restore literal <br> the model emitted. Everything is escaped first, so a
   * model that writes "<br>" for an in-cell line break (they do this constantly
   * inside markdown tables) had it turned into the visible text "&lt;br&gt;".
   * <br> carries no attributes and no XSS, so putting exactly this one tag back
   * is safe, and it is the only raw HTML the model is trusted to have meant. */
  html = html.replace(/&lt;br\s*\/?&gt;/gi, "<br>");

  /* Fenced code before anything else, so its contents are not re-processed. */
  var blocks = [];
  html = html.replace(/```([\s\S]*?)```/g, function (_, code) {
    blocks.push("<pre>" + code.replace(/^\n/, "") + "</pre>");
    return "\u0000BLOCK" + (blocks.length - 1) + "\u0000";
  });

  html = html
    .replace(/`([^`\n]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/^#{1,6}\s+(.+)$/gm, "<h4>$1</h4>");

  html = pipeTables(html);

  /* Lists: consecutive bullet or numbered lines become one list. The model
   * reaches for these constantly, and left alone they render as a wall. */
  html = html.replace(/(?:^[-*]\s+.+$\n?)+/gm, function (chunk) {
    var items = chunk.trim().split("\n").map(function (line) {
      return "<li>" + line.replace(/^[-*]\s+/, "") + "</li>";
    });
    return "<ul>" + items.join("") + "</ul>";
  });
  html = html.replace(/(?:^\d+[.)]\s+.+$\n?)+/gm, function (chunk) {
    var items = chunk.trim().split("\n").map(function (line) {
      return "<li>" + line.replace(/^\d+[.)]\s+/, "") + "</li>";
    });
    return "<ol>" + items.join("") + "</ol>";
  });

  html = html.replace(/\n{2,}/g, "</p><p>").replace(/\n/g, "<br>");
  html = "<p>" + html + "</p>";
  html = html.replace(/\u0000BLOCK(\d+)\u0000/g, function (_, i) { return blocks[+i]; });

  /* Paragraph wrapping happens last and does not know about the block elements
   * built above, so it wraps them: `<p><table>…</table></p>`. A browser silently
   * auto-closes the paragraph, so it renders but the spacing is wrong and the
   * markup is invalid. Unwrap them rather than trying to make the paragraph pass
   * clever enough to avoid it. */
  return html
    .replace(/<p>\s*(<(?:table|ul|ol|pre|h4)[\s\S]*?<\/(?:table|ul|ol|pre|h4)>)\s*<\/p>/g, "$1")
    .replace(/<p>\s*(<(?:table|ul|ol|pre|h4))/g, "$1")
    .replace(/(<\/(?:table|ul|ol|pre|h4)>)\s*<\/p>/g, "$1")
    .replace(/(<\/(?:table|ul|ol|pre|h4)>)\s*<br>/g, "$1")
    .replace(/<p>\s*<\/p>/g, "");
}

/* Pipe tables, because the models reach for them unprompted and a raw one is
 * unreadable in a 400px dock. Requires the |---| separator row, so a line that
 * merely contains a pipe is left alone. */
function pipeTables(html) {
  return html.replace(
    /^\|(.+)\|\n\|[\s|:-]+\|\n((?:\|.*\|\n?)+)/gm,
    function (_, head, body) {
      var cells = function (row) {
        return row.replace(/^\||\|$/g, "").split("|").map(function (c) { return c.trim(); });
      };
      var th = cells(head).map(function (c) { return "<th>" + c + "</th>"; }).join("");
      var rows = body.trim().split("\n").map(function (row) {
        return "<tr>" + cells(row).map(function (c) { return "<td>" + c + "</td>"; }).join("") + "</tr>";
      }).join("");
      return "<table><thead><tr>" + th + "</tr></thead><tbody>" + rows + "</tbody></table>";
    }
  );
}

/* ── rendering one turn ────────────────────────────────────────────────────── */

/* The gate's verdict as a badge. There are four states and they are NOT all
 * "pass" — "nothing-to-enforce" is the common one for ordinary questions and
 * showing it as a green pass would claim a check that never happened. */
function gateBadge(gate) {
  if (!gate) { return uiBadge("gate · pending"); }
  if (gate.decision === "block") { return uiBadge("gate · blocked", "broken"); }
  if (gate.decision === "pass") { return uiBadge("gate · passed", "built"); }
  if (gate.decision === "not-reached") { return uiBadge("gate · not reached", "missing"); }
  /* Deliberately styled as a fault, not as a neutral state. The answer was
   * delivered with NO obligation checked because the router was down — that is
   * a compliance hole, and it must not look like a quiet pass. */
  if (gate.decision === "unverified") { return uiBadge("gate · UNVERIFIED", "broken"); }
  return uiBadge("gate · nothing to enforce", "missing");
}

function skillChips(m) {
  if (!m.skills || !m.skills.length) { return ""; }
  return m.skills.map(function (s) { return uiBadge("skill · " + s, "partial"); }).join(" ");
}

/* The per-turn footer: what it cost and how long it took. Hidden by the stats
 * toggle, because it is diagnostic and not everyone reading wants it. */
function teleFooter(m) {
  if (!m.usage) { return ""; }
  var bits = [
    m.model,
    m.usage.input_tokens + " in / " + m.usage.output_tokens + " out",
    (m.usage.latency_ms / 1000).toFixed(1) + "s"
  ];
  if (m.usage.reasoning_chars) {
    bits.push(m.usage.reasoning_chars + " chars reasoning");
  }
  return '<div class="tele meta">' + esc(bits.join(" · ")) + "</div>";
}

function stageStrip(m) {
  return '<div class="stages">' + gateBadge(m.gate) + " " + skillChips(m) + "</div>" +
    (m.gate && m.gate.reason
      ? '<div class="tele meta gate-reason">' + esc(m.gate.reason) + "</div>"
      : "");
}

/* A turn still running. Shows the stage strip so the gate's pending state is
 * visible, then either the streamed draft or a waiting line. */
function streamingCard(m) {
  var waited = m.started ? Math.round((Date.now() - m.started) / 1000) : 0;
  var body;
  if (m.stream) {
    body = '<div class="draftmark label">draft — the gate has not judged this yet</div>' +
      '<div class="reply">' + mdToHtml(m.stream) + '<span class="caret"></span></div>';
  } else {
    body = '<div class="meta">thinking… ' + waited + "s" +
      (waited > 15
        ? "<br>still waiting. A reasoning model thinks before it writes, so the " +
          "first token can take a while."
        : "") + "</div>";
  }
  return uiCard(stageStrip(m) + body, { cls: "assistant" });
}

function turnCard(m) {
  if (m.error) {
    return uiCard(
      uiNotice("failed", "<strong>" + esc(m.error) + "</strong>" +
        (m.hint ? '<br><span class="label">' + esc(m.hint) + "</span>" : "")),
      { cls: "assistant" }
    );
  }

  var withheld = "";
  if (m.refused && m.draft) {
    /* The refused draft is kept and shown behind a disclosure. A refusal you
     * cannot inspect is unauditable — the point of the gate is that its
     * decisions can be reviewed, which needs the text it decided about. */
    withheld = '<details class="withheld"><summary>what the model actually said (withheld)</summary>' +
      '<div class="reply">' + mdToHtml(m.draft) + "</div></details>";
  }

  return uiCard(
    stageStrip(m) +
    '<div class="reply">' + mdToHtml(m.reply) + "</div>" +
    withheld +
    teleFooter(m),
    { cls: m.refused ? "assistant refused" : "assistant" }
  );
}

function renderChatLog() {
  if (!CHAT.length) {
    return '<div class="chatempty">' +
      "<p>Send a message and watch it run through the harness.</p>" +
      "<p>Every turn reports which skills triggered and what the obligation " +
      "gate decided.</p>" + "</div>";
  }
  return CHAT.map(function (m) {
    if (m.role === "user") { return '<div class="bubble">' + esc(m.text) + "</div>"; }
    return m.pending ? streamingCard(m) : turnCard(m);
  }).join("");
}

function syncChatLog() {
  var el = document.getElementById("chatlog");
  if (!el) { return; }
  el.innerHTML = renderChatLog();
  el.scrollTop = el.scrollHeight;
}

/* ── the stream ────────────────────────────────────────────────────────────── */

/* One server event folded into the live turn. Returns nothing — the caller
 * repaints. Kept separate from the transport so the event contract is readable
 * in one place. */
function applyEvent(pending, ev) {
  if (ev.kind === "start") {
    pending.model = ev.model;
    pending.provider = ev.provider;
    pending.skills = ev.skills || [];
    pending.trigger_reason = ev.trigger_reason;
    return;
  }
  if (ev.kind === "text") {
    pending.stream = (pending.stream || "") + (ev.delta || "");
    return;
  }
  if (ev.kind === "reasoning") {
    /* Counted, not shown. It is the model's scratchpad, it is not the answer,
     * and displaying it as one is how chain-of-thought ends up quoted as fact. */
    pending.reasoning_chars = (pending.reasoning_chars || 0) + (ev.delta || "").length;
    return;
  }
  if (ev.kind === "gate") {
    pending.gate = { decision: ev.decision, reason: ev.reason,
                     blocking: ev.blocking || [], observed: ev.observed || [] };
    return;
  }
  if (ev.kind === "error") {
    pending.pending = false;
    pending.error = ev.error;
    pending.hint = ev.hint;
    pending.stream = "";
    return;
  }
  if (ev.kind === "done") {
    pending.pending = false;
    if (ev.supersedes_draft) { pending.stream = ""; }
    pending.reply = ev.reply;
    pending.draft = ev.draft;
    pending.refused = ev.refused;
    pending.gate = ev.gate;
    pending.usage = ev.usage;
    pending.model = ev.model;
    pending.skills = ev.skills || [];
  }
}

async function sendChat() {
  var input = document.getElementById("chatmsg");
  var text = (input && input.value || "").trim();
  if (!text) { return; }

  /* One turn at a time. Two concurrent turns would interleave into the same
   * session history and the model would see a scrambled conversation. */
  if (CHAT.some(function (m) { return m.pending; })) { return; }

  input.value = "";
  CHAT.push({ role: "user", text: text });
  var pending = { role: "assistant", pending: true, stream: "", started: Date.now() };
  CHAT.push(pending);
  syncChatLog();

  /* Repaint while waiting so the elapsed counter moves. Without it a slow first
   * token is indistinguishable from a hung request. */
  var ticker = setInterval(function () {
    if (pending.pending && !pending.stream) { syncChatLog(); }
  }, 1000);

  try {
    var body = { message: text, session: SESSION };
    if (MODEL_OVERRIDE) { body.model = MODEL_OVERRIDE; }

    var res = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      var detail = await res.json().catch(function () { return {}; });
      throw new Error(detail.error || res.status + " from /api/chat/stream");
    }

    var reader = res.body.getReader();
    var decoder = new TextDecoder();
    var buffer = "";
    for (;;) {
      var step = await reader.read();
      if (step.done) { break; }
      buffer += decoder.decode(step.value, { stream: true });
      /* Frames are separated by a blank line. Anything after the last blank
       * line is a partial frame and stays in the buffer. */
      var cut;
      while ((cut = buffer.indexOf("\n\n")) >= 0) {
        var line = buffer.slice(0, cut);
        buffer = buffer.slice(cut + 2);
        if (line.indexOf("data:") !== 0) { continue; }
        try {
          applyEvent(pending, JSON.parse(line.slice(5).trim()));
        } catch (e) {
          /* A frame we cannot parse is dropped rather than killing the turn. */
        }
        syncChatLog();
      }
    }
  } catch (error) {
    pending.pending = false;
    pending.error = String(error.message || error);
    pending.stream = "";
  }

  clearInterval(ticker);
  /* A stream that ended without a `done` frame — the server died, or the turn
   * was abandoned. Do not leave a spinner running forever. */
  if (pending.pending) {
    pending.pending = false;
    pending.error = "the stream ended before the turn finished";
    pending.hint = "check the terminal running `agent dashboard`";
  }
  syncChatLog();
  if (input) { input.focus(); }
}

/* ── controls ──────────────────────────────────────────────────────────────── */

async function newChat() {
  var res = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "new" })
  }).then(function (r) { return r.json(); }).catch(function () { return {}; });
  if (res.session) { SESSION = res.session; }
  CHAT = [];
  syncChatLog();
}

function toggleStats() {
  var off = localStorage.getItem("eaf_stats") === "0";
  localStorage.setItem("eaf_stats", off ? "1" : "0");
  applyStats();
}

function applyStats() {
  var off = localStorage.getItem("eaf_stats") === "0";
  document.body.classList.toggle("no-stats", off);
  var button = document.getElementById("statstoggle");
  if (button) { button.classList.toggle("on", !off); }
}

function syncModelChip() {
  var chip = document.getElementById("modelchip");
  if (!chip || !CONFIG) { return; }
  var name = MODEL_OVERRIDE || CONFIG.model;
  /* The provider is shown when it is not a real one. An echo reply that looked
   * like a model reply would be the single most misleading thing this UI could
   * do, so it is labelled at the point of choice, not only in the reply. */
  var label = CONFIG.provider === "echo" ? "echo — no model" : name;
  chip.textContent = label + " ▾";
  chip.title = "model: " + name + " · region: " + CONFIG.region +
    " · credentials: " + CONFIG.credential_source;
}

function toggleModelMenu(event) {
  event.stopPropagation();
  var existing = document.getElementById("modelmenu");
  if (existing) { existing.remove(); return; }
  if (!CONFIG) { return; }

  var items = CONFIG.verified_models.map(function (entry) {
    var on = (MODEL_OVERRIDE || CONFIG.model) === entry.id;
    return '<button class="menuitem" onclick="pickModel(\'' + esc(entry.id) + '\')">' +
      (on ? "● " : "○ ") + "<code>" + esc(entry.id) + "</code>" +
      '<span class="label">' + esc(entry.note) +
      (entry.reasoning ? " · thinks first" : "") + "</span></button>";
  }).join("");

  var menu = document.createElement("div");
  menu.id = "modelmenu";
  menu.innerHTML = '<div class="label menuhead">verified on this account</div>' + items;
  document.getElementById("dock").appendChild(menu);
  setTimeout(function () {
    document.addEventListener("click", function once() {
      var m = document.getElementById("modelmenu");
      if (m) { m.remove(); }
      document.removeEventListener("click", once);
    });
  }, 0);
}

function pickModel(id) {
  MODEL_OVERRIDE = id;
  var menu = document.getElementById("modelmenu");
  if (menu) { menu.remove(); }
  syncModelChip();
}

function setDockClosed(closed) {
  document.body.classList.toggle("dock-closed", closed);
  localStorage.setItem("eaf_dock_closed", closed ? "1" : "0");
}

async function wireDock() {
  try {
    CONFIG = await getJSON("/api/config");
  } catch (e) {
    CONFIG = null;
  }
  syncModelChip();

  var send = document.getElementById("chatsend");
  var input = document.getElementById("chatmsg");
  if (send) { send.onclick = function () { sendChat(); }; }
  if (input) {
    input.onkeydown = function (e) { if (e.key === "Enter") { sendChat(); } };
  }

  var close = document.getElementById("dock-close");
  var reopen = document.getElementById("dock-reopen");
  if (close) { close.onclick = function () { setDockClosed(true); }; }
  if (reopen) { reopen.onclick = function () { setDockClosed(false); }; }

  var saved = localStorage.getItem("eaf_dock_closed");
  setDockClosed(saved === null ? window.innerWidth < 1200 : saved === "1");

  applyStats();
  syncChatLog();
}
