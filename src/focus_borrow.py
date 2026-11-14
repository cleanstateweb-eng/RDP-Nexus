"""Background mode: bring the RDP window forward for a moment, then give focus back.

The Remote Desktop client only acts on keyboard input while its own window is the
active window (verified live against mstsc: keys posted to it in the background
were ignored).  So when an app switch is due while you are using another app, the
engine waits until you have not touched the keyboard or mouse for a while, then:

1. remembers which window you were using,
2. restores the RDP window if it was minimized and makes it the active window,
3. sends the keys through the normal SendInput path (with all its per-key checks),
4. makes your previous window active again and re-minimizes the RDP window if it was.

Steps 1, 2 and 4 live here; the engine owns step 3.  Windows only lets the active
app change the foreground window, so activation briefly attaches to the input queue
of the window that is currently active (the documented AttachThreadInput route).
"""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from ctypes import wintypes

import winapi as w
from window_detection import RdpWindow, WindowInspector


@dataclass(frozen=True)
class Borrow:
    ok: bool
    message: str = ""
    previous: int = 0          # the window that was active before (gets focus back)
    was_minimized: bool = False


class Win32Focus:
    """The few Win32 calls needed to move the foreground window (replaceable in tests)."""

    @staticmethod
    def is_iconic(hwnd: int) -> bool:
        return bool(w.IsIconic(hwnd))

    @staticmethod
    def is_window(hwnd: int) -> bool:
        return bool(hwnd) and bool(w.IsWindow(hwnd))

    @staticmethod
    def show(hwnd: int, cmd: int) -> None:
        w.ShowWindow(hwnd, cmd)

    @staticmethod
    def activate(hwnd: int) -> None:
        msg = wintypes.MSG()
        w.PeekMessageW(ctypes.byref(msg), None, 0, 0, w.PM_NOREMOVE)  # this thread needs an input queue
        fg = w.hwnd_int(w.GetForegroundWindow())
        me = int(w.GetCurrentThreadId())
        other = int(w.GetWindowThreadProcessId(fg, None)) if fg else 0
        attached = bool(other) and other != me and bool(w.AttachThreadInput(me, other, True))
        try:
            w.BringWindowToTop(hwnd)
            w.SetForegroundWindow(hwnd)
        finally:
            if attached:
                w.AttachThreadInput(me, other, False)


class FocusBorrower:
    def __init__(self, inspector: WindowInspector, api=None, settle_s: float = 0.35, timeout_s: float = 1.5,
                 sleep=time.sleep, clock=time.monotonic):
        self.inspector = inspector
        self._api = api or Win32Focus()
        self._settle_s = settle_s
        self._timeout_s = timeout_s
        self._sleep = sleep
        self._clock = clock

    def bring_forward(self, target: RdpWindow) -> Borrow:
        """Make the RDP window the active window.  On failure everything is put back as it was."""
        api = self._api
        previous = self.inspector.foreground_root()
        was_minimized = api.is_iconic(target.hwnd)
        if was_minimized:
            api.show(target.hwnd, w.SW_RESTORE)
        deadline = self._clock() + self._timeout_s
        while True:
            api.activate(target.hwnd)
            self._sleep(0.05)
            if self.inspector.is_foreground(target):
                break
            if self._clock() >= deadline:
                self._restore(target, previous, was_minimized)
                return Borrow(False, "Windows did not let RDP Nexus bring the RDP window forward")
        self._sleep(self._settle_s)  # let the RDP client take the keyboard (its Windows-key hook needs focus)
        return Borrow(True, "", previous, was_minimized)

    def give_back(self, target: RdpWindow, borrow: Borrow) -> None:
        if borrow.ok:
            self._restore(target, borrow.previous, borrow.was_minimized)

    def _restore(self, target: RdpWindow, previous: int, was_minimized: bool) -> None:
        api = self._api
        if previous and previous != target.hwnd and api.is_window(previous):
            api.activate(previous)
        if was_minimized:
            api.show(target.hwnd, w.SW_SHOWMINNOACTIVE)
