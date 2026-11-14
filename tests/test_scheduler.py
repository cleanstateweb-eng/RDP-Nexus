"""State-machine tests for the automation engine using a fake clock and fake I/O.

No real input is ever sent: keyboard/pointer/inspector/gate are fakes that
record what the engine asked for.
"""

import threading

import pytest

from input_safety import Verdict
from keyboard_navigation import SHUFFLE_APPS, ActionResult
from pointer_controller import GlideOutcome
from scheduler import AutomationEngine, DisplayState, EngineConfig, PointerState
from window_detection import CLOSED, DIALOG, DISCONNECTED, HIDDEN, MINIMIZED, NOT_FOREGROUND, OK, RdpWindow, status

TARGET = RdpWindow(42, 7, "mstsc.exe", "TscShellContainerClass", "host - Remote Desktop Connection", True)


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t

    def advance(self, s):
        self.t += s


class FakeScreen:
    """Stands in for screen_watch.SwitchWatcher: no screen capture, no real waiting."""

    def __init__(self):
        self.waits = []

    def snapshot(self, area):
        return None

    def wait_for_switch(self, area, before, cancel):
        self.waits.append(area)
        return True, 0.0


class FakeInspector:
    def __init__(self):
        self.code = OK
        self.fullscreen = False

    def is_fullscreen(self, target):
        return self.fullscreen

    def input_area(self, target):
        return None

    def check(self, target, require_foreground=True, allow_background=False):
        if target is None:
            return status("no_target")
        if self.code == NOT_FOREGROUND and not require_foreground:
            return status(OK)
        if allow_background and self.code in (NOT_FOREGROUND, MINIMIZED):
            return status(OK)
        return status(self.code)


class FakeGate:
    def __init__(self, clock):
        self.clock = clock
        self.last_activity = None

    def observe(self):
        pass

    def session_verdict(self):
        return Verdict(True, "ok", "OK")

    def seconds_since_user_activity(self):
        return None if self.last_activity is None else self.clock() - self.last_activity

    def mark_user_activity(self):
        self.last_activity = self.clock()

    held = ()

    def activity_marker(self):
        return self.last_activity

    def absorb_input_since(self, marker):
        self.absorbed = getattr(self, "absorbed", 0) + 1
        self.last_activity = marker

    def held_keys(self):
        return list(self.held)

    def held_buttons(self):
        return []

    def user_active_within(self, seconds):
        since = self.seconds_since_user_activity()
        return since is not None and since < seconds


class FakeFocus:
    """Stands in for focus_borrow.FocusBorrower: records bring-forward / give-back."""

    def __init__(self):
        self.calls = []
        self.refuse = False

    def bring_forward(self, target):
        from focus_borrow import Borrow
        self.calls.append("forward")
        return Borrow(False, "Windows did not let RDP Nexus bring the RDP window forward") if self.refuse \
            else Borrow(True, "", previous=900)

    def give_back(self, target, borrow):
        self.calls.append("back")


class FakeRdpKeys:
    def __init__(self, mode=2):
        self.mode = mode

    def lookup(self, pid, process_name):
        from rdp_settings import KeyboardHookInfo
        return KeyboardHookInfo(self.mode, "test")


class FakeKeyboard:
    def send_chord(self, target, keys, guard, repeat=1, pacing=None, cancel=None, background=False):
        self.last_pacing = pacing
        self.last_guard = guard
        self.last_background = background
        if self.next_result is not None:
            r, self.next_result = self.next_result, None
            return r
        self.sent.append((keys, repeat))
        self.modes.append("background" if background else "foreground")
        return ActionResult(True, "ok", f"Sent {keys}x{repeat}")

    def __init__(self):
        self.sent = []
        self.modes = []
        self.next_result = None


class FakeMonitor:
    def __init__(self):
        self.armed = False
        self.triggered = False
        self.reason = ""
        self.running = False
        self.install_error = ""

    def start(self):
        self.running = True
        return True

    def stop(self):
        self.running = False

    def arm(self):
        self.armed, self.triggered = True, False

    def disarm(self):
        self.armed, self.triggered = False, False


