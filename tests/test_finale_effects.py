"""The false shell is inert; cinematic frames and child cleanup stay bounded."""

import errno
import fcntl
import os
from pathlib import Path
import pty
import re
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import patch

from ending_effects import (CLUE, CRASH_DURATION, PANIC_MESSAGES, REOPEN_TAUNT,
                            render_fake_crash, render_fake_shell,
                            render_fallback_panic, render_panic, render_true_end,
                            shell_context)
from fight import JsonPeer
from callback_art import BOOK_ART, MUG_ART, RECEIPT_ART
from ending_config import MAX_PANIC_WINDOWS, panic_close, panic_start


PROJECT = Path(__file__).resolve().parents[1]
CONTEXT = {"username": "player", "hostname": "local", "cwd": "~/game",
           "shell": "bash", "prompt": "player@local:~/game$ "}


def lines(screen):
    plain = re.sub(r"\x1b\[[0-9;]*m", "", screen)
    return re.findall(r"\x1b\[(\d+);(\d+)H([^\x1b]*)", plain)


def text(screen):
    return "\n".join(line.rstrip() for _, _, line in lines(screen))


def contains_art(screen, art):
    rows = [line for _, _, line in lines(screen)]
    source = art.splitlines()
    width = max(map(len, source))
    return any(all(rows[top + row][left:left + len(line)] == line
                   for row, line in enumerate(source))
               for top in range(len(rows) - len(source) + 1)
               for left in range(len(rows[top]) - width + 1))


