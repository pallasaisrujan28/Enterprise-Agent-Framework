# Connectors in the cluster — the web OAuth design (not yet built)

## Why this doc exists

The Google Calendar connector we ship today (`agent/tools/calendar.py`) uses the
**desktop OAuth flow** (`InstalledAppFlow.run_local_server`). That is correct and
sufficient for **local** use: it opens the user's browser, catches the redirect
on `http://localhost:<port>`, and caches the token at `$EAF_HOME/google-token.json`.

It does **not** work in the **cluster** (the Kubernetes deployment in `k8s/`):
a deployed instance is headless (no browser), serves **many users**, and has no
per-user home directory. The desktop flow assumes one user at a machine with a
browser — none of which holds there.

waku does not solve this either: it is explicitly local-first. So this is a
genuinely new piece we build when we deploy multi-user. This doc captures the
design so it is ready.

## What changes: desktop flow → web (authorization-code) flow

| Concern | Local (today) | Cluster (this design) |
|---|---|---|
| OAuth client type | Desktop app | **Web application** |
| Redirect URI | `http://localhost:<random>` | a registered `https://<app>/oauth/google/callback` |
| Who opens the browser | the user's own machine | the user's browser → our web endpoint |
| Where the token lives | `~/.eaf/google-token.json` (file) | **per-user, server-side, encrypted** store |
| How a turn finds the token | read the file | look it up by the authenticated user id |

## The flow (per user, once)

1. User clicks **Connect Google** in the web UI.
2. Backend builds Google's consent URL for the **web** client (`client_id`,
   scope `calendar.events.readonly`, `redirect_uri=https://<app>/oauth/google/callback`,
   plus a signed `state` carrying the user id + CSRF nonce) and redirects the browser to it.
3. User approves on Google.
4. Google redirects the browser back to **our** `/oauth/google/callback?code=…&state=…`.
5. Backend validates `state`, exchanges `code` (+ client secret) for tokens, and
   **stores the refresh token encrypted, keyed by the authenticated user id**.
6. Every later turn for that user loads their token from the store and
   auto-refreshes it — no browser, exactly like the local flow.

## What we must build

1. **Two HTTP endpoints** (on the deployed API, not the desktop dashboard):
   - `GET /oauth/google/start` → 302 to Google's consent URL (with signed `state`).
   - `GET /oauth/google/callback` → validate `state`, exchange code, store token,
     redirect back into the app.
2. **A per-user token store** behind an interface (`get(user)/put(user, token)/delete(user)`):
   - encrypted at rest (KMS/Secrets Manager, or a DB column encrypted with a KMS
     data key). The refresh token is a long-lived credential — never plaintext.
   - keyed by the authenticated user id (we already have auth in `agent/auth/`).
3. **Registered redirect URI + Web OAuth client** in Google Cloud Console, and the
   consent screen **Published** (Testing-mode refresh tokens expire after 7 days).
4. **`calendar.py` token source becomes pluggable**: today it reads a file; in the
   cluster it reads the per-user store. The read/refresh logic is identical — only
   *where the token comes from* changes. Introduce a small `TokenStore` seam:
   - `FileTokenStore` (local, current behaviour)
   - `EncryptedUserTokenStore` (cluster)
   selected by config, so `list_calendar_events` is unchanged.
5. **Connections UI** gains a per-user connected/disconnected state (already have
   the `/api/config` `connectors` shape locally; extend it to be per-session-user).

## Security notes

- Only ever store/serve a **boolean** connected-status to the client, never the
  token (the local `/api/config` already follows this).
- Encrypt the refresh token at rest; scope the KMS key tightly.
- `state` must be signed and single-use (CSRF + bind to the user).
- Read-only scope only, until a write feature is deliberately designed and gated.
- `redirect_uri` must be an exact registered `https` match — Google rejects
  anything else, which is the core anti-phishing check.

## Scope estimate

Two endpoints + a `TokenStore` seam + one encrypted store implementation + the
Google Cloud web-client setup. Isolated from the agent loop — `list_calendar_events`
does not change. Build it as its own task at deploy time; nothing here blocks the
local connector, which is complete.
