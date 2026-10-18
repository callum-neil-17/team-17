"""The bartender offers a hint after five wrong inputs, without solving the bar."""

import contextlib
import io
import unittest
from unittest.mock import patch

import game
from levels import Level1, Level2, Level3
from levels.level3 import BAR_FRAMES


HINT = "Think about how you could open a tab?"
DOOR_HINT = "ENTER!!! the room"


class Level3HintTests(unittest.TestCase):
    def test_fifth_wrong_guess_reveals_the_hint_once_and_keeps_it_visible(self):
        level = Level3()
        original_prompt = level.prompt
        for index in range(4):
            level.react_to_wrong_input("x", now=10.0 + index)
            level.update_reaction(now=11.0 + index)
            self.assertEqual(level.prompt, original_prompt)
            self.assertNotIn(HINT, level.render())

        level.react_to_wrong_input("z", now=14.0)
        self.assertEqual(level.prompt, original_prompt.rstrip() + "\n" + HINT)
        level.clear_reaction()
        level.idle_frame += 1
        self.assertIn(HINT, level.render())

        for index in range(8):
            level.react_to_wrong_input("x", now=20.0 + index)
            level.update_reaction(now=21.0 + index)
        self.assertEqual(level.wrong_guesses, 5)
        self.assertEqual(level.prompt.count(HINT), 1)
        self.assertNotIn(HINT, Level3().render())

    def test_each_wrong_key_counts_while_the_art_reaction_is_active(self):
        level = Level3()
        level.react_to_wrong_input("x", now=10.0)
        deadline = level.reaction_deadline
        for index in range(4):
            level.react_to_wrong_input("x", now=10.01 + index * 0.01)
        self.assertEqual(level.wrong_guesses, 5)
        self.assertEqual(level.reaction_deadline, deadline)
        self.assertEqual(level.reaction_frame, 0)
        self.assertIn(HINT, level.render())

    def test_ignored_controls_tab_and_idle_updates_do_not_count(self):
        level = Level3()
        self.assertEqual(level.required_input, ("\t",))
        ignored = (None, "", "q", "\x03", "\x04", "\x1a", "\x1c",
                   "\x13", "\x11", "\x1b", "\t")
        for index, key in enumerate(ignored):
            level.react_to_wrong_input(key, now=10.0 + index)
            level.update_reaction(now=11.0 + index)
        for index in range(20):
            level.idle_frame += 1
            level.update_reaction(now=100.0 + index)
        self.assertEqual(level.wrong_guesses, 0)
        self.assertFalse(level.solved)
        self.assertNotIn(HINT, level.render())

    def test_hint_does_not_solve_the_bar_and_tab_still_starts_serving(self):
        level = Level3()
        for index in range(5):
            self.assertFalse(level.check_input("x"))
            level.react_to_wrong_input("x", now=10.0 + index)
        self.assertFalse(level.solved)
        self.assertEqual(level.frame, 0)
        self.assertEqual(level.frames, BAR_FRAMES)
        self.assertFalse(level.check_input("\r"))
        self.assertFalse(level.check_input("\n"))
        self.assertTrue(level.check_input("\t"))
        self.assertTrue(level.solved)
        self.assertEqual(level.wrong_guesses, 5)

    def test_hint_stays_in_the_prompt_section_and_uses_raw_mode_newlines(self):
        level = Level3()
        for index in range(5):
            level.react_to_wrong_input("x", now=10.0 + index)
        screen = level.render()
        sections = screen.rstrip("\r\n").split("\r\n\r\n")
        self.assertEqual(len(sections), 4)
        self.assertEqual(sections[1], "Level 3")
        self.assertEqual(sections[-1], level.prompt.replace("\n", "\r\n"))
        self.assertTrue(sections[-1].endswith(HINT))
        self.assertNotIn("\n", screen.replace("\r\n", ""))

    def test_door_and_bar_hint_counters_are_independent(self):
        door, bar = Level2(), Level3()
        for index in range(5):
            door.react_to_wrong_input("x", now=10.0 + index)
        self.assertIn(DOOR_HINT, door.render())
        self.assertEqual(bar.wrong_guesses, 0)
        self.assertNotIn(HINT, bar.render())

        for index in range(5):
            bar.react_to_wrong_input("x", now=20.0 + index)
        self.assertIn(HINT, bar.render())
        self.assertNotIn(DOOR_HINT, bar.render())
        self.assertIn(DOOR_HINT, door.render())
        self.assertNotIn(HINT, door.render())


class Level3HintGameTests(unittest.TestCase):
    def test_game_shows_the_bar_hint_then_advances_automatically_after_tab(self):
        level = Level3()
        original_settings = ["saved terminal settings"]
        with patch.object(game, "Level3", return_value=level), \
             patch.object(game.sys, "stdin") as stdin, \
             patch.object(game.termios, "tcgetattr", return_value=original_settings), \
             patch.object(game.termios, "tcsetattr") as restore, \
             patch.object(game.tty, "setraw") as setraw, \
             patch.object(game.time, "monotonic", return_value=10.0), \
             patch.object(game, "read_key", side_effect=["Y", "\r"] + ["x"] * 5 + ["\t", ""]), \
             patch.object(game, "play_frames", return_value=True) as play, \
             patch.object(game, "render_screen") as render, \
             contextlib.redirect_stdout(io.StringIO()):
            stdin.fileno.return_value = 17
            game.main()

        screens = [call.args[0] for call in render.call_args_list]
        self.assertTrue(any("Level 3" in screen and HINT in screen for screen in screens))
        for screen in screens:
            if "Level 1" in screen or "Level 2" in screen or "Level 4" in screen:
                self.assertNotIn(HINT, screen)
        self.assertIn("Level 4", screens[-1])
        self.assertFalse(level.check_input("\r"))
        self.assertTrue(level.solved)
        self.assertEqual(play.call_count, 3)
        self.assertIsInstance(play.call_args_list[0].args[0], Level1)
        self.assertIsInstance(play.call_args_list[1].args[0], Level2)
        self.assertEqual(play.call_args_list[2].args, (level, 17))
        setraw.assert_called_once_with(17)
        restore.assert_called_once_with(17, game.termios.TCSADRAIN, original_settings)


if __name__ == "__main__":
    unittest.main()
