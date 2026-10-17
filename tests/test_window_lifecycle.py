"""Ownership boundaries for the two-terminal ending and its launcher."""

import base64
import os
import queue
import threading
import unittest
from unittest.mock import patch

import fight_windows
import launcher


class WindowLifecycleTests(unittest.TestCase):
    def test_x11_closes_only_exact_game_window(self):
        windows = (
            "0x01 0 host Two Keys Wizard private-extra\n"
            "0x02 0 host prefix Two Keys Wizard private\n"
            "0x03 0 host Two Keys Wizard private\n"
            "0x04 0 host Two Keys Player private\n"
        )
        with patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11'}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Linux'), \
             patch.object(fight_windows.platform, 'release', return_value='generic'), \
             patch.object(fight_windows.shutil, 'which', return_value='/usr/bin/wmctrl'), \
             patch.object(fight_windows, '_run', side_effect=[windows, '']) as run:
            self.assertTrue(fight_windows.close_owned_window('wizard', 'private'))
        self.assertEqual(run.call_args_list[1].args[0], ['wmctrl', '-ic', '0x03'])
        self.assertEqual(run.call_count, 2)

    def test_existing_player_can_be_focused_without_closing_it(self):
        with patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11'}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Linux'), \
             patch.object(fight_windows.platform, 'release', return_value='generic'), \
             patch.object(fight_windows.shutil, 'which', return_value='/usr/bin/wmctrl'), \
             patch.object(fight_windows, '_run', side_effect=['0x04 0 host Two Keys Player private\n', '']) as run:
            self.assertTrue(fight_windows.focus_player('private'))
        self.assertEqual(run.call_args_list[1].args[0], ['wmctrl', '-ia', '0x04'])

    def test_x11_restores_only_the_player_to_fullscreen_without_toggling(self):
        windows = '0x04 0 host Two Keys Player private\n0x05 0 host Two Keys Player private-extra\n'
        with patch.dict(os.environ, {'XDG_SESSION_TYPE': 'x11'}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Linux'), \
             patch.object(fight_windows.platform, 'release', return_value='generic'), \
             patch.object(fight_windows.shutil, 'which', return_value='/usr/bin/wmctrl'), \
             patch.object(fight_windows, '_run', side_effect=[windows, '', '', windows, '', '']) as run:
            self.assertTrue(fight_windows.fullscreen_player('private'))
            self.assertTrue(fight_windows.fullscreen_player('private'))
        commands = [call.args[0] for call in run.call_args_list]
        self.assertEqual(commands.count(['wmctrl', '-ir', '0x04', '-b', 'add,fullscreen']), 2)
        self.assertEqual(commands.count(['wmctrl', '-ia', '0x04']), 2)

    def test_macos_fullscreen_sets_attribute_on_exact_player_window(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Darwin'), \
             patch.object(fight_windows.platform, 'release', return_value='23.0'), \
             patch.object(fight_windows, '_run', return_value='found\n') as run:
            self.assertTrue(fight_windows.fullscreen_player('private'))
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ['Two Keys Player private', 'fullscreen'])
        self.assertIn('set value of attribute "AXFullScreen" of window targetWindowName to true', command[2])

    def test_wsl_fullscreen_checks_current_state_before_alt_enter(self):
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': 'Ubuntu-Same'}, clear=True), \
             patch.object(fight_windows, '_run', return_value='found\n') as run:
            self.assertTrue(fight_windows.fullscreen_player('private'))
        script = base64.b64decode(run.call_args.args[0][-1]).decode('utf-16le')
        self.assertIn("$TargetTitle = 'Two Keys Player private'", script)
        self.assertIn("$RequestedAction = 'fullscreen'", script)
        self.assertIn('if (-not $alreadyFullscreen)', script)

    def test_invalid_or_generic_identities_never_reach_desktop(self):
        with patch.object(fight_windows, '_run') as run:
            for role, token in [('terminal', 'private'), ('wizard', ''), ('wizard', "'; write evil")]:
                with self.assertRaises(ValueError):
                    fight_windows.close_owned_window(role, token)
        run.assert_not_called()

    def test_wsl_exact_title_action_is_encoded_and_bounded(self):
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': 'Ubuntu-Same'}, clear=True), \
             patch.object(fight_windows, '_run', return_value='found\n') as run:
            self.assertTrue(fight_windows.close_owned_window('wizard', 'private'))
        command = run.call_args.args[0]
        self.assertEqual(command[0], 'powershell.exe')
        script = base64.b64decode(command[-1]).decode('utf-16le')
        self.assertIn("$TargetTitle = 'Two Keys Wizard private'", script)
        self.assertIn('-ceq $TargetTitle', script)
        self.assertNotIn('Stop-Process', script)
        self.assertEqual(run.call_args.args[1], 4)

    def test_macos_matches_exact_custom_title(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Darwin'), \
             patch.object(fight_windows.platform, 'release', return_value='23.0'), \
             patch.object(fight_windows, '_run', return_value='found\n') as run:
            self.assertTrue(fight_windows.close_owned_window('wizard', 'private'))
        command = run.call_args.args[0]
        self.assertEqual(command[-2:], ['Two Keys Wizard private', 'close'])
        self.assertIn('custom title of selected tab of w is targetTitle', command[2])
        self.assertNotIn('contains', command[2])

    def test_macos_wizard_launch_sets_its_explicit_custom_title(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(fight_windows.platform, 'system', return_value='Darwin'), \
             patch.object(fight_windows.platform, 'release', return_value='23.0'), \
             patch.object(fight_windows.sys, 'executable', '/Python Path/python3'):
            command, _ = fight_windows.launch_command(12345, 'private')
        self.assertIn('set gameTab to do script (item 1 of argv)', command[2])
        self.assertIn('set custom title of gameTab to (item 2 of argv)', command[2])
        self.assertTrue(command[3].startswith("exec '/Python Path/python3'"))
        self.assertEqual(command[4], 'Two Keys Wizard private')

    def test_finish_runs_after_pair_closed_and_reports_manual_fallback(self):
        pair = object.__new__(fight_windows.WindowPair)
        pair.closed = threading.Event()
        pair.closed.set()
        pair.events = queue.SimpleQueue()
        with patch.object(fight_windows.time, 'sleep') as delay, \
             patch.object(fight_windows.platform, 'system', return_value='Darwin'), \
             patch.object(fight_windows, 'close_owned_window', return_value=False) as close, \
             patch.object(fight_windows, 'fullscreen_player', return_value=False) as fullscreen, \
             patch.object(fight_windows, 'focus_player', return_value=False) as focus:
            pair._finish_wizard('private')
        delay.assert_called_once_with(0.15)
        close.assert_called_once_with('wizard', 'private')
        fullscreen.assert_called_once_with('private')
        focus.assert_called_once_with('private')
        event, detail = pair.events.get_nowait()
        self.assertEqual(event, 'wizard_closed')
        self.assertIn('manually', detail)

    def test_finish_fullscreens_player_before_releasing_epilogue(self):
        pair = object.__new__(fight_windows.WindowPair)
        pair.events = queue.SimpleQueue()
        actions = []
        with patch.object(fight_windows.time, 'sleep'), \
             patch.object(fight_windows, 'close_owned_window', side_effect=lambda *args: actions.append('close-wizard') or True), \
             patch.object(fight_windows, 'fullscreen_player', side_effect=lambda *args: actions.append('fullscreen-player') or True):
            pair._finish_wizard('private')
        self.assertEqual(actions, ['close-wizard', 'fullscreen-player'])
        self.assertEqual(pair.events.get_nowait(), ('wizard_closed', ''))

    def test_finish_retries_transient_x11_window_removal_race(self):
        pair = object.__new__(fight_windows.WindowPair)
        pair.events = queue.SimpleQueue()
        with patch.object(fight_windows.time, 'sleep'), \
             patch.object(fight_windows.platform, 'system', return_value='Linux'), \
             patch.object(fight_windows, '_is_wsl', return_value=False), \
             patch.object(fight_windows, 'close_owned_window', return_value=True), \
             patch.object(fight_windows, 'fullscreen_player', side_effect=[False, True]) as fullscreen:
            pair._finish_wizard('private')
        self.assertEqual(fullscreen.call_count, 2)
        self.assertEqual(pair.events.get_nowait(), ('wizard_closed', ''))

    def test_finish_request_is_idempotent(self):
        pair = object.__new__(fight_windows.WindowPair)
        pair.finishing = threading.Event()
        with patch.object(fight_windows.threading, 'Thread') as thread:
            pair.finish_wizard('private')
            pair.finish_wizard('private')
        thread.assert_called_once()
        thread.return_value.start.assert_called_once()

    def test_owned_player_close_waits_for_game_exit_in_detached_helper(self):
        with patch.object(fight_windows.subprocess, 'Popen') as popen, \
             patch.object(fight_windows.os, 'getpid', return_value=12345):
            self.assertTrue(fight_windows.schedule_player_close('private'))
        command = popen.call_args.args[0]
        self.assertEqual(command[-4:], ['--close-player', 'private', '--after-pid', '12345'])
        self.assertTrue(popen.call_args.kwargs['start_new_session'])
        self.assertNotIn('shell', popen.call_args.kwargs)
        with patch.object(fight_windows, '_process_alive', side_effect=[True, False]), \
             patch.object(fight_windows.time, 'sleep') as delay, \
             patch.object(fight_windows, 'close_owned_window') as close:
            fight_windows._close_player_after_exit('private', 12345)
        delay.assert_called_once_with(0.05)
        close.assert_called_once_with('player', 'private')

    def test_detached_helper_leaves_still_running_game_alone(self):
        with patch.object(fight_windows, '_process_alive', return_value=True), \
             patch.object(fight_windows.time, 'monotonic', side_effect=[0, 6]), \
             patch.object(fight_windows, 'close_owned_window') as close:
            fight_windows._close_player_after_exit('private', 12345)
        close.assert_not_called()


class LauncherOwnershipTests(unittest.TestCase):
    def test_linux_launcher_marks_only_new_window_as_owned(self):
        with patch.dict(os.environ, {'GNOME_TERMINAL_SCREEN': 'old-screen'}, clear=True), \
             patch.object(launcher.platform, 'system', return_value='Linux'), \
             patch.object(launcher.platform, 'release', return_value='generic'), \
             patch.object(launcher.secrets, 'token_hex', return_value='unique'), \
             patch.object(launcher.subprocess, 'Popen') as popen:
            launcher.launch('--ending')
        command = popen.call_args.args[0]
        self.assertIn('--full-screen', command)
        self.assertIn('--title=Two Keys Player unique', command)
        self.assertEqual(command[-4:], ['--owned-window', '--window-token', 'unique', '--ending'])
        self.assertNotIn('GNOME_TERMINAL_SCREEN', popen.call_args.kwargs['env'])
        self.assertIn(launcher.sys.executable, command)

    def test_wsl_launcher_uses_current_distribution_and_forwards_fight(self):
        with patch.dict(os.environ, {'WSL_DISTRO_NAME': 'Ubuntu-MyGame'}, clear=True), \
             patch.object(launcher.platform, 'system', return_value='Linux'), \
             patch.object(launcher.platform, 'release', return_value='microsoft'), \
             patch.object(launcher.secrets, 'token_hex', return_value='unique'), \
             patch.object(launcher.shutil, 'which', return_value='wt.exe'), \
             patch.object(launcher.subprocess, 'run') as run:
            launcher.launch('--fight')
        command = run.call_args.args[0]
        self.assertIn('Ubuntu-MyGame', command)
        self.assertIn(launcher.sys.executable, command)
        self.assertIn('--fullscreen', command)
        self.assertIn('--suppressApplicationTitle', command)
        self.assertEqual(command[-4:], ['--owned-window', '--window-token', 'unique', '--fight'])

    def test_macos_launcher_sets_custom_title_and_passes_ownership(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(launcher.platform, 'system', return_value='Darwin'), \
             patch.object(launcher.secrets, 'token_hex', return_value='unique'), \
             patch.object(launcher.subprocess, 'run') as run:
            launcher.launch('--ending')
        command = run.call_args.args[0]
        self.assertEqual(command[-1], 'Two Keys Player unique')
        self.assertIn('--owned-window --window-token unique --ending', command[-2])
        self.assertIn('set custom title of gameTab', command[2])
        self.assertIn(launcher.sys.executable, command[-2])

    def test_native_windows_uses_configured_default_distro_without_hardcoding(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(launcher.platform, 'system', return_value='Windows'), \
             patch.object(launcher.shutil, 'which', return_value='wt.exe'), \
             patch.object(launcher.subprocess, 'run') as run:
            launcher.launch('--finale')
        command = run.call_args.args[0]
        self.assertNotIn('--distribution', command)
        self.assertNotIn('Ubuntu', command)
        self.assertIn('python3.12', command)
        self.assertEqual(command[-1], '--finale')

    def test_wsl_launcher_requires_identifiable_active_distribution(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(launcher.platform, 'system', return_value='Linux'), \
             patch.object(launcher.platform, 'release', return_value='microsoft'), \
             patch.object(launcher.subprocess, 'run') as run:
            with self.assertRaisesRegex(SystemExit, 'WSL_DISTRO_NAME'):
                launcher.launch('--finale')
        run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
