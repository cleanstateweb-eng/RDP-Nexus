"""Background mode: the RDP window is brought forward for a moment (keys), and the remote
pointer is nudged with posted mouse moves.  No real input or focus change happens here:
the Win32 calls, poster, gate and inspector are fakes that record what would have happened.
"""

import random
import threading

import winapi as w
from background_input import point_lparam
from focus_borrow import FocusBorrower
from input_safety import ALLOWED, Verdict
from pointer_controller import PointerController, permitted_area
from window_detection import BACKGROUND, NOT_FOREGROUND, OK, Rect, RdpWindow, status

TARGET = RdpWindow(42, 7, "mstsc.exe", "TscShellContainerClass", "host - Remote Desktop Connection", True)
INPUT_HWND = 777
LOCAL_APP = 900


def test_point_lparam():
    assert point_lparam(10, 20) == (20 << 16) | 10
    assert point_lparam(-1, -2) == 0xFFFEFFFF  # signed 16-bit coordinates (monitors left of / above primary)


def test_background_status_counts_as_usable():
    assert status(BACKGROUND).ok and status(OK).ok and not status(NOT_FOREGROUND).ok


def test_no_key_posting_left():
    import keyboard_navigation
    assert not hasattr(keyboard_navigation.KeyboardNavigator, "_post_chord")  # mstsc ignores posted keys


# --- bringing the RDP window forward for a moment -----------------------------------------

class Desktop:
    """Fake foreground/minimize state, with a switch for Windows refusing focus changes."""

    def __init__(self, foreground=LOCAL_APP, minimized=False, refuse=False):
        self.foreground = foreground
        self.minimized = {TARGET.hwnd: minimized}
        self.refuse = refuse
        self.calls = []

    # inspector side
    def foreground_root(self):
        return self.foreground

    def is_foreground(self, target):
        return self.foreground == target.hwnd

    # Win32 side
    def is_iconic(self, hwnd):
        return self.minimized.get(hwnd, False)

    def is_window(self, hwnd):
        return hwnd in (TARGET.hwnd, LOCAL_APP)

    def show(self, hwnd, cmd):
        self.calls.append(("show", hwnd, cmd))
        self.minimized[hwnd] = cmd in (w.SW_MINIMIZE, w.SW_SHOWMINNOACTIVE)

    def activate(self, hwnd):
        self.calls.append(("activate", hwnd))
        if not self.refuse or hwnd != TARGET.hwnd:
            self.foreground = hwnd


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def sleep(self, s):
        self.t += s


def borrower(desk):
    clock = Clock()
    return FocusBorrower(desk, api=desk, sleep=clock.sleep, clock=clock), clock


def test_bring_forward_then_give_back_returns_your_window():
    desk = Desktop()
    fb, clock = borrower(desk)
    b = fb.bring_forward(TARGET)
    assert b.ok and b.previous == LOCAL_APP and desk.foreground == TARGET.hwnd
    assert clock.t >= 0.35  # settle time so the RDP client takes the keyboard before keys are sent
    fb.give_back(TARGET, b)
    assert desk.foreground == LOCAL_APP


def test_minimized_rdp_window_is_restored_for_the_moment_and_minimized_again():
    desk = Desktop(minimized=True)
    fb, _ = borrower(desk)
    b = fb.bring_forward(TARGET)
    assert b.ok and b.was_minimized and ("show", TARGET.hwnd, w.SW_RESTORE) in desk.calls
    fb.give_back(TARGET, b)
    assert desk.foreground == LOCAL_APP and desk.minimized[TARGET.hwnd]
    assert desk.calls[-1] == ("show", TARGET.hwnd, w.SW_SHOWMINNOACTIVE)  # minimized without stealing focus


def test_refused_focus_change_puts_everything_back():
    desk = Desktop(minimized=True, refuse=True)
    fb, clock = borrower(desk)
    b = fb.bring_forward(TARGET)
    assert not b.ok and "did not let" in b.message
    assert desk.foreground == LOCAL_APP and desk.minimized[TARGET.hwnd]
    assert clock.t <= 2.0  # gives up quickly


