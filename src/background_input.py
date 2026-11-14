"""Building blocks for background mode: input for an RDP window that is NOT the active window.

SendInput always delivers to whichever window is active, so it is only used
while the RDP window is in front.  In background mode RDP Nexus instead posts
keyboard and mouse window messages straight to the RDP client's input window
(mstsc's "Input Capture Window", class IHWindowClass).  A posted message
reaches only that one window: it never changes which window is active, never
moves the real mouse pointer and never reaches any other app on this computer.

Microsoft does not document posted input for mstsc/msrdc.  If a client version
ignores it, background mode simply has no effect: RDP Nexus never falls back to
bringing the RDP window to the front.

Everything here is pure (no Win32 calls) so it can be tested anywhere.
"""

from __future__ import annotations

import winapi as w


def key_message(down: bool, alt_context: bool) -> int:
    """WM_KEYDOWN/UP, or the WM_SYSKEY* variants Windows uses while Alt is held."""
    if alt_context:
        return w.WM_SYSKEYDOWN if down else w.WM_SYSKEYUP
    return w.WM_KEYDOWN if down else w.WM_KEYUP


def key_lparam(scan: int, extended: bool, down: bool, alt_context: bool) -> int:
    """lParam of a keyboard message, laid out exactly as Windows does for a real key event.

    bits 0-15 repeat count (1) · 16-23 scan code · 24 extended key · 29 Alt held (context code)
    · 30 previous key state (1 = was down) · 31 transition state (1 = being released)
    """
    lp = 1 | (scan & 0xFF) << 16
    if extended:
        lp |= 1 << 24
    if alt_context:
        lp |= 1 << 29
    if not down:
        lp |= (1 << 30) | (1 << 31)
    return lp


def point_lparam(x: int, y: int) -> int:
    """MAKELPARAM(x, y) for mouse messages (signed 16-bit coordinates)."""
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)


def wheel_wparam(delta: int) -> int:
    """wParam of WM_MOUSEWHEEL: wheel delta in the high word, no buttons or keys held."""
    return (delta & 0xFFFF) << 16
