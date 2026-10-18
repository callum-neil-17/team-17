"""The door puzzle reveals its own hint after five wrong inputs."""

import contextlib
import io
import unittest
from unittest.mock import patch

import game
from levels import Level1, Level2, Level5


HINT = "ENTER!!! the room"


class Level2HintTests(unittest.TestCase):
    def test_fifth_wrong_guess_reveals_the_hint_once_and_keeps_it_visible(self):
        level = Level2()
        original_prompt = level.prompt
        for index in range(4):
            level.react_to_wrong_input("x", now=10.0 + index)
            level.update_reaction(now=11.0 + index)
            self.assertEqual(level.prompt, original_prompt)
            self.assertNotIn(HINT, level.render())

        level.react_to_wrong_input("z", now=14.0)
        self.assertEqual(level.prompt, original_prompt.rstrip() + "\n" + HINT)
        self.assertIn(HINT, level.render())
        level.clear_reaction()
        level.idle_frame += 1
        self.assertIn(HINT, level.render())

        for index in range(8):
            level.react_to_wrong_input("x", now=20.0 + index)
            level.update_reaction(now=21.0 + index)
        self.assertEqual(level.wrong_guesses, 5)
        self.assertEqual(level.prompt.count(HINT), 1)
        self.assertNotIn(HINT, Level2().render())

    def test_each_wrong_key_counts_while_the_art_reaction_is_active(self):
        level = Level2()
        level.react_to_wrong_input("x", now=10.0)
        deadline = level.reaction_deadline
        for index in range(4):
            level.react_to_wrong_input("x", now=10.01 + index * 0.01)
        self.assertEqual(level.wrong_guesses, 5)
        self.assertEqual(level.reaction_deadline, deadline)
        self.assertEqual(level.reaction_frame, 0)
        self.assertIn(HINT, level.render())

    def test_ignored_controls_correct_answers_and_idle_updates_do_not_count(self):
        level = Level2()
        self.assertEqual(level.required_input, ("\r", "\n"))
        ignored = (None, "", "q", "\x03", "\x04", "\x1a", "\x1c",
                   "\x13", "\x11", "\x1b", *level.required_input)
        for index, key in enumerate(ignored):
            level.react_to_wrong_input(key, now=10.0 + index)
            level.update_reaction(now=11.0 + index)
        for index in range(20):
            level.idle_frame += 1
            level.update_reaction(now=100.0 + index)
        self.assertEqual(level.wrong_guesses, 0)
        self.assertNotIn(HINT, level.render())
        for key in level.required_input:
            self.assertTrue(level.check_input(key))

    def test_hint_stays_in_the_prompt_section_and_uses_raw_mode_newlines(self):
        level = Level2()
        for index in range(5):
            level.react_to_wrong_input("x", now=10.0 + index)
        screen = level.render()
        sections = screen.rstrip("\r\n").split("\r\n\r\n")
        self.assertEqual(len(sections), 3)
        self.assertEqual(sections[0], "Level 2")
        self.assertEqual(sections[-1], level.prompt.replace("\n", "\r\n"))
        self.assertTrue(sections[-1].endswith(HINT))
        self.assertNotIn("\n", screen.replace("\r\n", ""))

    def test_other_levels_preserve_their_clues_and_never_show_the_door_hint(self):
        for level in (Level1(), Level5()):
            with self.subTest(level=level.number):
                original_prompt = level.prompt
                for index in range(12):
                    level.react_to_wrong_input("x", now=10.0 + index)
                    level.update_reaction(now=11.0 + index)
                self.assertTrue(level.prompt.startswith(original_prompt.rstrip()))
                self.assertNotIn(HINT, level.render())


class Level2HintGameTests(unittest.TestCase):
    def test_game_shows_hint_only_at_door_and_leaves_it_behind_after_enter(self):
        level = Level2()
        original_settings = ["saved terminal settings"]
        with patch.object(game, "Level2", return_value=level), \
             patch.object(game.sys, "stdin") as stdin, \
             patch.object(game.termios, "tcgetattr", return_value=original_settings), \
             patch.object(game.termios, "tcsetattr") as restore, \
             patch.object(game.tty, "setraw") as setraw, \
             patch.object(game.time, "monotonic", return_value=10.0), \
             patch.object(game, "read_key", side_effect=["Y"] + ["x"] * 5 + ["\r", ""]), \
             patch.object(game, "play_frames", return_value=True) as play, \
             patch.object(game, "render_screen") as render, \
             contextlib.redirect_stdout(io.StringIO()):
            stdin.fileno.return_value = 17
            game.main()

        screens = [call.args[0] for call in render.call_args_list]
        self.assertTrue(any("Level 2" in screen and HINT in screen for screen in screens))
        self.assertTrue(any("Level 1" in screen for screen in screens))
        for screen in screens:
            if "Level 1" in screen or "Level 3" in screen:
                self.assertNotIn(HINT, screen)
        self.assertIn("Level 3", screens[-1])
        self.assertNotIn(HINT, screens[-1])
        self.assertEqual(play.call_count, 2)
        self.assertIsInstance(play.call_args_list[0].args[0], Level1)
        self.assertEqual(play.call_args_list[0].args[1], 17)
        self.assertEqual(play.call_args_list[1].args, (level, 17))
        setraw.assert_called_once_with(17)
        restore.assert_called_once_with(17, game.termios.TCSADRAIN, original_settings)


if __name__ == "__main__":
    unittest.main()
