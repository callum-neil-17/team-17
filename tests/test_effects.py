"""The cinematic is deterministic, bounded and safe at small terminal sizes."""

import re
import unittest

from fight.effects import (DEATH_DURATION, ERRORS, FATAL_ERROR, PLAYER_HAND_ROW,
                           PLAYER_POSES, render_death, render_terminal_collapse)


def frame_lines(screen):
    plain = re.sub(r"\x1b\[[0-9;]*m", "", screen)
    return re.findall(r"\x1b\[(\d+);1H\x1b\[2K([^\x1b]*)", plain)


def collapse_lines(screen):
    plain = re.sub(r"\x1b\[[0-9;]*m", "", screen)
    return re.findall(r"\x1b\[(\d+);(\d+)H(\x1b\[2K)?([^\x1b]*)", plain)


class EffectsTests(unittest.TestCase):
    def test_impact_keeps_live_wizard_anchor(self):
        from fight.controller import draw_scene

        for size, lane in (((104, 53), 24), ((60, 30), 13), ((50, 28), 12)):
            with self.subTest(size=size):
                live = dict(frame_lines(draw_scene(
                    "wizard", size, "The spell reaches the wizard...", row=lane,
                    level_number=11, description="There's no taking this one back!")))
                impact = dict(frame_lines(render_death(size, 0, color=False, row=lane)))
                hat_row = next(row for row, text in live.items() if "_,-'|" in text)
                self.assertIn("_,-'|", impact[hat_row])
                self.assertEqual(live[hat_row].index("_,-'|"), impact[hat_row].index("_,-'|"))

    def test_effect_frames_remain_inside_terminal(self):
        for size in ((80, 30), (40, 24), (20, 12), (4, 4), (1, 1)):
            for elapsed in (0, 0.1, 0.5, 1, 1.7, 3.3, 3.7, 4.8, 5.2, 6.8, 7.5, 8, 20):
                with self.subTest(size=size, elapsed=elapsed):
                    screen = render_death(size, elapsed)
                    lines = frame_lines(screen)
                    self.assertEqual(len(lines), size[1])
                    self.assertTrue(all(1 <= int(row) <= size[1] for row, _ in lines))
                    self.assertTrue(all(len(line) <= max(1, size[0] - 1) for _, line in lines))
                    self.assertTrue(all(all(32 <= ord(char) <= 126 for char in line) for _, line in lines))

    def test_visual_stages_and_final_fatal_are_distinct_and_deterministic(self):
        times = (0.05, 0.8, 2.5, 4.3, 6.0, DEATH_DURATION)
        frames = [render_death((80, 30), elapsed, color=False) for elapsed in times]
        self.assertEqual(len(set(frames)), len(times))
        self.assertEqual(frames, [render_death((80, 30), elapsed, color=False) for elapsed in times])
        final_text = "\n".join(line for _, line in frame_lines(frames[-1]))
        self.assertIn(FATAL_ERROR, final_text)
        self.assertIn("CACHE FLUSH COMPLETE", final_text)
        self.assertIn("PROCESS TERMINATED", final_text)
        self.assertEqual(frames[-1], render_death((80, 30), 100, color=False))
        self.assertGreaterEqual(sum(error in final_text for error in ERRORS), 5)

    def test_no_color_setting_and_frame_work_are_bounded(self):
        screen = render_death((10000, 10000), 6.8, color=False)
        self.assertNotRegex(screen, r"\x1b\[[0-9;]*m")
        self.assertLess(len(screen), 240 * 80 + 2000)
        self.assertEqual(len(frame_lines(screen)), 80)

    def test_player_poses_share_footline_and_printable_ascii(self):
        self.assertEqual(set(PLAYER_POSES), {"ready", "recoil", "victory"})
        heights = {len(pose.splitlines()) for pose in PLAYER_POSES.values()}
        self.assertEqual(heights, {12})
        self.assertLess(PLAYER_HAND_ROW, 12)
        for pose in PLAYER_POSES.values():
            self.assertTrue(all(char == "\n" or 32 <= ord(char) <= 126 for char in pose))
            self.assertLessEqual(max(map(len, pose.splitlines())), 20)
            self.assertIn("[", pose.splitlines()[-1])

    def test_terminal_collapse_changes_deterministically_while_preserving_the_clue(self):
        times = (0, 2, 5, 9)
        frames = [render_terminal_collapse((80, 30), elapsed, color=False)
                  for elapsed in times]
        self.assertEqual(len(set(frames)), len(times))
        self.assertEqual(frames, [render_terminal_collapse((80, 30), elapsed, color=False)
                                  for elapsed in times])
        for size in ((60, 30), (80, 24), (120, 40)):
            for elapsed in times:
                with self.subTest(size=size, elapsed=elapsed):
                    screen = render_terminal_collapse(size, elapsed, color=False)
                    text = "\n".join(line for _, _, _, line in collapse_lines(screen))
                    self.assertIn("There's only one way to leave the terminal.", text)

    def test_terminal_collapse_redraws_bounded_ascii_rows_inside_the_terminal(self):
        for size in ((1, 1), (4, 4), (20, 12), (80, 30), (240, 80), (10000, 10000)):
            width = max(1, min(239, size[0] - 1))
            height = max(1, min(80, size[1]))
            left = (max(1, size[0] - 1) - width) // 2 + 1
            top = (size[1] - height) // 2 + 1
            for elapsed in (0, 2, 5, 9):
                with self.subTest(size=size, elapsed=elapsed):
                    screen = render_terminal_collapse(size, elapsed, color=False)
                    lines = collapse_lines(screen)
                    self.assertEqual(len(lines), height)
                    self.assertEqual([int(row) for row, _, _, _ in lines],
                                     list(range(top, top + height)))
                    for _, column, erase, line in lines:
                        self.assertEqual(int(column), left)
                        self.assertLessEqual(len(line), width)
                        self.assertLessEqual(int(column) + len(line) - 1,
                                             max(1, size[0] - 1))
                        self.assertTrue(erase or len(line) == width)
                        self.assertTrue(all(32 <= ord(char) <= 126 for char in line))
                    self.assertLess(len(screen), 239 * 80 + 4000)

    def test_terminal_collapse_clear_and_color_flags(self):
        first = render_terminal_collapse((80, 30), 2, color=False, clear=True)
        next_frame = render_terminal_collapse((80, 30), 2, color=False, clear=False)
        self.assertIn("\x1b[2J", first)
        self.assertNotIn("\x1b[2J", next_frame)
        self.assertEqual(collapse_lines(first), collapse_lines(next_frame))
        self.assertNotRegex(first + next_frame, r"\x1b\[[0-9;]*m")


if __name__ == "__main__":
    unittest.main()
