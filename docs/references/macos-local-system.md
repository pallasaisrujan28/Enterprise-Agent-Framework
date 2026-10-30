# How macOS runs apps: a low-level reference for local-system agent access

Purpose: understand what really happens on this Mac when an app is installed, opened, used, closed and deleted, so the EAF agent's local-access tools can be designed around the real mechanisms and security gates, not around guesses.

## This machine

| Item | Value | Why it matters |
|---|---|---|
| OS | macOS 15.7.4 (Sequoia), build 24G517 | Permission prompts and APIs below are as of macOS 15 |
| CPU | Apple silicon (arm64) | Apps are native arm64 or run under Rosetta 2 |
| System Integrity Protection (SIP) | Enabled | System files and the permissions database cannot be edited, even as root |
| Gatekeeper | Enabled ("assessments enabled") | Downloaded apps are checked before first launch |
| Device management | Enrolled in **Microsoft Intune MDM** (user approved) | The organisation can push apps, settings and permission profiles, and can block things |
| Security software | Trend Micro EDR, Microsoft Defender, FortiClient VPN | Endpoint monitoring will see (and may block or flag) automated actions |
| Running apps | 18 at the time of writing, each a launchd job (e.g. `application.com.google.Chrome.…`, `application.com.microsoft.Word.…`) | Confirms apps are launchd-supervised processes |
| Apps | 36 items in `/Applications`, Apple's own apps in `/System/Applications`; Homebrew at `/opt/homebrew` (casks: gcloud-cli, tflint) | Three install channels are in use: drag-and-drop, `.pkg` installers, Homebrew |
| Sandboxed app data | 596 folders under `~/Library/Containers` | Most Apple and App Store apps keep their data in per-app sandboxes |

Because this is a company-managed Mac, some of what follows (granting permissions, installing or deleting apps) may be restricted or overridden by IT policy. Check with IT before giving an agent broad control here.

## 1. The layers involved

From the bottom up:

