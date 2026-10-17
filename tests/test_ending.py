"""The final spell must make one return trip and leave both terminals clean."""

import contextlib
import errno
import fcntl
import io
import os
from pathlib import Path
import pty
import queue
import socket
import struct
import subprocess
import sys
import termios
import time
import unittest
from unittest.mock import patch

import fight
import game


PROJECT = Path(__file__).resolve().parents[1]


def drain_terminal(fd: int, output: bytearray) -> None:
    """Read an available PTY frame, including the normal close-on-exit case."""
    try:
        while chunk := os.read(fd, 65536):
            output.extend(chunk)
    except BlockingIOError:
        pass
    except OSError as error:
        if error.errno != errno.EIO:
            raise


class EndingFightTests(unittest.TestCase):
    def setUp(self):
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.size = patch.object(fight, "terminal_size", return_value=(60, 30))
        self.size.start()
        self.addCleanup(self.size.stop)
        self.session = fight.PlayerFight(start_level=11)
        self.addCleanup(self.session.close)

    def connect(self):
        peer = fight.JsonPeer(socket.create_connection(("127.0.0.1", self.session.port)))
        self.addCleanup(peer.close)
        peer.send({"type": "hello", "token": self.session.token, "columns": 50, "rows": 28})
        self.session.tick()
        messages = peer.poll()
        self.assertEqual(self.session.state, "preparing")
        self.assertTrue(any(message.get("number") == 11 for message in messages))
        self.assertTrue(any(message["type"] == "layout" for message in messages))
        peer.send({"type": "ready"})
        self.session.tick()
        cast = next(message for message in peer.poll() if message["type"] == "cast")
        self.assertEqual(cast["id"], 2)
        self.assertEqual(cast["glyph"], fight.SPELL)
        self.assertEqual(self.session.state, "wizard_spell")
        return peer

    def wait_for_undo(self, peer):
        peer.send({"type": "handoff", "id": 2})
        self.session.tick()
        self.assertEqual(self.session.state, "player_spell")
        self.session.tick(self.session.last_tick + 4)
        self.assertEqual(self.session.state, "awaiting_undo")
        self.assertEqual(self.session.player_x, fight.STOP_X)

    def return_spell(self, peer):
        self.wait_for_undo(peer)
        self.session.handle_key("\x1a")
        self.assertEqual(self.session.state, "return_player")
        self.session.tick(self.session.last_tick + 4)
        self.assertEqual(self.session.state, "return_wizard")
        messages = peer.poll()
        returns = [message for message in messages if message["type"] == "return"]
        self.assertEqual(returns, [{"type": "return", "id": 2, "glyph": fight.SPELL[::-1],
                                    "row": self.session.row, "speed": fight.SPEED}])

    def test_one_ctrl_z_returns_spell_and_finishes_without_more_input(self):
        peer = self.connect()
        self.return_spell(peer)
        for key in ("\x1a", "\x1a", "\r", "q", None):
            self.session.handle_key(key)
        self.session.tick(self.session.last_tick + 0.1)
        self.assertEqual(self.session.state, "return_wizard")
        self.assertFalse(any(message["type"] == "return" for message in peer.poll()))
        peer.send({"type": "impact", "id": 2})
        self.session.tick()
        self.assertEqual(self.session.state, "defeating")
        self.session.handle_key("\x1a")
        self.assertEqual(self.session.state, "defeating")
        peer.send({"type": "death_complete", "id": 2})
        self.session.tick()
        self.assertEqual(self.session.state, "epilogue")
        self.assertIsNone(self.session.peer)
        self.assertEqual(self.session.listener.fileno(), -1)
        self.assertIn("ESCAPE TERMINAL", self.session.render())
        self.session.handle_key("\x1a")
        self.assertEqual(self.session.state, "epilogue")

    def test_early_ctrl_z_is_latched_until_the_spell_reaches_player(self):
        peer = self.connect()
        for _ in range(4):
            self.session.handle_key("\x1a")
        self.assertEqual(self.session.state, "wizard_spell")
        peer.send({"type": "handoff", "id": 2})
        self.session.tick()
        self.assertEqual(self.session.state, "player_spell")
        self.session.tick(self.session.last_tick + 4)
        self.assertEqual(self.session.state, "return_player")
        self.assertEqual(self.session.player_x, fight.STOP_X)
        self.session.tick(self.session.last_tick + 4)
        messages = peer.poll()
        self.assertEqual(sum(message["type"] == "return" for message in messages), 1)

    def test_only_ctrl_z_solves_the_undo_puzzle_and_old_spell_events_are_ignored(self):
        peer = self.connect()
        peer.send({"type": "handoff", "id": 1})
        self.session.tick()
        self.assertEqual(self.session.state, "wizard_spell")
        self.wait_for_undo(peer)
        for key in ("\r", "\n", "z", "Z", "q", "\x03", "\x7f", None):
            self.session.handle_key(key)
            self.assertEqual(self.session.state, "awaiting_undo")
        self.session.tick(self.session.last_tick + 0.5)
        self.assertEqual(self.session.player_x, fight.STOP_X)
        peer.send({"type": "impact", "id": 1})
        peer.send({"type": "death_complete", "id": 1})
        self.session.tick()
        self.assertEqual(self.session.state, "awaiting_undo")

    def test_epilogue_waits_for_owned_wizard_window_closure(self):
        class Windows:
            def __init__(self):
                self.events = queue.SimpleQueue()
                self.finished = []

            def finish_wizard(self, token):
                self.finished.append(token)

            def close(self):
                pass

        peer = self.connect()
        self.return_spell(peer)
        windows = Windows()
        self.session.windows = windows
        peer.send({"type": "impact", "id": 2})
        self.session.tick()
        peer.send({"type": "death_complete", "id": 2})
        self.session.tick()
        self.assertEqual(self.session.state, "closing_wizard")
        self.assertEqual(windows.finished, [self.session.token])
        peer.close()
        for _ in range(3):
            self.session.handle_key("\x1a")
            self.session.tick()
        self.assertEqual(self.session.state, "closing_wizard")
        self.assertEqual(windows.finished, [self.session.token])
        windows.events.put(("wizard_closed", ""))
        self.session.tick()
        self.assertEqual(self.session.state, "epilogue")

    def test_real_wizard_pty_reverses_and_plays_whole_death_sequence(self):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 50, 0, 0))
        env = os.environ.copy()
        env.pop("COLUMNS", None)
        env.pop("LINES", None)
        process = subprocess.Popen(
            [sys.executable, "-B", "wizard.py", "--port", str(self.session.port),
             "--token", self.session.token],
            cwd=PROJECT, stdin=slave, stdout=slave, stderr=slave,
            env=env, start_new_session=True,
        )
        os.close(slave)
        os.set_blocking(master, False)
        output, states = bytearray(), set()
        solved = False
        death_started = death_finished = None
        try:
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline and self.session.state not in ("epilogue", "failed"):
                self.session.tick()
                states.add(self.session.state)
                if self.session.state == "awaiting_undo" and not solved:
                    self.session.handle_key("\x1a")
                    states.add(self.session.state)
                    solved = True
                if self.session.state == "defeating" and death_started is None:
                    death_started = time.monotonic()
                drain_terminal(master, output)
                time.sleep(0.01)
            death_finished = time.monotonic()
            drain_terminal(master, output)
            self.assertEqual(self.session.state, "epilogue", self.session.status)
            self.assertTrue(solved)
            self.assertTrue({"wizard_spell", "player_spell", "awaiting_undo", "return_player",
                             "return_wizard", "defeating", "epilogue"} <= states | {self.session.state})
            self.assertIsNotNone(death_started)
            self.assertGreaterEqual(death_finished - death_started, 6)
            self.assertLess(death_finished - death_started, 12)
            for message in (b"ERR_SPELL_ROLLBACK", b"ROOT_ACCESS_REVOKED",
                            b"NULL_WAND_REFERENCE", b"STACK_OVERFLOW", b"SEGMENTATION_FAULT",
                            b"FATAL: wizard.exe has stopped responding"):
                self.assertIn(message, output)
            self.assertIn(b"Level 11 - Wizard", output)
            self.assertIn(fight.SPELL[::-1].encode("ascii"), output)
            self.assertNotIn(b"Traceback", output)
            self.assertIsNone(self.session.peer)
            process.wait(timeout=3)
            self.assertEqual(process.returncode, 0)
            self.assertIn("ESCAPE TERMINAL", self.session.render())
        finally:
            self.session.close()
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
            os.close(master)