class FinaleEffectsTests(unittest.TestCase):
    def test_frames_are_printable_bounded_and_centered_in_large_terminals(self):
        renderers = (
            lambda size, elapsed: render_fake_shell(size, elapsed, context=CONTEXT),
            lambda size, elapsed: render_fake_crash(size, elapsed, context=CONTEXT),
            render_panic, render_fallback_panic, render_true_end,
        )
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            for size in ((1, 1), (4, 4), (20, 12), (80, 30), (240, 80), (10000, 10000)):
                width = max(1, min(239, size[0] - 1))
                height = max(1, min(80, size[1]))
                expected_left = (max(1, size[0] - 1) - width) // 2 + 1
                expected_top = (size[1] - height) // 2 + 1
                for renderer in renderers:
                    for elapsed in (0, 0.8, 2, 4.5, 8, 50):
                        with self.subTest(size=size, renderer=renderer, elapsed=elapsed):
                            screen = renderer(size, elapsed)
                            frame = lines(screen)
                            self.assertEqual(len(frame), height)
                            self.assertEqual([int(row) for row, _, _ in frame],
                                             list(range(expected_top, expected_top + height)))
                            self.assertTrue(all(int(column) == expected_left for _, column, _ in frame))
                            self.assertTrue(all(len(line) == width for _, _, line in frame))
                            self.assertTrue(all(32 <= ord(char) <= 126
                                                for _, _, line in frame for char in line))
                            self.assertNotRegex(screen, r"\x1b\[[0-9;]*m")
                            self.assertLess(len(screen), 239 * 80 + 4000)

    def test_false_shell_exits_then_types_exact_clue_without_an_extra_key_hint(self):
        first = text(render_fake_shell((100, 30), 0, context=CONTEXT))
        early = text(render_fake_shell((100, 30), 2, context=CONTEXT))
        complete = text(render_fake_shell((100, 30), 10, context=CONTEXT))
        self.assertIn("[Process exited with status 0]", first)
        self.assertIn(CONTEXT["prompt"] + "_", first)
        self.assertNotIn("[wizard]", first)
        self.assertIn("[wizard]", early)
        self.assertNotIn(CLUE, early)
        self.assertIn(CLUE, complete)
        self.assertNotIn("Press End", complete)
        self.assertNotIn("END KEY", complete)
        reopened = text(render_fake_shell((100, 30), 10, context=CONTEXT, reopened=1))
        self.assertIn(REOPEN_TAUNT, reopened)
        self.assertIn(CLUE, reopened)

    def test_context_and_printable_echo_cannot_inject_terminal_controls(self):
        with patch("ending_effects.getpass.getuser", return_value="user\x1b]0;owned\x07"), \
                patch("ending_effects.socket.gethostname", return_value="host\nname"), \
                patch("ending_effects.os.getcwd", return_value="/tmp/game\r\n"):
            context = shell_context()
        self.assertTrue({"username", "hostname", "cwd", "shell", "prompt"} <= context.keys())
        self.assertTrue(all(32 <= ord(char) <= 126 for value in context.values() for char in value))
        output = render_fake_shell((80, 24), 0, context={"prompt": "$ \x1b]0;owned\x07"},
                                   typed="hello\x1b[2J\n" * 1000)
        self.assertNotIn("\x1b]", output)
        self.assertNotIn("\x1b[2J", output)
        self.assertLess(len(output), 4000)

    def test_shell_context_uses_the_local_shells_prompt_convention(self):
        for shell, character in (("/bin/bash", "$"), ("/bin/sh", "$"),
                                 ("/bin/zsh", "%"), ("/bin/csh", "%"),
                                 ("/usr/bin/tcsh", "%")):
            with self.subTest(shell=shell), patch.dict(os.environ, {"SHELL": shell}):
                context = shell_context()
                self.assertTrue(context["prompt"].endswith(character + " "))
                narrow = text(render_fake_shell((30, 12), 0, context=context))
                self.assertIn(character + " python3 game.py", narrow)

    def test_crash_freezes_then_fragments_the_clue_before_the_fictional_traceback(self):
        start = render_fake_crash((100, 30), 0, context=CONTEXT)
        self.assertEqual(start, render_fake_crash((100, 30), 0.3, context=CONTEXT))
        self.assertIn(CLUE, text(start))
        self.assertEqual(start, render_fake_shell((100, 30), 10, context=CONTEXT))
        self.assertNotIn("Traceback", text(start))
        fragmented = text(render_fake_crash((100, 30), 0.75, context=CONTEXT))
        displaced = text(render_fake_crash((100, 30), 1.1, context=CONTEXT))
        self.assertIn("You managed to e", fragmented)
        self.assertTrue(any(line.strip() == "scape my" for line in fragmented.splitlines()))
        self.assertNotIn(CLUE, fragmented)
        self.assertNotIn("Traceback", fragmented)
        self.assertNotEqual(fragmented, displaced)
        self.assertIn("[wizard]", displaced)
        self.assertNotIn("Traceback", displaced)
        self.assertIn("<wizard/curse>", text(render_fake_crash((100, 30), 1.7, context=CONTEXT)))
        final = render_fake_crash((100, 30), CRASH_DURATION, context=CONTEXT)
        self.assertIn("FATAL: wizard runtime", text(final))
        self.assertIn("[recovery fork requested: 10 copies]", text(final))
        self.assertEqual(final, render_fake_crash((100, 30), 100, context=CONTEXT))

    def test_panic_variants_start_as_the_wizard_then_delete_and_collapse(self):
        frames = []
        for index in range(MAX_PANIC_WINDOWS):
            start = render_panic((100, 30), 0, index=index)
            self.assertIn("_,-'|", text(start))
            frames.append(start)
            stage_text = [text(render_panic((100, 30), elapsed, index=index, duration=6))
                          for elapsed in (0, 2.5, 4.3, 6)]
            for message, frame in zip(PANIC_MESSAGES, stage_text):
                self.assertIn(message, frame)
            self.assertNotIn("_,-'|", stage_text[-1])
        self.assertEqual(len(set(frames)), MAX_PANIC_WINDOWS)
        fallback = text(render_fallback_panic((100, 35), 1.8))
        self.assertIn("reference 10", fallback)
        self.assertIn("+---", fallback)
        self.assertIn(PANIC_MESSAGES[-1], text(render_fallback_panic((100, 35), 8)))

    def test_fallback_staggers_ten_panels_then_retires_them_one_by_one(self):
        def references(elapsed, duration=8):
            frame = text(render_fallback_panic((200, 70), elapsed, duration))
            return re.findall(r"wizard@local / reference (\d{2})", frame)

        self.assertEqual(references(0), ["01"])
        for count in range(1, MAX_PANIC_WINDOWS + 1):
            elapsed = panic_start(count - 1) + 0.1
            with self.subTest(elapsed=elapsed):
                self.assertEqual(references(elapsed), [f"{index:02d}" for index in range(1, count + 1)])
        # Sample after the next 12 Hz frame at each window's close deadline.
        for retired in range(1, MAX_PANIC_WINDOWS + 1):
            elapsed = panic_close(retired - 1) + 0.1
            with self.subTest(elapsed=elapsed):
                self.assertEqual(references(elapsed), [f"{index:02d}" for index in
                                                       range(retired + 1, MAX_PANIC_WINDOWS + 1)])
        for elapsed in (7.9, 8, 100):
            frame = text(render_fallback_panic((200, 70), elapsed))
            self.assertEqual(frame.strip(), PANIC_MESSAGES[-1])
        self.assertEqual(references(0, duration=4), ["01"])
        self.assertEqual(references(0.9, duration=4),
                         [f"{index:02d}" for index in range(1, MAX_PANIC_WINDOWS + 1)])
        self.assertEqual(references(4, duration=4), [])

    def test_final_panic_recalls_earlier_scene_objects_then_deletes_them(self):
        memories = (MUG_ART, RECEIPT_ART, BOOK_ART)
        for index in range(MAX_PANIC_WINDOWS):
            memory = memories[index % len(memories)]
            with self.subTest(index=index):
                start = render_panic((100, 30), 0, index=index, duration=6)
                recalled = render_panic((100, 30), 3, index=index, duration=6)
                corrupted = render_panic((100, 30), 4.6, index=index, duration=6)
                deleted = render_panic((100, 30), 5.5, index=index, duration=6)
                self.assertFalse(contains_art(start, memory))
                self.assertTrue(contains_art(recalled, memory))
                self.assertFalse(contains_art(corrupted, memory))
                self.assertFalse(contains_art(deleted, memory))
                self.assertIn("wizard@local / reference", text(recalled).splitlines()[0])
                self.assertEqual(lines(recalled)[-2][2].strip(), PANIC_MESSAGES[1])
                self.assertEqual(lines(deleted)[-2][2].strip(), PANIC_MESSAGES[-1])
                self.assertEqual(recalled, render_panic((100, 30), 3.01, index=index, duration=6))

    def test_inline_panic_reuses_the_same_memory_without_obscuring_its_footer(self):
        recalled = render_fallback_panic((200, 70), 4.5)
        self.assertTrue(contains_art(recalled, BOOK_ART))
        self.assertEqual(text(recalled).splitlines()[-1].strip(), PANIC_MESSAGES[1])
        deleted = render_fallback_panic((200, 70), 8)
        self.assertFalse(any(contains_art(deleted, memory)
                             for memory in (MUG_ART, RECEIPT_ART, BOOK_ART)))
        self.assertEqual(text(deleted).strip(), PANIC_MESSAGES[-1])

    def test_glitch_fragments_move_without_covering_the_reference_or_final_plea(self):
        frames = [render_panic((100, 30), elapsed, index=4, duration=6)
                  for elapsed in (2.4, 3.6, 5.2)]
        for frame, message in zip(frames, (PANIC_MESSAGES[1], PANIC_MESSAGES[1],
                                          PANIC_MESSAGES[2])):
            with self.subTest(message=message):
                self.assertIn("wizard@local / reference 05", text(frame).splitlines()[0])
                self.assertEqual(lines(frame)[-2][2].strip(), message)
                self.assertRegex(text(frame), r"(?:[01]{3,}#?[01]*|REF_LOST|0x\?{4})")
                self.assertNotRegex(frame, r"\x1b\[(?:5|7)m")
        self.assertEqual(len(set(frames)), 3)
        self.assertTrue(contains_art(frames[1], RECEIPT_ART))
        # Every copy, including the new tenth copy, retains its identity after
        # tearing. This catches accidental six-variant wrapping in the viewer.
        tenth = render_panic((100, 30), 3.6, index=9, duration=6)
        self.assertIn("wizard@local / reference 10", text(tenth).splitlines()[0])
        self.assertNotEqual(tenth, frames[1])

    def test_animation_is_quantized_and_final_title_has_a_blank_beat(self):
        for renderer in (render_panic, render_fallback_panic):
            self.assertEqual(renderer((80, 30), 2.001), renderer((80, 30), 2.01))
        before = render_true_end((100, 30), 0.74)
        after = render_true_end((100, 30), 0.75)
        self.assertFalse(text(before).strip())
        self.assertEqual(text(after).strip(), "THE END")
        row, column, line = next(item for item in lines(after) if "THE END" in item[2])
        self.assertEqual(int(row), 16)
        self.assertEqual(int(column) + line.index("THE END"), 47)


