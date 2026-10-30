"""Generate the EAF agent internals diagram as .excalidraw (editable) and .svg (preview).

Every node, middleware and tool here was read from the BUILT agent
(create_deep_agent's middleware list, graph nodes and edges) on 2026-10-02,
not from memory. Re-run after changing agent/brain.py:

    python3 scripts/dev/make_agent_internals_diagram.py \
        docs/design/agent-internals.excalidraw docs/design/agent-internals.svg
"""

import json
import random
import sys
from html import escape

OUT_X, OUT_SVG = sys.argv[1], sys.argv[2]
random.seed(11)
W, H = 1960, 1500

C = {
    "entry": ("#1971c2", "#d0ebff"),
    "build": ("#5f3dc4", "#e5dbff"),
    "state": ("#495057", "#f1f3f5"),
    "node": ("#2b8a3e", "#d3f9d8"),
    "gate": ("#e8590c", "#ffe8cc"),
    "loop": ("#0c8599", "#e3fafc"),
    "mw": ("#5c940d", "#f4fce3"),
    "tool": ("#364fc7", "#edf2ff"),
    "defer": ("#862e9c", "#f8f0fc"),
    "ext": ("#495057", "#ffffff"),
    "hitl": ("#c92a2a", "#ffe3e3"),
}
LINE = 17


def h_for(lines, extra=0):
    return 42 + LINE * len(lines) + extra


boxes, zones, arrows = [], [], []


def box(i, x, y, w, kind, title, lines=(), h=None, dashed=False, size=15):
    lines = list(lines)
    boxes.append((i, x, y, w, h or h_for(lines), kind, title, lines, dashed, size))
    return y + (h or h_for(lines))


def zone(i, x, y, w, h, kind, title):
    zones.append((i, x, y, w, h, kind, title))


def arrow(a, b, label="", dashed=False, fs="b", ts="t", via=(), lab=None):
    arrows.append((a, b, label, dashed, fs, ts, list(via), lab))


# ── column 1: entry, build, state, filesystem, subagents ─────────────────────
X1, W1 = 30, 420
zone("z1", X1 - 10, 60, W1 + 20, 1420, "state", "Around the loop")
y = (
    box(
        "entry",
        X1,
        100,
        W1,
        "entry",
        "Entry points",
        [
            "dashboard  POST /api/chat/stream (SSE)",
            "  · new turn: {messages:[user]}",
            "  · Send / Don't send: Command(resume=…)",
            "  · 409 while an action awaits a decision",
            "HTTP service (agent/service.py)",
        ],
    )
    + 30
)
y = (
    box(
        "build",
        X1,
        y,
        W1,
        "build",
        "build_agent()  — once per model, cached",
        [
            "model: Kimi K3 (Bedrock)  fast: Nova Lite",
            "system prompt = soul.md + today's date",
            "  + grounding rules + delegation guidance",
            "  (+ browser rules if AGENT_BROWSER)",
            "create_deep_agent(tools, middleware,",
            "  backend, subagents, skills=['/skills'],",
            "  interrupt_on={send_draft}, checkpointer)",
        ],
    )
    + 30
)
y = (
    box(
        "ckpt",
        X1,
        y,
        W1,
        "state",
        "Checkpointer — SQLite ~/.eaf/checkpoints.sqlite",
        [
            "one row-set per thread_id (= chat session)",
            "state: messages · todos · files (scratch)",
            "  unlocked_tools · recalled_memory",
            "  memory_turns · obligation_verdict",
            "  pending interrupts (HITL)",
        ],
    )
    + 30
)
y = (
    box(
        "fs",
        X1,
        y,
        W1,
        "state",
        "Filesystem — CompositeBackend",
        [
            "/workspace/  → S3 (MinIO locally) — persists",
            "/skills/     → disk: repo skills/ (read)",
            "everything else → StateBackend",
            "  (lives in thread state, per chat)",
            "execute: registered, refuses —",
            "  no sandbox backend, no host shell",
        ],
    )
    + 30
)
box(
    "subs",
    X1,
    y,
    W1,
    "build",
    "Subagents  (via task / eval)",
    [
        "general-purpose: inherits main tools",
        "  + interrupt_on (send still gated)",
        "research: web_search + fetch_url only",
        "browsing: Playwright MCP (AGENT_BROWSER=on)",
        "eval: QuickJS interpreter — task() global,",
        "  read-only PTC: web_search, fetch_url",
    ],
)

