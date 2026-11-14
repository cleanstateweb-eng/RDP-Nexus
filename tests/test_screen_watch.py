"""Waiting for a remote app switch to finish before scrolling (no real screen capture)."""

from PIL import Image

from screen_watch import THUMB, SwitchWatcher, changed_percent
from window_detection import Rect

AREA = Rect(0, 0, 400, 300)


def frame(value, size=THUMB):
    return Image.new("L", size, value)


class FakeTime:
    """A fake clock plus a cancel event whose wait() just advances the clock."""

    def __init__(self):
        self.t = 0.0
        self.waits = []

    def __call__(self):
        return self.t

    def wait(self, seconds):
        self.waits.append(seconds)
        self.t += seconds
        return False

    def is_set(self):
        return False


def watcher(frames, clock, own=()):
    grabs = iter(frames)
    return SwitchWatcher(None, grab=lambda box: next(grabs), clock=clock, own_rects=lambda: list(own))


def test_changed_percent():
    assert changed_percent(frame(0), frame(0)) == 0
    assert changed_percent(frame(0), frame(255)) == 100
    assert changed_percent(None, frame(0)) == 100
    assert changed_percent(frame(0), frame(0, (10, 10))) == 100


def test_waits_until_new_app_has_appeared_and_settled():
    clock = FakeTime()
    big = (AREA.width, AREA.height)
    w = watcher([frame(0, big)] * 3 + [frame(255, big)] * 20, clock)
    seen, waited = w.wait_for_switch(AREA, frame(0), clock)
    assert seen and 0.8 <= waited < 2.0


def test_never_returns_before_minimum_even_if_screen_changes_at_once():
    clock = FakeTime()
    big = (AREA.width, AREA.height)
    w = watcher([frame(255, big)] * 40, clock)
    seen, waited = w.wait_for_switch(AREA, frame(0), clock)
    assert seen and waited >= 0.8


def test_gives_up_after_timeout_without_a_change():
    clock = FakeTime()
    big = (AREA.width, AREA.height)
    w = watcher([frame(0, big)] * 100, clock)
    seen, waited = w.wait_for_switch(AREA, frame(0), clock)
    assert not seen and waited >= 4.0


def test_fixed_wait_when_screen_cannot_be_watched():
    clock = FakeTime()
    w = watcher([], clock)
    assert w.wait_for_switch(None, None, clock) == (False, 1.5)
    assert clock.waits == [1.5]


def test_snapshot_masks_own_windows_and_survives_capture_errors():
    big = (AREA.width, AREA.height)
    w = watcher([frame(255, big)], FakeTime(), own=[Rect(0, 0, 200, 300)])  # left half covered by our panel
    img = w.snapshot(AREA)
    assert img.size == THUMB
    assert img.getpixel((10, 50)) == 0 and img.getpixel((THUMB[0] - 10, 50)) == 255

    def boom(box):
        raise OSError("capture blocked")

    assert SwitchWatcher(None, grab=boom, own_rects=lambda: []).snapshot(AREA) is None
    assert SwitchWatcher(None, grab=boom, own_rects=lambda: []).snapshot(None) is None
