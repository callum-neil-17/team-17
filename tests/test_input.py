"""Terminal byte streams become complete keys across polling and PTY reads."""

import os
import pty
import tty
import unittest
from unittest.mock import patch

from terminal_input import END, ESCAPE, KeyReader


class KeyReaderTests(unittest.TestCase):
    def setUp(self):
        self.input_fd, self.output_fd = os.pipe()
        self.addCleanup(os.close, self.input_fd)
        self.addCleanup(self.close_output)
        self.reader = KeyReader(self.input_fd, escape_timeout=0.025)

    def close_output(self):
        if self.output_fd is not None:
            os.close(self.output_fd)
            self.output_fd = None

    def send(self, data):
        os.write(self.output_fd, data)

    def test_idle_and_raw_control_bytes_are_distinct_from_eof(self):
        self.assertIsNone(self.reader.read(0))
        self.send(b"q\x03\x1a\x04\x7f\xff")
        for expected in ("q", "\x03", "\x1a", "\x04", "\x7f", "\xff"):
            self.assertEqual(self.reader.read(0), expected)
        self.assertIsNone(self.reader.read(0))
        self.close_output()
        self.assertEqual(self.reader.read(0), "")
        self.assertEqual(self.reader.read(0), "")

    def test_end_encodings_and_modifiers_each_form_one_event(self):
        sequences = (b"\x1b[F", b"\x1bOF", b"\x1b[4~", b"\x1b[8~",
                     b"\x1b[1;2F", b"\x1b[1;5F", b"\x1bO1;2F",
                     b"\x1b[4;5~", b"\x1b[8;3~", b"\x1b[1;2:1F")
        for sequence in sequences:
            with self.subTest(sequence=sequence):
                self.send(sequence + b"x")
                self.assertEqual(self.reader.read(0), END)
                self.assertEqual(self.reader.read(0), "x")
                self.assertIsNone(self.reader.read(0))

    def test_arrows_and_function_keys_are_preserved_as_complete_raw_strings(self):
        sequences = (b"\x1b[A", b"\x1b[B", b"\x1b[C", b"\x1b[D",
                     b"\x1b[1;5D", b"\x1bOP", b"\x1b[15~", b"\x1b[[E",
                     b"\x1b[3~", b"\x1b[5F", b"\x1b[?1F", b"\x1b(0",
                     b"\x1bx")
        self.send(b"".join(sequences))
        for sequence in sequences:
            with self.subTest(sequence=sequence):
                self.assertEqual(self.reader.read(0), sequence.decode("latin-1"))
        self.assertIsNone(self.reader.read(0))

    def test_split_end_survives_short_polls(self):
        for fragment in (b"\x1b", b"[", b"1;", b"5"):
            self.send(fragment)
            self.assertIsNone(self.reader.read(0))
        self.send(b"F")
        self.assertEqual(self.reader.read(0), END)
        self.assertIsNone(self.reader.read(0))

    def test_linux_console_f5_survives_a_split_after_the_extra_bracket(self):
        self.send(b"\x1b[[")
        self.assertIsNone(self.reader.read(0))
        self.send(b"E")
        self.assertEqual(self.reader.read(0), "\x1b[[E")

    def test_repeated_coalesced_keys_preserve_event_order(self):
        self.send(b"\x1b[F\x1b[4~\x1bOF\x1b[15~a\x03\x1a\x1b\x1b[8~")
        expected = (END, END, END, "\x1b[15~", "a", "\x03", "\x1a", ESCAPE, END)
        self.assertEqual([self.reader.read(0) for _ in expected], list(expected))
        self.assertIsNone(self.reader.read(0))

    def test_standalone_escape_waits_for_ambiguity_timeout(self):
        self.send(b"\x1b")
        self.assertIsNone(self.reader.read(0))
        self.assertEqual(self.reader.read(0.2), ESCAPE)
        self.assertIsNone(self.reader.read(0))

    def test_incomplete_sequence_expires_as_one_raw_event(self):
        self.send(b"\x1b[1;")
        self.assertIsNone(self.reader.read(0))
        self.assertEqual(self.reader.read(0.2), "\x1b[1;")
        self.assertIsNone(self.reader.read(0))

    def test_eof_flushes_partial_sequence_before_reporting_closure(self):
        self.send(b"\x1b[")
        self.close_output()
        self.assertEqual(self.reader.read(0), "\x1b[")
        self.assertEqual(self.reader.read(0), "")

    def test_eof_resolves_standalone_escape(self):
        self.send(b"\x1b")
        self.close_output()
        self.assertEqual(self.reader.read(0), ESCAPE)
        self.assertEqual(self.reader.read(0), "")

    def test_control_strings_are_single_events_even_with_embedded_escape(self):
        sequences = (b"\x1b]0;title\x07", b"\x1b]0;title\x1b\\",
                     b"\x1bPdata\x1b[A\x1b\\", b"\x1b_hidden\x1b\\")
        self.send(b"".join(sequences) + b"x")
        for sequence in sequences:
            self.assertEqual(self.reader.read(0), sequence.decode("latin-1"))
        self.assertEqual(self.reader.read(0), "x")

    def test_raw_control_byte_cancels_an_incomplete_csi_without_being_lost(self):
        self.send(b"\x1b[\x03\x1a")
        self.assertEqual(self.reader.read(0), "\x1b[")
        self.assertEqual(self.reader.read(0), "\x03")
        self.assertEqual(self.reader.read(0), "\x1a")

    def test_ctrl_c_cancels_pending_osc_or_dcs_and_remains_a_separate_key(self):
        for prefix in (b"\x1b]0;unfinished title", b"\x1bPunfinished data\x1b[A"):
            with self.subTest(prefix=prefix):
                self.send(prefix)
                self.assertIsNone(self.reader.read(0))
                self.send(b"\x03\x1b[4~")
                self.assertEqual(self.reader.read(0), prefix.decode("latin-1"))
                self.assertEqual(self.reader.read(0), "\x03")
                self.assertEqual(self.reader.read(0), END)
                self.assertIsNone(self.reader.read(0))

    def test_unterminated_control_string_is_bounded_and_releases_input(self):
        payload = b"\x1b]" + b"x" * 4094
        self.send(payload)
        self.assertEqual(self.reader.read(0), payload.decode("latin-1"))
        self.send(b"\x03")
        self.assertEqual(self.reader.read(0), "\x03")