# ── column 2: the graph (turn loop) ──────────────────────────────────────────
X2, W2 = 500, 430
zone(
    "z2", X2 - 10, 60, W2 + 20, 1420, "node", "One turn = one graph run (LangGraph nodes, in order)"
)
y = (
    box("n_start", X2, 100, W2, "node", "__start__", ["user message appended to thread"], size=14)
    + 18
)
y = (
    box(
        "n_skills",
        X2,
        y,
        W2,
        "node",
        "SkillsMiddleware.before_agent",
        ["load skill catalogue from /skills (name + 1 line)"],
    )
    + 18
)
y = (
    box(
        "n_patch",
        X2,
        y,
        W2,
        "node",
        "PatchToolCalls.before_agent",
        ["close dangling tool calls from a crash/resume"],
    )
    + 18
)
y = (
    box(
        "n_ib",
        X2,
        y,
        W2,
        "node",
        "CodeInterpreter.before_agent",
        ["start the QuickJS session for eval"],
    )
    + 18
)
y = (
    box(
        "n_mem",
        X2,
        y,
        W2,
        "gate",
        "MEMORY GATE — Memory.before_agent",
        [
            "Nova Lite: does this message need memory?",
            "  no  → skip (log: memory gate: skip)",
            "  yes → Graphiti recall (facts + notes), ≤12 s",
            "  slow → answer without it, flagged",
            "→ state.recalled_memory",
        ],
    )
    + 26
)
loop_top = y
zone(
    "loop", X2, loop_top, W2, 470, "loop", "THE LOOP  (repeats until the model stops calling tools)"
)
y = (
    box(
        "n_model",
        X2 + 20,
        loop_top + 44,
        W2 - 40,
        "loop",
        "model",
        ["one Kimi K3 call, through the", "wrap_model_call stack →"],
    )
    + 16
)
y = (
    box(
        "n_hitl",
        X2 + 20,
        y,
        W2 - 40,
        "hitl",
        "HumanInTheLoop.after_model",
        ["send_draft? → PAUSE (interrupt)", "dashboard shows Send / Don't send"],
    )
    + 16
)
y = (
    box(
        "n_todo",
        X2 + 20,
        y,
        W2 - 40,
        "loop",
        "TodoList.after_model → route",
        ["tool calls → tools   ·   none → exit loop"],
    )
    + 16
)
box(
    "n_tools",
    X2 + 20,
    y,
    W2 - 40,
    "loop",
    "tools",
    ["run each tool call through the", "wrap_tool_call stack → back to model"],
)
y = loop_top + 470 + 26
y = (
    box(
        "n_mema",
        X2,
        y,
        W2,
        "gate",
        "Memory.after_agent — consolidation",
        [
            "quality gate: skip failed/trivial turns",
            "every 3 turns → Graphiti add_episode",
            "  (background, never blocks the reply)",
        ],
    )
    + 18
)
y = (
    box("n_ia", X2, y, W2, "node", "CodeInterpreter.after_agent", ["close the interpreter session"])
    + 18
)
y = (
    box(
        "n_obl",
        X2,
        y,
        W2,
        "gate",
        "EVAL GATE — ObligationGate.after_agent",
        [
            "Nova Lite routes the question to policies",
            "  (obligations/*.yaml, e.g. legislation)",
            "evaluate the final answer: must_cite, …",
            "pass · nothing-to-enforce · unverified · block",
            "block → answer replaced by a refusal",
        ],
    )
    + 18
)
box("n_end", X2, y, W2, "node", "__end__", ["dashboard reads verdict + reply from state"], size=14)

# ── column 3: wrap stacks ────────────────────────────────────────────────────
X3, W3 = 980, 440
zone("z3", X3 - 10, 60, W3 + 20, 1420, "mw", "Middleware wrapped around every call (outer → inner)")
mw = [
    ("Skills", "adds skill catalogue to the prompt"),
    ("Filesystem", "adds ls/read/write/edit/glob/grep prose"),
    ("SubAgent", "adds task tool + subagent roster"),
    ("Summarization", "> 80k tokens: Nova Lite summary, keep 20 msgs"),
    ("TodoList", "write_todos for genuinely multi-step work"),
    ("ContextEditing", "> 40k tokens: clear old tool outputs, keep 4"),
    ("CodeInterpreter", "adds eval (JS) + task() inside code"),
    ("ToolCatalog", "hides deferred tools until find_tools"),
    ("Memory", "injects recalled facts + notes"),
    ("PromptDebug", "prints the prompt if AGENT_DEBUG_PROMPT"),
    ("Prompt caching", "Bedrock / Anthropic cache markers"),
]
y = 100
box("wm_head", X3, y, W3, "mw", "wrap_model_call — each model call", [], h=36)
y += 44
for k, (name, what) in enumerate(mw):
    box(
        f"wm{k}",
        X3 + 10 + k * 3,
        y,
        W3 - 20 - k * 6,
        "mw",
        f"{k + 1}. {name}",
        [what],
        h=52,
        size=14,
    )
    y += 58
