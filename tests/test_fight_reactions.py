"""Incorrect fight guesses animate the characters without extra dialogue."""

import contextlib
import errno
import fcntl
import io
import os
from pathlib import Path
import pty
import re
import struct
import subprocess
import sys
import termios
import time
import unittest
from unittest.mock import patch

import fight
import wizard
from levels import Level11


def lines(screen):
    screen = re.sub(r"\x1b\[[0-9;]*m", "", screen)
    return dict(re.findall(r"\x1b\[(\d+);1H\x1b\[2K([^\x1b]*)", screen))


class Listener:
    def bind(self, address):
        pass

    def listen(self, backlog):
        pass

    def setblocking(self, value):
        pass

    def getsockname(self):
        return "127.0.0.1", 12345

    def close(self):
        pass


class Peer:
    def __init__(self):
        self.messages = []
        self.eof = False

    def send(self, message):
        self.messages.append(message)

    def poll(self):
        return []

    def close(self):
        pass


class FightReactionTests(unittest.TestCase):
    def setUp(self):
        socket_patch = patch.object(fight.socket, "socket", return_value=Listener())
        socket_patch.start()
        self.addCleanup(socket_patch.stop)
        size_patch = patch.object(fight, "terminal_size", return_value=(60, 30))
        size_patch.start()
        self.addCleanup(size_patch.stop)
        with patch.object(fight.time, "monotonic", return_value=100.0):
            self.session = fight.PlayerFight()
        self.addCleanup(self.session.close)
        self.peer = Peer()
        self.session.peer = self.peer

    def wait_for_solution(self, number=10):
        self.peer.messages.clear()
        if number == 11:
            self.session.level = Level11()
        self.session.state = "awaiting_undo" if number == 11 else "awaiting_dodge"
        self.session.status = ""
        self.session.player_x = fight.STOP_X

    def test_wrong_guess_animates_actual_art_and_sends_one_event(self):
        for number in (10, 11):
            with self.subTest(level=number):
                self.wait_for_solution(number)
                state = self.session.state
                before = self.session.render()
                self.session.handle_key("x")
                after = self.session.render()
                self.assertIsNotNone(self.session.level.reaction_frame)
                self.assertNotEqual(before, after)
                self.assertIn("(o)_/ |=====| \\_(o)", after)
                self.assertEqual(self.peer.messages, [{"type": "wrong_guess", "number": number}])
                self.assertEqual(self.session.state, state)
                self.assertEqual(self.session.player_x, fight.STOP_X)
                # Clue, layout footer and spell stay fixed; only the sprite changes.
                old_lines, new_lines = lines(before), lines(after)
                for row in list(old_lines)[:6] + list(old_lines)[-4:]:
                    self.assertEqual(old_lines[row], new_lines[row])
                if number == 10:
                    row = next(row for row, value in old_lines.items() if fight.SPELL in value)
                    self.assertIn(fight.SPELL, new_lines[row])
                # A second guess cannot restart or overlap the gesture.
                deadline = self.session.level.reaction_deadline
                self.session.handle_key("z")
                self.assertEqual(self.session.level.reaction_deadline, deadline)
                self.assertEqual(len(self.peer.messages), 1)
                self.session.tick(self.session.last_tick + 0.13)
                self.assertNotEqual(after, self.session.render())
                self.session.tick(self.session.last_tick + 0.5)
                self.assertIsNone(self.session.level.reaction_frame)
                self.assertEqual(self.session.state, state)
                self.assertEqual(self.session.render(), before)

    def test_correct_solution_clears_art_without_delay(self):
        self.wait_for_solution()
        self.session.handle_key("x")
        self.session.handle_key("\x7f")
        self.assertEqual(self.session.state, "dodging")
        self.assertIsNone(self.session.level.reaction_frame)
        self.assertEqual(self.peer.messages, [
            {"type": "wrong_guess", "number": 10}, {"type": "dodge", "id": 1},
        ])

        self.wait_for_solution(11)
        self.session.handle_key("x")
        self.session.handle_key("\x1a")
        self.assertEqual(self.session.state, "return_player")
        self.assertTrue(self.session.undo_requested)
        self.assertIsNone(self.session.level.reaction_frame)
        self.assertEqual(self.peer.messages, [
            {"type": "wrong_guess", "number": 11}, {"type": "undo", "id": 2},
        ])
        self.session.handle_key("\x1a")
        self.assertEqual(len(self.peer.messages), 2)

    def test_ordinary_undo_does_not_need_an_extra_clear_event(self):
        self.wait_for_solution(11)
        self.session.handle_key("\x1a")
        self.assertFalse(self.peer.messages)
        self.assertEqual(self.session.state, "return_player")

    def test_wrong_input_only_reacts_while_waiting(self):
        self.session.level = Level11()
        with patch.object(self.session.level, "react_to_wrong_input") as react:
            for state in ("connecting", "preparing", "wizard_spell", "player_spell",
                          "dodging", "return_player", "return_wizard", "defeating",
                          "closing_wizard", "epilogue", "complete", "failed"):
                self.session.state = state
                self.session.handle_key("x")
            react.assert_not_called()
        self.assertFalse(self.peer.messages)

    def test_previously_ignored_controls_stay_silent(self):
        self.wait_for_solution()
        for key in (None, "", "q", "\x04", "\x1a", "\x1c", "\x13", "\x11"):
            with self.subTest(key=key):
                self.session.handle_key(key)
                self.assertIsNone(self.session.level.reaction_frame)
                self.assertEqual(self.session.state, "awaiting_dodge")
                self.assertFalse(self.peer.messages)

    def test_new_level_clears_previous_reaction(self):
        self.wait_for_solution()
        self.session.handle_key("x")
        next_level = Level11()
        next_level.react_to_wrong_input("x", now=self.session.last_tick)
        self.assertIsNotNone(next_level.reaction_frame)
        self.session.begin_level(next_level)
        self.assertEqual(self.session.state, "awaiting_undo")
        self.assertIsNone(self.session.level.reaction_frame)


