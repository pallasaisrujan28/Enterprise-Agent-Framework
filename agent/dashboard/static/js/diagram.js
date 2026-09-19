/* The architecture chart — the flow of one request, left to right.
 *
 * Nodes declare a grid slot (col, row) in agent/dashboard/topology.py; this file
 * turns slots into pixels, draws the bands around them, routes the edges and
 * labels them. Position is DESIGNED because a flow is a design decision; the
 * node set, the edges and the statuses are still data and still tested, so the
 * chart cannot show a component that does not exist.
 *
 * Read it as four lanes stacked top to bottom: the harness turn, the tool path,
 * memory, then the offline ops loop.
 *
 * HOW EDGES ARE ROUTED, AND WHY IT IS NOT THE OBVIOUS THING
 *
 * An edge between neighbouring rows takes one dogleg through the grid. An edge
 * spanning two or more rows takes a BUS: it leaves through the row gap below (or
 * above) its source, runs sideways into a GUTTER beside the grid, travels
 * vertically there in a lane of its own, comes back along the row gap beside its
 * target, and drops into the target's top or bottom face.
 *
 * Every part of that earns its keep against a simpler version that failed:
 *   - straight through the grid drew the retrieval gate's four memory lines
 *     across the tool-path boxes, which reads as a connection to whatever the
 *     line crosses;
 *   - leaving sideways sent `agent -> usage ledger` through working memory and
 *     the channel, because those share agent's row;
 *   - entering sideways sent the four memory lines through each other's boxes,
 *     since they all approach row 4 from the left at the same height;
 *   - one shared gutter lane stacked eleven lines on top of each other.
 * Entering through the row gap also makes the four memory lines share one
 * horizontal run with four drops off it, which is what a bus should look like.
 *
 * Labels are drawn in a final pass, after the boxes. Drawn alongside the lines
 * they were painted over by boxes laid down afterwards, and a label wider than
 * the gap it sat in lost its ends: "pass or refuse" rendered as "ass or refu".
 * Hence also COL_GAP being wide enough to hold one.
 */

var CELL_W = 170;
var CELL_H = 60;
var COL_GAP = 90;
var ROW_GAP = 40;
var PAD = 22;
var BAND_PAD = 16;
var BAND_LABEL_H = 22;

/* Extra vertical room where one band ends and the next begins, so a band's
 * label never sits on the box above it. Without this the TOOL PATH label was
 * struck through by the harness row. */
var BAND_BREAK = 30;

/* Bus geometry. LANE is the spacing between parallel gutter runs; GUTTER_CLEAR
 * keeps the innermost lane off the band border; RAIL_OFFSET is how far into a
 * row gap a horizontal run sits — under half of ROW_GAP, so a rail is always
 * inside a gap and never on a box. */
var LANE = 16;
var GUTTER_CLEAR = 26;
var RAIL_OFFSET = 18;

/* Lines leaving or entering the same face are nudged apart by this much, so a
 * bus drop does not land exactly on top of a direct edge. */
var DROP_NUDGE = 13;

/* Δrow at which an edge stops going through the grid and takes the bus. */
var LONG_EDGE_SPAN = 2;

/* Same-row edges skipping at least this many columns arc over the top of the
 * band instead of going straight along the row — straight would put them
 * through every box in between. */
var SKIP_COLS = 2;

/* How far above the band an arc sits, and the spacing if there are several. */
var ARC_CLEAR = 12;

/* Row positions are accumulated rather than multiplied, because the gap between
 * two rows depends on whether they belong to the same band.
 *
 * `topReserve` is space held for arcs that pass over the top band; without it
 * the first arc would land at a negative y and be cropped by the viewBox.
 *
 * Assumes each row belongs to exactly one band — pinned by
 * test_bands_own_disjoint_rows in test/test_topology.py, because a shared row
 * would silently make two bands overlap. */
function rowPositions(data, topReserve) {
  const bandOfRow = {};
  data.nodes.forEach(function (node) { bandOfRow[node.row] = node.group; });

  const rows = Object.keys(bandOfRow).map(Number).sort(function (a, b) { return a - b; });
  const y = {};
  let cursor = PAD + BAND_LABEL_H + (topReserve || 0);
  let previousBand = null;

  rows.forEach(function (row) {
    if (previousBand !== null && bandOfRow[row] !== previousBand) {
      cursor += BAND_BREAK + BAND_LABEL_H;
    }
    y[row] = cursor;
    cursor += CELL_H + ROW_GAP;
    previousBand = bandOfRow[row];
  });

  return y;
}

