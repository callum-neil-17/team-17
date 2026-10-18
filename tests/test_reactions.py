"""Wrong guesses animate the artwork without changing clues or puzzle state."""

import contextlib
import io
import re
import unittest
from unittest.mock import patch

import game
from levels import (Level, Level1, Level2, Level3, Level4, Level5,
                    Level6, Level7, Level8, Level9)
from levels.level4 import CTRL_R, F5_SEQUENCES


class ReactionTests(unittest.TestCase):
    def make_level(self, **kwargs):
        options = dict(number=1, title="Test level", required_input=("\r", "\n"),
                       art=["| o |", "|   |"], description="A quiet room.",
                       prompt="The clue remains.", wrong_frames=["|o  |", "|  o|", "| o |"])
        options.update(kwargs)
        return Level(**options)

    def test_animation_uses_local_time_then_restores_the_original_scene(self):
        level = self.make_level()
        original = level.render()
        self.assertTrue(level.react_to_wrong_input("x", now=10.0))
        self.assertEqual(level.art(0), "|o  |")
        self.assertAlmostEqual(level.reaction_deadline, 10.12)
        self.assertFalse(level.update_reaction(now=10.119))
        self.assertTrue(level.update_reaction(now=10.12))
        self.assertEqual(level.art(0), "|  o|")
        self.assertEqual(level.frame, 0)
        self.assertTrue(level.update_reaction(now=10.36))
        self.assertIsNone(level.reaction_frame)
        self.assertIsNone(level.reaction_deadline)
        self.assertEqual(level.render(), original)

    def test_late_tick_skips_frames_without_delaying_input(self):
        level = self.make_level()
        level.react_to_wrong_input("x", now=10.0)
        self.assertTrue(level.update_reaction(now=10.25))
        self.assertEqual(level.reaction_frame, 2)
        self.assertTrue(level.update_reaction(now=20.0))
        self.assertIsNone(level.reaction_frame)
        self.assertFalse(level.update_reaction(now=30.0))

    def test_repeated_or_different_guesses_cannot_restart_an_active_animation(self):
        level = self.make_level()
        level.react_to_wrong_input("x", now=10.0)
        level.update_reaction(now=10.12)
        deadline = level.reaction_deadline
        for key in ("x", "a", "x", "\t"):
            self.assertFalse(level.react_to_wrong_input(key, now=10.2))
            self.assertEqual(level.reaction_frame, 1)
            self.assertEqual(level.reaction_deadline, deadline)
        level.update_reaction(now=10.36)
        self.assertFalse(level.react_to_wrong_input("x", now=10.5))
        self.assertTrue(level.react_to_wrong_input("x", now=10.75))

    def test_correct_and_ignored_keys_do_not_start_a_reaction(self):
        level = self.make_level()
        for key in (None, "", "q", "\x04", "\x1a", "\x1c", "\x13", "\x11", "\r", "\n"):
            with self.subTest(key=key):
                self.assertFalse(level.react_to_wrong_input(key, now=10.0))
                self.assertIsNone(level.reaction_frame)
        self.assertTrue(level.react_to_wrong_input("\x03", now=10.0))

    def test_clear_interrupts_reaction_without_changing_success_frames(self):
        level = self.make_level()
        original_frames = list(level.frames)
        level.react_to_wrong_input("x", now=10.0)
        level.clear_reaction()
        self.assertIsNone(level.reaction_frame)
        self.assertEqual(level.art(0), original_frames[0])
        self.assertEqual(level.frames, original_frames)
        self.assertEqual(level.frame, 0)

    def test_levels_without_reaction_art_keep_their_original_render(self):
        level = self.make_level(wrong_frames=[])
        before = level.render()
        self.assertFalse(level.react_to_wrong_input("x", now=10.0))
        self.assertEqual(level.render(), before)

    def test_every_scene_changes_only_art_with_fixed_dimensions_and_no_new_text(self):
        for cls in (Level1, Level2, Level3, Level4, Level5, Level6, Level7, Level8, Level9):
            with self.subTest(level=cls.__name__):
                level = cls()
                before = level.render()
                normal = level.art(0).splitlines()
                shape = len(normal), max(map(len, normal))
                original = (level.prompt, level.description, level.required_input,
                            list(level.frames), level.frame)
                self.assertTrue(level.react_to_wrong_input("z", now=10.0))
                rendered = []
                for index in range(len(level.wrong_frames)):
                    level.update_reaction(now=10 + index * level.wrong_frame_delay)
                    picture = level.art(0)
                    rows = picture.splitlines()
                    self.assertEqual((len(rows), max(map(len, rows))), shape)
                    self.assertTrue(all(32 <= ord(char) <= 126 for row in rows for char in row))
                    screen = level.render()
                    sections = screen.rstrip("\r\n").split("\r\n\r\n")
                    self.assertEqual(sections[-1], level.prompt.replace("\n", "\r\n"))
                    self.assertNotIn("\n", screen.replace("\r\n", ""))
                    rendered.append(picture)
                self.assertGreaterEqual(len(set(rendered)), 3)
                self.assertEqual((level.prompt, level.description, level.required_input,
                                  level.frames, level.frame), original)
                level.clear_reaction()
                self.assertEqual(level.render(), before)

    def test_waiting_scenes_loop_without_touching_the_solve_animation(self):
        for cls in (Level2, Level3, Level4, Level5, Level6, Level7, Level8, Level9):
            with self.subTest(level=cls.__name__):
                level = cls()
                self.assertIsNotNone(level.idle_frame_delay)
                normal = level.art(0).splitlines()
                shape = len(normal), max(map(len, normal))
                pictures = []
                for index in range(len(level.idle_frames) + 1):
                    level.idle_frame = index
                    rows = level.art(0).splitlines()
                    self.assertEqual((len(rows), max(map(len, rows))), shape)
                    pictures.append(level.art(0))
                self.assertGreaterEqual(len(set(pictures)), 2)
                # The loop wraps, and later frames still play the solve sequence.
                self.assertEqual(pictures[-1], pictures[0])
                self.assertEqual(level.art(1), level.frames[1].strip("\n"))

    def test_door_reaction_keeps_title_art_and_clue_at_their_original_rows(self):
        level = Level2()
        screens = [level.render()]
        level.react_to_wrong_input("k", now=10.0)
        level.update_reaction(now=10.12)
        screens.append(level.render())
        positioned = []
        with patch.object(game.shutil, "get_terminal_size", return_value=(80, 40)):
            for screen in screens:
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    game.render_screen(screen, level.layout)
                positioned.append(re.findall(r"\x1b\[(\d+);1H", output.getvalue()))
        self.assertEqual(positioned[0], positioned[1])

    def test_bar_and_refresh_solutions_still_work_during_reactions(self):
        bar = Level3()
        self.assertFalse(bar.check_input("x"))
        bar.react_to_wrong_input("x", now=10.0)
        self.assertFalse(bar.solved)
        self.assertTrue(bar.check_input("\t"))
        self.assertTrue(bar.solved)
        for key in (*F5_SEQUENCES, CTRL_R):
            level = Level4()
            level.react_to_wrong_input("x", now=10.0)
            self.assertFalse(level.react_to_wrong_input(key, now=10.1))
            self.assertTrue(level.check_input(key))