y = (
    box(
        "bedrock",
        X3,
        y + 6,
        W3,
        "ext",
        "→ Bedrock Converse: Kimi K3",
        ["system prompt + visible tools + messages"],
    )
    + 30
)
box("wt_head", X3, y, W3, "mw", "wrap_tool_call — each tool call", [], h=36)
y += 44
for k, (name, what) in enumerate(
    [
        ("Filesystem", "route path → backend; big results → files"),
        ("ToolError", "exception → readable error message"),
        ("HumanInTheLoop", "applies Send / Don't send decision"),
    ]
):
    box(
        f"wt{k}",
        X3 + 10 + k * 3,
        y,
        W3 - 20 - k * 6,
        "mw",
        f"{k + 1}. {name}",
        [what],
        h=52,
        size=14,
    )
    y += 58
box(
    "toolrun",
    X3,
    y + 6,
    W3,
    "tool",
    "→ the tool runs",
    ["result → ToolMessage → back to the model"],
)

# ── column 4: tools + external ───────────────────────────────────────────────
X4, W4 = 1470, 460
zone("z4", X4 - 10, 60, W4 + 20, 1420, "tool", "Tools (what the model can call)")
y = (
    box(
        "core",
        X4,
        100,
        W4,
        "tool",
        "Core — always visible (13)",
        [
            "files: ls read_file write_file edit_file",
            "       delete glob grep  (execute refuses)",
            "plan: write_todos      delegate: task, eval",
            "web: searxng_web_search (MCP), fetch_url",
            "find_tools — semantic catalog search",
        ],
    )
    + 24
)
y = (
    box(
        "deferred",
        X4,
        y,
        W4,
        "defer",
        "Deferred — loaded by find_tools",
        [
            "Titan v2 embedding of 'name: description',",
            "cosine + keyword bonus, ≥80% of best,",
            "whole area loads; stays for the thread",
            "email: list_recent_emails read_email",
            "       draft_email send_draft (HITL)",
            "calendar: list_calendar_events",
            "memory: save_note manage_memory",
            "persona: update_soul   skills: create_skill",
        ],
    )
    + 24
)
y = (
    box(
        "skills",
        X4,
        y,
        W4,
        "defer",
        "Skills — progressive disclosure",
        [
            "catalogue (name + 1 line) in every prompt",
            "model read_file('/skills/<name>/SKILL.md')",
            "  only when the task matches",
            "create_skill writes new ones",
        ],
    )
    + 24
)
box(
    "ext",
    X4,
    y,
    W4,
    "ext",
    "External services",
    [
        "Bedrock: Kimi K3 · Nova Lite · Titan v2",
        "Neo4j + Graphiti (long-term memory)",
        "SearXNG (MCP) · Gmail / Calendar API",
        "MinIO (S3 workspace) · Playwright MCP",
        "LangSmith tracing (every call)",
    ],
)

# ── arrows ───────────────────────────────────────────────────────────────────
chain = ["n_start", "n_skills", "n_patch", "n_ib", "n_mem"]
for a, b in zip(chain, chain[1:], strict=False):
    arrow(a, b)
arrow("n_mem", "n_model", "", fs="b", ts="t")
arrow("n_model", "n_hitl")
arrow("n_hitl", "n_todo")
arrow("n_todo", "n_tools", "tool calls")
arrow(
    "n_tools", "n_model", "loop", fs="r", ts="r", via=[(X2 + W2 + 0, 0), (X2 + W2, 0)]
)  # placeholder, fixed below
arrow(
    "n_todo", "n_mema", "no tool calls", fs="l", ts="l", via=[(X2 - 2, 0), (X2 - 2, 0)]
)  # placeholder
for a, b in zip(["n_mema", "n_ia", "n_obl"], ["n_ia", "n_obl", "n_end"], strict=False):
    arrow(a, b)