class SimulatedTerminal:
    """A deterministic fd/clock that delivers scheduled read fragments."""

    def __init__(self, fragments):
        self.now = 0.0
        self.fragments = list(fragments)

    def select(self, readable, writable, exceptional, timeout):
        if self.fragments and (timeout is None or self.fragments[0][0] <= self.now + timeout):
            self.now = max(self.now, self.fragments[0][0])
            return readable, [], []
        self.now += timeout
        return [], [], []

    def read(self, fd, count):
        _, data = self.fragments.pop(0)
        if len(data) > count:
            self.fragments.insert(0, (self.now, data[count:]))
        return data[:count]

    def patches(self):
        return (patch("terminal_input.time.monotonic", side_effect=lambda: self.now),
                patch("terminal_input.select.select", side_effect=self.select),
                patch("terminal_input.os.read", side_effect=self.read))


class KeyReaderTimingTests(unittest.TestCase):
    def test_inter_byte_timer_extends_for_a_slow_split_end(self):
        terminal = SimulatedTerminal(((0, b"\x1b"), (0.06, b"["),
                                      (0.12, b"4"), (0.18, b"~")))
        clock, readiness, reads = terminal.patches()
        with clock, readiness, reads:
            self.assertEqual(KeyReader(123).read(0.3), END)
        self.assertAlmostEqual(terminal.now, 0.18)

    def test_caller_timeout_retains_prefix_for_the_next_call(self):
        terminal = SimulatedTerminal(((0, b"\x1b"), (0.06, b"["), (0.12, b"F")))
        clock, readiness, reads = terminal.patches()
        with clock, readiness, reads:
            reader = KeyReader(123)
            self.assertIsNone(reader.read(0.04))
            self.assertAlmostEqual(terminal.now, 0.04)
            self.assertIsNone(reader.read(0.04))
            self.assertAlmostEqual(terminal.now, 0.08)
            self.assertEqual(reader.read(0.05), END)

    def test_ready_suffix_wins_over_expired_prefix_on_next_poll(self):
        terminal = SimulatedTerminal(((0, b"\x1b"), (0.1, b"[F")))
        clock, readiness, reads = terminal.patches()
        with clock, readiness, reads:
            reader = KeyReader(123)
            self.assertIsNone(reader.read(0))
            terminal.now = 0.2
            self.assertEqual(reader.read(0), END)


class KeyReaderPtyTests(unittest.TestCase):
    def setUp(self):
        self.master, self.slave = pty.openpty()
        tty.setraw(self.slave)
        self.addCleanup(os.close, self.slave)
        self.addCleanup(self.close_master)
        self.reader = KeyReader(self.slave, escape_timeout=0.025)

    def close_master(self):
        if self.master is not None:
            os.close(self.master)
            self.master = None

    def test_split_forwarded_end_f5_and_ctrl_keys_through_raw_pty(self):
        os.write(self.master, b"\x1b")
        self.assertIsNone(self.reader.read(0.01))
        os.write(self.master, b"[")
        self.assertIsNone(self.reader.read(0))
        os.write(self.master, b"8~\x1b[15~\x03\x1a")
        self.assertEqual(self.reader.read(0.2), END)
        self.assertEqual(self.reader.read(0), "\x1b[15~")
        self.assertEqual(self.reader.read(0), "\x03")
        self.assertEqual(self.reader.read(0), "\x1a")

    def test_arrow_then_standalone_escape_do_not_mix(self):
        os.write(self.master, b"\x1b[A\x1b")
        self.assertEqual(self.reader.read(0.2), "\x1b[A")
        self.assertEqual(self.reader.read(0.2), ESCAPE)

    def test_pty_disconnect_reports_eof(self):
        self.close_master()
        self.assertEqual(self.reader.read(0.2), "")


if __name__ == "__main__":
    unittest.main()
