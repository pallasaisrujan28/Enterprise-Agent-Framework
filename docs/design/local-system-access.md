# Design: local-system access for the EAF agent

Status: proposal. Diagram: [`local-system-access.excalidraw`](local-system-access.excalidraw) (open in excalidraw.com or the VS Code Excalidraw extension). The SVG is a preview of the same layout. Background on how macOS installs, opens, drives, closes and deletes apps: [`../references/macos-local-system.md`](../references/macos-local-system.md).

## Goal

Let the agent work on this Mac (open and quit apps, find and read files, tidy folders, drive an app's UI, run a few known commands) without ever being able to act like malware: no data theft, no persistence, no destruction, no disabling security. That holds even when a web page or email it reads tells it to.

## Principles

1. **The model proposes; code decides.** Every local action is checked by a deterministic policy engine that the model can't edit, bypass or talk its way past. Prompt rules are a courtesy, not the control.
2. **Capabilities, not a shell.** The agent gets typed verbs (`apps.open(bundle_id)`, `files.move_to_trash(path)`). There's no tool that takes a free-text shell command, and deepagents' `execute` stays off the host.
3. **Permissions live in one place.** A separate, signed helper app (the *Local Bridge*) holds the macOS permissions. Kiro, Terminal and Python never get Accessibility or Full Disk Access, because macOS grants permissions to the launching app and everything it runs.
4. **Default deny.** Apps by bundle id, folders by root, commands by exact name. Anything not listed is refused.
5. **Reversible by default, human for the rest.** Reads and undoable actions run automatically and are logged. Consequential actions pause for an Approve / Deny decision showing exactly what will happen, using the same mechanism as Gmail's Send button. Destructive or system-level actions don't exist as options.
6. **Everything is recorded.** Every request, decision and result goes to an append-only audit log the dashboard can show.

## Components

| Component | What it is | Why |
|---|---|---|
| `local_*` tools | Thin MCP-client tools in the agent, deferred in the tool catalog (area: "this Mac") | The agent loads them only when a task needs them |
| Local Bridge | A separate process in its own signed `.app`, running as you. Listens on a Unix socket `~/.eaf/bridge.sock` (mode 0600) with a per-session token. No TCP port | Keeps permissions narrow and revocable in one place. Not reachable from the network or other users |
| Policy engine | Code inside the bridge. Reads `~/.eaf/policy.yaml` (owned by you, on the bridge's own deny list) | The rules can't be changed by the agent |
| Approval gate | Bridge returns `needs_approval` with a preview; the agent tool raises a HumanInTheLoop interrupt; the dashboard shows Approve / Deny | The decision is a button, enforced by the graph |
| Executor | `posix_spawn` with an argv array, never `sh -c`. Scrubbed environment, workspace cwd, timeout, output cap, own process group, `sandbox-exec` profile without network for commands | A command runs exactly as listed, can't reach the network, and can't hang |
| Output filter | Caps size, redacts secrets (key/token patterns), wraps results in `<untrusted>` | Results going back to the model are data, not instructions |
| Audit log | `~/.eaf/local-audit.jsonl`, append-only, each line hashed with the previous one | Tamper-evident record for the dashboard and for you |
| Kill switch | Stop button in the dashboard, plus `agent local off`. Creates `~/.eaf/local.disabled`; the bridge refuses everything while it exists | One action stops all local access immediately |

## How one command executes

Example: *"Move last month's invoices from Downloads into Documents/Invoices."*

1. **Discover.** The agent calls `find_tools("files on my Mac")`, and the catalog loads `local_files_*`.
2. **Propose.** The agent calls `local_files_list(root="~/Downloads", glob="*invoice*.pdf", modified_after=…)`, then `local_files_move(paths=[…], dest="~/Documents/Invoices")`.
3. **Transport.** The tool sends JSON over the Unix socket with the session token. The bridge rejects anything that isn't a known verb with valid fields (step 1, schema check).
4. **Normalise** (step 2). Every path goes through `realpath`, so symlinks and `..` are resolved before checking. Apps are identified by bundle id, not display name. Commands become argv arrays.
5. **Policy** (step 3):
   1. The **hard-deny list** comes first (see below). If anything matches, the request is blocked at tier 3 and logged.
   2. **Allow lists**: are both paths inside an allowed root, and is the app on the list?
   3. **Risk tier.** Moving 1 file is tier 1. Moving 2 or more, or more than 50 MB, is tier 2.
   4. **Taint.** If this session has read untrusted content (web, email, a file's contents) since your last message, the tier is raised by one for anything that writes, sends or runs.
   5. **Rate limit.** More than 30 actions a minute, or more than 100 files touched per task, means a pause and a request for approval.
6. **Approve** (step 4, tier 2). The bridge returns the exact plan ("Move 12 files, 4.3 MB, from ~/Downloads to ~/Documents/Invoices", with the file list). The agent's tool raises an interrupt, and the dashboard shows **Approve / Deny**. Deny returns "the user declined" to the model.
7. **Execute** (step 5). The bridge performs the move itself through the file APIs. For an allowed command, it spawns the argv under the sandbox profile with a timeout. For apps, it uses LaunchServices, a polite Apple Events quit, or Accessibility actions.
8. **Return** (step 6). The result is capped, redacted and wrapped as `<untrusted>`, then logged and sent back to the agent.

## Risk tiers

| Tier | Examples | What happens |
|---|---|---|
| 0 read | List running apps, read the frontmost app's UI tree, list or read files in allowed roots, file metadata | Allowed, logged |
| 1 reversible | Open or activate an app, polite quit (Apple Events `quit`, so the app can ask to save), create a file in the workspace, move **one** file to Trash | Allowed, logged |
| 2 consequential | Type or submit in another app, press a button that sends or saves, move or rename many files, run an allowed command, open a file the browser downloaded | **Approve / Deny** with an exact preview |
| 3 destructive/system | Everything on the hard-deny list | **Blocked.** Not offered, not approvable |

## Stopping malware-style behaviour

| Threat | What the attacker wants | Control |
|---|---|---|
| Destruction / ransomware | Delete or encrypt many files | No delete verb, only Trash (recoverable). The bridge never empties the Trash. Blast-radius limits (files and bytes per task). Writes only inside allowed roots. Bulk operations need approval |
| Credential theft | `~/.ssh`, Keychain, browser cookies and passwords, `~/.aws`, `~/.eaf` tokens, `.env` | Hard-denied paths, checked after `realpath`. Secret patterns redacted in output. The bridge doesn't request Full Disk Access |
| Exfiltration | Send data out | Commands run with no network (sandbox profile). No `curl`/`nc`/`scp` on the allow list. Email sends already need the Send button. Results are capped |
| Persistence | Survive reboot | Hard-deny writes to `~/Library/LaunchAgents`, `/Library/Launch*`, login and background items, cron, shell rc files (`.zshrc`, `.zprofile`) |
| Privilege escalation | Become root | No `sudo`, no `osascript … with administrator privileges`, no installers (`.pkg`, `brew`, `installer`) |
| Disabling defences | Turn off protection | Hard-deny `spctl`, `csrutil`, `tccutil`, `defaults write` on security domains, `profiles`, `launchctl` unload, killing EDR or MDM processes, editing `policy.yaml` or `local.disabled` |
| Running downloaded code | Execute a payload | No `chmod +x`. Opening a quarantined download is tier 2. Shell pipelines (`curl … \| sh`) aren't possible because there's no shell |
| Prompt injection | Content steering the agent | Taint raises the tier, so injected instructions can at most make the agent *ask* you. The policy is outside the model's reach. Untrusted output is marked as such |
| UI abuse | Silent clicks in other apps | Accessibility only on allowed apps (by bundle id). Typing and submitting is tier 2. Synthetic input (CGEvent) isn't offered in v1 |
| Runaway agent | Loops, floods | Rate limits, per-command timeouts, a step budget per task, and the kill switch |

### The hard-deny list (v1)

- **Paths:** `~/.ssh`, `~/.gnupg`, `~/.aws`, `~/.eaf` (except the workspace), `~/Library/Keychains`, `~/Library/Application Support/{Google/Chrome,BraveSoftware,Firefox}/**/{Cookies,Login Data}*`, `~/Library/Cookies`, `~/Library/Application Support/com.apple.TCC`, `~/Library/LaunchAgents`, `/Library`, `/System`, `/usr`, `/private`, `/etc`, shell rc files, any `.env`.
- **Programs and verbs:** `sudo`, `su`, `installer`, `brew`, `pip install` (outside the workspace venv), `spctl`, `csrutil`, `tccutil`, `profiles`, `launchctl`, `crontab`, `osascript` with free text, `chmod`, `chown`, `kill -9` / force quit, `rm`, emptying the Trash, `diskutil`, `networksetup`.

## What v1 offers

| Area | Verbs | Tier |
|---|---|---|
| Apps | `list_running`, `list_installed`, `frontmost`, `open(bundle_id, file?)`, `quit(bundle_id)` (polite) | 0–1 |
| Files | `list`, `search` (Spotlight `mdfind`, scoped to allowed roots), `read_text`, `metadata`, `create` (workspace), `move`, `rename`, `move_to_trash` | 0–2 |
| UI (phase 2) | `read_ui(bundle_id)` (Accessibility tree), `press(element)`, `set_value(element, text)` | 0 / 2 |
| Commands (phase 3) | Exact allow list such as `git status`, `open -R`, `pdftotext`, `ls`, all with argv templates | 2 |
| Never | Shell, installers, security settings, the hard-deny list | 3 |

Allowed roots by default: `~/Documents`, `~/Downloads`, `~/Desktop`, and the EAF workspace. Allowed apps by default: Finder, Preview, TextEdit, Calendar, Notes, Microsoft Word, Excel and PowerPoint. You edit `policy.yaml` to change either.

## Phasing

1. **Phase 1: read and tidy.** Apps (open, quit, list) and Files (tiers 0–2) through the bridge, plus the approval UI (reusing the Send / Don't send work), audit log, kill switch and tests with a fake bridge. Needs: Files and Folders consent for the three roots, and Automation only for the polite quit.
2. **Phase 2: see and act in apps.** Accessibility read, press and set value on allowed apps. Needs the Accessibility permission for the bridge app only.
3. **Phase 3: allowed commands.** Spawned under the sandbox profile with no network.

## Decisions needed

1. **Which Mac.** This one is managed by your company (Intune, Trend Micro EDR, Defender). IT may need to approve the bridge, ideally with a privacy-permissions profile, and EDR may flag automated actions. Recommendation: build and test phase 1 here (it only needs folder consent), and check with IT before phase 2.
2. **Bridge implementation.** Start as a Python MCP server packaged as its own `.app`, ad-hoc signed. That means re-approving permissions after each rebuild. Move to Swift and Developer ID signing when it stabilises, so grants stay stable.
3. **Default allow lists.** Confirm the roots and apps above.
4. **Taint rule.** "Read untrusted content → writes need approval" is safer but asks more often. Confirm you want it on.