function rowSpan(edge, byId) {
  const from = byId[edge.src], to = byId[edge.dst];
  if (!from || !to) { return 0; }
  return Math.abs(from.row - to.row);
}

function colSpan(edge, byId) {
  const from = byId[edge.src], to = byId[edge.dst];
  if (!from || !to) { return 0; }
  return Math.abs(from.col - to.col);
}

/* Same row, several columns apart — the return line from reply to the channel is
 * the one that matters. Routed over the band, not along the row. */
function isArc(edge, byId) {
  return rowSpan(edge, byId) === 0 && colSpan(edge, byId) >= SKIP_COLS;
}

/* Arcs are numbered so several can stack above each other. */
function assignArcs(data, byId) {
  const arcs = {};
  let next = 0;
  data.edges.forEach(function (e) {
    if (byId[e.src] && byId[e.dst] && isArc(e, byId)) {
      arcs[e.src + ">" + e.dst] = next;
      next += 1;
    }
  });
  return { arcs: arcs, count: next };
}

/* A bus edge travelling a short distance uses the COLUMN GAP beside it rather
 * than the outer gutter. Sending all of them outside worked, but it drew eleven
 * rails the full width of the chart for edges whose endpoints were one column
 * apart, and the outer gutter should be reserved for what genuinely crosses the
 * whole picture: the ops feedback lines. */
var LOCAL_COLS = 2;
var LOCAL_ROWS = 3;

/* A column gap is COL_GAP wide, so it holds a handful of lanes and no more. */
var GAP_LANE_MAX = 4;

function isLocalBus(from, to) {
  return Math.abs(from.col - to.col) <= LOCAL_COLS &&
         Math.abs(from.row - to.row) <= LOCAL_ROWS;
}

/* Give every bus edge a lane of its own — a column gap where it is travelling
 * locally, an outer gutter where it is not.
 *
 * Outer side is whichever needs the shorter reach, measured in columns so it can
 * be decided before layout. When the two are within one column the emptier
 * gutter wins: without that tie-break almost everything chose the left, and a
 * ten-lane gutter is its own kind of unreadable.
 *
 * Short spans are assigned first so they take the inner lanes, which keeps
 * crossings down — a line travelling further already has further to go. */
function planBuses(data, byId, maxCol) {
  const bus = data.edges
    .filter(function (e) {
      return byId[e.src] && byId[e.dst] && rowSpan(e, byId) >= LONG_EDGE_SPAN;
    })
    .sort(function (a, b) { return rowSpan(a, byId) - rowSpan(b, byId); });

  const outer = { left: 0, right: 0 };
  const gapUse = {};
  const plans = {};

  function gapRoom(g) {
    return g >= 0 && g <= maxCol - 1 && (gapUse[g] || 0) < GAP_LANE_MAX;
  }

  bus.forEach(function (e) {
    const from = byId[e.src], to = byId[e.dst];
    const key = e.src + ">" + e.dst;

    if (isLocalBus(from, to)) {
      const right = Math.max(from.col, to.col);
      const left = Math.min(from.col, to.col) - 1;
      let g = null;
      if (gapRoom(right) && gapRoom(left)) {
        g = (gapUse[right] || 0) <= (gapUse[left] || 0) ? right : left;
      } else if (gapRoom(right)) { g = right; }
      else if (gapRoom(left)) { g = left; }

      if (g !== null) {
        plans[key] = { type: "gap", gap: g, lane: gapUse[g] || 0 };
        gapUse[g] = (gapUse[g] || 0) + 1;
        return;
      }
    }

    const leftCost = from.col + to.col;
    const rightCost = (maxCol - from.col) + (maxCol - to.col);
    let side;
    if (Math.abs(leftCost - rightCost) <= 1) {
      side = outer.left <= outer.right ? "left" : "right";
    } else {
      side = leftCost < rightCost ? "left" : "right";
    }
    plans[key] = { type: "outer", side: side, lane: outer[side] };
    outer[side] += 1;
  });

  return { plans: plans, outer: outer, gapUse: gapUse };
}

