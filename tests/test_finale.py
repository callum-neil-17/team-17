"""The false exit has one controller, a bounded lifetime and scoped children."""

import contextlib
import io
import queue
import unittest
from unittest.mock import patch

import ending
import game
from terminal_input import END, ESCAPE


class Listener:
    def bind(self, address): pass
    def listen(self, count): pass
    def setblocking(self, blocking): pass
    def getsockname(self): return ("127.0.0.1", 43210)
    def accept(self): raise BlockingIOError
    def close(self): self.closed = True


class Peer:
    eof = False

    def __init__(self):
        self.sent = []
        self.incoming = []
        self.closed = False

    def send(self, message): self.sent.append(message)
    def close(self): self.closed = True
    def poll(self):
        messages, self.incoming = self.incoming, []
        return messages


class Windows:
    def __init__(self, supported=True):
        self.events = queue.SimpleQueue()
        self.supported = supported
        self.launched = []
        self.retired = []
        self.registered = []
        self.active = set()
        self.peak = 0
        self.focused = []
        self.closed = 0

    def launch(self, window_id, role, port, token, index=0):
        self.launched.append((window_id, role, index))
        if not self.supported:
            return False
        self.active.add(window_id)
        self.peak = max(self.peak, len(self.active))
        return True

    def close_window(self, window_id):
        if window_id in self.active:
            self.active.remove(window_id)
            self.retired.append(window_id)
            self.events.put(("closed", window_id, ""))

    def register_pid(self, window_id, pid): self.registered.append((window_id, pid))
    def focus_player(self, token): self.focused.append(token)
    def close(self): self.closed += 1


