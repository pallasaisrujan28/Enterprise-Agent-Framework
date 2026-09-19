/* Geometry check for the architecture chart.
 *
 * test/test_topology.py pins the DATA — every node has a status and a reason,
 * every edge points at a node that exists. Nothing pinned the PICTURE, and the
 * picture is where the defects were: eight lines routed straight through boxes
 * they had nothing to do with, and three labels stacked on each other so that
 * "pass or refuse" rendered as "ass or refu". A reader does not review a chart
 * for that; they read the line and believe it.
 *
 * So this renders the real payload through the real js/diagram.js and asserts
 * the result geometrically. No packages: plain node, executed by
 * test/test_chart_geometry.py so it runs inside the existing pytest gate.
 *
 * Usage: node test/chart_geometry.mjs <diagram.js> <payload.json>
 * Exits non-zero with one line per violation.
 */

import fs from "node:fs";

const [, , diagramPath, payloadPath] = process.argv;
const src = fs.readFileSync(diagramPath, "utf8");
const payload = JSON.parse(fs.readFileSync(payloadPath, "utf8"));

/* diagram.js expects a global `esc` from js/util.js. Identity is enough: this
 * measures positions, not escaping, and test_topology.py already forbids the
 * characters that would matter. */
const svg = new Function("esc", src + "\nreturn {archSVG};")(String).archSVG(payload);

const failures = [];
const viewBox = /viewBox="0 0 ([\d.]+) ([\d.]+)"/.exec(svg);
const WIDTH = +viewBox[1];
const HEIGHT = +viewBox[2];

/* ── pull the geometry back out of the emitted SVG ───────────────────────── */

const byId = {};
payload.nodes.forEach((n) => (byId[n.id] = n));

const rectMatches = [
  ...svg.matchAll(
    /data-status="[a-z]+"(?: data-emphasis="true")? x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"/g
  )
].map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }));

/* Node groups appear in payload order, so the nth rect belongs to the nth
 * box-shaped node. Diamonds are polygons and are skipped — a diamond is only
 * used for the gate, and its corners are inside the slot a box would occupy. */
const boxes = {};
let cursor = 0;
[...svg.matchAll(/data-node="([a-z_]+)"/g)]
  .map((m) => m[1])
  .forEach((id) => {
    if (byId[id].shape === "box") { boxes[id] = rectMatches[cursor++]; }
  });

const lines = [...svg.matchAll(/class="e-line"[^>]*? d="([^"]+)"/g)].map((m) => m[1]);
const drawnEdges = payload.edges.filter((e) => byId[e.src] && byId[e.dst]);

const labels = [
  ...svg.matchAll(
    /class="e-label-bg" x="([-\d.]+)" y="([-\d.]+)" width="([\d.]+)" height="([\d.]+)"/g
  )
].map((m) => ({ x: +m[1], y: +m[2], w: +m[3], h: +m[4] }));
const labelText = [...svg.matchAll(/class="e-label" x="[-\d.]+" y="[-\d.]+">([^<]*)</g)].map(
  (m) => m[1]
);

if (lines.length !== drawnEdges.length) {
  failures.push(`drew ${lines.length} lines for ${drawnEdges.length} edges`);
}
if (Object.keys(boxes).length !== payload.nodes.filter((n) => n.shape === "box").length) {
  failures.push("box count does not match the payload");
}

/* ── the checks ──────────────────────────────────────────────────────────── */

function points(d) {
  return d.split(/ (?=[ML])/).map((s) => {
    const [x, y] = s.replace(/^[ML]/, "").split(",").map(Number);
    return { x, y };
  });
}

/* 2px inset so a line legitimately touching a face is not a violation; only a
 * line through the interior is. */
const INSET = 2;

function segmentEntersBox(a, b, box) {
  return (
    Math.max(a.x, b.x) > box.x + INSET &&
    Math.min(a.x, b.x) < box.x + box.w - INSET &&
    Math.max(a.y, b.y) > box.y + INSET &&
    Math.min(a.y, b.y) < box.y + box.h - INSET
  );
}

drawnEdges.forEach((edge, i) => {
  const path = points(lines[i]);
  for (let s = 0; s < path.length - 1; s++) {
    Object.keys(boxes).forEach((id) => {
      if (id === edge.src || id === edge.dst) { return; }
      if (segmentEntersBox(path[s], path[s + 1], boxes[id])) {
        failures.push(`${edge.src} -> ${edge.dst} passes through ${id}`);
      }
    });
  }
});

function overlaps(a, b) {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

labels.forEach((label, i) => {
  Object.keys(boxes).forEach((id) => {
    if (overlaps(label, boxes[id])) {
      failures.push(`label "${labelText[i]}" sits on top of ${id}`);
    }
  });
});

for (let i = 0; i < labels.length; i++) {
  for (let j = i + 1; j < labels.length; j++) {
    if (overlaps(labels[i], labels[j])) {
      failures.push(`labels "${labelText[i]}" and "${labelText[j]}" overlap`);
    }
  }
}

/* Anything outside the viewBox is cropped, and a cropped element is invisible
 * rather than obviously wrong. This is how the ops column disappeared. */
function inCanvas(r) {
  return r.x >= 0 && r.y >= 0 && r.x + r.w <= WIDTH && r.y + r.h <= HEIGHT;
}

Object.keys(boxes).forEach((id) => {
  if (!inCanvas(boxes[id])) { failures.push(`${id} is outside the canvas`); }
});
labels.forEach((label, i) => {
  if (!inCanvas(label)) { failures.push(`label "${labelText[i]}" is outside the canvas`); }
});
lines.forEach((d, i) => {
  points(d).forEach((p) => {
    if (p.x < 0 || p.y < 0 || p.x > WIDTH || p.y > HEIGHT) {
      failures.push(`${drawnEdges[i].src} -> ${drawnEdges[i].dst} leaves the canvas`);
    }
  });
});

/* ── report ──────────────────────────────────────────────────────────────── */

if (failures.length) {
  failures.forEach((f) => console.error(f));
  process.exit(1);
}

console.log(
  `ok — ${Object.keys(boxes).length} boxes, ${lines.length} lines, ` +
  `${labels.length} labels on a ${WIDTH}x${HEIGHT} canvas`
);
