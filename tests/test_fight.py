import ast
import contextlib
import errno
import fcntl
import io
import os
import pty
import socket
import struct
import subprocess
import sys
import termios
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import fight
import fight_windows
import game
from levels import Level11


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.sender, receiver = socket.socketpair()
        self.peer = fight.JsonPeer(receiver)
        self.addCleanup(self.sender.close)
        self.addCleanup(self.peer.close)

    def test_split_and_coalesced_messages(self):
        self.sender.sendall(b'{"type":"rea')
        self.assertEqual(self.peer.poll(), [])
        self.sender.sendall(b'dy"}\n{"type":"handoff","id":1}\n{"type":')
        self.assertEqual(self.peer.poll(), [{"type": "ready"}, {"type": "handoff", "id": 1}])
        self.sender.sendall(b'"pong"}\n')
        self.assertEqual(self.peer.poll(), [{"type": "pong"}])

    def test_closed_partial_message_and_invalid_message(self):
        self.sender.sendall(b'{"type":')
        self.sender.shutdown(socket.SHUT_WR)
        with self.assertRaises(ConnectionError):
            self.peer.poll()

    def test_malformed_json(self):
        self.sender.sendall(b'not json\n')
        with self.assertRaises(ConnectionError):
            self.peer.poll()

    def test_partial_nonblocking_writes(self):
        class SlowSocket:
            def __init__(self):
                self.output = bytearray()
                self.calls = 0

            def setblocking(self, value):
                pass

            def send(self, data):
                self.calls += 1
                if self.calls % 2 == 0:
                    raise BlockingIOError
                self.output.extend(data[:3])
                return min(3, len(data))

        sock = SlowSocket()
        peer = fight.JsonPeer(sock)
        peer.send({"type": "cast"})
        self.assertTrue(peer.outgoing)
        for _ in range(20):
            peer.flush()
        self.assertEqual(bytes(sock.output), b'{"type":"cast"}\n')
        self.assertFalse(peer.outgoing)


