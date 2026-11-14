# RDP Nexus

A small floating Windows utility that keeps a **Remote Desktop (RDP) session** gently active.
On a timer (default **13 minutes**) it switches apps or tabs and scrolls *inside the RDP window
you choose*, and it can nudge the remote mouse pointer a few pixels within that window.

**Selecting the RDP window is enough.** With **background mode** (on by default) RDP Nexus keeps
working while you use other apps: the RDP window can stay behind other windows or be minimized,
and you don't have to keep your mouse over it. When an app switch is due and you have paused for 10
seconds, the RDP window comes forward for a moment, switches app, and the window you were using gets
focus back. Keys never go to your local apps.

## ⬇️ [Download RDP Nexus for Windows](https://github.com/cleanstateweb-eng/RDP-Nexus/releases/latest/download/RDPNexus-setup.exe)

One click downloads the latest installer (`RDPNexus-setup.exe`); double-click it to install.
Windows 10/11 · no admin rights · nothing else to install. All versions: [Releases](https://github.com/cleanstateweb-eng/RDP-Nexus/releases).

> Don't use GitHub's green **Code → Download ZIP** button to install: that is the source code, not the app.

---

## 🚀 Easy Download & One-Click Setup (For Non-Programmers)

**Zero technical knowledge or programming required!** 
All dependencies, libraries, and Python runtimes are completely built into the application package. You do **not** need to install Python, run any commands, or configure any settings.

### Option 1: Standard Installer (Recommended — 1-Click Setup)
1. Click **[Download RDPNexus-setup.exe](https://github.com/cleanstateweb-eng/RDP-Nexus/releases/latest/download/RDPNexus-setup.exe)** (always the latest version).
2. **Double-click** the downloaded file. That's it: it installs in a few seconds with no questions (no
   administrator rights needed), adds **Desktop** and **Start Menu** shortcuts, and starts RDP Nexus.
   An older version that is running is closed and replaced automatically; your settings are kept.

> **Only the first time:** because the app is new and not code-signed, your browser may ask you to **Keep**
> the file, and Windows may show *"Windows protected your PC"*: click **More info → Run anyway**. These
> warnings come from the browser and Windows, not from RDP Nexus, and can't be switched off by the app.

---

### Option 2: Portable Version (Zero Installation)
- Download **`RDPNexus-<version>-portable.exe`** from the latest [Release](https://github.com/cleanstateweb-eng/RDP-Nexus/releases/latest).
- Simply double-click the file to open and use RDP Nexus immediately.
- Nothing gets installed; you can even run it directly from a USB flash drive.

---

## 🎯 Quick Start Guide

1. Open your Remote Desktop connection (`mstsc`, or the Microsoft Remote Desktop / Windows App client).
2. In RDP Nexus, click the **▾** (settings) button → **Target** tab:
   - Select your RDP window from the dropdown list, or
   - Click **Pick by clicking it** and click inside your RDP window.
3. On the **Keys** tab, keep **Switch → Cycle through all apps** (default recommended).
4. *(Optional test)* Press **Test now** and keep still. The RDP window comes forward for a moment, switches to
   another remote app and scrolls, then RDP Nexus gets focus back.
5. Press **▶ Start**. That's it — carry on with your local apps. The status shows **Running in background**
   while the RDP window isn't the active window, and **Running** while it is.

> **Safety note:** keys only ever go to the RDP window while it is the active window, never to your local apps.
> A due switch waits for a 3-second pause in your typing and mouse use; in background mode the RDP window is then
> brought forward for under a second.
> Prefer the old behaviour (only act while the RDP window is active)? Turn off **Options → Background**.

---

## ✨ Features

- **Background mode** (default): keeps the session active while you work elsewhere — RDP window behind other windows or minimized. It comes forward for a moment for each app switch, once you've paused.
- **Compact floating panel**: dark, rounded and draggable, with an optional always-on-top mode and a one-line status. Expand it for settings; minimize it to the taskbar (default) or the system tray.
- **Start / Pause / Resume / Stop**, with a countdown to the next cycle and clear states: **Stopped**, **Running**, **Running in background**, **Paused**, **RDP Unavailable** and **Manual pointer control**.
- **Cycle through all apps** (default): like pressing Alt+Tab to go through open applications. Every switch brings up the app used longest ago, visiting every open window in turn without needing an app count.
- **Shuffle apps**: visits every app once per round in a random order that changes each round.
- **Remote apps** and **Browser tabs** modes with an allow-list of shortcuts, plus a configurable scroll (Page keys, arrow keys or mouse wheel) and direction (down, up or alternate).
- **Gentle pointer movement**: small, smooth glides that stay inside the RDP window's client area, with an adjustable range (default 20 px) and no clicks, ever.
- **Your input always wins**: while the RDP window is active, touching your mouse over it immediately pauses automated movement of your pointer until you resume it, and recent keyboard or mouse activity skips that cycle.
- **Test now**: run one switch + scroll immediately to verify client compatibility without waiting for the timer.
- **Key timing** (Normal / Slow) adapts to laggy or high-latency remote connections.
- Per-user settings, optional launch at sign-in (off by default), per-user installer needing no admin rights, and a portable exe.

---

## ⚙️ How It Works

### Two ways of delivering input
| RDP window is… | How input is delivered | Your local apps / mouse |
| --- | --- | --- |
| **the active window** | Real key presses (SendInput), at your first 3-second pause in typing and mouse use | Untouched — keys only go to the active RDP window |
| **in the background or minimized** (background mode) | At your first 3-second pause in typing and mouse use: the RDP window is brought forward for a moment (restored if minimized), the same real key presses are sent, then the window you were using gets focus back (and the RDP window is minimized again if it was) | Untouched — keys only go to the RDP window while it is in front |

Why the brief focus? The Remote Desktop client ignores keyboard input sent to it while it is not the active
window (tested against `mstsc`), so there is no way to switch remote apps without it. Background mode still
pauses when the RDP session shows a dialog or disconnects, when the RDP window is closed or on another
virtual desktop, when your PC is locked or the screen saver runs, and while you hold a key. If you start
typing or click somewhere during the moment it is in front, the keys stop at once and the switch is retried.

### Keyboard Navigation (Every *N* minutes, default 13)
Each cycle sends **one** switch action, then **one** scroll once the switched-to app has appeared.

| Mode | Switch options | Notes |
| --- | --- | --- |
| **Remote apps** | **Cycle through all apps** (default), Shuffle apps, Back and forth (last two apps), Off | Keys are chosen automatically before every switch. |
| **Browser tabs** | Ctrl+Tab, Ctrl+Shift+Tab, Ctrl+Page Down, Ctrl+Page Up, Off | Acts on the browser that is active in the remote session. |

Remote app switching normally uses **Alt+Page Up / Alt+Page Down**, Remote Desktop's own keys for a remote
Alt+Tab. **Alt+Tab** itself is only sent to an RDP window that is the active window *and* set to pass Windows
key combinations to the remote PC (full screen with the default setting, or "Apply Windows key combinations:
On the remote computer"). If that setting is ever misread and an Alt+Tab reaches your PC, RDP Nexus notices
and uses Alt+Page Up for that window from then on.

Scroll: Page Down/Page Up, Arrow Down/Up, mouse wheel (or Off), with direction **Down**, **Up** or
**Alternate** (flips after each successful cycle).

### Gentle Pointer Movement
- Performs one subtle glide (≈0.2–0.7 s) every *N* seconds (default 60), within *range* pixels (default 20).
- **Your pointer resting over the active RDP window:** arms after 3 s of rest and moves your pointer gently.
  Any physical mouse movement or click immediately switches to **Manual control** until you press *Resume pointer*.
- **Anywhere else** (RDP in the background, or your pointer on another window/monitor): only the **remote**
  pointer is nudged (best effort — some RDP clients ignore it); your own mouse pointer is never moved and the
  RDP window is never brought forward for this.
- Stays strictly inside the RDP window area and never clicks, drags, or types.

### Input Isolation Safeguards
- **Explicit target**: Only valid Remote Desktop session windows (`mstsc.exe` / `msrdc.exe`) are accepted. Local windows are completely ignored.
- **Pre-action validation**: Re-verifies the window handle, connection state and responsiveness before every single event.
- **Fail closed**: Real key presses stop the instant the RDP window stops being the active window or you touch the keyboard or mouse; held keys are always released, and in background mode your window gets focus back.

---

## 📁 Settings, Logs and Files

| What | Where |
| --- | --- |
| Settings (JSON) | `%APPDATA%\RDP Nexus\settings.json` |
| Logs | `%LOCALAPPDATA%\RDP Nexus\logs\` (Options → Log → *Open log folder*) |
| Installed program | `%LOCALAPPDATA%\Programs\RDP Nexus\` |
| Launch at sign-in | `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` → `RDP Nexus` |

---

## 🛠️ Troubleshooting

- **The RDP window doesn't come forward in the background:**
  A due switch waits for a 3-second pause in your typing and mouse use (the countdown shows **due** and the
  status line says so). If Windows
  refuses to let it bring the window forward, the Log tab says so and it tries again a minute later.
- **Status says "RDP Unavailable – not the active window":**
  Background mode is off. Turn on **Options → Background**, or click inside the RDP window.
- **RDP window isn't in the list:**
  Ensure the remote session is connected (not just the initial connection dialog) and press the ⟳ refresh button.
- **App switching does nothing:**
  Use **Keys → Test now** and view the **Log** tab. If more than one app is open in your remote session, try setting **Options → Key timing → Slow**.
- **Windows SmartScreen warning:**
  The executable is unsigned. Click *More info → Run anyway*.
- **"Blocked by Windows":**
  If your RDP client is running as administrator, launch RDP Nexus as administrator as well so Windows allows input delivery.

---

## 💻 Build from Source (For Developers)

Requirements: Windows 10/11, Python 3.10–3.13, and [Inno Setup 6](https://jrsoftware.org/isinfo.php).

```bat
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python src\main.py
```

Run the tests (the desktop tests in `tests/integration` are opt-in: set `RDPNEXUS_INTERACTIVE_TESTS=1`):
```bat
.venv\Scripts\python -m pytest
```

Build the standalone package and installer (runs the tests first):
```bat
scripts\build_windows.bat
```
The output files will be created in the `release/` folder. Don't compile `installer\setup.iss` by hand
from a fresh copy: it only packages the program that `build_windows.bat` builds first.

### Publishing a release
1. Bump `APP_VERSION` in `src/app_info.py` and add `docs/releases/v<version>.md`.
2. Commit, then tag and push: `git tag v1.0.8` and `git push origin v1.0.8`.
3. GitHub Actions (*Build and release*) tests and builds everything on GitHub's own Windows machine,
   checks the tag matches `APP_VERSION`, and publishes the Release with the installer, the portable exe,
   `SHA256SUMS.txt` and `RDPNexus-setup.exe` (the file behind the one-click download link).

---

## 📄 License

MIT License © 2026.