class FakePointer:
    def __init__(self, monitor):
        self.monitor = monitor
        self.glides = 0
        self.ready = True
        self.pos = (500, 400)
        self.outcome = None
        self.posted = []

    def _cursor(self):
        return self.pos

    def reset_anchor(self):
        pass

    def cursor_ready(self, target):
        return (self.ready, "" if self.ready else "outside")

    def glide(self, target, range_px, guard, cancel):
        self.glides += 1
        if self.outcome is not None:
            return self.outcome
        self.pos = (self.pos[0] + 5, self.pos[1])
        return GlideOutcome(ActionResult(True, "ok", "moved"), self.pos)

    def glide_posted(self, target, range_px, cancel, idle_guard_s=None, foreground=False):
        self.posted.append({"guard": idle_guard_s, "foreground": foreground})
        return GlideOutcome(ActionResult(True, "ok", "moved the remote pointer"))

    def wheel_posted(self, target, down, notches=3):
        self.posted.append({"wheel": down})
        return ActionResult(True, "ok", "wheel")


# The original tests cover the foreground-only behaviour (background mode switched off).
CFG = EngineConfig(interval_s=13 * 60, switch_shortcut="alt_pageup", scroll_key="page", scroll_direction="alternate",
                   pointer_enabled=False, action_gap_s=0, background_input=False)


@pytest.fixture
def env():
    clock = Clock()
    insp = FakeInspector()
    gate = FakeGate(clock)
    kb = FakeKeyboard()
    mon = FakeMonitor()
    ptr = FakePointer(mon)
    eng = AutomationEngine(insp, gate, kb, ptr, mon, CFG, clock=clock, cursor=ptr._cursor, start_thread=False,
                           rdp_keys=FakeRdpKeys(), screen_watcher=FakeScreen(), focus=FakeFocus())
    return eng, clock, insp, gate, kb, mon, ptr


def run_for(eng, clock, seconds, step=1.0):
    t = 0.0
    while t < seconds:
        clock.advance(step)
        t += step
        eng.step()


def test_start_requires_target(env):
    eng, *_ = env
    assert not eng.start()
    assert eng.snapshot().state == DisplayState.STOPPED


def test_start_validates_target(env):
    eng, clock, insp, *_ = env
    insp.code = MINIMIZED
    eng.set_target(TARGET)
    assert not eng.start()
    assert "minimized" in eng.snapshot().detail


def test_default_interval_is_13_minutes():
    assert EngineConfig().interval_s == 13 * 60


