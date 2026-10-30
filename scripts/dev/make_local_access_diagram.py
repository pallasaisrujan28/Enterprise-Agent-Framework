"""Generate the local-access design diagram as .excalidraw (editable) and .svg (preview)."""

import json
import random
import sys
from html import escape

OUT_EXCALIDRAW, OUT_SVG = sys.argv[1], sys.argv[2]
random.seed(7)

C = {
    "user": ("#1971c2", "#d0ebff"),
    "agent": ("#5f3dc4", "#e5dbff"),
    "bridge": ("#2b8a3e", "#ebfbee"),
    "step": ("#2b8a3e", "#d3f9d8"),
    "gate": ("#e8590c", "#ffe8cc"),
    "mac": ("#495057", "#f1f3f5"),
    "deny": ("#c92a2a", "#ffe3e3"),
    "untrusted": ("#e67700", "#fff3bf"),
    "note": ("#495057", "#ffffff"),
}

boxes = []  # (id, x, y, w, h, kind, title, lines, dashed)
arrows = []  # (from, to, label, dashed, from_side, to_side)
zones = []  # (id, x, y, w, h, kind, title)


def box(i, x, y, w, h, kind, title, lines=(), dashed=False):
    boxes.append((i, x, y, w, h, kind, title, list(lines), dashed))


def arrow(a, b, label="", dashed=False, fs="r", ts="l", via=(), lab=None):
    arrows.append((a, b, label, dashed, fs, ts, list(via), lab))


# ── layout ───────────────────────────────────────────────────────────────────
box(
    "user",
    40,
    300,
    220,
    150,
    "user",
    "You (dashboard)",
    ["chat request", "Approve / Deny buttons", "Stop switch"],
)
box(
    "agent",
    330,
    300,
    250,
    150,
    "agent",
    "EAF agent (Kimi K3)",
    ["find_tools('local …')", "→ local_* tools", "never sees a shell"],
)
box(
    "untrusted",
    330,
    80,
    250,
    130,
    "untrusted",
    "Untrusted content",
    ["web pages, emails, files,", "screen text = DATA,", "never instructions"],
    dashed=True,
)

zones.append(
    (
        "bridgezone",
        650,
        60,
        640,
        700,
        "bridge",
        "EAF Local Bridge — separate signed app, owns the macOS permissions",
    )
)
box(
    "s1",
    680,
    120,
    270,
    90,
    "step",
    "1  Schema check",
    ["typed capability, not a shell", "unknown verb → reject"],
)
box(
    "s2",
    990,
    120,
    270,
    90,
    "step",
    "2  Normalise target",
    ["realpath, resolve symlinks,", "bundle id, argv (no strings)"],
)
box(
    "s3",
    680,
    250,
    580,
    120,
    "gate",
    "3  Policy engine (deterministic code, not the model)",
    [
        "deny list first → allow lists (apps by bundle id, folder roots, commands)",
        "risk tier: 0 read · 1 reversible · 2 consequential · 3 destructive/system",
        "rate + blast-radius limits; tainted session (read untrusted) raises tier",
    ],
)
box(
    "s4",
    680,
    410,
    270,
    110,
    "gate",
    "4  Approval gate",
    ["tier ≥ 2 → pause (HITL)", "exact preview: app, paths,", "argv, file count"],
)
box(
    "s5",
    990,
    410,
    270,
    110,
    "step",
    "5  Executor",
    [
        "exec argv (no shell), timeout,",
        "scrubbed env, workspace cwd,",
        "sandbox profile: no network",
    ],
)
box(
    "s6",
    680,
    560,
    270,
    90,
    "step",
    "6  Output filter",
    ["size cap, redact secrets,", "wrap as <untrusted>"],
)
box(
    "audit",
    990,
    560,
    270,
    90,
    "note",
    "Audit log (append-only)",
    ["every request, decision and", "result · ~/.eaf/local-audit.jsonl"],
)
box(
    "unix",
    680,
    690,
    580,
    50,
    "note",
    "Unix socket ~/.eaf/bridge.sock (0600) + session token · no TCP port",
    [],
)

