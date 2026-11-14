"""Background mode: input posted to the RDP window only, never through SendInput.

No real input is sent: the poster, gate and inspector are fakes that record
what would have been delivered.
"""

import random
import threading

import winapi as w
from background_input import key_lparam, key_message, point_lparam, wheel_wparam
from input_safety import ALLOWED, Verdict
from keyboard_navigation import PACING, KeyboardNavigator
from pointer_controller import PointerController, permitted_area
from window_detection import BACKGROUND, NOT_FOREGROUND, OK, Rect, RdpWindow, status

TARGET = RdpWindow(42, 7, "mstsc.exe", "TscShellContainerClass", "host - Remote Desktop Connection", True)
INPUT_HWND = 777


# --- pure helpers -----------------------------------------------------------------------

def test_key_lparam_matches_windows_layout():
    assert key_lparam(0x38, False, True, True) == 0x20380001            # Alt down: context bit set
    assert key_lparam(0x49, True, True, True) == 0x21490001             # Page Up down while Alt held
    assert key_lparam(0x49, True, False, True) == 0xE1490001            # ... released (bits 30, 31)
    assert key_lparam(0x38, False, False, False) == 0xC0380001          # Alt released after the chord


def test_key_message_uses_sys_variants_only_while_alt_is_held():
    assert key_message(True, True) == w.WM_SYSKEYDOWN
    assert key_message(False, True) == w.WM_SYSKEYUP
    assert key_message(True, False) == w.WM_KEYDOWN
    assert key_message(False, False) == w.WM_KEYUP


def test_point_and_wheel_params():
    assert point_lparam(10, 20) == (20 << 16) | 10
    assert point_lparam(-1, -2) == 0xFFFEFFFF  # signed 16-bit coordinates (monitors left of / above primary)
    assert wheel_wparam(-360) == ((-360) & 0xFFFF) << 16
    assert wheel_wparam(120) == 120 << 16


def test_background_status_counts_as_usable():
    assert status(BACKGROUND).ok and status(OK).ok and not status(NOT_FOREGROUND).ok


# --- keyboard -----------------------------------------------------------------------------

class Inspector:
    def __init__(self):
        self.size = (INPUT_HWND, 800, 600)
        self.area = Rect(100, 50, 900, 650)
        self.root = 42

    def input_window(self, target):
        return INPUT_HWND

    def input_client_size(self, target):
        return self.size

    def client_to_screen(self, hwnd, x, y):
        return x + 100, y + 50

    def input_area(self, target):
        return self.area

    def root_at(self, x, y):
        return self.root

    def point_on_monitor(self, x, y):
        return True


class Gate:
    """check_background only: the foreground gate (check_keyboard / check_pointer) must never be used."""

    def __init__(self):
        self.inspector = Inspector()
        self.calls = []
        self.fail_from = None  # 1-based call number from which the gate refuses
        self.foreground = False

    def check_background(self, target, idle_guard_s=None, allow_foreground=False):
        self.calls.append((idle_guard_s, allow_foreground))
        if self.fail_from is not None and len(self.calls) >= self.fail_from:
            return Verdict(False, "now_foreground", "the RDP window became the active window")
        return ALLOWED

    def still_foreground(self, target):
        return self.foreground


class Poster:
    def __init__(self):
        self.posts = []

    def __call__(self, hwnd, msg, wparam, lparam):
        self.posts.append((hwnd, msg, wparam, lparam))
        return True

    def keys(self):
        """(message, vk, scan, extended, alt-context, released) for every posted key message."""
        return [(m, wp, (lp >> 16) & 0xFF, bool(lp >> 24 & 1), bool(lp >> 29 & 1), bool(lp >> 31 & 1))
                for _h, m, wp, lp in self.posts]


def no_send_input(_inputs):
    raise AssertionError("background mode must never use SendInput")


class Ledger:
    def record(self):
        raise AssertionError("posted messages are not SendInput injections")


def navigator(gate=None):
    gate = gate or Gate()
    poster = Poster()
    nav = KeyboardNavigator(gate, Ledger(), send=no_send_input, sleep=lambda s: None, post=poster)
    return nav, gate, poster