class FinaleChildTests(unittest.TestCase):
    def setUp(self):
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(1)
        self.listener.settimeout(3)
        self.addCleanup(self.listener.close)
        self.master, self.slave = pty.openpty()
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
        self.saved_tty = termios.tcgetattr(self.slave)
        self.addCleanup(os.close, self.slave)
        self.addCleanup(os.close, self.master)
        os.set_blocking(self.master, False)
        self.output = bytearray()
        self.pending = []
        self.process = subprocess.Popen(
            [sys.executable, "-B", "ending_window.py", "--port",
             str(self.listener.getsockname()[1]), "--token", "abc123", "--window-id", "s0",
             "--role", "shell"], cwd=PROJECT, stdin=self.slave,
            stdout=self.slave, stderr=self.slave, start_new_session=True,
        )
        self.addCleanup(self.stop_process)
        sock, _ = self.listener.accept()
        self.peer = JsonPeer(sock)
        self.addCleanup(self.peer.close)
        hello = self.wait_message("hello")
        self.assertEqual({key: hello[key] for key in ("token", "window_id", "role", "pid")},
                         {"token": "abc123", "window_id": "s0", "role": "shell", "pid": self.process.pid})

    def stop_process(self):
        if self.process.poll() is None:
            self.process.kill()
        self.process.wait(timeout=3)

    def drain(self):
        try:
            while chunk := os.read(self.master, 65536):
                self.output.extend(chunk)
        except BlockingIOError:
            pass
        except OSError as error:
            if error.errno != errno.EIO:
                raise

    def wait_message(self, kind, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.drain()
            self.pending.extend(self.peer.poll())
            for index, message in enumerate(self.pending):
                if message["type"] == kind:
                    return self.pending.pop(index)
            if self.process.poll() is not None:
                self.fail(f"Child exited early: {self.output.decode('ascii', errors='replace')}")
            time.sleep(0.01)
        self.fail(f"No {kind} event received")

    def wait_output(self, needle, start=0, timeout=2):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.drain()
            self.pending.extend(self.peer.poll())
            if needle in self.output[start:]:
                return
            if self.process.poll() is not None:
                self.fail("Child exited before drawing the requested scene")
            time.sleep(0.01)
        self.fail(f"No {needle!r} output received")

    def assert_restored(self):
        self.process.wait(timeout=3)
        self.drain()
        self.assertEqual(self.process.returncode, 0)
        self.assertEqual(termios.tcgetattr(self.slave), self.saved_tty)
        self.assertIn(b"\x1b[?25h\x1b[?1049l", self.output)

    def test_ctrl_c_is_inert_end_still_works_and_shell_text_is_never_executed(self):
        self.peer.send({"type": "scene", "scene": "shell", "elapsed": 10, "context": CONTEXT})
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory, "executed")
            os.write(self.master, f"printf unsafe > {marker}\r".encode("ascii"))
            os.write(self.master, b"\x03")
            self.process.send_signal(signal.SIGINT)
            self.peer.send({"type": "ping"})
            self.wait_message("pong")
            self.assertFalse(any(message["type"] == "input" for message in self.pending))
            os.write(self.master, b"\x1b[4~")
            self.assertEqual(self.wait_message("input")["key"], "END")
            os.write(self.master, b"\x03")
            self.process.send_signal(signal.SIGINT)
            self.peer.send({"type": "ping"})
            self.wait_message("pong")
            self.assertIsNone(self.process.poll())
            self.assertFalse(any(message["type"] == "input" for message in self.pending))
            self.assertFalse(marker.exists())
        # Neither raw Ctrl+C nor SIGINT may freeze the ensuing animations.
        self.peer.send({"type": "scene", "scene": "crash", "elapsed": 2.35,
                        "context": CONTEXT})
        os.write(self.master, b"\x03")
        self.assertEqual(self.wait_message("finished")["scene"], "crash")
        self.peer.send({"type": "scene", "scene": "panic", "duration": 0.2,
                        "index": MAX_PANIC_WINDOWS - 1})
        os.write(self.master, b"\x03")
        self.process.send_signal(signal.SIGINT)
        self.assertEqual(self.wait_message("finished")["scene"], "panic")
        self.assertFalse(any(message["type"] == "input" for message in self.pending))
        self.assertIn(b"reference 10", self.output)
        self.peer.send({"type": "shutdown"})
        self.assert_restored()
        self.assertIn(CLUE.encode("ascii"), self.output)

    def test_finished_frames_hold_once_then_eof_restores_the_terminal(self):
        self.peer.send({"type": "scene", "scene": "crash", "elapsed": 3, "context": CONTEXT})
        self.assertEqual(self.wait_message("finished")["scene"], "crash")
        self.peer.send({"type": "ping"})
        self.wait_message("pong")
        self.assertFalse(any(message["type"] == "finished" for message in self.pending))
        self.peer.send({"type": "scene", "scene": "panic", "elapsed": 0.2,
                        "duration": 0.1, "index": 4})
        self.assertEqual(self.wait_message("finished")["scene"], "panic")
        self.peer.close()
        self.assert_restored()

    def test_window_close_signal_runs_cleanup(self):
        self.process.send_signal(signal.SIGHUP)
        self.assert_restored()

    def test_scene_changes_and_resizes_clear_outside_the_bounded_canvas(self):
        clear = b"\x1b[2J\x1b[H"
        self.peer.send({"type": "scene", "scene": "shell", "elapsed": 10, "context": CONTEXT})
        self.wait_output(CLUE.encode("ascii"))
        start = len(self.output)
        self.peer.send({"type": "scene", "scene": "crash", "elapsed": 0, "context": CONTEXT})
        self.wait_output(clear, start)
        self.wait_output(CLUE.encode("ascii"), start)
        start = len(self.output)
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", 100, 300, 0, 0))
        self.wait_output(clear, start)
        self.wait_output(b"\x1b[11;31H", start)
        # Even a finished scene redraws after resize and sends finished once.
        self.peer.send({"type": "scene", "scene": "panic", "elapsed": 1,
                        "duration": 0.1, "index": 0})
        self.wait_message("finished")
        start = len(self.output)
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", 20, 60, 0, 0))
        self.wait_output(clear, start)
        self.wait_output(b"WIZARD_PROCESS_NOT_FOUND", start)
        self.peer.send({"type": "ping"})
        self.wait_message("pong")
        self.assertFalse(any(message["type"] == "finished" for message in self.pending))
        self.peer.send({"type": "shutdown"})
        self.assert_restored()


if __name__ == "__main__":
    unittest.main()