def test_give_back_skips_a_window_that_closed_meanwhile():
    desk = Desktop(foreground=12345)  # not a window any more by the time we give focus back
    fb, _ = borrower(desk)
    b = fb.bring_forward(TARGET)
    fb.give_back(TARGET, b)
    assert desk.calls.count(("activate", 12345)) == 0 and desk.foreground == TARGET.hwnd


# --- remote pointer (posted mouse moves) ------------------------------------------------------

class Inspector:
    def __init__(self):
        self.size = (INPUT_HWND, 800, 600)
        self.area = Rect(100, 50, 900, 650)
        self.root = 42

    def input_client_size(self, target):
        return self.size

    def input_area(self, target):
        return self.area

    def root_at(self, x, y):
        return self.root

    def point_on_monitor(self, x, y):
        return True


class Gate:
    def __init__(self):
        self.inspector = Inspector()
        self.calls = []
        self.refuse = False
        self.foreground = False

    def check_background(self, target, idle_guard_s=None, allow_foreground=False):
        self.calls.append((idle_guard_s, allow_foreground))
        return Verdict(False, "now_foreground", "the RDP window became the active window") if self.refuse \
            else ALLOWED

    def still_foreground(self, target):
        return self.foreground


class Poster:
    def __init__(self):
        self.posts = []

    def __call__(self, hwnd, msg, wparam, lparam):
        self.posts.append((hwnd, msg, wparam, lparam))
        return True


def no_send_input(_inputs):
    raise AssertionError("remote-pointer moves must never use SendInput")


class Ledger:
    def record(self):
        raise AssertionError("posted messages are not SendInput injections")


def pointer(gate=None, cursor=(5000, 5000)):
    gate = gate or Gate()
    poster = Poster()
    pc = PointerController(gate.inspector, gate, Ledger(), monitor=None, send=no_send_input,
                           cursor=lambda: cursor, rng=random.Random(3), sleep_step=0, post=poster)
    return pc, gate, poster


def test_posted_glide_moves_only_the_remote_pointer_inside_the_rdp_window():
    pc, gate, poster = pointer()
    area = permitted_area(Rect(0, 0, 800, 600))
    for _ in range(5):
        out = pc.glide_posted(TARGET, 20, threading.Event())
        assert out.result.ok and "your mouse was not touched" in out.result.message
    assert poster.posts and all(h == INPUT_HWND and m == w.WM_MOUSEMOVE and wp == 0 for h, m, wp, _lp in poster.posts)
    for *_rest, lp in poster.posts:
        x, y = lp & 0xFFFF, lp >> 16
        assert area.contains(x, y)
        assert abs(x - area.center[0]) <= 21 and abs(y - area.center[1]) <= 21  # stays near where it started
    assert gate.calls == [(None, False)] * 5  # background: no idle guard, RDP must not be active


def test_posted_glide_in_foreground_uses_idle_guard():
    gate = Gate()
    gate.foreground = True  # RDP active, your pointer elsewhere
    pc, gate, poster = pointer(gate)
    assert pc.glide_posted(TARGET, 20, threading.Event(), idle_guard_s=10.0, foreground=True).result.ok
    assert gate.calls == [(10.0, True)]


def test_posted_glide_stops_when_your_pointer_arrives_over_the_active_rdp_window():
    gate = Gate()
    gate.foreground = True
    pc, gate, poster = pointer(gate, cursor=(500, 400))  # resting over the RDP window
    out = pc.glide_posted(TARGET, 20, threading.Event(), idle_guard_s=10.0, foreground=True)
    assert out.result.code == "aborted" and poster.posts == []


def test_posted_glide_stops_when_rdp_becomes_active():
    gate = Gate()
    gate.foreground = True
    pc, gate, poster = pointer(gate)
    out = pc.glide_posted(TARGET, 20, threading.Event())  # background glide, but RDP is now active
    assert out.result.code == "aborted" and poster.posts == []


def test_posted_glide_skips_without_a_visible_area_or_when_gate_refuses():
    pc, gate, poster = pointer()
    gate.inspector.size = None
    assert pc.glide_posted(TARGET, 20, threading.Event()).result.code == "outside"
    gate.inspector.size = (INPUT_HWND, 800, 600)
    gate.refuse = True
    assert pc.glide_posted(TARGET, 20, threading.Event()).result.code == "now_foreground"
    assert poster.posts == []
