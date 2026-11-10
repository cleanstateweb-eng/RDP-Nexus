# RDP Nexus

A small floating Windows utility that keeps a **Remote Desktop (RDP) session** gently active.
On a timer (default **13 minutes**) it switches apps or tabs and scrolls *inside the RDP window
you choose*, and it can nudge the mouse pointer a few pixels within that window. Everything stops
the moment the RDP window isn't the active window, and it never touches your local apps.

---

## 🚀 Easy Download & One-Click Setup (For Non-Programmers)

**Zero technical knowledge or programming required!** 
All dependencies, libraries, and Python runtimes are completely built into the application package. You do **not** need to install Python, run any commands, or configure any settings.

### Option 1: Standard Installer (Recommended — 1-Click Setup)
1. Download **`RDPNexus-1.0.4-setup.exe`** from the [Releases](https://github.com/cleanstateweb-eng/RDP-Nexus/releases) page.
2. **Double-click** the downloaded setup file.
3. If a blue Windows SmartScreen popup appears (*"Windows protected your PC"*):
   - Click **More info**
   - Click **Run anyway**
4. Click **Next** and **Install** (No administrator privileges required!).
5. Click **Finish** — RDP Nexus launches instantly, and shortcuts are added to your **Desktop** and **Start Menu**.

---

### Option 2: Portable Version (Zero Installation)
- Download **`RDPNexus-1.0.4-portable.exe`**.
- Simply double-click the file to open and use RDP Nexus immediately.
- Nothing gets installed; you can even run it directly from a USB flash drive.

---

## 🎯 Quick Start Guide

1. Open your Remote Desktop connection (`mstsc`, or the Microsoft Remote Desktop / Windows App client).
2. In RDP Nexus, click the **▾** (settings) button → **Target** tab:
   - Select your RDP window from the dropdown list, or
   - Click **Pick by clicking it** and click inside your RDP window.
3. On the **Keys** tab, keep **Switch → Cycle through all apps** (default recommended).
4. *(Optional test)* Press **Test now**, then click inside the RDP window. Within a couple of seconds, it will perform a test switch and scroll so you know it's working.
5. Press **▶ Start**, then **click inside your RDP window** and leave it active.
   - The countdown will automatically start whenever your RDP window is active.

> **Safety note:** RDP Nexus never brings the RDP window to the front on its own. When you switch to your local computer apps, RDP Nexus automatically pauses itself. When you return to the RDP window, it automatically resumes.

---

## ✨ Features

- **Compact floating panel**: dark, rounded and draggable, with an optional always-on-top mode and a one-line status. Expand it for settings; minimize it to the taskbar (default) or the system tray.
- **Start / Pause / Resume / Stop**, with a countdown to the next cycle and clear states: **Stopped**, **Running**, **Paused**, **RDP Unavailable** and **Manual pointer control**.
- **Cycle through all apps** (default): like pressing Alt+Tab to go through open applications. Every switch brings up the app used longest ago, visiting every open window in turn without needing an app count.
- **Shuffle apps**: visits every app once per round in a random order that changes each round.
- **Remote apps** and **Browser tabs** modes with an allow-list of shortcuts, plus a configurable scroll key and direction (down, up or alternate).
- **Gentle pointer movement**: small, smooth glides that stay inside the RDP window's client area, with an adjustable range (default 20 px) and no clicks, ever.
- **Your input always wins**: touching your mouse immediately pauses automated pointer movement until you resume it. Recent keyboard or mouse activity skips that cycle.
- **Test now**: run one switch + scroll immediately to verify client compatibility without waiting for the timer.
- **Key timing** (Normal / Slow) adapts to laggy or high-latency remote connections.
- Per-user settings, optional launch at sign-in (off by default), per-user installer needing no admin rights, and a portable exe.

---

## ⚙️ How It Works

### Keyboard Navigation (Every *N* minutes, default 13)
Each cycle sends **one** switch action, then (after half a second, if the target is still valid) **one** scroll key.

| Mode | Switch options | Notes |
| --- | --- | --- |
| **Remote apps** | **Cycle through all apps** (default), Shuffle apps, Back and forth (last two apps), Off | Keys are chosen automatically before every switch. |
| **Browser tabs** | Ctrl+Tab, Ctrl+Shift+Tab, Ctrl+Page Down, Ctrl+Page Up, Off | Acts on the browser that is active in the remote session. |

Scroll: Page Down/Page Up or Arrow Down/Up (or Off), with direction **Down**, **Up** or **Alternate** (flips after each successful cycle).

### Gentle Pointer Movement
- Arms only after the mouse has rested over the RDP window for 3 seconds.
- Performs one subtle glide (≈0.2–0.7 s) every *N* seconds (default 60), within *range* pixels (default 20) of where you left the pointer.
- Stays strictly inside the RDP window area and never clicks, drags, or types.
- **Manual control detection**: any physical mouse movement or click immediately switches to **Manual control** to ensure you stay in complete command.

### Input Isolation Safeguards
- **Explicit target**: Only valid Remote Desktop session windows (`mstsc.exe` / `msrdc.exe`) are accepted. Local windows are completely ignored.
- **Pre-action validation**: Re-verifies window handle, active state, and responsiveness before every single event.
- **Fail closed**: If focus shifts, automation instantly suspends.

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

- **Status says "RDP Unavailable – not the active window":**
  Click inside the RDP window after pressing Start. RDP Nexus only runs when the remote window is active in the foreground.
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

Build the standalone package and installer:
```bat
scripts\build_windows.bat
```
The output files will be created in the `release/` folder.

---

## 📄 License

MIT License © 2026.