class WizardReactionTests(unittest.TestCase):
    def test_local_gesture_changes_art_without_moving_feet_or_text(self):
        reaction = wizard.WizardReaction()
        for number, state in ((10, "handed_off"), (11, "ready")):
            with self.subTest(level=number):
                before = fight.draw_scene("wizard", (60, 32), "", "Layout note",
                                          level_number=number, description="Existing clue", row=12)
                self.assertTrue(reaction.start(number, number, state, 100.0))
                after = fight.draw_scene("wizard", (60, 32), "", "Layout note",
                                         level_number=number, description="Existing clue", row=12,
                                         wizard_reaction=reaction.frame(100.0))
                self.assertNotEqual(before, after)
                old_lines, new_lines = lines(before), lines(after)
                changed = [int(row) for row in old_lines if old_lines[row] != new_lines[row]]
                self.assertTrue(changed)
                self.assertLessEqual(max(changed) - min(changed), 5)
                self.assertEqual(old_lines["1"], new_lines["1"])
                self.assertEqual(old_lines["3"], new_lines["3"])
                self.assertEqual(old_lines["32"], new_lines["32"])
                self.assertFalse(reaction.start(number, number, state, 100.1))
                self.assertEqual(reaction.frame(100.13), 1)
                self.assertIsNone(reaction.frame(100.5))
                restored = fight.draw_scene("wizard", (60, 32), "", "Layout note",
                                            level_number=number, description="Existing clue", row=12,
                                            wizard_reaction=reaction.frame(100.5))
                self.assertEqual(restored, before)

    def test_stale_or_busy_wizard_events_are_ignored(self):
        reaction = wizard.WizardReaction()
        for number, current, state in ((10, 11, "ready"), (11, 10, "handed_off"),
                                       (10, 10, "waiting"), (10, 10, "casting"),
                                       (11, 11, "returning"), (11, 11, "dying")):
            self.assertFalse(reaction.start(number, current, state, 100.0))
            self.assertIsNone(reaction.frame(100.0))

    def test_wizard_loop_renders_then_clears_without_recasting(self):
        peer = Peer()
        batches = iter([
            [{"type": "level", "number": 11, "description": "Existing clue"},
             {"type": "layout", "row": 12, "note": "Layout note"}],
            [{"type": "wrong_guess", "number": 11}], [],
            [{"type": "undo", "id": 2}], [{"type": "shutdown"}],
        ])
        peer.poll = lambda: next(batches)
        with patch.object(wizard.socket, "create_connection"), \
                patch.object(wizard, "JsonPeer", return_value=peer), \
                patch.object(wizard, "terminal_size", return_value=(60, 32)), \
                patch.object(wizard.time, "monotonic", side_effect=[100.0, 100.0, 100.1, 100.23, 100.35, 100.5]), \
                patch.object(wizard.time, "sleep"), \
                patch.object(wizard, "draw_scene", wraps=fight.draw_scene) as draw, \
                contextlib.redirect_stdout(io.StringIO()):
            wizard.run(12345, "test")
        self.assertEqual([call.kwargs["wizard_reaction"] for call in draw.call_args_list],
                         [None, 0, 1, None])
        self.assertEqual([message["type"] for message in peer.messages], ["hello", "ready"])
        self.assertTrue(all(call.kwargs["x"] is None for call in draw.call_args_list))


