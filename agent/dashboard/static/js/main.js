/* Bootstrap. Loads LAST — everything below depends on the other files.
 *
 * One way in and one way out:
 *   refresh()  →  D  →  render()  →  #view
 * A failed fetch renders the failure rather than leaving the last good screen
 * up, because a stale dashboard that looks healthy is worse than a blank one.
 */

async function refresh() {
  try {
    D = await getJSON("/api/topology");
  } catch (error) {
    D = null;
    document.getElementById("view").innerHTML =
      "<h1>Overview</h1>" +
      uiNotice("failed", "Could not load <code>/api/topology</code>: " + esc(error.message) +
        ". Is <code>agent dashboard</code> still running?");
    return;
  }
  render();
}

function render() {
  if (!D) { return; }
  const route = currentRoute();
  const view = VIEWS[route] || VIEWS.overview;

  document.getElementById("view").innerHTML = view(D);

  document.querySelectorAll("#nav a").forEach(function (link) {
    const target = link.getAttribute("href").slice(1);
    if (target === route) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

window.addEventListener("hashchange", render);
window.addEventListener("DOMContentLoaded", refresh);