1. **XNU kernel**: processes, memory, files, and the enforcement points for code signing (AMFI), the sandbox, and SIP.
2. **launchd** (process 1): starts and supervises every other process. System services are "daemons"; per-user background helpers are "agents". Apps are also launched as launchd jobs (labelled `application.<bundle-id>.<n>`; `launchctl list | grep application.` shows them).
3. **Security services**: `syspolicyd` (Gatekeeper and notarization), `amfid` (code signatures), `tccd` (privacy permissions), `XProtect` (Apple's malware signatures).
4. **LaunchServices** (`launchservicesd`): the registry of every app on disk, which file types and URL schemes each one handles, and the service that actually opens apps and documents. **RunningBoard** (`runningboardd`) tracks each running app's lifecycle and priority.
5. **WindowServer**: owns the screen, windows, the mouse and the keyboard. It routes input events to the frontmost app.
6. **App frameworks** (AppKit, SwiftUI, Foundation): the code inside every app that runs its event loop, windows, menus and documents.
7. **User-facing shells**: Finder, Dock, Spotlight, Launchpad. These are ordinary apps that ask LaunchServices to open things.

## 2. Where apps live

| Location | What's there | Can be changed? |
|---|---|---|
| `/System/Applications` | Apple's built-in apps (Calculator, Calendar, Books, ...) | No. Part of the read-only, cryptographically sealed system volume |
| `/Applications` | Apps you or IT installed (Chrome, Office, Docker, Kiro, ...) | Yes, by admins; macOS 13+ also requires "App Management" permission to modify another app's bundle |
| `~/Applications` | Per-user apps (e.g. Chrome web apps) | Yes, by the user |
| `/opt/homebrew` | Homebrew formulae (CLI tools) and cask metadata; casks usually place the `.app` in `/Applications` | Yes, by the user |
| `/Library/LaunchDaemons`, `/Library/LaunchAgents`, `~/Library/LaunchAgents` | Background services that start at boot or login (on this Mac: Intune, OneDrive updater, Fortinet, Trend Micro, Google Keystone, Adobe) | Admin or user, depending on folder |

### Anatomy of an app bundle

An `.app` is a folder that Finder displays as one item. Example: `/System/Applications/Calculator.app`:

```
Calculator.app/
  Contents/
    Info.plist          identity and capabilities: CFBundleIdentifier (com.apple.calculator),
                        CFBundleExecutable (Calculator), supported document types, URL schemes,
                        minimum OS, privacy-usage strings
    MacOS/Calculator    the actual executable (Mach-O binary)
    Resources/          icons, UI files, translations, the scripting dictionary (.sdef) if scriptable
    Frameworks/         bundled libraries (when present)
    PlugIns/            extensions (widgets, share extensions, ...)
    _CodeSignature/     the signature covering every file in the bundle
    PkgInfo, version.plist
```

The **bundle identifier** (e.g. `com.google.Chrome`) is the app's real identity. LaunchServices, permissions, preferences and sandboxes are all keyed by it, not by the file name.

### Where an app's data lives (not inside the bundle)

| Path | Contents |
|---|---|
| `~/Library/Preferences/<bundle-id>.plist` | Settings (read and write with `defaults read <bundle-id>`) |
| `~/Library/Application Support/<App>/` | Databases, profiles, downloaded content |
| `~/Library/Caches/<bundle-id>/` | Disposable caches |
| `~/Library/Containers/<bundle-id>/` | The whole private home folder of a **sandboxed** app (App Store and many Apple apps) |
| `~/Library/Group Containers/<team>.<group>/` | Data shared between apps from the same developer (e.g. Office) |
| `~/Library/Saved Application State/` | Window positions for restoring after relaunch |
| `~/Library/Logs/`, `~/Library/HTTPStorages/`, `~/Library/Cookies/` | Logs, network caches, cookies |

Deleting an app does **not** remove any of these (see section 7).

## 3. Installing an app

There are five channels. Every channel that installs an `.app` ends with it registered in LaunchServices and indexed by Spotlight.

### 3a. Drag-and-drop (`.dmg` or `.zip`)

1. The browser downloads the file and tags it with the **quarantine** attribute `com.apple.quarantine` (records which app downloaded it, when, and from where). You can see it with `xattr -l <file>`.
2. Opening the `.dmg` mounts a disk image; dragging the `.app` into `/Applications` is a plain file copy. The quarantine tag travels with it.
3. Finder (via `lsregister`) registers the new bundle in the LaunchServices database: its bundle id, document types and URL schemes. Spotlight indexes it.
4. Nothing has been checked yet. Security checks happen at **first launch** (section 4).

### 3b. Installer packages (`.pkg`)

1. `Installer.app` (or `installer -pkg ... -target /` on the command line) hands the package to `installd` / `system_installd`.
2. The package is signature-checked. It can run **pre- and post-install scripts as root** and can place files anywhere that SIP allows: the app in `/Applications`, helpers, launch daemons, kernel or system extensions.
3. A receipt is recorded: `pkgutil --pkgs` lists installed packages (here: FortiClient, Trend Micro, Microsoft Defender, Adobe, Google Keystone, ...), and `pkgutil --files <id>` lists every file a package placed. History is in `/Library/Receipts/InstallHistory.plist`.
4. This is the most powerful channel and the one IT uses. An agent should never run `.pkg` installers unattended.

### 3c. Mac App Store

`storedownloadd` downloads a signed, sandboxed app with a purchase receipt and installs it into `/Applications`. No quarantine tag and no first-launch prompt. Removal goes through Launchpad or Finder.

### 3d. Homebrew

- `brew install <formula>` builds or downloads CLI tools into `/opt/homebrew/Cellar` and links them into `/opt/homebrew/bin`. No LaunchServices registration, because they are not apps.
- `brew install --cask <app>` downloads the vendor's `.dmg` or `.pkg` and performs step 3a or 3b for you. Homebrew records what it placed, so `brew uninstall --zap` can also remove support files.

### 3e. MDM (Intune / Company Portal)

IT can push apps silently. Managed apps may be **re-installed automatically** if removed, and IT can block apps from running.

## 4. Opening an app

What happens when you double-click `Google Chrome.app` (or click it in the Dock, Spotlight or Launchpad):

1. **Finder asks LaunchServices** to open the item (`LSOpenURLsWithRole` or the modern `NSWorkspace.openApplication`). The Dock, Spotlight and the `open` command all go the same way: `open -a "Google Chrome"`, or `open -b com.google.Chrome` by bundle id.
2. **LaunchServices resolves the target**: which bundle and which version, whether it's already running (if so, it just activates it and sends a "reopen" event, with no new process).
3. **Gatekeeper, first launch only** (quarantined apps): `syspolicyd` checks the Developer ID signature, the **notarization** ticket (Apple has scanned it) and XProtect signatures. You see "downloaded from the internet, are you sure?". If you approve, the result is remembered. Quarantined apps opened from an odd location may be run from a randomised read-only copy (App Translocation).
4. **launchd spawns the process** as a per-user `application.<bundle-id>` job. RunningBoard starts tracking it.
5. **The kernel loads and verifies the code**: AMFI checks that every page matches the code signature; `dyld` loads frameworks. If the app is sandboxed, the sandbox profile from its entitlements is applied before any app code runs.
6. **The app starts up**: `NSApplicationMain` reads `Info.plist`, loads the main UI, connects to **WindowServer**, gets a Dock icon and menu bar, and starts its **run loop**, an endless "wait for an event, handle it" cycle.
7. **Documents and links**: opening a file sends the app an "open documents" Apple Event (`odoc`). LaunchServices chooses the app from the file's type (UTI) and the handlers each app declared. URLs (`https:`, `mailto:`, `slack:`, `vscode:` ...) are routed the same way by scheme.

`lsregister -dump` (at `/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister`) shows the whole registry: every app, its bundle id, and what it claims to open.

## 5. Using an app: every way an action can be driven

When a person clicks a button: the trackpad → HID driver → **WindowServer** works out which window is under the pointer → the event goes into that app's queue → AppKit passes it through the "responder chain" to the button → the button runs its action.

An agent can drive an app at several levels. Higher in this list is more reliable and easier to audit.

| Level | Mechanism | What it can do | Permission required (TCC) | Reliability |
|---|---|---|---|---|
| 1. Native interface | The app's CLI, API or URL scheme (`open "slack://..."`, `code --goto`, `gh`, Office via Graph API) | Whatever the vendor exposes | Usually none locally | Highest; stable, structured |
| 2. Apple Events / AppleScript / JXA | `osascript -e 'tell application "Mail" to ...'`; works for apps with a scripting dictionary (Finder, Mail, Calendar, Safari, Music, Office, Keynote, ...) | Structured commands: open, get text, create event, send | **Automation**: one prompt per controlling app → target app pair | High, for scriptable apps |
| 3. Shortcuts / App Intents | `shortcuts run "<name>"`; apps publish intents | Actions apps chose to publish | Per-shortcut prompts | High but limited coverage |
| 4. Accessibility API | `AXUIElement`: read the on-screen UI tree (buttons, text fields, menus, values) and perform "press", "set value", "pick menu item" | Almost any visible control in any app | **Accessibility** | Medium; breaks when the UI changes |
| 5. Synthetic input | `CGEvent`: fake mouse moves, clicks and key presses | Anything a human can do | **Accessibility** (and **Input Monitoring** to read keys) | Low; blind and timing-sensitive |
| 6. Screen capture + vision | `screencapture`, ScreenCaptureKit, then a vision model reads the pixels | "See" any app, including non-accessible ones | **Screen Recording** (re-confirmed periodically on macOS 15) | Low to medium; slow and costly |

Files and data outside the UI are controlled separately:

| Access | Permission |
|---|---|
| `~/Desktop`, `~/Documents`, `~/Downloads`, iCloud Drive, removable and network volumes | Per-folder prompts ("Files and Folders") |
| Mail, Messages, Safari history, other apps' containers, Time Machine | **Full Disk Access** |
| Contacts, Calendars, Reminders, Photos, Camera, Microphone, Location | Each has its own prompt |
| Changing or deleting other apps' bundles | **App Management** |

How TCC decides:

- Permissions are stored per app in TCC databases (`~/Library/Application Support/com.apple.TCC/TCC.db` and a system-wide one). Both are protected by SIP; they can only be changed through System Settings → Privacy & Security, or by an MDM privacy profile (PPPC).
- A permission belongs to the **"responsible" app**, not the script. A Python script run from Kiro's terminal is judged as **Kiro**; run from Terminal it is judged as **Terminal**. Granting Accessibility "to the agent" therefore really grants it to whatever app launched it, plus everything else that app runs.
- `tccutil reset <Service> <bundle-id>` revokes a permission; there is no command to grant one.

## 6. Closing an app

| How | What actually happens |
|---|---|
| Red close button | Closes the **window** only. Most apps keep running (the Dock dot stays); single-window utilities may quit |
| Cmd-Q or Menu → Quit | The app receives `applicationShouldTerminate`. It can ask "save changes?" or delay the quit. Then it saves its state, closes documents and exits cleanly |
| `osascript -e 'quit app "Pages"'` | Sends a "quit" Apple Event (`aevt/quit`), which is the same polite path as Cmd-Q. Needs Automation permission |
| Log out or shut down | Every app gets the quit event; any one app can cancel the logout by refusing |
| `kill -TERM <pid>` | A Unix signal: well-behaved apps exit, but unsaved work may be lost with no prompt |
| Force Quit (Opt-Cmd-Esc) or `kill -9` | `SIGKILL`: immediate, no saving, no cleanup |
| macOS on its own | App Nap throttles hidden apps; "automatic termination" can quietly quit idle apps that support it and relaunch them on demand |

After exit, RunningBoard and launchd clean up the job, WindowServer removes the windows, and the Dock icon goes (unless pinned). The next launch may restore windows from Saved Application State.

## 7. Deleting an app

1. **Drag to Trash / Finder "Move to Bin"**: moves only the `.app` bundle to `~/.Trash`. It's deleted when the Trash is emptied.
   - macOS 13+ asks for **App Management** permission if another program (not Finder) tries to change or remove an app bundle.
   - Deleting a running app is refused or warned about.
2. **LaunchServices** notices the bundle is gone and deregisters it. Files that opened with it fall back to another handler.
3. **What stays behind**: everything in section 2's data table (Preferences, Application Support, Caches, Containers, Group Containers), plus:
   - launch agents and daemons (they keep trying to start a missing helper),
   - login items and background items (System Settings → General → Login Items),
   - system extensions, network extensions, VPN profiles, kernel extensions,
   - `.pkg` receipts (`pkgutil --forget <id>` removes the receipt only, not the files).
4. **Proper removal by channel**:
   - Drag-and-drop apps: delete the bundle, then the data folders for its bundle id.
   - `.pkg` apps: use the vendor's uninstaller (on this Mac: FortiClientUninstaller, Chrome Remote Desktop Host Uninstaller), or remove the files listed by `pkgutil --files`.
   - App Store apps: Launchpad (hold → ✕) or Finder.
   - Homebrew: `brew uninstall --zap --cask <app>`.
   - **MDM-managed apps**: may be reinstalled by Intune, or removal may be blocked. Don't fight it; ask IT.
5. **Can't be deleted**: anything in `/System/Applications`, because it's on the sealed system volume under SIP.

## 8. The security gates in one place

| Gate | Protects | An agent will hit it when |
|---|---|---|
| SIP + sealed system volume | System files, TCC databases, Apple apps | Trying to change the OS or grant itself permissions (it can't, by design) |
| Gatekeeper + notarization + XProtect | First launch of downloaded apps | Opening something it just downloaded |
| Code signing (AMFI) | Integrity of every running binary | Modifying an app bundle breaks its signature |
| App Sandbox | What a sandboxed app itself can touch | Reading another app's container |
| TCC privacy permissions | UI control, screen, files, personal data | Nearly every useful action in section 5 |
| App Management | Other apps' bundles | Installing, updating or deleting apps |
| MDM (Intune) | Company policy; can grant or deny TCC via profiles, push or block apps | Anything IT hasn't allowed |
| EDR (Trend Micro, Defender) | Behaviour monitoring | Synthetic input, mass file changes, scripted installs can look like malware |

## 9. What this means for the agent's design

1. **Use the highest level that works.** Prefer each app's CLI, API or URL scheme, then AppleScript for scriptable apps, then the Accessibility tree. Use synthetic clicks and screenshots only as a last resort. Higher levels are faster, auditable, and don't break when a button moves.
2. **Give permissions to one dedicated, signed helper app, not to Kiro, Terminal or Python.** Because TCC trusts the responsible app, granting Accessibility or Full Disk Access to Kiro or Terminal would extend it to everything run there. A small helper (for example `EAF Local Bridge.app`) that the agent talks to over a local socket keeps the grant narrow and revocable in one place.
3. **Treat actions by risk, in code, not just in the prompt:**
   - Read-only (list apps, read UI state, read files in allowed folders): allowed.
   - Reversible (open or activate an app, open a file, move a window, polite quit): allowed, logged.
   - Consequential (type or submit into an app, send, move files, change settings): confirm first.
   - Destructive or system-level (delete files or apps, force quit, run installers, `sudo`, change security settings): always confirm, or not offered at all.
4. **Allow-lists, not blanket access**: which apps it may control (by bundle id), which folders it may read and write. Default-deny everything else.
5. **Quit politely**: use the Apple Event quit so apps can save; never `kill -9` by default.
6. **"Delete" means Trash, not erase.** Moving to Trash is recoverable; emptying it is not. The agent should never empty the Trash itself.
7. **Log every action**: app, action, target and result, in the same style as the tool cards in the dashboard.
8. **This Mac is company-managed.** Confirm with IT what's allowed before granting Accessibility, Screen Recording or Full Disk Access. They may prefer to grant it through an Intune privacy profile, and EDR may flag automated input.

## 10. Commands for exploring (all read-only)

```bash
sw_vers; csrutil status; spctl --status          # OS, SIP, Gatekeeper
profiles status -type enrollment                 # MDM enrollment
ls /Applications /System/Applications ~/Applications
mdls -name kMDItemCFBundleIdentifier /Applications/*.app     # bundle ids
defaults read /Applications/Safari.app/Contents/Info.plist CFBundleIdentifier
codesign -dv --verbose=2 /Applications/<App>.app # who signed it
spctl -a -vv /Applications/<App>.app             # would Gatekeeper allow it
xattr -l ~/Downloads/<file>                      # quarantine tag
pkgutil --pkgs; pkgutil --files <pkg-id>          # installer receipts and files
launchctl list | grep application.               # running apps as launchd jobs
lsappinfo list                                    # LaunchServices' view of running apps
ls ~/Library/LaunchAgents /Library/LaunchAgents /Library/LaunchDaemons
ls /System/Applications/Calendar.app/Contents/Resources/*.sdef   # an app's AppleScript dictionary
                                                  # (the `sdef` tool itself needs full Xcode)
```

## Open questions before building

1. Which apps and actions does the agent actually need first (for example Calendar, Mail, Finder files, Office documents, browser)? That decides the permission set.
2. Will IT allow Accessibility and Automation permissions for a helper app on this managed Mac, or should we test on a personal machine first?
3. Should the helper be a signed Swift app (needs a Developer ID for stable TCC grants) or start as a local MCP server run from a dedicated app wrapper?