class FightTests(unittest.TestCase):
    def setUp(self):
        self.size = patch.object(fight, 'terminal_size', return_value=(60, 30))
        self.size.start()
        self.addCleanup(self.size.stop)
        self.session = fight.PlayerFight()
        self.addCleanup(self.session.close)

    def connect(self):
        peer = fight.JsonPeer(socket.create_connection(('127.0.0.1', self.session.port)))
        self.addCleanup(peer.close)
        peer.send({'type': 'hello', 'token': self.session.token, 'columns': 70, 'rows': 24})
        self.session.tick()
        self.assertEqual(self.session.state, 'preparing')
        messages = peer.poll()
        layout = next(message for message in messages if message['type'] == 'layout')
        level = next(message for message in messages if message['type'] == 'level')
        self.assertEqual(level['description'], self.session.level.description)
        self.assertEqual(layout['row'], fight.spell_row(30, 24))
        peer.send({'type': 'ready'})
        self.session.tick()
        cast = next(message for message in peer.poll() if message['type'] == 'cast')
        self.assertEqual(cast['glyph'], fight.SPELL)
        self.assertEqual(cast['row'], layout['row'])
        return peer

    def pause_spell(self, peer):
        peer.send({'type': 'handoff', 'id': 1})
        self.session.tick()
        self.assertEqual(self.session.state, 'player_spell')
        self.assertGreater(self.session.player_x, 58)
        self.assertNotIn('The spell crosses', self.session.render())
        self.session.tick(self.session.last_tick + 3)
        self.assertEqual(self.session.state, 'awaiting_dodge')
        self.assertEqual(self.session.player_x, fight.STOP_X)

    def test_local_handoff_pauses_until_backspace_then_misses(self):
        peer = self.connect()
        self.assertEqual(self.session.state, 'wizard_spell')
        self.pause_spell(peer)
        for key in ('\r', '\n', 'q', '\x03', 'x', None):
            self.session.handle_key(key)
            self.assertEqual(self.session.state, 'awaiting_dodge')
        self.session.tick(self.session.last_tick + 1)
        self.assertEqual(self.session.player_x, fight.STOP_X)
        self.session.handle_key('\x7f')
        self.assertEqual(self.session.state, 'dodging')
        self.session.tick(self.session.last_tick + 3)
        self.assertEqual(self.session.state, 'complete')
        self.assertEqual(self.session.player_step, 1)
        messages = []
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline and not any(m['type'] == 'missed' for m in messages):
            messages.extend(peer.poll())
            time.sleep(0.005)
        self.assertIn({'type': 'dodge', 'id': 1}, messages)
        self.assertIn({'type': 'missed', 'id': 1}, messages)

    def test_backspace_byte_and_early_input(self):
        peer = self.connect()
        self.session.handle_key('\x08')
        self.assertEqual(self.session.state, 'wizard_spell')
        self.pause_spell(peer)
        self.session.handle_key('\x08')
        self.assertEqual(self.session.state, 'dodging')
        self.session.tick(self.session.last_tick + fight.DODGE_TIME / 2)
        self.assertGreater(self.session.player_step, 0)
        self.assertLess(self.session.player_step, 1)
        self.assertEqual(self.session.player_x, fight.STOP_X)

    def test_level11_preserves_existing_connection(self):
        peer = self.connect()
        self.pause_spell(peer)
        self.session.handle_key('\x7f')
        self.session.tick(self.session.last_tick + 3)
        connection, port, token = self.session.peer, self.session.port, self.session.token
        self.session.begin_level(Level11())
        self.assertEqual(self.session.state, 'awaiting_undo')
        self.assertIs(self.session.peer, connection)
        self.assertEqual((self.session.port, self.session.token), (port, token))
        self.assertIn('Level 11 - Player', self.session.render())
        messages = peer.poll()
        self.assertIn({'type': 'level', 'number': 11, 'description': Level11().description}, messages)
        self.assertFalse(any(message['type'] == 'cast' for message in messages))
        self.assertNotIn(fight.SPELL, self.session.render())

    def test_closed_wizard_and_timeout(self):
        peer = self.connect()
        peer.close()
        self.session.tick()
        self.assertEqual(self.session.state, 'failed')
        self.assertIn('closed', self.session.status)
        self.assertIsNone(self.session.peer)

    def test_connection_timeout(self):
        self.session.tick(self.session.started + 21)
        self.assertEqual(self.session.state, 'failed')
        self.assertEqual(self.session.listener.fileno(), -1)

    def test_wrong_token_fails_cleanly(self):
        peer = fight.JsonPeer(socket.create_connection(('127.0.0.1', self.session.port)))
        self.addCleanup(peer.close)
        peer.send({'type': 'hello', 'token': 'wrong', 'columns': 60, 'rows': 30})
        self.session.tick()
        self.assertEqual(self.session.state, 'failed')

    def test_resize_shares_same_spell_row(self):
        peer = self.connect()
        peer.send({'type': 'resize', 'columns': 40, 'rows': 18})
        self.session.tick()
        layouts = [message for message in peer.poll() if message['type'] == 'layout']
        self.assertEqual(layouts[-1]['row'], self.session.row)
        self.assertEqual(self.session.row, fight.spell_row(30, 18))

    def test_level10_missed_stream_clears_the_larger_players_head(self):
        import re
        self.session.state = 'dodging'
        self.session.player_step = 1
        self.session.player_x = 0
        screen = re.sub(r'\x1b\[[0-9;]*m', '', self.session.render())
        lines = re.findall(r'\x1b\[(\d+);1H\x1b\[2K([^\x1b]*)', screen)
        spell_line = next(int(row) for row, line in lines if fight.SPELL in line)
        head_line = next(int(row) for row, line in lines if '.----.' in line)
        self.assertLess(spell_line, head_line)

    def test_wizard_subprocess_handoff_in_real_pty(self):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 28, 50, 0, 0))
        env = os.environ.copy()
        env.pop('COLUMNS', None)
        env.pop('LINES', None)
        process = subprocess.Popen(
            [sys.executable, '-B', 'wizard.py', '--port', str(self.session.port), '--token', self.session.token],
            cwd=Path(__file__).resolve().parents[1], stdin=slave, stdout=slave, stderr=slave,
            env=env, start_new_session=True,
        )
        os.close(slave)
        os.set_blocking(master, False)
        output = bytearray()
        states = set()
        paused_at = None
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline and self.session.state not in ('complete', 'failed'):
                self.session.tick()
                states.add(self.session.state)
                if self.session.state == 'awaiting_dodge':
                    if paused_at is None:
                        paused_at = time.monotonic()
                    elif time.monotonic() - paused_at > 0.1:
                        self.session.handle_key('\x7f')
                try:
                    output.extend(os.read(master, 65536))
                except BlockingIOError:
                    pass
                time.sleep(0.01)
            self.assertEqual(self.session.state, 'complete', self.session.status)
            self.assertTrue({'wizard_spell', 'player_spell', 'awaiting_dodge', 'dodging', 'complete'} <= states)
            self.assertIn(b'Level 10 - Wizard', output)
            self.assertIn(fight.SPELL.encode(), output)
            self.assertNotIn(b'The spell is entering', output)
            self.session.begin_level(Level11())
            deadline = time.monotonic() + 2
            while b'Level 11 - Wizard' not in output and time.monotonic() < deadline:
                self.session.tick()
                try:
                    output.extend(os.read(master, 65536))
                except BlockingIOError:
                    pass
                time.sleep(0.01)
            self.assertIn(b'Level 11 - Wizard', output)
            self.assertIsNone(process.poll())
            self.session.close()
            process.wait(timeout=3)
            self.assertEqual(process.returncode, 0)
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
            os.close(master)


