/* The architecture chart, laid out from /api/topology.
 *
 * NOTHING HERE IS HAND-POSITIONED. Every box and line is computed from the
 * payload, so a component cannot appear on the chart without a status and a
 * reason, and one cannot disappear from the code while staying on the picture.
 * That is the whole reason the topology is data on the server rather than an
 * SVG in this file.
 *
 * Layout is one column per group, left to right, nodes stacked in declaration
 * order. Deliberately simple: a force layout or an edge router would look
 * better and would make the picture non-deterministic, so two loads of the same
 * data could not be compared.
 */

var BOX_W = 196;
var BOX_H = 54;
var BOX_GAP = 12;
var COL_GAP = 52;
var PAD = 16;
var HEADER_H = 26;

/* Where each node's box sits. Keyed by node id, built once per render. */
function layout(data) {
  const byGroup = {};
  data.groups.forEach(function (g) { byGroup[g.id] = []; });
  data.nodes.forEach(function (n) {
    if (byGroup[n.group]) { byGroup[n.group].push(n); }
  });

  const positions = {};
  const columns = [];
  let x = PAD;

  data.groups.forEach(function (group) {
    const nodes = byGroup[group.id];
    let y = PAD + HEADER_H;
    nodes.forEach(function (node) {
      positions[node.id] = { x: x, y: y, node: node };
      y += BOX_H + BOX_GAP;
    });
    columns.push({
      group: group,
      x: x,
      height: y - PAD - BOX_GAP,
      count: nodes.length
    });
    x += BOX_W + COL_GAP;
  });

  return {
    positions: positions,
    columns: columns,
    width: x - COL_GAP + PAD,
    height: Math.max.apply(null, columns.map(function (c) { return c.height; })) + PAD * 2
  };
}

/* An edge leaves the right side of its source and enters the left side of its
 * target, with a mid-way step so parallel lines are distinguishable. When the
 * target is to the LEFT (a feedback path) the line routes below both boxes
 * rather than cutting back through the columns. */
function edgePath(from, to) {
  const x1 = from.x + BOX_W;
  const y1 = from.y + BOX_H / 2;
  const x2 = to.x;
  const y2 = to.y + BOX_H / 2;

  if (x2 > x1) {
    const mid = x1 + (x2 - x1) / 2;
    return "M" + x1 + "," + y1 + " L" + mid + "," + y1 +
           " L" + mid + "," + y2 + " L" + x2 + "," + y2;
  }

  const drop = Math.max(from.y, to.y) + BOX_H + BOX_GAP / 2;
  return "M" + (from.x + BOX_W / 2) + "," + (from.y + BOX_H) +
         " L" + (from.x + BOX_W / 2) + "," + drop +
         " L" + (to.x + BOX_W / 2) + "," + drop +
         " L" + (to.x + BOX_W / 2) + "," + (to.y + BOX_H);
}

/* Fit a label to the box. Truncating in the renderer rather than shortening the
 * source keeps the full text available for the table and the tooltip. */
function fit(text, max) {
  return text.length <= max ? text : text.slice(0, max - 1) + "…";
}

function archSVG(data) {
  const plan = layout(data);
  const parts = [];

  parts.push(
    '<svg viewBox="0 0 ' + plan.width + ' ' + plan.height + '" ' +
    'width="' + plan.width + '" height="' + plan.height + '" ' +
    'role="img" aria-label="Architecture overview">'
  );

  /* group frames first, so boxes and lines draw over them */
  plan.columns.forEach(function (column) {
    if (!column.count) { return; }
    parts.push(
      '<rect class="g-box" x="' + (column.x - 8) + '" y="' + (PAD - 4) + '" ' +
      'width="' + (BOX_W + 16) + '" height="' + (column.height + HEADER_H - 8) + '" rx="6"/>'
    );
    parts.push(
      '<text class="g-label" x="' + column.x + '" y="' + (PAD + 10) + '">' +
      esc(column.group.label) + '</text>'
    );
  });

  /* edges under the boxes */
  data.edges.forEach(function (edge) {
    const from = plan.positions[edge.src];
    const to = plan.positions[edge.dst];
    if (!from || !to) { return; }
    parts.push(
      '<path class="e-line" data-kind="' + esc(edge.kind) + '" ' +
      'd="' + edgePath(from, to) + '"/>'
    );
  });

  /* boxes */
  data.nodes.forEach(function (node) {
    const at = plan.positions[node.id];
    if (!at) { return; }
    parts.push(
      '<g class="node-group" data-node="' + esc(node.id) + '">' +
        '<title>' + esc(node.label + " — " + node.detail) + '</title>' +
        '<rect class="n-box" data-status="' + esc(node.status) + '" ' +
          'x="' + at.x + '" y="' + at.y + '" width="' + BOX_W + '" height="' + BOX_H + '"/>' +
        '<text class="n-label" x="' + (at.x + 10) + '" y="' + (at.y + 21) + '">' +
          esc(fit(node.label, 26)) + '</text>' +
        '<text class="n-status" x="' + (at.x + 10) + '" y="' + (at.y + 39) + '">' +
          esc(node.status + (node.evidence === "probed" ? " · probed" : "")) + '</text>' +
      '</g>'
    );
  });

  parts.push("</svg>");
  return parts.join("");
}