box(
    "mac",
    1360,
    250,
    260,
    270,
    "mac",
    "macOS",
    [
        "LaunchServices: open / quit",
        "Apple Events (allow-listed",
        "  app + verb templates)",
        "Accessibility tree: read,",
        "  press, set value",
        "Files in allowed roots",
        "Trash (never empty it)",
    ],
)
box(
    "deny",
    1360,
    560,
    260,
    200,
    "deny",
    "Never (hard deny)",
    [
        "sudo, installers (.pkg), brew",
        "~/.ssh, Keychain, browser",
        "  cookies/passwords, TCC.db",
        "LaunchAgents, login items, cron",
        "spctl/csrutil/tccutil, EDR, MDM",
        "curl | sh, chmod +x downloads",
        "rm -rf, empty Trash, kill -9",
    ],
)
box(
    "legend",
    40,
    800,
    1580,
    200,
    "note",
    "Risk tiers → what happens   (agent cannot edit policy: ~/.eaf/policy.yaml is hard-denied · kill switch: Stop button / `agent local off`)",
    [
        "0 read: list apps, read UI tree, read allowed files → allow, log",
        "1 reversible: open/activate app, polite quit, move to Trash (1 file),",
        "   create file in workspace → allow, log",
        "2 consequential: type/submit in an app, move/rename many files,",
        "   run an allow-listed command → ASK (Approve / Deny)",
        "3 destructive/system: anything on the hard-deny list → BLOCK",
    ],
)

arrow("user", "agent", "ask")
arrow("untrusted", "agent", "read by tools", dashed=True, fs="b", ts="t")
arrow("agent", "s1", "MCP call", fs="r", ts="l", lab=(540, 292))
arrow("s1", "s2")
arrow("s2", "s3", "", fs="b", ts="t")
arrow("s3", "s4", "tier 2", fs="b", ts="t")
arrow("s3", "s5", "tier 0-1", fs="b", ts="t")
arrow("s4", "s5", "yes", lab=(958, 456))
arrow(
    "s4", "user", "Approve / Deny (exact preview)", fs="l", ts="b", via=[(150, 465)], lab=(170, 486)
)
arrow(
    "s3",
    "deny",
    "tier 3 → blocked",
    dashed=True,
    fs="r",
    ts="r",
    via=[(1330, 265), (1330, 232), (1645, 232), (1645, 660)],
    lab=(1350, 226),
)
arrow("s5", "mac", "")
arrow(
    "mac",
    "s6",
    "raw result",
    fs="b",
    ts="r",
    via=[(1390, 540), (965, 540), (965, 605)],
    lab=(1180, 534),
)
arrow("s6", "agent", "untrusted result", fs="l", ts="b", via=[(520, 605)], lab=(530, 597))

# ── geometry helpers ─────────────────────────────────────────────────────────
geo = {b[0]: b[1:5] for b in boxes}


def anchor(i, side):
    x, y, w, h = geo[i]
    return {
        "l": (x, y + h / 2),
        "r": (x + w, y + h / 2),
        "t": (x + w / 2, y),
        "b": (x + w / 2, y + h),
    }[side]


# ── excalidraw ───────────────────────────────────────────────────────────────
els = []