arrow("entry", "build")
arrow("build", "n_start", "invoke(thread_id)", fs="r", ts="l")
arrow("n_model", "wm_head", "each call", fs="r", ts="l")
arrow("n_tools", "wt_head", "each call", fs="r", ts="l")
arrow("ckpt", "n_start", "", dashed=True, fs="r", ts="l")

geo = {b[0]: b[1:5] for b in boxes}
geo.update({z[0]: z[1:5] for z in zones})


def anchor(i, side):
    x, y, w, h = geo[i]
    return {
        "l": (x, y + h / 2),
        "r": (x + w, y + h / 2),
        "t": (x + w / 2, y),
        "b": (x + w / 2, y + h),
    }[side]


# Real waypoints for the two loop arrows (need final geometry).
mx, my, mw_, mh = geo["n_model"]
tx, ty, tw, th = geo["n_tools"]
dx, dy, dw, dh = geo["n_todo"]
ax, ay, aw, ah = geo["n_mema"]
for k, a in enumerate(arrows):
    if a[0] == "n_tools" and a[1] == "n_model":
        right = X2 + W2 - 6
        arrows[k] = (
            "n_tools",
            "n_model",
            "loop",
            False,
            "r",
            "r",
            [(right, ty + th / 2), (right, my + mh / 2)],
            (right - 40, ty - 6),
        )
    if a[0] == "n_todo" and a[1] == "n_mema":
        left = X2 + 8
        arrows[k] = (
            "n_todo",
            "n_mema",
            "no tool calls",
            False,
            "l",
            "t",
            [(left, dy + dh / 2), (left, ay - 14), (ax + aw / 2, ay - 14)],
            (left + 6, ay - 20),
        )
    if a[0] == "build" and a[1] == "n_start":
        bx, by, bw, bh = geo["build"]
        sx, sy, sw, sh = geo["n_start"]
        arrows[k] = (
            "build",
            "n_start",
            "invoke(thread_id)",
            False,
            "r",
            "l",
            [(470, by + 20), (470, sy + sh / 2)],
            (330, by + 14),
        )
    if a[0] == "ckpt":
        cx, cy, cw, ch = geo["ckpt"]
        sx, sy, sw, sh = geo["n_start"]
        arrows[k] = (
            "ckpt",
            "n_start",
            "load / save state",
            True,
            "r",
            "l",
            [(480, cy + 20), (480, sy + sh / 2 + 10)],
            (300, cy + 14),
        )
    if a[0] == "n_tools" and a[1] == "wt_head":
        wx, wy, ww, wh = geo["wt_head"]
        arrows[k] = (
            "n_tools",
            "wt_head",
            "each tool call",
            False,
            "r",
            "l",
            [(955, ty + th / 2 + 12), (955, wy + wh / 2)],
            (842, ty + th / 2 + 4),
        )
    if a[0] == "n_model" and a[1] == "wm_head":
        wx, wy, ww, wh = geo["wm_head"]
        arrows[k] = (
            "n_model",
            "wm_head",
            "each model call",
            False,
            "r",
            "l",
            [(955, my + mh / 2), (955, wy + wh / 2)],
            (836, my + mh / 2 - 6),
        )


def route(a, b, fs, ts, via):
    (x1, y1), (x2, y2) = anchor(a, fs), anchor(b, ts)
    if via:
        vx, vy = via[0]
        y1 = vy if fs in "lr" else y1
        x1 = vx if fs in "tb" else x1
        lx, ly = via[-1]
        x2 = lx if ts in "tb" else x2
        y2 = ly if ts in "lr" else y2
    return [(x1, y1), *via, (x2, y2)]


# ── excalidraw ───────────────────────────────────────────────────────────────
els = []


def base(i, t, x, y, w, h, stroke, bg, dashed=False):
    return {
        "id": i,
        "type": t,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "angle": 0,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": 2,
        "strokeStyle": "dashed" if dashed else "solid",
        "roughness": 1,
        "opacity": 100,
        "groupIds": [],
        "frameId": None,
        "roundness": {"type": 3} if t == "rectangle" else None,
        "seed": random.randint(1, 2**31),
        "version": 1,
        "versionNonce": random.randint(1, 2**31),
        "isDeleted": False,
        "boundElements": [],
        "updated": 1,
        "link": None,
        "locked": False,
    }


def text(i, x, y, w, s, size, color):
    n = s.count("\n") + 1
    t = base(i, "text", x, y, w, size * 1.25 * n, color, "transparent")
    t.update(
        {
            "text": s,
            "originalText": s,
            "fontSize": size,
            "fontFamily": 1,
            "textAlign": "left",
            "verticalAlign": "top",
            "containerId": None,
            "lineHeight": 1.25,
            "autoResize": True,
        }
    )
    return t


