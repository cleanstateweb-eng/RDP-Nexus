"""Message layout for background-mode remote-pointer moves (pure, testable anywhere).

Background mode moves only the *remote* pointer by posting WM_MOUSEMOVE to the RDP
client's input window (mstsc's "Input Capture Window", class IHWindowClass).  A posted
message reaches only that window: it never changes which window is active and never
moves your real mouse pointer.  This is best effort: Microsoft does not document how
Remote Desktop clients treat it.

Keyboard input is never posted: the client ignores keys sent that way (verified live),
so background app switching brings the RDP window forward for a moment instead
(see focus_borrow.py).
"""

from __future__ import annotations


def point_lparam(x: int, y: int) -> int:
    """MAKELPARAM(x, y) for mouse messages (signed 16-bit coordinates)."""
    return ((y & 0xFFFF) << 16) | (x & 0xFFFF)