class EndingInputTests(unittest.TestCase):
    def test_ctrl_z_is_a_raw_byte_without_suspension_and_tty_is_restored(self):
        master, slave = pty.openpty()
        original = termios.tcgetattr(slave)
        script = """
import fcntl, os, termios, tty
import game
fd = 0
fcntl.ioctl(fd, termios.TIOCSCTTY, 0)
original = termios.tcgetattr(fd)
try:
    tty.setraw(fd)
    assert not (termios.tcgetattr(fd)[3] & termios.ISIG)
    print('RAW_READY', flush=True)
    key = game.read_key(fd, timeout=3)
    print('INPUT=' + ascii(key), flush=True)
finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, original)
"""
        process = subprocess.Popen([sys.executable, "-B", "-c", script], cwd=PROJECT,
                                   stdin=slave, stdout=slave, stderr=slave, start_new_session=True)
        os.set_blocking(master, False)
        output = bytearray()
        try:
            deadline = time.monotonic() + 3
            while b"RAW_READY" not in output and time.monotonic() < deadline:
                drain_terminal(master, output)
                time.sleep(0.005)
            self.assertIn(b"RAW_READY", output)
            os.write(master, b"\x1a")
            process.wait(timeout=3)
            drain_terminal(master, output)
            self.assertEqual(process.returncode, 0, output.decode("ascii", "replace"))
            self.assertIn(b"INPUT='\\x1a'", output)
            self.assertEqual(termios.tcgetattr(slave), original)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
            os.close(master)
            os.close(slave)

    def test_escape_lookahead_does_not_treat_arrow_sequences_as_quitting(self):
        with patch.object(game, "read_key", side_effect=["[", "D", None]):
            self.assertFalse(game.escape_pressed(0, "\x1b"))
        with patch.object(game, "read_key", return_value=None):
            self.assertTrue(game.escape_pressed(0, "\x1b"))
        with patch.object(game, "read_key") as read:
            self.assertFalse(game.escape_pressed(0, "z"))
            read.assert_not_called()

    def test_owned_player_is_closed_only_after_tty_restoration(self):
        events = []
        with patch.object(game.termios, "tcgetattr", return_value="original"), \
             patch.object(game.termios, "tcsetattr", side_effect=lambda *args: events.append("restore")), \
             patch.object(game.tty, "setraw"), \
             patch.object(game, "play_fight", return_value=True), \
             patch.object(game, "schedule_player_close",
                          side_effect=lambda token: events.append(("schedule", token))), \
             contextlib.redirect_stdout(io.StringIO()):
            game.main(start_ending=True, owned_window=True, window_token="owned-player")
        self.assertEqual(events, ["restore", ("schedule", "owned-player")])

    def test_existing_shell_is_left_open_after_epilogue_escape(self):
        with patch.object(game.termios, "tcgetattr", return_value="original"), \
             patch.object(game.termios, "tcsetattr") as restore, \
             patch.object(game.tty, "setraw"), \
             patch.object(game, "play_fight", return_value=True), \
             patch.object(game, "schedule_player_close") as close, \
             contextlib.redirect_stdout(io.StringIO()):
            game.main(start_ending=True)
        restore.assert_called_once()
        close.assert_not_called()

    def test_fight_epilogue_stays_until_standalone_escape(self):
        class Demo:
            token = "test-ending"
            state = "awaiting_undo"
            ticks = 0
            solves = 0
            closed = False

            def open_window(self):
                pass

            def tick(self):
                self.ticks += 1
                if self.state == "defeating" and self.ticks >= 5:
                    self.state = "epilogue"

            def render(self):
                return "ESCAPE TERMINAL" if self.state == "epilogue" else ""

            def handle_key(self, key):
                if key == "\x1a" and self.state == "awaiting_undo":
                    self.solves += 1
                    self.state = "defeating"

            def close(self):
                self.closed = True

        demo = Demo()
        # The first Escape begins an arrow sequence; the second stands alone.
        keys = ["q", "\x03", "\x1a", "\x1a", None, "\r", "q", "\x1a", "\x1b", "\x03", "\x1b"]

        def escape(fd, key):
            if key != "\x1b":
                return False
            escape.count += 1
            return escape.count == 2

        escape.count = 0
        with patch.object(game, "PlayerFight", return_value=demo) as create, \
             patch.object(game, "read_key", side_effect=keys) as read, \
             patch.object(game, "escape_pressed", side_effect=escape), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(game.play_fight(0, start_level=11))
        self.assertEqual(create.call_args.kwargs.get("start_level"), 11)
        self.assertEqual(read.call_count, len(keys))
        self.assertEqual(demo.solves, 1)
        self.assertTrue(demo.closed)


if __name__ == "__main__":
    unittest.main()