class FinaleTests(unittest.TestCase):
    def setUp(self):
        self.clock = [100.0]
        self.windows = Windows()
        self.listener_patch = patch.object(ending.socket, "socket", return_value=Listener())
        self.listener_patch.start()
        self.addCleanup(self.listener_patch.stop)
        self.controller = ending.FinaleController("original-player", windows=self.windows,
                                                 clock=lambda: self.clock[0])
        self.addCleanup(self.controller.close)
        self.controller.start()

    def connect(self, child_id=None):
        child_id = child_id or self.controller.shell_id
        child = self.controller.children[child_id]
        peer = Peer()
        self.assertTrue(self.controller._hello(peer, {
            "type": "hello", "token": self.controller.token,
            "window_id": child_id, "role": child.role, "pid": 12345 + len(self.windows.registered),
        }, self.clock[0]))
        return peer

    def advance(self, seconds):
        self.clock[0] += seconds
        for child in self.controller.children.values():
            if child.peer is not None:
                child.peer.incoming.append({"type": "pong"})
        self.controller.tick()

    def test_only_end_solves_and_repeated_end_cannot_overlap(self):
        peer = self.connect()
        for key in ("e", "n", "d", "\r", ESCAPE, "\x1b[F", "x"):
            self.controller.handle_key(key)
        self.assertEqual(self.controller.phase, "shell")
        self.controller.handle_key(END)
        self.assertEqual(self.controller.phase, "crash")
        self.assertFalse(self.controller.reopening_enabled)
        for _ in range(4):
            self.controller.handle_key(END)
        self.assertEqual(sum(message.get("scene") == "crash" for message in peer.sent), 1)
        peer.eof = True
        self.advance(0.1)
        self.assertEqual(len(self.windows.launched), 1)
        self.assertTrue(self.controller.inline)

    def test_close_reopens_twice_with_same_puzzle_then_exits(self):
        first_started = None
        for attempt in range(3):
            peer = self.connect()
            first_started = first_started or self.controller.shell_started
            self.assertEqual(self.controller.shell_started, first_started)
            scene = next(message for message in peer.sent if message.get("scene") == "shell")
            self.assertEqual(scene["reopened"], attempt)
            self.assertAlmostEqual(scene["elapsed"], self.clock[0] - first_started)
            self.clock[0] += 1
            peer.eof = True
            self.controller.tick()
        self.assertEqual(self.controller.reopenings, 2)
        self.assertEqual([item[0] for item in self.windows.launched], ["s0", "s1", "s2"])
        self.assertEqual(self.controller.phase, "aborted")

    def test_emergency_exit_wins_over_close_and_never_reopens(self):
        peer = self.connect()
        peer.eof = True
        self.controller.handle_key("\x03")
        self.advance(1)
        self.controller.close()
        self.controller.close()
        self.assertEqual(self.controller.phase, "aborted")
        self.assertEqual(len(self.windows.launched), 1)
        self.assertEqual(self.windows.closed, 1)
        self.assertTrue(peer.closed)

    def test_queued_ctrl_c_is_read_before_socket_eof_in_real_loop(self):
        peer = self.connect()
        peer.eof = True
        with patch.object(ending, "FinaleController", return_value=self.controller), \
             contextlib.redirect_stdout(io.StringIO()):
            completed = ending.run_finale(123, "original-player", read_input=lambda *a, **k: "\x03")
        self.assertFalse(completed)
        self.assertEqual([item[0] for item in self.windows.launched], ["s0"])
        self.assertTrue(self.controller.closed)

    def test_real_window_path_has_six_copies_then_returns_to_original(self):
        self.connect()
        self.controller.handle_key(END)
        self.advance(ending.CRASH_DURATION)
        self.assertEqual(self.controller.phase, "closing_shell")
        self.advance(0)
        self.assertEqual(self.controller.phase, "panic")
        panic_started = self.controller.phase_started
        for _ in range(6):
            for child in list(self.controller.children.values()):
                if child.role == "panic" and child.peer is None:
                    self.connect(child.window_id)
            self.advance(ending.PANIC_STAGGER + 0.001)
        for child in list(self.controller.children.values()):
            if child.role == "panic" and child.peer is None:
                self.connect(child.window_id)
        self.assertEqual(self.controller.panic_spawned, 6)
        self.assertEqual(self.windows.peak, 6)
        for close_offset in (5.5, 5.9, 6.3, 6.7, 7.1, 7.5, 8.0):
            self.advance(max(0, panic_started + close_offset - self.clock[0]) + 0.001)
            self.advance(0)
        self.assertEqual(self.controller.phase, "true_end")
        self.assertEqual([name for name in self.windows.retired if name.startswith("p")],
                         [f"p{index}" for index in range(6)])
        self.assertFalse(self.windows.active)
        self.assertIn("original-player", self.windows.focused)
        self.advance(0.8)
        self.assertIn("THE END", self.controller.render((80, 24)))
        self.advance(ending.TRUE_END_DURATION)
        self.assertEqual(self.controller.phase, "done")

    def test_failed_launch_uses_complete_inline_ending(self):
        self.controller.close()
        windows = Windows(supported=False)
        controller = ending.FinaleController("original-player", windows=windows,
                                             clock=lambda: self.clock[0])
        self.addCleanup(controller.close)
        controller.start()
        self.assertTrue(controller.inline)
        self.clock[0] += 5
        controller.tick()
        self.assertIn("You managed to escape my curse", controller.render((100, 30)))
        controller.handle_key(END)
        self.clock[0] += ending.CRASH_DURATION
        controller.tick()
        self.assertEqual(controller.phase, "panic")
        self.assertTrue(controller.panic_fallback)
        self.clock[0] += ending.PANIC_DURATION
        controller.tick()
        self.assertEqual(controller.phase, "true_end")
        self.assertEqual(len(windows.launched), 1)

    def test_missing_hello_uses_fallback_instead_of_relaunch_loop(self):
        self.advance(ending.HELLO_TIMEOUT)
        self.assertEqual(self.controller.phase, "shell")
        self.assertTrue(self.controller.inline)
        self.assertEqual(self.controller.reopenings, 0)
        self.assertEqual(len(self.windows.launched), 1)

    def test_unconfirmed_desktop_closure_continues_inline_with_manual_guidance(self):
        self.connect()
        self.controller.handle_key(END)
        self.advance(ending.CRASH_DURATION)
        while not self.windows.events.empty():
            self.windows.events.get_nowait()
        self.windows.events.put(("closed", "s0", "Desktop closure failed"))
        self.advance(0)
        self.assertEqual(self.controller.phase, "panic")
        self.assertTrue(self.controller.panic_fallback)
        self.assertIn("manually", self.controller.window_warning)
        self.assertEqual(self.controller.panic_spawned, 6)

    def test_invalid_authentication_never_registers_or_owns_a_pid(self):
        peer = Peer()
        self.assertFalse(self.controller._hello(peer, {
            "type": "hello", "token": "wrong", "window_id": "s0",
            "role": "shell", "pid": 2345,
        }, self.clock[0]))
        self.assertFalse(self.windows.registered)
        self.assertIsNone(self.controller.children["s0"].peer)

    def test_socket_setup_failure_still_offers_inline_puzzle(self):
        with patch.object(ending.socket, "socket", side_effect=OSError("unavailable")):
            controller = ending.FinaleController("original-player", windows=Windows(),
                                                 clock=lambda: self.clock[0])
        self.addCleanup(controller.close)
        controller.start()
        self.assertTrue(controller.inline)
        self.assertEqual(controller.phase, "shell")


class FinaleIntegrationTests(unittest.TestCase):
    def test_false_exit_runs_only_after_escape_and_restores_tty_afterwards(self):
        for escaped in (False, True):
            with self.subTest(escaped=escaped), \
                 patch.object(game.termios, "tcgetattr", return_value="original"), \
                 patch.object(game.termios, "tcsetattr") as restore, \
                 patch.object(game.tty, "setraw"), \
                 patch.object(game, "play_fight", return_value=escaped), \
                 patch.object(game, "run_finale", return_value=True) as finale, \
                 contextlib.redirect_stdout(io.StringIO()):
                game.main(start_ending=True, window_token="test-player")
            self.assertEqual(finale.call_count, int(escaped))
            restore.assert_called_once()


if __name__ == "__main__":
    unittest.main()