def test_cycle_runs_after_interval_then_alternates_scroll(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    assert eng.start()
    eng.step()
    snap = eng.snapshot()
    assert snap.state == DisplayState.RUNNING and snap.countdown_s == pytest.approx(780)
    run_for(eng, clock, 779)
    assert kb.sent == []
    run_for(eng, clock, 2)
    assert kb.sent == [(("alt", "pageup"), 1), (("pagedown",), 1)]
    run_for(eng, clock, 781)
    assert kb.sent[2:] == [(("alt", "pageup"), 1), (("pageup",), 1)]  # direction alternated
    assert eng.snapshot().cycles == 2


def test_shuffle_uses_alt_pageup_with_steps(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_config(EngineConfig(interval_s=60, switch_shortcut=SHUFFLE_APPS, app_count=5, scroll_key="off",
                                pointer_enabled=False))
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 60 * 10 + 5)
    assert len(kb.sent) == 10
    assert all(keys == ("alt", "pageup") and 1 <= rep <= 4 for keys, rep in kb.sent)


def test_focus_loss_suspends_and_never_sends(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 100)
    insp.code = NOT_FOREGROUND
    eng.step()
    snap = eng.snapshot()
    assert snap.state == DisplayState.UNAVAILABLE and snap.countdown_s is None
    run_for(eng, clock, 3600)
    assert kb.sent == []


def test_return_restarts_full_countdown_no_missed_actions(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 700)
    insp.code = MINIMIZED
    run_for(eng, clock, 3000)
    insp.code = OK
    eng.step()
    assert kb.sent == []
    assert eng.snapshot().countdown_s == pytest.approx(780)


def test_manual_resume_policy_pauses_on_return(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_config(EngineConfig(**{**CFG.__dict__, "resume_policy": "manual"}))
    eng.set_target(TARGET)
    eng.start()
    eng.step()
    insp.code = DISCONNECTED
    eng.step()
    assert eng.snapshot().state == DisplayState.UNAVAILABLE
    insp.code = OK
    eng.step()
    assert eng.snapshot().state == DisplayState.PAUSED
    run_for(eng, clock, 3600)
    assert kb.sent == []
    eng.resume()
    eng.step()
    assert eng.snapshot().state == DisplayState.RUNNING


def test_pause_and_stop_cancel(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 10)
    cancel = eng._cancel
    eng.pause()
    assert cancel.is_set()
    run_for(eng, clock, 5000)
    assert kb.sent == [] and eng.snapshot().countdown_s is None
    eng.resume()
    eng.step()
    assert eng.snapshot().countdown_s == pytest.approx(780)
    eng.stop()
    run_for(eng, clock, 5000)
    assert kb.sent == []
    assert eng.snapshot().state == DisplayState.STOPPED


def test_double_start_is_a_noop(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    assert eng.start()
    eng.step()
    run_for(eng, clock, 400)
    assert eng.start()  # must not reset or duplicate the countdown
    assert eng.snapshot().countdown_s == pytest.approx(380)


def test_only_one_worker_thread():
    from scheduler import AutomationEngine as AE
    clock = Clock()
    mon = FakeMonitor()
    eng = AE(FakeInspector(), FakeGate(clock), FakeKeyboard(), FakePointer(mon), mon, CFG, tick_s=0.01,
             rdp_keys=FakeRdpKeys())
    try:
        eng.set_target(TARGET)
        for _ in range(5):
            eng.start()
        names = [t.name for t in threading.enumerate() if t.name == "rdpnexus-engine"]
        assert len(names) == 1
    finally:
        eng.shutdown()
    assert not any(t.name == "rdpnexus-engine" and t.is_alive() for t in threading.enumerate())


def test_long_gap_does_not_fire_immediately(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 700)
    clock.advance(4000)  # e.g. laptop slept
    eng.step()
    assert kb.sent == []
    assert eng.snapshot().countdown_s == pytest.approx(780)


def test_closed_window_stops_automation(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    insp.code = CLOSED
    eng.step()
    snap = eng.snapshot()
    assert snap.state == DisplayState.STOPPED and "closed" in snap.detail


def test_target_cannot_change_while_running(env):
    eng, *_ = env
    eng.set_target(TARGET)
    eng.start()
    assert not eng.set_target(None)
    assert eng.target == TARGET


def test_keyboard_disabled_means_no_countdown(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_config(EngineConfig(**{**CFG.__dict__, "keyboard_enabled": False}))
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 3000)
    assert kb.sent == [] and eng.snapshot().countdown_s is None


def test_skipped_action_is_retried_at_your_next_pause_not_after_a_full_interval(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 779)
    kb.next_result = ActionResult(False, "user_active", "Skipped Alt+Page Up: You used the keyboard")
    run_for(eng, clock, 2)
    snap = eng.snapshot()
    assert "Skipped" in snap.detail and kb.sent == []
    assert snap.countdown_s <= CFG.retry_s  # retried in a moment, the whole countdown is NOT restarted
    run_for(eng, clock, 2)
    assert kb.sent == [(("alt", "pageup"), 1), (("pagedown",), 1)]


def test_focus_change_during_send_suspends(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 779)
    kb.next_result = ActionResult(False, "focus_changed", "Focus left the RDP window")
    run_for(eng, clock, 2)
    assert eng.snapshot().state == DisplayState.UNAVAILABLE


# --- pointer --------------------------------------------------------------------------

PCFG = EngineConfig(keyboard_enabled=False, pointer_enabled=True, pointer_interval_s=60, pointer_rest_s=3,
                    background_input=False)


def start_pointer(env):
    eng, clock, insp, gate, kb, mon, ptr = env
    eng.set_config(PCFG)
    eng.set_target(TARGET)
    eng.start()
    return eng, clock, insp, gate, kb, mon, ptr


def test_pointer_arms_after_rest_and_moves(env):
    eng, clock, insp, gate, kb, mon, ptr = start_pointer(env)
    gate.mark_user_activity()
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.ARMING
    run_for(eng, clock, 4)
    assert eng.snapshot().pointer_state == PointerState.ACTIVE and mon.armed
    run_for(eng, clock, 61)
    assert ptr.glides == 1


def test_pointer_waits_while_cursor_outside(env):
    eng, clock, insp, gate, kb, mon, ptr = start_pointer(env)
    ptr.ready = False
    run_for(eng, clock, 300)
    assert eng.snapshot().pointer_state == PointerState.ARMING and ptr.glides == 0


def test_manual_movement_suspends_until_explicit_resume(env):
    eng, clock, insp, gate, kb, mon, ptr = start_pointer(env)
    run_for(eng, clock, 2)
    assert eng.snapshot().pointer_state == PointerState.ACTIVE
    mon.triggered, mon.reason = True, "mouse moved"
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.MANUAL
    run_for(eng, clock, 3600)
    assert ptr.glides == 0 and eng.snapshot().pointer_state == PointerState.MANUAL
    eng.resume_pointer()
    assert eng.snapshot().pointer_state == PointerState.ARMING


def test_polling_detects_cursor_moved_by_user(env):
    eng, clock, insp, gate, kb, mon, ptr = start_pointer(env)
    run_for(eng, clock, 2)
    ptr.pos = (700, 400)  # moved without the hook noticing
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.MANUAL


def test_user_movement_while_unavailable_counts_as_manual(env):
    eng, clock, insp, gate, kb, mon, ptr = start_pointer(env)
    run_for(eng, clock, 2)
    insp.code = NOT_FOREGROUND
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.SUSPENDED
    mon.triggered, mon.reason = True, "mouse moved"
    eng.step()
    insp.code = OK
    run_for(eng, clock, 300)
    assert eng.snapshot().pointer_state == PointerState.MANUAL and ptr.glides == 0


def test_pointer_fault_disables_feature(env):
    eng, clock, insp, gate, kb, mon, ptr = start_pointer(env)
    run_for(eng, clock, 2)
    ptr.outcome = GlideOutcome(ActionResult(False, "fault", "outside"), (1, 1))
    run_for(eng, clock, 61)
    assert eng.snapshot().pointer_state == PointerState.FAULT
    run_for(eng, clock, 600)
    assert ptr.glides == 1


def test_pause_disarms_pointer(env):
    eng, clock, insp, gate, kb, mon, ptr = start_pointer(env)
    run_for(eng, clock, 2)
    eng.pause()
    assert not mon.armed
    run_for(eng, clock, 600)
    assert ptr.glides == 0
    eng.stop()
    eng.step()
    assert not mon.running  # hook removed when stopped


# --- Test now ---------------------------------------------------------------------------


def test_test_now_requires_target(env):
    eng, *_ = env
    assert not eng.test_now()


def test_test_now_runs_one_cycle_without_starting(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    assert eng.test_now()
    eng.step()
    assert kb.sent == [(("alt", "pageup"), 1), (("pagedown",), 1)]
    assert kb.last_guard == 1.0  # short idle guard for a user-initiated test
    snap = eng.snapshot()
    assert snap.state == DisplayState.STOPPED and not eng.testing
    run_for(eng, clock, 3000)
    assert len(kb.sent) == 2  # one-shot


def test_test_now_waits_for_focus_and_stillness(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    insp.code = NOT_FOREGROUND
    eng.test_now()
    run_for(eng, clock, 5)
    assert kb.sent == [] and "Test waiting" in eng.snapshot().detail
    insp.code = OK
    gate.mark_user_activity()  # the click into the RDP window
    eng.step()
    assert kb.sent == [] and "keep still" in eng.snapshot().detail
    run_for(eng, clock, 2)
    assert len(kb.sent) == 2


def test_test_now_times_out(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    insp.code = NOT_FOREGROUND
    eng.test_now()
    run_for(eng, clock, 16)
    assert not eng.testing and "cancelled" in eng.snapshot().detail
    insp.code = OK
    run_for(eng, clock, 5)
    assert kb.sent == []


def test_stop_cancels_pending_test(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    insp.code = NOT_FOREGROUND
    eng.test_now()
    eng.stop()
    insp.code = OK
    run_for(eng, clock, 5)
    assert kb.sent == [] and not eng.testing


def test_slow_key_timing_is_passed_to_keyboard(env):
    from keyboard_navigation import PACING
    eng, clock, insp, gate, kb, *_ = env
    eng.set_config(EngineConfig(**{**CFG.__dict__, "key_timing": "slow"}))
    eng.set_target(TARGET)
    eng.test_now()
    eng.step()
    assert kb.last_pacing == PACING["slow"]


def test_testing_flag_stays_set_while_test_keys_are_sent(env):
    eng, clock, insp, gate, kb, *_ = env
    seen = []
    original = kb.send_chord

    def spy(*args, **kwargs):
        seen.append(eng.testing)
        return original(*args, **kwargs)

    kb.send_chord = spy
    eng.set_target(TARGET)
    eng.test_now()
    eng.step()
    assert seen == [True, True] and not eng.testing


# --- which keys switch remote apps -----------------------------------------------------


def _one_test_cycle(env, switch="alt_pageup", mode=2, fullscreen=False):
    eng, clock, insp, gate, kb, *_ = env
    eng.rdp_keys = FakeRdpKeys(mode)
    insp.fullscreen = fullscreen
    eng.set_config(EngineConfig(**{**CFG.__dict__, "switch_shortcut": switch, "scroll_key": "off"}))
    eng.set_target(TARGET)
    eng.test_now()
    eng.step()
    return kb.sent


def test_fullscreen_default_setting_uses_alt_tab(env):
    assert _one_test_cycle(env, fullscreen=True) == [(("alt", "tab"), 1)]


def test_fullscreen_previous_app_uses_alt_shift_tab(env):
    assert _one_test_cycle(env, "alt_pagedown", fullscreen=True) == [(("alt", "shift", "tab"), 1)]


def test_windowed_default_setting_uses_alt_pageup(env):
    assert _one_test_cycle(env, fullscreen=False) == [(("alt", "pageup"), 1)]


def test_setting_on_this_computer_never_uses_alt_tab(env):
    assert _one_test_cycle(env, mode=0, fullscreen=True) == [(("alt", "pageup"), 1)]


def test_setting_on_remote_computer_uses_alt_tab_even_windowed(env):
    assert _one_test_cycle(env, mode=1, fullscreen=False) == [(("alt", "tab"), 1)]


def test_shuffle_fullscreen_taps_tab(env):
    eng, clock, insp, gate, kb, *_ = env
    insp.fullscreen = True
    eng.set_config(EngineConfig(interval_s=60, switch_shortcut=SHUFFLE_APPS, app_count=4, scroll_key="off",
                                pointer_enabled=False))
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 60 * 6 + 5)
    assert len(kb.sent) == 6 and all(k == ("alt", "tab") and 1 <= rep <= 3 for k, rep in kb.sent)
    assert "full-screen RDP passes Alt+Tab" in eng.snapshot().events[-1].message


def test_alt_tab_falls_back_after_focus_moves(env):
    eng, clock, insp, gate, kb, *_ = env
    insp.fullscreen = True
    eng.set_target(TARGET)
    eng.set_config(EngineConfig(**{**CFG.__dict__, "scroll_key": "off"}))
    kb.next_result = ActionResult(False, "focus_changed", "Focus left the RDP window right after Alt+Tab")
    eng.test_now()
    eng.step()
    assert any("will use Alt+Page Up" in e.message for e in eng.snapshot().events)
    eng.test_now()
    eng.step()
    assert kb.sent[-1] == (("alt", "pageup"), 1)


def test_cycle_mode_full_screen_and_windowed(env):
    from keyboard_navigation import CYCLE_APPS
    assert _one_test_cycle(env, CYCLE_APPS, fullscreen=True) == [(("alt", "shift", "tab"), 1)]
    eng = env[0]
    assert "cycling through all open apps" in eng.snapshot().events[-2].message


def test_cycle_mode_windowed_uses_alt_pagedown(env):
    from keyboard_navigation import CYCLE_APPS
    assert _one_test_cycle(env, CYCLE_APPS, fullscreen=False) == [(("alt", "pagedown"), 1)]


def test_default_engine_switch_is_cycle():
    from keyboard_navigation import CYCLE_APPS
    assert EngineConfig().switch_shortcut == CYCLE_APPS


# --- background mode (RDP window not the active window) ---------------------------------------

BCFG = EngineConfig(**{**CFG.__dict__, "background_input": True})


def start_background(env, cfg=BCFG, code=NOT_FOREGROUND):
    eng, clock, insp, gate, kb, mon, ptr = env
    eng.set_config(cfg)
    eng.set_target(TARGET)
    insp.code = code
    assert eng.start()
    eng.step()
    return eng, clock, insp, gate, kb, mon, ptr


def test_background_brings_rdp_forward_for_the_switch_then_gives_focus_back(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    snap = eng.snapshot()
    assert snap.state == DisplayState.BACKGROUND and snap.countdown_s == pytest.approx(780)
    assert snap.target_status.ok and "background" in snap.target_status.message
    run_for(eng, clock, 781)
    assert eng.focus.calls == ["forward", "back"]
    # the normal foreground keys; scroll first so the RDP window is in front for well under a second
    assert kb.sent == [(("pagedown",), 1), (("alt", "pageup"), 1)]
    assert eng.screen.waits == []  # no waiting for the new app while the window is borrowed
    assert snap.countdown_s is not None and eng.snapshot().cycles == 1


def test_background_uses_the_same_keys_as_when_rdp_is_active(env):
    eng, clock, insp, gate, kb, *_ = env
    insp.fullscreen = True  # your setup: full screen with the default keyboard setting
    start_background(env, EngineConfig(**{**BCFG.__dict__, "scroll_key": "off"}))
    run_for(eng, clock, 781)
    assert kb.sent == [(("alt", "tab"), 1)]  # real Alt+Tab, exactly like 1.0.4 in front


def test_minimized_rdp_window_still_gets_its_switch(env):
    eng, clock, insp, gate, kb, *_ = start_background(env, code=MINIMIZED)
    run_for(eng, clock, 781)
    assert len(kb.sent) == 2 and eng.focus.calls == ["forward", "back"]


def test_rdp_on_another_virtual_desktop_is_not_brought_forward(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_config(BCFG)
    eng.set_target(TARGET)
    insp.code = HIDDEN
    assert not eng.start()  # it would switch your desktop: unavailable instead


def test_due_switch_waits_for_a_short_pause_then_goes_ahead(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    run_for(eng, clock, 779)
    gate.mark_user_activity()  # you are working in a local app when the switch is due
    run_for(eng, clock, 2)
    snap = eng.snapshot()
    assert eng.focus.calls == [] and kb.sent == []
    assert snap.switch_waiting and "waiting for a 3-second pause" in snap.detail  # panel shows "due"
    gate.mark_user_activity()  # still busy...
    run_for(eng, clock, 2)
    assert eng.focus.calls == [] and eng.snapshot().switch_waiting
    run_for(eng, clock, 3)  # a 3-second pause: it goes ahead
    assert eng.focus.calls == ["forward", "back"] and len(kb.sent) == 2
    snap = eng.snapshot()
    assert not snap.switch_waiting and snap.countdown_s > 770  # next switch a full interval later
    due = [e for e in snap.events if "App switch due" in e.message]
    assert len(due) == 1  # logged once, not every retry


def test_due_switch_waits_for_a_pause_with_the_rdp_window_in_front_too(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    eng.start()
    run_for(eng, clock, 779)
    gate.mark_user_activity()  # you are typing in the RDP window
    run_for(eng, clock, 2)
    assert kb.sent == [] and eng.snapshot().switch_waiting
    assert eng.snapshot().countdown_s <= CFG.retry_s  # not back to 13 minutes
    run_for(eng, clock, 3)
    assert kb.sent == [(("alt", "pageup"), 1), (("pagedown",), 1)]


def test_background_waits_while_a_key_is_held(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    gate.held = ("Shift",)
    run_for(eng, clock, 790)
    assert eng.focus.calls == [] and kb.sent == []
    gate.held = ()
    run_for(eng, clock, 6)
    assert len(kb.sent) == 2


def test_refused_focus_change_retries_in_a_minute(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    eng.focus.refuse = True
    run_for(eng, clock, 781)
    assert kb.sent == [] and eng.focus.calls == ["forward"]  # no keys unless the RDP window is in front
    assert eng.snapshot().countdown_s == pytest.approx(60, abs=1.5)
    eng.focus.refuse = False
    run_for(eng, clock, 61)
    assert len(kb.sent) == 2 and eng.focus.calls == ["forward", "forward", "back"]


def test_focus_change_during_a_borrowed_moment_only_postpones(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    run_for(eng, clock, 779)
    kb.next_result = ActionResult(False, "focus_changed", "Focus left the RDP window")
    run_for(eng, clock, 1)
    snap = eng.snapshot()
    assert snap.state == DisplayState.BACKGROUND and eng.focus.calls == ["forward", "back"]
    assert snap.countdown_s <= BCFG.retry_s and kb.sent == []
    run_for(eng, clock, 2)  # tried again a moment later
    assert len(kb.sent) == 2 and eng.focus.calls == ["forward", "back", "forward", "back"]


def test_switching_between_rdp_and_local_apps_keeps_the_countdown(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    run_for(eng, clock, 400)
    insp.code = OK  # you clicked into the RDP window
    eng.step()
    snap = eng.snapshot()
    assert snap.state == DisplayState.RUNNING and snap.countdown_s == pytest.approx(380)
    run_for(eng, clock, 381)
    assert eng.focus.calls == [] and len(kb.sent) == 2  # in front: no borrowing needed
    assert any("bring it forward for a moment" in e.message for e in eng.snapshot().events)


def test_background_still_stops_for_dialogs_and_closed_windows(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    insp.code = DIALOG
    eng.step()
    assert eng.snapshot().state == DisplayState.UNAVAILABLE
    run_for(eng, clock, 3600)
    assert kb.sent == [] and eng.focus.calls == []
    insp.code = CLOSED
    eng.step()
    assert eng.snapshot().state == DisplayState.STOPPED


def test_test_now_in_background_waits_for_stillness_then_borrows_focus(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_config(BCFG)
    eng.set_target(TARGET)
    insp.code = NOT_FOREGROUND
    gate.mark_user_activity()  # you just clicked "Test now"
    assert eng.test_now()
    eng.step()
    assert kb.sent == [] and "keep still" in eng.snapshot().detail
    run_for(eng, clock, 2)
    assert eng.focus.calls == ["forward", "back"] and len(kb.sent) == 2 and not eng.testing
    assert eng.snapshot().state == DisplayState.STOPPED


BPCFG = EngineConfig(keyboard_enabled=False, pointer_enabled=True, pointer_interval_s=60, pointer_rest_s=3,
                     background_input=True)


def test_background_pointer_moves_only_the_remote_pointer(env):
    eng, clock, insp, gate, kb, mon, ptr = start_background(env, BPCFG)
    snap = eng.snapshot()
    assert snap.pointer_state == PointerState.BACKGROUND and not mon.armed
    run_for(eng, clock, 61)
    assert ptr.glides == 0 and ptr.posted == [{"guard": None, "foreground": False}]
    assert eng.focus.calls == []  # pointer nudges never take focus
    assert eng.snapshot().pointer_countdown_s == pytest.approx(60, abs=1)


def test_pointer_elsewhere_while_rdp_active_moves_remote_pointer_with_idle_guard(env):
    eng, clock, insp, gate, kb, mon, ptr = env
    ptr.ready = False  # your pointer is not over the RDP window
    start_background(env, BPCFG, code=OK)
    run_for(eng, clock, 61)
    assert ptr.glides == 0 and ptr.posted == [{"guard": BPCFG.idle_guard_s, "foreground": True}]


def test_pointer_back_over_rdp_rearms_real_pointer_moves(env):
    eng, clock, insp, gate, kb, mon, ptr = env
    ptr.ready = False
    start_background(env, BPCFG, code=OK)
    assert eng.snapshot().pointer_state == PointerState.BACKGROUND
    ptr.ready = True
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.ARMING
    run_for(eng, clock, 4)
    assert eng.snapshot().pointer_state == PointerState.ACTIVE and mon.armed


def test_manual_control_is_remembered_across_background_periods(env):
    eng, clock, insp, gate, kb, mon, ptr = start_background(env, BPCFG, code=OK)
    run_for(eng, clock, 2)
    assert eng.snapshot().pointer_state == PointerState.ACTIVE
    mon.triggered, mon.reason = True, "mouse moved"
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.MANUAL
    insp.code = NOT_FOREGROUND
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.BACKGROUND
    insp.code = OK
    eng.step()
    assert eng.snapshot().pointer_state == PointerState.MANUAL
    eng.resume_pointer()
    assert eng.snapshot().pointer_state == PointerState.ARMING


def test_background_off_keeps_the_old_behaviour(env):
    eng, clock, insp, gate, kb, *_ = env
    eng.set_target(TARGET)
    insp.code = MINIMIZED
    assert not eng.start()  # foreground-only mode cannot start on a minimized window


def test_borrowed_moment_ignores_the_rdp_clients_own_focus_keys(env):
    eng, clock, insp, gate, kb, *_ = start_background(env)
    run_for(eng, clock, 781)
    assert getattr(gate, "absorbed", 0) == 1  # input caused by bringing the window forward is not you