class GameReactionTests(unittest.TestCase):
    def run_level(self, level, inputs, *, frames=None):
        clock = [0.0]
        events = iter(inputs)

        def read_key(fd, timeout=None):
            elapsed, key = next(events)
            clock[0] += elapsed
            return key

        with patch.object(game, "Level1", return_value=level), \
             patch.object(game.termios, "tcgetattr", return_value="original"), \
             patch.object(game.termios, "tcsetattr") as restore, \
             patch.object(game.tty, "setraw"), \
             patch.object(game.time, "monotonic", side_effect=lambda: clock[0]), \
             patch.object(game, "read_key", side_effect=read_key) as read, \
             patch.object(game, "play_frames", side_effect=frames or (lambda *args: True)) as play, \
             patch.object(game, "render_screen") as render, \
             contextlib.redirect_stdout(io.StringIO()):
            game.main()
        restore.assert_called_once()
        return read, play, render

    def level(self):
        return Level(1, "Reaction room", ("\r",), art=["normal", "solved"],
                     prompt="The clue remains.", wrong_frames=["shake1", "shake2", "normal"])

    def test_wrong_guess_animates_without_more_keys_then_returns_to_normal(self):
        level = self.level()
        read, play, render = self.run_level(level, [(0.1, "x"), (0.12, None),
                                                   (0.12, None), (0.12, None), (0.0, "")])
        screens = [call.args[0] for call in render.call_args_list]
        self.assertIn("shake1", screens[1])
        self.assertIn("shake2", screens[2])
        self.assertIn("normal", screens[-1])
        self.assertIsNone(level.reaction_frame)
        self.assertIsNone(read.call_args_list[0].kwargs["timeout"])
        for call in read.call_args_list[1:4]:
            self.assertGreater(call.kwargs["timeout"], 0)
            self.assertLessEqual(call.kwargs["timeout"], 0.120001)
        self.assertIsNone(read.call_args_list[-1].kwargs["timeout"])
        play.assert_not_called()

    def test_correct_input_interrupts_immediately_before_success_animation(self):
        level = self.level()
        animation_states = []

        def frames(current, fd):
            animation_states.append((current.reaction_frame, current.art(0)))
            return True

        _, play, render = self.run_level(level, [(0.1, "x"), (0.01, "\r"), (0.0, "")], frames=frames)
        self.assertEqual(animation_states, [(None, "normal")])
        play.assert_called_once()
        self.assertIn("Level 2", render.call_args.args[0])

    def test_idle_stars_continue_during_and_after_a_reaction(self):
        level = self.level()
        level.idle_frame_delay = 0.4
        _, play, render = self.run_level(level, [(0.1, "x"), (0.12, None),
                                                (0.12, None), (0.12, None), (0.4, None), (0.0, "")])
        self.assertIsNone(level.reaction_frame)
        self.assertGreaterEqual(level.idle_frame, 1)
        self.assertGreaterEqual(render.call_count, 4)
        play.assert_not_called()

    def test_existing_ignored_keys_stay_silent(self):
        level = self.level()
        ignored = ("q", "\x04", "\x1a", "\x1c", "\x13", "\x11", None)
        read, play, render = self.run_level(level, [(0.1, key) for key in ignored] + [(0.0, "")])
        self.assertEqual(read.call_count, len(ignored) + 1)
        render.assert_called_once()
        self.assertIsNone(level.reaction_frame)
        play.assert_not_called()


if __name__ == "__main__":
    unittest.main()