class WizardReactionPtyTests(unittest.TestCase):
    def test_real_protocol_animates_restores_and_cancels_without_casting(self):
        project = Path(__file__).resolve().parents[1]
        with patch.object(fight, "terminal_size", return_value=(60, 32)):
            session = fight.PlayerFight(start_level=11)
            master, slave = pty.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 32, 60, 0, 0))
            process = subprocess.Popen(
                [sys.executable, "-B", str(project / "wizard.py"), "--port", str(session.port),
                 "--token", session.token], stdin=slave, stdout=slave, stderr=slave,
                cwd=project, start_new_session=True,
            )
            os.close(slave)
            os.set_blocking(master, False)
            output = bytearray()

            def pump_until(predicate, timeout=0.5):
                deadline = time.monotonic() + timeout
                while time.monotonic() < deadline:
                    session.tick()
                    try:
                        while chunk := os.read(master, 65536):
                            output.extend(chunk)
                    except BlockingIOError:
                        pass
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                    if predicate():
                        return
                    time.sleep(0.005)
                self.fail("Wizard did not reach the expected reaction frame in time.")

            try:
                pump_until(lambda: session.state == "awaiting_undo" and b"= ,. =" in output,
                           timeout=1.0)
                self.assertNotIn(fight.SPELL.encode(), output)
                self.assertNotIn(b"- ** -", output)
                with patch.object(session.peer, "send", wraps=session.peer.send) as send:
                    output.clear()
                    started = time.monotonic()
                    session.handle_key("x")
                    pump_until(lambda: b"- ** -" in output)
                    self.assertEqual(session.state, "awaiting_undo")
                    output.clear()
                    pump_until(lambda: session.level.reaction_frame is None and b"= ,. =" in output,
                               timeout=0.7)
                    # Wait out the ordinary held-key cooldown, still drawing idle frames.
                    pump_until(lambda: time.monotonic() - started >= 0.8)
                    output.clear()
                    session.handle_key("z")
                    pump_until(lambda: b"- ** -" in output)
                    output.clear()
                    session.handle_key("\x1a")
                    pump_until(lambda: b"= ,. =" in output)
                    self.assertEqual(session.state, "return_player")
                    self.assertIsNone(session.level.reaction_frame)
                    self.assertEqual([call.args[0] for call in send.call_args_list], [
                        {"type": "wrong_guess", "number": 11},
                        {"type": "wrong_guess", "number": 11},
                        {"type": "undo", "id": 2},
                    ])
                    self.assertNotIn(fight.SPELL.encode(), output)
                    self.assertNotIn(b"Traceback", output)
            finally:
                session.close()
                try:
                    process.wait(timeout=2)
                finally:
                    if process.poll() is None:
                        process.terminate()
                        process.wait(timeout=2)
                    os.close(master)


if __name__ == "__main__":
    unittest.main()