for zid, x, y, w, h, kind, title in zones:
    stroke, bg = C[kind]
    els.append(
        base(
            zid,
            "rectangle",
            x,
            y,
            w,
            h,
            stroke,
            "transparent" if zid != "loop" else bg,
            dashed=True,
        )
    )
    els.append(text(zid + "-t", x + 14, y + 10, w - 28, title, 16, stroke))
for i, x, y, w, h, kind, title, lines, dashed, size in boxes:
    stroke, bg = C[kind]
    els.append(base(i, "rectangle", x, y, w, h, stroke, bg, dashed))
    els.append(text(i + "-t", x + 10, y + 8, w - 20, title, size + 1, stroke))
    if lines:
        els.append(text(i + "-b", x + 10, y + 32, w - 20, "\n".join(lines), 13, "#343a40"))
for n, (a, b, label, dashed, fs, ts, via, lab) in enumerate(arrows):
    pts = route(a, b, fs, ts, via)
    (x1, y1) = pts[0]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ar = base(
        f"a{n}",
        "arrow",
        x1,
        y1,
        max(xs) - min(xs),
        max(ys) - min(ys),
        "#343a40",
        "transparent",
        dashed,
    )
    ar.update(
        {
            "points": [[px - x1, py - y1] for px, py in pts],
            "lastCommittedPoint": None,
            "startBinding": {"elementId": a, "focus": 0, "gap": 4},
            "endBinding": {"elementId": b, "focus": 0, "gap": 4},
            "startArrowhead": None,
            "endArrowhead": "arrow",
            "elbowed": False,
        }
    )
    els.append(ar)
    if label:
        (x2, y2) = pts[-1]
        lx, ly = lab if lab else ((x1 + x2) / 2 + 8, (y1 + y2) / 2 - 8)
        els.append(text(f"a{n}-l", lx, ly - 14, 200, label, 13, "#c2255c"))
title = "EAF agent internals — one turn through the deepagents graph, its middleware, tools, memory and gates"
els.append(text("title", 30, 14, 1800, title, 24, "#212529"))
with open(OUT_X, "w") as f:
    json.dump(
        {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": els,
            "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
            "files": {},
        },
        f,
        indent=1,
    )

# ── svg preview ──────────────────────────────────────────────────────────────
font = "Virgil, 'Comic Sans MS', 'Segoe Print', cursive"
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{font}">',
    '<defs><marker id="ah" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#343a40"/></marker></defs>',
    f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
    f'<text x="30" y="40" font-size="24" fill="#212529">{escape(title)}</text>',
]
for zid, x, y, w, h, kind, ztitle in zones:
    stroke, bg = C[kind]
    fill = bg if zid == "loop" else "none"
    svg.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="2" stroke-dasharray="8 6"/>'
    )
    svg.append(
        f'<text x="{x + 14}" y="{y + 28}" font-size="15" font-weight="bold" fill="{stroke}">{escape(ztitle)}</text>'
    )
for _i, x, y, w, h, kind, btitle, lines, _dashed, size in boxes:
    stroke, bg = C[kind]
    svg.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{bg}" stroke="{stroke}" stroke-width="2"/>'
    )
    svg.append(
        f'<text x="{x + 10}" y="{y + 24}" font-size="{size}" font-weight="bold" fill="{stroke}">{escape(btitle)}</text>'
    )
    for k, line in enumerate(lines):
        svg.append(
            f'<text x="{x + 10}" y="{y + 44 + k * LINE}" font-size="12.5" fill="#343a40" xml:space="preserve">{escape(line)}</text>'
        )
for a, b, label, dashed, fs, ts, via, lab in arrows:
    pts = route(a, b, fs, ts, via)
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    d = ' stroke-dasharray="7 5"' if dashed else ""
    svg.append(
        f'<polyline points="{" ".join(f"{px},{py}" for px, py in pts)}" fill="none" stroke="#343a40" stroke-width="2" marker-end="url(#ah)"{d}/>'
    )
    if label:
        lx, ly = lab if lab else ((x1 + x2) / 2 + 8, (y1 + y2) / 2 - 8)
        svg.append(f'<text x="{lx}" y="{ly}" font-size="13" fill="#c2255c">{escape(label)}</text>')
svg.append("</svg>")
with open(OUT_SVG, "w") as f:
    f.write("\n".join(svg))
print("elements:", len(els))