function place(data, originX, topReserve) {
  const rowY = rowPositions(data, topReserve);
  const at = {};
  data.nodes.forEach(function (node) {
    const x = originX + node.col * (CELL_W + COL_GAP);
    const y = rowY[node.row];
    at[node.id] = {
      node: node, x: x, y: y, w: CELL_W, h: CELL_H,
      cx: x + CELL_W / 2, cy: y + CELL_H / 2
    };
  });
  return at;
}

/* A band is the bounding box of every node that names it, inflated. Computed
 * rather than declared so a node moving cannot leave its band behind. */
function bandBoxes(data, at) {
  return data.bands.map(function (band) {
    const members = data.nodes.filter(function (n) { return n.group === band.id; });
    if (!members.length) { return null; }
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    members.forEach(function (n) {
      const p = at[n.id];
      x1 = Math.min(x1, p.x); y1 = Math.min(y1, p.y);
      x2 = Math.max(x2, p.x + p.w); y2 = Math.max(y2, p.y + p.h);
    });
    return {
      band: band,
      x: x1 - BAND_PAD,
      y: y1 - BAND_PAD - BAND_LABEL_H,
      w: (x2 - x1) + BAND_PAD * 2,
      h: (y2 - y1) + BAND_PAD * 2 + BAND_LABEL_H
    };
  }).filter(Boolean);
}

/* Anchor on the side facing the target, so a line never crosses its own box. */
function anchor(from, to) {
  const dx = to.cx - from.cx;
  const dy = to.cy - from.cy;
  if (Math.abs(dx) >= Math.abs(dy)) {
    return dx >= 0
      ? { x: from.x + from.w, y: from.cy, side: "r" }
      : { x: from.x, y: from.cy, side: "l" };
  }
  return dy >= 0
    ? { x: from.cx, y: from.y + from.h, side: "b" }
    : { x: from.cx, y: from.y, side: "t" };
}

/* Neighbouring rows: one dogleg through the grid. */
function routeDirect(from, to) {
  const a = anchor(from, to);
  const b = anchor(to, from);
  let mid;
  if (a.side === "r" || a.side === "l") {
    mid = a.x + (b.x - a.x) / 2;
    return {
      d: "M" + a.x + "," + a.y + " L" + mid + "," + a.y +
         " L" + mid + "," + b.y + " L" + b.x + "," + b.y,
      lx: mid, ly: (a.y + b.y) / 2
    };
  }
  mid = a.y + (b.y - a.y) / 2;
  return {
    d: "M" + a.x + "," + a.y + " L" + a.x + "," + mid +
       " L" + b.x + "," + mid + " L" + b.x + "," + b.y,
    lx: (a.x + b.x) / 2, ly: mid
  };
}

/* Two or more rows apart: out through the row gap, down the gutter, back in
 * through the row gap, drop into the face. */
function routeBus(from, to, gx, lane) {
  const downward = to.cy > from.cy;
  const nudge = ((lane % 3) - 1) * DROP_NUDGE;

  const exitX = from.cx + nudge;
  const exitY = downward ? from.y + from.h : from.y;
  const exitRail = downward ? exitY + RAIL_OFFSET : exitY - RAIL_OFFSET;

  const dropX = to.cx + nudge;
  const faceY = downward ? to.y : to.y + to.h;
  const enterRail = downward ? faceY - RAIL_OFFSET : faceY + RAIL_OFFSET;

  return {
    d: "M" + exitX + "," + exitY +
       " L" + exitX + "," + exitRail +
       " L" + gx + "," + exitRail +
       " L" + gx + "," + enterRail +
       " L" + dropX + "," + enterRail +
       " L" + dropX + "," + faceY,
    /* On the final drop, clear of the rail it just left. */
    lx: dropX,
    ly: downward ? faceY - 9 : faceY + 9
  };
}

/* Same row, columns apart: up out of the top, over the band, back down. */
function routeArc(from, to, arcY) {
  return {
    d: "M" + from.cx + "," + from.y +
       " L" + from.cx + "," + arcY +
       " L" + to.cx + "," + arcY +
       " L" + to.cx + "," + to.y,
    /* On the arc itself, which is clear of every box by construction. */
    lx: (from.cx + to.cx) / 2,
    ly: arcY
  };
}

function diamond(p) {
  const cx = p.cx, cy = p.cy, rx = p.w / 2, ry = p.h / 2 + 6;
  return [cx + "," + (cy - ry), (cx + rx) + "," + cy,
          cx + "," + (cy + ry), (cx - rx) + "," + cy].join(" ");
}

