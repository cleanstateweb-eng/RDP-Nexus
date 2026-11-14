# RDP Nexus

A small floating Windows utility that keeps a **Remote Desktop (RDP) session** gently active.
On a timer (default **13 minutes**) it switches apps or tabs and scrolls *inside the RDP window
you choose*, and it can nudge the remote mouse pointer a few pixels within that window.

**Selecting the RDP window is enough.** With **background mode** (on by default) RDP Nexus keeps
working while you use other apps: the RDP window can stay behind other windows or be minimized,
and you don't have to keep your mouse over it. Input is sent straight to the RDP window, so your
local apps, keyboard focus and mouse pointer are never touched.

Source: <https://github.com/cleanstateweb-eng/RDP-Nexus>

---

## 🚀 Easy Download & One-Click Setup (For Non-Programmers)

**Zero technical knowledge or programming required!** 
All dependencies, libraries, and Python runtimes are completely built into the application package. You do **not** need to install Python, run any commands, or configure any settings.

### Option 1: Standard Installer (Recommended — 1-Click Setup)
1. Download **`RDPNexus-1.0.5-setup.exe`** from the [Releases](https://github.com/cleanstateweb-eng/RDP-Nexus/releases) page.
2. **Double-click** the downloaded setup file.
3. If a blue Windows SmartScreen popup appears (*"Windows protected your PC"*):
   - Click **More info**
   - Click **Run anyway**
4. Click **Next** and **Install** (No administrator privileges required!).
5. Click **Finish** — RDP Nexus launches instantly, and shortcuts are added to your **Desktop** and **Start Menu**.

---

### Option 2: Portable Version (Zero Installation)
- Download **`RDPNexus-1.0.5-portable.exe`**.
- Simply double-click the file to open and use RDP Nexus immediately.
- Nothing gets installed; you can even run it directly from a USB flash drive.

---

## 🎯 Quick Start Guide

1. Open your Remote Desktop connection (`mstsc`, or the Microsoft Remote Desktop / Windows App client).
2. In RDP Nexus, click the **▾** (settings) button → **Target** tab:
   - Select your RDP window from the dropdown list, or
   - Click **Pick by clicking it** and click inside your RDP window.
3. On the **Keys** tab, keep **Switch → Cycle through all apps** (default recommended).
4. *(Optional test)* Keep the RDP window visible and press **Test now**. Within a couple of seconds you should see
   an app switch and a scroll inside the remote session.
5. Press **▶ Start**. That's it — carry on with your local apps. The status shows **Running in background**
   while the RDP window isn't the active window, and **Running** while it is.

> **Safety note:** RDP Nexus never brings the RDP window to the front on its own and never sends input to your
> local apps. Prefer the old behaviour (only act while the RDP window is active)? Turn off
> **Options → Background**.

---

## ✨ Features

- **Background mode** (default): keeps the session active while you work elsewhere — RDP window behind other windows, minimized or on another virtual desktop.
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
| **the active window** | Real key presses (SendInput), only when you haven't used the keyboard or mouse for 10 s | Untouched — keys only go to the active RDP window |
| **in the background or minimized** (background mode) | Keyboard and mouse messages posted directly to the RDP window | Untouched — nothing else receives them, focus never changes |

Background mode works with your normal use of the PC: typing in local apps does not hold it back. It still
pauses when the RDP session shows a dialog or disconnects, when the RDP window is closed, when your PC is
locked or the screen saver runs, and for a moment while you hold Shift, Ctrl, Alt or Win.

> Microsoft doesn't document sending input to a Remote Desktop window in the background. If your RDP client
> ignores it, background mode simply does nothing (see Troubleshooting). RDP Nexus never falls back to
> bringing the RDP window to the front.

### Keyboard Navigation (Every *N* minutes, default 13)
Each cycle sends **one** switch action, then **one** scroll once the switched-to app has appeared (in the
background a fixed 1.5 s wait is used instead).

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
  pointer moves; your own mouse pointer is never moved.
- Stays strictly inside the RDP window area and never clicks, drags, or types.

### Input Isolation Safeguards
- **Explicit target**: Only valid Remote Desktop session windows (`mstsc.exe` / `msrdc.exe`) are accepted. Local windows are completely ignored.
- **Pre-action validation**: Re-verifies the window handle, connection state and responsiveness before every single event.
- **Fail closed**: Real key presses stop the instant the RDP window stops being the active window; background input stops the instant the RDP window becomes active (you may be typing into it) or the session becomes unavailable. Held keys are always released.

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

- **Nothing happens while the RDP window is in the background:**
  Keep the RDP window visible next to another app, click the other app, then press **Keys → Test now** and watch the
  remote screen. If it doesn't switch or scroll, your RDP client ignores background input: turn off
  **Options → Background** and keep the RDP window active while RDP Nexus runs.
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
The output files will be created in the `release/` folder.

---

## 📄 License

MIT License © 2026.