def base(kind_id, t, x, y, w, h, stroke, bg, dashed=False):
    return {
        "id": kind_id,
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


def text(i, x, y, w, s, size, color, align="left"):
    lines = s.split("\n")
    t = base(i, "text", x, y, w, size * 1.25 * len(lines), color, "transparent")
    t.update(
        {
            "text": s,
            "originalText": s,
            "fontSize": size,
            "fontFamily": 1,
            "textAlign": align,
            "verticalAlign": "top",
            "containerId": None,
            "lineHeight": 1.25,
            "autoResize": True,
        }
    )
    return t


for zid, x, y, w, h, kind, title in zones:
    stroke, bg = C[kind]
    z = base(zid, "rectangle", x, y, w, h, stroke, "transparent", dashed=True)
    els.append(z)
    els.append(text(zid + "-t", x + 16, y + 14, w - 32, title, 18, stroke))

for i, x, y, w, h, kind, title, lines, dashed in boxes:
    stroke, bg = C[kind]
    els.append(base(i, "rectangle", x, y, w, h, stroke, bg, dashed))
    els.append(text(i + "-t", x + 12, y + 10, w - 24, title, 17, stroke))
    if lines:
        els.append(text(i + "-b", x + 12, y + 36, w - 24, "\n".join(lines), 14, "#343a40"))


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


for n, (a, b, label, dashed, fs, ts, via, lab) in enumerate(arrows):
    pts = route(a, b, fs, ts, via)
    (x1, y1), (x2, y2) = pts[0], pts[-1]
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
        lx, ly = lab if lab else ((x1 + x2) / 2 + 6, (y1 + y2) / 2 - 20)
        els.append(text(f"a{n}-l", lx, ly - 14 if lab else ly, 260, label, 13, "#c2255c"))

els.append(
    text(
        "title",
        40,
        10,
        1500,
        "EAF local-system access — how a command runs and where malware-style actions are stopped",
        24,
        "#212529",
    )
)
doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "https://excalidraw.com",
    "elements": els,
    "appState": {"viewBackgroundColor": "#ffffff", "gridSize": None},
    "files": {},
}
with open(OUT_EXCALIDRAW, "w") as f:
    json.dump(doc, f, indent=1)

# ── svg preview (same layout) ────────────────────────────────────────────────
W, H = 1680, 1030
font = "Virgil, 'Comic Sans MS', 'Segoe Print', cursive"
svg = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{font}">',
    '<defs><marker id="ah" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto"><path d="M0,0 L10,4 L0,8 z" fill="#343a40"/></marker></defs>',
    f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
    f'<text x="40" y="36" font-size="22" fill="#212529">{escape(els[-1]["text"])}</text>',
]
for _zid, x, y, w, h, kind, title in zones:
    stroke, _ = C[kind]
    svg.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="none" stroke="{stroke}" stroke-width="2" stroke-dasharray="8 6"/>'
    )
    svg.append(
        f'<text x="{x + 16}" y="{y + 30}" font-size="16" fill="{stroke}">{escape(title)}</text>'
    )
for _i, x, y, w, h, kind, title, lines, dashed in boxes:
    stroke, bg = C[kind]
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    svg.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{bg}" stroke="{stroke}" stroke-width="2"{dash}/>'
    )
    svg.append(
        f'<text x="{x + 12}" y="{y + 26}" font-size="16" font-weight="bold" fill="{stroke}">{escape(title)}</text>'
    )
    for k, line in enumerate(lines):
        svg.append(
            f'<text x="{x + 12}" y="{y + 50 + k * 18}" font-size="13" fill="#343a40" xml:space="preserve">{escape(line)}</text>'
        )
for a, b, label, dashed, fs, ts, via, lab in arrows:
    pts = route(a, b, fs, ts, via)
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    path = " ".join(f"{px},{py}" for px, py in pts)
    svg.append(
        f'<polyline points="{path}" fill="none" stroke="#343a40" stroke-width="2" marker-end="url(#ah)"{dash}/>'
    )
    if label:
        mx, my = lab if lab else ((x1 + x2) / 2 + 6, (y1 + y2) / 2 - 6)
        svg.append(f'<text x="{mx}" y="{my}" font-size="13" fill="#c2255c">{escape(label)}</text>')
svg.append("</svg>")
with open(OUT_SVG, "w") as f:
    f.write("\n".join(svg))
print("elements:", len(els))