def test_background_chord_posts_paced_events_to_the_rdp_input_window_only():
    nav, gate, poster = navigator()
    r = nav.send_chord(TARGET, ("alt", "pageup"), 10.0, background=True)
    assert r.ok and "background" in r.message
    assert {h for h, *_ in poster.posts} == {INPUT_HWND}
    assert poster.keys() == [
        (w.WM_SYSKEYDOWN, 0x12, 0x38, False, True, False),   # Alt down
        (w.WM_SYSKEYDOWN, 0x21, 0x49, True, True, False),    # Page Up down (Alt held)
        (w.WM_SYSKEYUP, 0x21, 0x49, True, True, True),       # Page Up up (Alt held)
        (w.WM_KEYUP, 0x12, 0x38, False, False, True),        # Alt up
    ]
    assert all(guard is None for guard, _fg in gate.calls)  # your local typing never blocks background input


def test_background_shuffle_repeats_tab_while_alt_is_held():
    nav, gate, poster = navigator()
    assert nav.send_chord(TARGET, ("alt", "tab"), 10.0, repeat=2, pacing=PACING["slow"], background=True).ok
    scans = [(scan, up) for _m, _vk, scan, _e, _a, up in poster.keys()]
    assert scans == [(0x38, False), (0x0F, False), (0x0F, True), (0x0F, False), (0x0F, True), (0x38, True)]


def test_background_chord_stops_and_releases_keys_when_you_switch_to_the_rdp_window():
    gate = Gate()
    gate.fail_from = 3  # initial check + Alt down pass; the RDP window becomes active before Page Up
    nav, gate, poster = navigator(gate)
    r = nav.send_chord(TARGET, ("alt", "pageup"), 10.0, background=True)
    assert not r.ok and r.code == "now_foreground" and "keys released" in r.message
    assert poster.keys() == [(w.WM_SYSKEYDOWN, 0x12, 0x38, False, True, False),
                             (w.WM_KEYUP, 0x12, 0x38, False, False, True)]  # Alt released, Page Up never sent


def test_background_chord_cancel_releases_keys():
    nav, gate, poster = navigator()
    cancel = threading.Event()
    nav._sleep = lambda s: cancel.set()  # Pause pressed right after the first event
    r = nav.send_chord(TARGET, ("alt", "pageup"), 10.0, cancel=cancel, background=True)
    assert r.code == "cancelled"
    downs = [k for k in poster.keys() if not k[5]]
    ups = [k for k in poster.keys() if k[5]]
    assert len(downs) == len(ups) == 1


def test_background_chord_skipped_when_gate_refuses():
    gate = Gate()
    gate.fail_from = 1
    nav, gate, poster = navigator(gate)
    r = nav.send_chord(TARGET, ("pagedown",), 10.0, background=True)
    assert not r.ok and r.message.startswith("Skipped") and poster.posts == []


def test_foreground_path_is_unchanged_and_never_posts():
    class FgGate(Gate):
        def check_keyboard(self, target, guard):
            return Verdict(False, "user_active", "You used the keyboard")

    nav, gate, poster = navigator(FgGate())
    r = nav.send_chord(TARGET, ("pagedown",), 10.0)
    assert r.code == "user_active" and poster.posts == []


# --- pointer --------------------------------------------------------------------------------

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


def test_posted_glide_skips_without_a_visible_area():
    pc, gate, poster = pointer()
    gate.inspector.size = None
    out = pc.glide_posted(TARGET, 20, threading.Event())
    assert out.result.code == "outside" and poster.posts == []


def test_posted_wheel_scrolls_at_the_remote_pointer_position():
    pc, gate, poster = pointer()
    r = pc.wheel_posted(TARGET, down=True)
    assert r.ok
    (hwnd, msg, wparam, lparam), = poster.posts
    assert hwnd == INPUT_HWND and msg == w.WM_MOUSEWHEEL
    assert wparam == wheel_wparam(-3 * w.WHEEL_DELTA)
    assert (lparam & 0xFFFF, lparam >> 16) == (400 + 100, 300 + 50)  # client centre -> screen


def test_posted_wheel_respects_gate():
    gate = Gate()
    gate.fail_from = 1
    pc, gate, poster = pointer(gate)
    assert not pc.wheel_posted(TARGET, down=False).ok and poster.posts == []