class IntegrationTests(unittest.TestCase):
    def test_earlier_progression_enters_fight_after_tree(self):
        keys = ['y', '\r', '\t', '\x12', game.Level5().required_input[0], '\x17', '\x06', '.', '\x18']
        with patch.object(game.termios, 'tcgetattr', return_value='original'), \
             patch.object(game.termios, 'tcsetattr') as restore, \
             patch.object(game.tty, 'setraw') as raw, \
             patch.object(game, 'read_key', side_effect=keys), \
             patch.object(game, 'play_frames', return_value=True) as frames, \
             patch.object(game, 'play_fight', return_value=True) as demo, \
             patch.object(game, 'render_screen') as render:
            game.main()
        demo.assert_called_once()
        self.assertEqual([call.args[0].number for call in frames.call_args_list], list(range(1, 10)))
        self.assertIn('Level 9', render.call_args.args[0])
        raw.assert_called_once()
        restore.assert_called_once_with(game.sys.stdin.fileno(), termios.TCSADRAIN, 'original')

    def test_raw_settings_restored_after_fight_exception(self):
        with patch.object(game.termios, 'tcgetattr', return_value='original'), \
             patch.object(game.termios, 'tcsetattr') as restore, \
             patch.object(game.tty, 'setraw'), \
             patch.object(game, 'play_fight', side_effect=RuntimeError('test failure')):
            with self.assertRaises(RuntimeError):
                game.main(start_fight=True)
        restore.assert_called_once_with(game.sys.stdin.fileno(), termios.TCSADRAIN, 'original')

    def test_disconnected_player_terminal_exits_and_restores_settings(self):
        with patch.object(game.termios, 'tcgetattr', return_value='original'), \
             patch.object(game.termios, 'tcsetattr') as restore, \
             patch.object(game.tty, 'setraw'), \
             patch.object(game, 'play_fight', side_effect=BrokenPipeError(errno.EPIPE, 'terminal closed')):
            game.main(start_fight=True)
        restore.assert_called_once_with(game.sys.stdin.fileno(), termios.TCSADRAIN, 'original')

    def test_fight_automatically_advances_after_dodge_and_ignores_quit_bytes(self):
        class Demo:
            token = 'test'
            state = 'wizard_spell'
            ticks = 0

            def open_window(self):
                pass

            def tick(self):
                self.ticks += 1
                if self.ticks == 4:
                    self.state = 'complete'

            def render(self):
                return ''

            def handle_key(self, key):
                if key == '\x1a':
                    self.state = 'epilogue'

            def begin_level(self, level):
                self.state = 'wizard_spell'
                self.level = level

            def close(self):
                self.closed = True

        demo = Demo()
        with patch.object(game, 'PlayerFight', return_value=demo), \
             patch.object(game, 'read_key', side_effect=['q', '\x03', 'x', '\x1a', '\x1b', None]) as read, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertTrue(game.play_fight(0))
        self.assertEqual(read.call_count, 6)
        self.assertEqual(demo.level.number, 11)
        self.assertTrue(demo.closed)
        self.assertTrue(all(call.kwargs['timeout'] == fight.FRAME_TIME for call in read.call_args_list[:-1]))
        self.assertEqual(read.call_args_list[-1].kwargs['timeout'], 0.025)

    def test_wsl_launch_uses_same_distro_and_a_new_window(self):
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': 'Ubuntu-Test'}), \
             patch.object(fight_windows.shutil, 'which', return_value='/mnt/c/wt.exe'):
            command, _ = fight_windows.launch_command(12345, 'test-token')
        self.assertEqual(command[1:4], ['--window', 'new', 'new-tab'])
        self.assertIn('Ubuntu-Test', command)
        self.assertIn(sys.executable, command)
        self.assertIn('12345', command)

    def test_macos_launch_quotes_python_and_uses_a_separate_terminal(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Darwin'), \
             patch.object(fight_windows.platform, 'release', return_value='23.0'), \
             patch.object(fight_windows.sys, 'executable', '/Python Path/python3'):
            command, _ = fight_windows.launch_command(12345, 'test-token')
        self.assertEqual(command[0], 'osascript')
        self.assertIn('tell application "Terminal"', command[2])
        self.assertIn('set gameTab to do script', command[2])
        self.assertTrue(command[3].startswith("exec '/Python Path/python3'"))

    def test_x11_tiling_leaves_fullscreen_and_accounts_for_decorations(self):
        calls = []

        def run(command, timeout=3):
            calls.append(command)
            if command == ['wmctrl', '-lG']:
                return ('0x01 0 0 0 800 600 host Player-test\n'
                        '0x02 0 100 100 800 600 host Wizard-test\n')
            if command == ['wmctrl', '-d']:
                return '0 * DG: 1920x1080 VP: 0,0 WA: 0,30 1920x1050 Workspace\n'
            if command[0] == 'xprop':
                return '_NET_FRAME_EXTENTS(CARDINAL) = 0, 0, 36, 0\n'
            return ''

        with patch.object(fight_windows, '_run', side_effect=run), \
             patch.object(fight_windows.shutil, 'which', side_effect=lambda name: name if name == 'xprop' else None), \
             patch.object(fight_windows.time, 'sleep'):
            fight_windows._tile_x11('Player-test', 'Wizard-test')
        self.assertIn(['wmctrl', '-ir', '0x01', '-b', 'remove,fullscreen'], calls)
        self.assertIn(['wmctrl', '-ir', '0x01', '-e', '0,0,30,960,1014'], calls)
        self.assertIn(['wmctrl', '-ir', '0x02', '-e', '0,960,30,960,1014'], calls)

    def test_wayland_keeps_manual_tiling_instructions(self):
        pair = object.__new__(fight_windows.WindowPair)
        import queue
        import threading
        pair.events = queue.SimpleQueue()
        pair.closed = threading.Event()
        with patch.dict(os.environ, {'XDG_SESSION_TYPE': 'wayland'}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Linux'), \
             patch.object(fight_windows.platform, 'release', return_value='generic'), \
             patch.object(fight_windows, '_run') as run:
            pair._arrange('test')
        run.assert_not_called()
        self.assertEqual(pair.events.get_nowait(), ('layout', fight_windows.MANUAL_LAYOUT))

    def test_rendering_stays_in_terminal_bounds(self):
        for size in [(80, 30), (40, 18), (10, 6)]:
            for role in ('player', 'wizard'):
                screen = fight.draw_scene(role, size, 'A spell is approaching.', fight_windows.MANUAL_LAYOUT,
                                          x=size[0] - 2, row=fight.spell_row(size[1], size[1]))
                import re
                parts = re.findall(r'\x1b\[(\d+);1H\x1b\[2K([^\x1b]*)', screen)
                self.assertEqual(len(parts), size[1])
                self.assertTrue(all(len(text) < size[0] for _, text in parts))

    def test_all_python_syntax(self):
        root = Path(__file__).resolve().parents[1]
        for path in [*root.glob('*.py'), *root.glob('levels/*.py')]:
            ast.parse(path.read_text(), filename=str(path))


if __name__ == '__main__':
    unittest.main()