function fit(text, max) {
  return text.length <= max ? text : text.slice(0, max - 1) + "…";
}

var LABEL_H = 14;

function labelWidth(text) { return text.length * 5.1 + 8; }

function overlaps(a, b) {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

/* Candidate displacements from a label's natural position, in order of
 * preference. Small vertical nudges first, then sideways along the gap the label
 * already sits in — a row gap is only 40px tall, so two labels meeting at the
 * same face cannot both be resolved by moving up and down. */
var LABEL_NUDGES = [
  [0, 0], [0, -11], [0, 11],
  [-58, 0], [58, 0], [-58, -11], [58, 11],
  [0, -22], [0, 22], [-104, 0], [104, 0]
];

/* Shift a label until it clears the boxes and the labels already placed. Small
 * moves only, so it stays attached to its own line: a label that has wandered
 * is worse than one slightly off-centre.
 *
 * Needed because a label's natural position is the middle of its line, and two
 * lines meeting at the same face put their labels in the same few pixels —
 * "emits a call" and "observe" both land under the agent. */
function placeLabels(raw, obstacles) {
  const taken = [];
  const out = [];

  raw.forEach(function (l) {
    const text = fit(l.text, 18);
    const w = labelWidth(text);
    let best = null;

    for (let i = 0; i < LABEL_NUDGES.length; i++) {
      const lx = l.lx + LABEL_NUDGES[i][0];
      const ly = l.ly + LABEL_NUDGES[i][1];
      const box = { x: lx - w / 2, y: ly - 7, w: w, h: LABEL_H };
      const clash = obstacles.some(function (o) { return overlaps(box, o); }) ||
                    taken.some(function (t) { return overlaps(box, t); });
      if (!clash) { best = { lx: lx, ly: ly, box: box }; break; }
    }
    if (!best) {
      best = { lx: l.lx, ly: l.ly, box: { x: l.lx - w / 2, y: l.ly - 7, w: w, h: LABEL_H } };
    }

    taken.push(best.box);
    out.push({ text: text, lx: best.lx, ly: best.ly, w: w });
  });

  return out;
}

function labelSVG(l) {
  const t = esc(l.text);
  return '<rect class="e-label-bg" x="' + (l.lx - l.w / 2) + '" y="' + (l.ly - 7) +
         '" width="' + l.w + '" height="' + LABEL_H + '" rx="3"/>' +
         '<text class="e-label" x="' + l.lx + '" y="' + (l.ly + 4) + '">' + t + '</text>';
}

function archSVG(data) {
  const byId = {};
  data.nodes.forEach(function (n) { byId[n.id] = n; });

  let maxCol = 0;
  data.nodes.forEach(function (n) { maxCol = Math.max(maxCol, n.col); });

  const busted = planBuses(data, byId, maxCol);
  const arced = assignArcs(data, byId);

  /* Reserve the left gutter and the top arcs before placing anything, so
   * nothing lands at a negative coordinate and gets cropped by the viewBox. */
  const leftGutter = busted.outer.left
    ? BAND_PAD + GUTTER_CLEAR + (busted.outer.left - 1) * LANE
    : 0;
  const originX = PAD + leftGutter;
  const topReserve = arced.count
    ? ARC_CLEAR + (arced.count - 1) * LANE + LABEL_H / 2
    : 0;

  const at = place(data, originX, topReserve);
  const bands = bandBoxes(data, at);

  let gridRight = 0, gridBottom = 0;
  Object.keys(at).forEach(function (id) {
    gridRight = Math.max(gridRight, at[id].x + at[id].w);
    gridBottom = Math.max(gridBottom, at[id].y + at[id].h);
  });

  /* Where a bus edge runs vertically: the middle of a column gap, or a lane in
   * one of the outer gutters. Lanes in a gap are centred on it, so a gap with
   * one line has it dead centre. */
  function busX(plan) {
    if (plan.type === "gap") {
      const centre = originX + plan.gap * (CELL_W + COL_GAP) + CELL_W + COL_GAP / 2;
      const used = busted.gapUse[plan.gap];
      return centre + (plan.lane - (used - 1) / 2) * LANE;
    }
    return plan.side === "left"
      ? originX - BAND_PAD - GUTTER_CLEAR - plan.lane * LANE
      : gridRight + BAND_PAD + GUTTER_CLEAR + plan.lane * LANE;
  }

  let width = gridRight + BAND_PAD;
  if (busted.outer.right) {
    width = gridRight + BAND_PAD + GUTTER_CLEAR + (busted.outer.right - 1) * LANE;
  }
  width += PAD;
  let height = gridBottom + BAND_PAD + PAD;
  bands.forEach(function (b) { height = Math.max(height, b.y + b.h + PAD); });

  const parts = [];
  parts.push(
    '<svg viewBox="0 0 ' + width + ' ' + height + '" width="' + width +
    '" height="' + height + '" role="img" aria-label="Architecture">' +
    '<defs><marker id="arrow" viewBox="0 0 8 8" refX="7" refY="4" ' +
    'markerWidth="7" markerHeight="7" orient="auto-start-reverse">' +
    '<path d="M0,0 L8,4 L0,8 z" class="e-head"/></marker></defs>'
  );

  bands.forEach(function (b) {
    parts.push(
      '<rect class="g-box" x="' + b.x + '" y="' + b.y + '" width="' + b.w +
      '" height="' + b.h + '" rx="8"/>' +
      '<text class="g-label" x="' + (b.x + 10) + '" y="' + (b.y + 14) + '">' +
      esc(b.band.label) + (b.band.note ? "  —  " + esc(b.band.note) : "") + '</text>'
    );
  });

  /* Pass 1: the lines. Pass 3 puts the labels back on top of them. */
  const raw = [];
  data.edges.forEach(function (edge) {
    const from = at[edge.src], to = at[edge.dst];
    if (!from || !to) { return; }
    const key = edge.src + ">" + edge.dst;
    const plan = busted.plans[key];
    let r;
    if (plan) {
      r = routeBus(from, to, busX(plan), plan.lane);
    } else if (key in arced.arcs) {
      const bandTop = from.y - BAND_PAD - BAND_LABEL_H;
      r = routeArc(from, to, bandTop - ARC_CLEAR - arced.arcs[key] * LANE);
    } else {
      r = routeDirect(from, to);
    }
    /* Edges routed to an outer gutter are the long-range ones — the offline ops
     * loop, mostly — and they cross the whole picture. Marked so they can be
     * drawn quietly: the eye should find the request path first, and four
     * full-width connectors at full strength is what stops it. */
    const range = plan && plan.type === "outer" ? "far" : "near";
    parts.push(
      '<path class="e-line" data-kind="' + esc(edge.kind) + '" data-range="' + range +
      '" d="' + r.d + '" marker-end="url(#arrow)"/>'
    );
    if (edge.label) { raw.push({ text: edge.label, lx: r.lx, ly: r.ly }); }
  });

  /* Pass 2: the boxes. */
  const obstacles = [];
  data.nodes.forEach(function (node) {
    const p = at[node.id];
    obstacles.push({ x: p.x, y: p.y, w: p.w, h: p.h });
    const shell = node.shape === "diamond"
      ? '<polygon class="n-box" data-status="' + esc(node.status) + '" points="' + diamond(p) + '"/>'
      : '<rect class="n-box" data-status="' + esc(node.status) + '"' +
        (node.emphasis ? ' data-emphasis="true"' : '') +
        ' x="' + p.x + '" y="' + p.y + '" width="' + p.w + '" height="' + p.h + '" rx="6"/>';

    parts.push(
      '<g class="node-group" data-node="' + esc(node.id) + '" tabindex="0" ' +
      'onclick="showNode(\'' + esc(node.id) + '\')" ' +
      'onkeypress="if(event.key===\'Enter\')showNode(\'' + esc(node.id) + '\')">' +
        '<title>' + esc(node.label + " — click for detail") + '</title>' +
        shell +
        '<text class="n-label" x="' + p.cx + '" y="' + (p.y + 25) + '">' +
          esc(fit(node.label, 22)) + '</text>' +
        '<text class="n-caption" x="' + p.cx + '" y="' + (p.y + 42) + '">' +
          esc(fit(node.caption, 26)) + '</text>' +
      '</g>'
    );
  });

  /* Pass 3: the labels, last, so nothing can be painted over them. */
  placeLabels(raw, obstacles).forEach(function (l) { parts.push(labelSVG(l)); });

  parts.push("</svg>");
  return parts.join("");
}
