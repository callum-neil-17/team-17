"""The drink puzzle offers its refresh hint after five wrong guesses."""

import contextlib
import io
import unittest
from unittest.mock import patch

import game
from levels import Level4
from levels.level4 import CTRL_R, F5_SEQUENCES


HINT = "How do you refresh ?"


class Level4HintTests(unittest.TestCase):
    def test_fifth_guess_reveals_one_persistent_hint_during_an_art_reaction(self):
        level = Level4()
        original_prompt = level.prompt
        for index in range(4):
            self.assertFalse(level.check_input("x"))
            level.react_to_wrong_input("x", now=10.0 + index * 0.01)
            self.assertEqual(level.prompt, original_prompt)
            self.assertNotIn(HINT, level.render())
        deadline = level.reaction_deadline

        level.react_to_wrong_input("x", now=10.04)
        self.assertEqual(level.wrong_guesses, 5)
        self.assertEqual(level.reaction_deadline, deadline)
        self.assertEqual(level.prompt, original_prompt.rstrip() + "\n" + HINT)
        level.clear_reaction()
        level.idle_frame += 1
        for index in range(5):
            level.react_to_wrong_input("z", now=20.0 + index)
        self.assertEqual(level.prompt.count(HINT), 1)
        screen = level.render()
        self.assertIn(HINT, screen)
        self.assertNotIn("\n", screen.replace("\r\n", ""))
        self.assertNotIn(HINT, Level4().render())

    def test_ignored_keys_do_not_count_and_all_refresh_shortcuts_still_solve(self):
        level = Level4()
        ignored = (None, "", "q", "\x03", "\x04", "\x1a", "\x1c",
                   "\x13", "\x11", "\x1b", CTRL_R, *F5_SEQUENCES)
        for index, key in enumerate(ignored):
            level.react_to_wrong_input(key, now=10.0 + index)
        self.assertEqual(level.wrong_guesses, 0)
        self.assertNotIn(HINT, level.render())

        for shortcut in (CTRL_R, *F5_SEQUENCES):
            with self.subTest(shortcut=repr(shortcut)):
                level = Level4()
                for index in range(5):
                    self.assertFalse(level.check_input("x"))
                    level.react_to_wrong_input("x", now=10.0 + index)
                self.assertTrue(level.check_input(shortcut))
                self.assertIn(HINT, level.render())

    def test_game_leaves_the_hint_behind_when_refresh_advances_to_level5(self):
        level = Level4()
        original_settings = ["saved terminal settings"]
        keys = ["Y", "\r", "\t"] + ["x"] * 5 + [CTRL_R, ""]
        with patch.object(game, "Level4", return_value=level), \
             patch.object(game.sys, "stdin") as stdin, \
             patch.object(game.termios, "tcgetattr", return_value=original_settings), \
             patch.object(game.termios, "tcsetattr") as restore, \
             patch.object(game.tty, "setraw") as setraw, \
             patch.object(game.time, "monotonic", return_value=10.0), \
             patch.object(game, "read_key", side_effect=keys), \
             patch.object(game, "play_frames", return_value=True) as play, \
             patch.object(game, "render_screen") as render, \
             contextlib.redirect_stdout(io.StringIO()):
            stdin.fileno.return_value = 17
            game.main()

        screens = [call.args[0] for call in render.call_args_list]
        self.assertTrue(any("Level 4" in screen and HINT in screen for screen in screens))
        for screen in screens:
            if "Level 4" not in screen:
                self.assertNotIn(HINT, screen)
        self.assertIn("Level 5", screens[-1])
        self.assertEqual(play.call_count, 4)
        self.assertEqual(play.call_args_list[-1].args, (level, 17))
        setraw.assert_called_once_with(17)
        restore.assert_called_once_with(17, game.termios.TCSADRAIN, original_settings)


if __name__ == "__main__":
    unittest.main()
