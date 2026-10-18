"""The finale can only create and retire its own explicitly identified windows."""

from contextlib import ExitStack
import os
from pathlib import Path
import queue
import shlex
import signal
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import Mock, patch

from ending import windows as ending_windows
from ending.config import (FIRST_PANIC_CLOSE, MAX_PANIC_WINDOWS, PANIC_CLOSE_STEP,
                           PANIC_DURATION, PANIC_STAGGER, panic_close, panic_start)
from fight import windows as fight_windows
TOKEN = "a" * 32
REAL_POPEN = subprocess.Popen


def wait_for(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            raise AssertionError("Desktop worker did not finish")
        threading.Event().wait(0.005)


def drain(events):
    result = []
    while True:
        try:
            result.append(events.get_nowait())
        except queue.Empty:
            return result


class EndingCommandTests(unittest.TestCase):
    def test_titles_match_existing_exact_title_actions(self):
        self.assertEqual(ending_windows.ending_title(TOKEN, "s0", "shell"),
                         fight_windows.window_title("player", TOKEN + "_s0"))
        self.assertEqual(ending_windows.ending_title(TOKEN, "p9", "panic"),
                         fight_windows.window_title("wizard", TOKEN + "_p9"))
        for token, window_id, role in [("", "s0", "shell"), ("a" * 126, "s0", "shell"),
                                        ("'; kill", "s0", "shell"), (TOKEN, "s3", "shell"),
                                        (TOKEN, "p10", "panic"), (TOKEN, "p0", "shell"),
                                        (TOKEN, "s0", "player")]:
            with self.assertRaises(ValueError):
                ending_windows.ending_title(token, window_id, role)

    def test_panic_schedule_and_command_indices_share_the_ten_window_limit(self):
        self.assertEqual(ending_windows.MAX_WINDOWS, MAX_PANIC_WINDOWS)
        self.assertEqual(MAX_PANIC_WINDOWS, 10)
        starts = [panic_start(index) for index in range(MAX_PANIC_WINDOWS)]
        closes = [panic_close(index) for index in range(MAX_PANIC_WINDOWS)]
        self.assertEqual(starts, [index * PANIC_STAGGER for index in range(MAX_PANIC_WINDOWS)])
        self.assertEqual(closes, [FIRST_PANIC_CLOSE + index * PANIC_CLOSE_STEP
                                 for index in range(MAX_PANIC_WINDOWS)])
        self.assertTrue(all(start < close < PANIC_DURATION for start, close in zip(starts, closes)))
        command = ending_windows.ending_command(12345, TOKEN, "p9", "panic", 9)
        self.assertEqual(command[-2:], ["--index", "9"])
        for index in (-1, 10, True, 1.5):
            with self.assertRaises(ValueError):
                ending_windows.ending_command(12345, TOKEN, "p9", "panic", index)
            with self.assertRaises(ValueError):
                panic_start(index)
            with self.assertRaises(ValueError):
                panic_close(index)

    def test_gnome_uses_active_interpreter_project_and_cleans_stale_environment(self):
        executables = {"wmctrl": "/usr/bin/wmctrl", "gnome-terminal": "/usr/bin/gnome-terminal"}
        with patch.dict(os.environ, {"GNOME_TERMINAL_SCREEN": "old", "GNOME_TERMINAL_SERVICE": "old",
                                     "VIRTUAL_ENV": "/active/.venv"}, clear=True), \
             patch.object(ending_windows.platform, "system", return_value="Linux"), \
             patch.object(ending_windows.platform, "release", return_value="generic"), \
             patch.object(ending_windows.shutil, "which", side_effect=executables.get), \
             patch.object(ending_windows.sys, "executable", "/active/.venv/bin/python"):
            command, env = ending_windows.launch_command(12345, TOKEN, "p3", "panic", 3)
        self.assertEqual(command[0], "/usr/bin/gnome-terminal")
        self.assertEqual(command[command.index("--") + 1:],
                         ["/active/.venv/bin/python", "-B", "-m", "ending.window",
                          "--port", "12345", "--token", TOKEN, "--window-id", "p3",
                          "--role", "panic", "--index", "3"])
        self.assertNotIn("GNOME_TERMINAL_SCREEN", env)
        self.assertNotIn("GNOME_TERMINAL_SERVICE", env)
        self.assertEqual(env["VIRTUAL_ENV"], "/active/.venv")

    def test_xterm_is_a_separate_direct_child_terminal(self):
        executables = {"wmctrl": "/bin/wmctrl", "xterm": "/bin/xterm"}
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(ending_windows.platform, "system", return_value="Linux"), \
             patch.object(ending_windows.platform, "release", return_value="generic"), \
             patch.object(ending_windows.shutil, "which", side_effect=executables.get):
            command, _ = ending_windows.launch_command(12345, TOKEN, "s1", "shell", 1)
        self.assertEqual(command[:4], ["/bin/xterm", "-T", ending_windows.ending_title(TOKEN, "s1", "shell"), "-e"])
        self.assertEqual(command[4], ending_windows.sys.executable)

    def test_wsl_uses_current_distribution_and_python_for_both_launchers(self):
        for launcher in ("wt.exe", "cmd.exe"):
            executables = {launcher: launcher, "powershell.exe": "powershell.exe"}
            with self.subTest(launcher=launcher), \
                 patch.dict(os.environ, {"WSL_DISTRO_NAME": "My-Actual-Distro"}, clear=True), \
                 patch.object(ending_windows.shutil, "which", side_effect=executables.get), \
                 patch.object(ending_windows.sys, "executable", "/project/.venv/bin/python"):
                command, _ = ending_windows.launch_command(12345, TOKEN, "p0", "panic")
            offset = command.index("wsl.exe")
            self.assertEqual(command[offset:offset + 8],
                             ["wsl.exe", "--distribution", "My-Actual-Distro", "--cd",
                              str(ending_windows.PROJECT), "--exec", "/project/.venv/bin/python", "-B"])
            if launcher == "wt.exe":
                self.assertIn("--suppressApplicationTitle", command)
                self.assertEqual(command[1:3], ["--window", "new"])

    def test_unknown_wsl_distribution_and_unscopable_linux_refuse_launch(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(ending_windows.platform, "release", return_value="microsoft-standard"), \
             patch.object(ending_windows.shutil, "which", return_value="wt.exe"):
            with self.assertRaisesRegex(OSError, "active WSL distribution"):
                ending_windows.launch_command(12345, TOKEN, "s0", "shell")
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "wayland"}, clear=True), \
             patch.object(ending_windows.platform, "system", return_value="Linux"), \
             patch.object(ending_windows.platform, "release", return_value="generic"), \
             patch.object(ending_windows.shutil, "which", return_value="/usr/bin/gnome-terminal"):
            with self.assertRaisesRegex(OSError, "X11"):
                ending_windows.launch_command(12345, TOKEN, "s0", "shell")

    def test_macos_quotes_fixed_exec_command_and_sets_exact_custom_title(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(ending_windows.platform, "system", return_value="Darwin"), \
             patch.object(ending_windows.platform, "release", return_value="darwin"), \
             patch.object(ending_windows.sys, "executable", "/Python Path/bin/python"), \
             patch.object(ending_windows, "PROJECT", Path("/Project With Spaces")):
            command, _ = ending_windows.launch_command(12345, TOKEN, "p1", "panic", 1)
        self.assertEqual(command[0], "osascript")
        self.assertEqual(shlex.split(command[3])[:8],
                         ["cd", "/Project With Spaces", "&&", "exec",
                          "/Python Path/bin/python", "-B", "-m", "ending.window"])
        self.assertIn("set custom title of gameTab", command[2])
        self.assertEqual(command[-1], ending_windows.ending_title(TOKEN, "p1", "panic"))

    def test_desktop_cleanup_uses_short_timeouts_and_only_an_exact_x11_title(self):
        title = ending_windows.ending_title(TOKEN, "p0", "panic")
        windows = f"0x01 0 host prefix {title}\n0x02 0 host {title}-extra\n0x03 0 host {title}\n"
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=True), \
             patch.object(ending_windows.platform, "system", return_value="Linux"), \
             patch.object(ending_windows.platform, "release", return_value="generic"), \
             patch.object(ending_windows.shutil, "which", return_value="/bin/wmctrl"), \
             patch.object(fight_windows, "_run", side_effect=[windows, ""]) as run:
            self.assertTrue(ending_windows._desktop_action("wizard", TOKEN + "_p0", "close"))
        self.assertEqual(run.call_args.args, (["wmctrl", "-ic", "0x03"], ending_windows._DESKTOP_TIMEOUT))

    def test_timed_out_desktop_action_reports_unconfirmed_cleanup(self):
        with patch.dict(os.environ, {"WSL_DISTRO_NAME": "Actual-Distro"}, clear=True), \
             patch.object(fight_windows, "_run", side_effect=subprocess.TimeoutExpired("powershell.exe", 0.8)) as run:
            self.assertFalse(ending_windows._desktop_action("wizard", TOKEN + "_p0", "close"))
        self.assertEqual(run.call_args.args[1], ending_windows._DESKTOP_TIMEOUT)


class EndingManagerTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(ending_windows, "_LAUNCH_GRACE", 0))
        self.stack.enter_context(patch.object(ending_windows, "_CLEANUP_DELAYS", (0,)))
        self.stack.enter_context(patch.object(ending_windows, "_CLOSE_JOIN_SECONDS", 2))
        self.command = self.stack.enter_context(patch.object(ending_windows, "launch_command", return_value=(["terminal"], {})))
        self.popen = self.stack.enter_context(patch.object(ending_windows.subprocess, "Popen"))
        self.popen.return_value.poll.return_value = 0
        self.close_owned = self.stack.enter_context(patch.object(ending_windows, "_desktop_action", return_value=True))
        self.manager = ending_windows.EndingWindows()
        self.addCleanup(self.manager.close)

    def idle(self):
        wait_for(lambda: not self.manager._threads)

    def test_ten_window_limit_includes_pending_launches(self):
        entered, release = threading.Event(), threading.Event()
        def pending(*args, **kwargs):
            entered.set()
            release.wait(2)
            return Mock(poll=Mock(return_value=0))
        self.popen.side_effect = pending
        for index in range(MAX_PANIC_WINDOWS):
            self.assertTrue(self.manager.launch(f"p{index}", "panic", 12345, TOKEN, index))
        self.assertTrue(entered.wait(1))
        self.assertFalse(self.manager.launch("s0", "shell", 12345, TOKEN))
        self.assertFalse(self.manager.launch("p0", "panic", 12345, TOKEN))
        release.set()
        self.idle()
        self.assertEqual(self.popen.call_count, MAX_PANIC_WINDOWS)

    def test_dispatcher_zero_exit_does_not_report_child_closed(self):
        self.assertTrue(self.manager.launch("s0", "shell", 12345, TOKEN))
        self.idle()
        self.assertEqual(drain(self.manager.events), [("launched", "s0", "")])
        self.assertTrue(self.manager._windows["s0"].active)
        self.assertNotIn("shell", self.popen.call_args.kwargs)

    def test_launch_errors_are_events_and_release_the_active_slot(self):
        self.popen.side_effect = OSError("desktop unavailable")
        self.assertTrue(self.manager.launch("s0", "shell", 12345, TOKEN))
        self.idle()
        self.assertEqual(drain(self.manager.events), [("launch_error", "s0", "desktop unavailable"),
                                                      ("closed", "s0", "")])
        self.assertFalse(self.manager._windows["s0"].active)
        self.popen.side_effect = None
        self.popen.return_value.poll.return_value = 7
        self.assertTrue(self.manager.launch("s1", "shell", 12345, TOKEN))
        self.idle()
        event = self.manager.events.get_nowait()
        self.assertEqual(event[:2], ("launch_error", "s1"))
        self.assertIn("7", event[2])

    def test_unavailable_launch_returns_false_and_reports_why(self):
        self.command.side_effect = OSError("No supported terminal")
        self.assertFalse(self.manager.launch("s0", "shell", 12345, TOKEN))
        self.assertEqual(self.manager.events.get_nowait(), ("launch_error", "s0", "No supported terminal"))
        self.popen.assert_not_called()

    def test_cancel_during_dispatch_closes_late_window_and_reports_once(self):
        entered, release = threading.Event(), threading.Event()
        def pending(*args, **kwargs):
            entered.set()
            release.wait(2)
            return Mock(poll=Mock(return_value=0))
        self.popen.side_effect = pending
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.assertTrue(entered.wait(1))
        self.manager.close_window("s0")
        self.manager.close_window("s0")
        self.assertTrue(self.manager._windows["s0"].active)
        release.set()
        self.idle()
        self.assertTrue(self.close_owned.called)
        self.assertTrue(all(call.args == ("player", TOKEN + "_s0", "close") for call in self.close_owned.call_args_list))
        self.assertEqual(drain(self.manager.events), [("closed", "s0", "")])
        self.assertFalse(self.manager._windows["s0"].active)

    def test_cancel_before_dispatch_does_not_open_a_terminal(self):
        with patch.object(self.manager, "_spawn"):
            self.manager.launch("s0", "shell", 12345, TOKEN)
            self.manager.close_window("s0")
            self.manager._launch(self.manager._windows["s0"])
            self.manager._cleanup(self.manager._windows["s0"])
        self.popen.assert_not_called()
        self.assertEqual(drain(self.manager.events), [("closed", "s0", "")])

    def test_unconfirmed_window_keeps_its_slot_in_the_ten_window_cap(self):
        for index in range(MAX_PANIC_WINDOWS):
            self.manager.launch(f"p{index}", "panic", 12345, TOKEN, index)
        self.idle()
        self.close_owned.return_value = False
        self.manager.close_window("p0")
        self.idle()
        self.assertTrue(self.manager._windows["p0"].active)
        self.assertFalse(self.manager.launch("s0", "shell", 12345, TOKEN))

    def test_unconfirmed_close_has_manual_fallback_and_close_is_idempotent(self):
        self.close_owned.return_value = False
        self.manager.launch("p2", "panic", 12345, TOKEN, 2)
        self.idle()
        drain(self.manager.events)
        self.manager.close()
        self.manager.close()
        events = drain(self.manager.events)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][:2], ("closed", "p2"))
        self.assertIn("manually", events[0][2])
        self.assertFalse(self.manager.launch("s0", "shell", 12345, TOKEN))

    def test_close_has_a_bound_even_when_dispatch_is_stuck(self):
        entered, release = threading.Event(), threading.Event()
        def pending(*args, **kwargs):
            entered.set()
            release.wait(2)
            return Mock(poll=Mock(return_value=0))
        self.popen.side_effect = pending
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.assertTrue(entered.wait(1))
        with patch.object(ending_windows, "_CLOSE_JOIN_SECONDS", 0.03):
            start = time.monotonic()
            self.manager.close()
            self.assertLess(time.monotonic() - start, 0.15)
        release.set()
        self.idle()
        self.assertEqual(drain(self.manager.events), [("closed", "s0", "")])

    def test_close_terminates_kills_and_reaps_its_exact_live_dispatcher(self):
        process = Mock()
        state = [None]
        process.poll.side_effect = lambda: state[0]
        def wait(timeout=None):
            if state[0] is None:
                raise subprocess.TimeoutExpired("terminal", timeout)
            return state[0]
        process.wait.side_effect = wait
        process.kill.side_effect = lambda: state.__setitem__(0, -signal.SIGKILL)
        self.popen.return_value = process
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.idle()
        self.manager.close()
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertEqual(process.poll(), -signal.SIGKILL)
        self.assertFalse(self.manager._threads)

    def test_close_reaps_a_real_live_owned_launcher_process(self):
        process = REAL_POPEN([sys.executable, "-B", "-c", "import time; time.sleep(30)"],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def retire():
            if process.poll() is None:
                process.kill()
            process.wait(timeout=2)
        self.addCleanup(retire)
        self.popen.return_value = process
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.idle()
        self.assertIsNone(process.poll())
        self.manager.close()
        self.assertIsNotNone(process.poll())
        self.assertFalse(self.manager._threads)

    def test_close_waits_for_racing_launch_and_reaps_it_before_returning(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        process = Mock()
        state = [None]
        process.poll.side_effect = lambda: state[0]
        process.terminate.side_effect = lambda: state.__setitem__(0, -signal.SIGTERM)
        process.wait.side_effect = lambda timeout=None: state[0]
        def pending(*args, **kwargs):
            entered.set()
            release.wait(2)
            return process
        self.popen.side_effect = pending
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.assertTrue(entered.wait(1))
        closer = threading.Thread(target=lambda: (self.manager.close(), finished.set()))
        closer.start()
        self.assertFalse(finished.wait(0.03))
        release.set()
        closer.join(2)
        self.assertTrue(finished.is_set())
        process.terminate.assert_called_once_with()
        self.assertFalse(self.manager._threads)
        self.assertEqual(drain(self.manager.events), [("closed", "s0", "")])

    def test_only_authenticated_command_and_birth_identity_can_be_signalled(self):
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.idle()
        window = self.manager._windows["s0"]
        identity = ("birth", *window.child_command)
        with patch.object(ending_windows, "_process_identity", return_value=identity), \
             patch.object(ending_windows.os, "pidfd_open", side_effect=OSError, create=True), \
             patch.object(ending_windows.os, "kill") as kill:
            self.manager.register_pid("s0", 987654)
            self.idle()
            self.assertEqual(window.pid, 987654)
            self.assertTrue(self.manager._signal_child(window, signal.SIGTERM))
            kill.assert_called_once_with(987654, signal.SIGTERM)
            kill.reset_mock()
            with patch.object(ending_windows, "_process_identity", return_value=("recycled", *window.child_command)):
                self.assertFalse(self.manager._signal_child(window, signal.SIGKILL))
            kill.assert_not_called()
        # Do not let test teardown inspect or signal the fabricated PID.
        window.pid = None

    def test_unrelated_and_unregistered_pids_are_ignored(self):
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.idle()
        with patch.object(ending_windows, "_process_identity", return_value=None), \
             patch.object(ending_windows.os, "kill") as kill:
            self.manager.register_pid("s0", 987654)
            self.manager.register_pid("absent", 987654)
            self.manager.register_pid("s0", os.getpid())
            self.idle()
            self.manager.close_window("s0")
            self.idle()
        kill.assert_not_called()

    def test_late_authenticated_pid_is_cleaned_after_an_earlier_window_close(self):
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.idle()
        self.manager.close_window("s0")
        self.idle()
        window = self.manager._windows["s0"]
        identity = ("birth", *window.child_command)
        current = [identity]
        with patch.object(ending_windows, "_process_identity", side_effect=lambda *args: current[0]), \
             patch.object(ending_windows.os, "pidfd_open", side_effect=OSError, create=True), \
             patch.object(ending_windows.time, "sleep"), \
             patch.object(ending_windows.os, "kill", side_effect=lambda *args: current.__setitem__(0, None)) as kill:
            self.manager.register_pid("s0", 987654)
            self.idle()
        kill.assert_called_once_with(987654, signal.SIGTERM)
        self.assertEqual(len([event for event in drain(self.manager.events) if event[0] == "closed"]), 1)
        window.pid = None

    def test_registration_after_manager_close_is_synchronous_and_retires_child(self):
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.idle()
        self.manager.close()
        window = self.manager._windows["s0"]
        current = [("birth", *window.child_command)]
        with patch.object(ending_windows, "_process_identity", side_effect=lambda *args: current[0]), \
             patch.object(ending_windows.os, "pidfd_open", side_effect=OSError, create=True), \
             patch.object(ending_windows.time, "sleep"), \
             patch.object(ending_windows.os, "kill", side_effect=lambda *args: current.__setitem__(0, None)) as kill, \
             patch.object(self.manager, "_spawn") as spawn:
            self.manager.register_pid("s0", 987654)
        kill.assert_called_once_with(987654, signal.SIGTERM)
        spawn.assert_not_called()
        self.assertFalse(self.manager._threads)
        window.pid = None

    def test_child_command_requires_all_exact_identity_arguments(self):
        expected = tuple(ending_windows.ending_command(12345, TOKEN, "p1", "panic", 1))
        self.assertTrue(ending_windows._same_command(expected, expected))
        for changed in (expected[:-1], (*expected[:-1], "2"),
                        tuple("other" if arg == TOKEN else arg for arg in expected),
                        tuple("fight.wizard" if arg == "ending.window" else arg for arg in expected)):
            self.assertFalse(ending_windows._same_command(changed, expected))

    def test_x11_scatter_uses_exact_owned_title_and_desktop_work_area(self):
        self.manager.launch("p9", "panic", 12345, TOKEN, 9)
        self.idle()
        window = self.manager._windows["p9"]
        title = ending_windows.ending_title(TOKEN, "p9", "panic")
        windows = f"0x01 0 host prefix {title}\n0x02 0 host {title}-extra\n0x03 0 host {title}\n"
        desktop = "0 * DG: 1920x1080 VP: 0,0 WA: 0,30 1920x1050 N/A\n"
        with patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=True), \
             patch.object(ending_windows.platform, "system", return_value="Linux"), \
             patch.object(ending_windows.platform, "release", return_value="generic"), \
             patch.object(ending_windows.shutil, "which", return_value="/bin/wmctrl"), \
             patch.object(fight_windows, "_run", side_effect=[windows, desktop, ""]) as run:
            self.manager._arrange_window(window)
        self.assertEqual(run.call_args.args[0], ["wmctrl", "-ir", "0x03", "-e", "0,0,660,700,420"])
        self.assertTrue(all(call.args[1] == ending_windows._DESKTOP_TIMEOUT for call in run.call_args_list))

    def test_all_ten_scattered_windows_stay_inside_small_and_offset_work_areas(self):
        self.manager.launch("p9", "panic", 12345, TOKEN, 9)
        self.idle()
        window = self.manager._windows["p9"]
        title = ending_windows.ending_title(TOKEN, "p9", "panic")
        windows = f"0x03 0 host {title}\n"
        for left, top, available_width, available_height in ((0, 30, 1920, 1050),
                                                            (-1920, 25, 1920, 1055),
                                                            (0, 0, 240, 160)):
            desktop = (f"0 * DG: 1920x1080 VP: 0,0 WA: {left},{top} "
                       f"{available_width}x{available_height} N/A\n")
            for index in range(MAX_PANIC_WINDOWS):
                window.index = index
                with self.subTest(area=(left, top, available_width, available_height), index=index), \
                     patch.dict(os.environ, {"XDG_SESSION_TYPE": "x11"}, clear=True), \
                     patch.object(ending_windows.platform, "system", return_value="Linux"), \
                     patch.object(ending_windows.platform, "release", return_value="generic"), \
                     patch.object(ending_windows.shutil, "which", return_value="/bin/wmctrl"), \
                     patch.object(fight_windows, "_run", side_effect=[windows, desktop, ""]) as run:
                    self.manager._arrange_window(window)
                    _, x, y, width, height = map(int, run.call_args.args[0][-1].split(","))
                    self.assertGreaterEqual(x, left)
                    self.assertGreaterEqual(y, top)
                    self.assertLessEqual(x + width, left + available_width)
                    self.assertLessEqual(y + height, top + available_height)

    def test_authenticated_shell_gets_exact_focus_and_cancelled_window_does_not_move(self):
        self.manager.launch("s0", "shell", 12345, TOKEN)
        self.idle()
        window = self.manager._windows["s0"]
        self.manager._arrange_window(window)
        self.close_owned.assert_called_once_with("player", TOKEN + "_s0", "focus")
        self.close_owned.reset_mock()
        window.cancelled.set()
        self.manager._arrange_window(window)
        self.close_owned.assert_not_called()
        # Teardown still needs to request this test's synthetic cancellation.
        self.manager._request_cleanup(window)

    def test_focus_only_calls_exact_existing_player_helper(self):
        with patch.object(ending_windows, "_desktop_action") as focus:
            self.manager.focus_player(TOKEN)
            self.idle()
        focus.assert_called_once_with("player", TOKEN, "focus")
        self.close_owned.assert_not_called()


class ChildSelfCloseTests(unittest.TestCase):
    def test_child_self_close_launches_only_a_scoped_close_helper(self):
        with patch.object(ending_windows.subprocess, "Popen") as popen, \
             patch.object(ending_windows.os, "getpid", return_value=12345):
            self.assertTrue(ending_windows.close_ending_window(TOKEN, "p4", "panic"))
        command = popen.call_args.args[0]
        self.assertEqual(command[:4], [sys.executable, "-B", "-m", "ending.windows"])
        self.assertEqual(command[-6:], ["--close", TOKEN, "p4", "panic", "--after-pid", "12345"])
        self.assertEqual(popen.call_args.kwargs["cwd"], ending_windows.PROJECT)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        self.assertNotIn("shell", popen.call_args.kwargs)
        with patch.object(fight_windows, "_process_alive", side_effect=[True, False]), \
             patch.object(ending_windows.time, "sleep") as delay, \
             patch.object(ending_windows, "_desktop_action") as close:
            ending_windows._close_after_exit(TOKEN, "p4", "panic", 12345)
        delay.assert_called_once_with(0.04)
        close.assert_called_once_with("wizard", TOKEN + "_p4", "close")

    def test_self_close_helper_stops_waiting_after_its_short_deadline(self):
        with patch.object(fight_windows, "_process_alive", return_value=True), \
             patch.object(ending_windows.time, "monotonic", side_effect=[0.0, 1.0]), \
             patch.object(ending_windows, "_desktop_action") as close:
            ending_windows._close_after_exit(TOKEN, "p4", "panic", 12345)
        close.assert_not_called()


if __name__ == "__main__":
    unittest.main()
