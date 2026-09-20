/* Shared helpers and the one global the views read from.
 *
 * Data flows ONE way, and every view depends on it:
 *   refresh()  fetches /api/topology into D
 *   render()   writes VIEWS[hash](D) into #view
 * Any mutation calls refresh() when it is done rather than patching the DOM,
 * so the screen is always a function of server state and cannot drift from it.
 */

/* The last payload fetched. Views read this; nothing else writes it. */
var D = null;

/* Escape anything that came from the server before it goes into innerHTML.
 * Every view builds HTML strings, so this is the only thing standing between a
 * status detail and script injection. Use it on every interpolated value. */
function esc(value) {
  return String(value === null || value === undefined ? "" : value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function getJSON(path) {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(path + " returned " + response.status);
  }
  return response.json();
}

/* The route name, defaulting to overview. Hash routing so the dashboard needs
 * no server-side routes beyond the API and the static files. */
function currentRoute() {
  const hash = (location.hash || "#overview").slice(1);
  return hash.split("?")[0] || "overview";
}
