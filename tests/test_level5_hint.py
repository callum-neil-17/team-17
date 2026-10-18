"""The ATM's five-guess hint preserves its uppercase-C solution."""

import unittest

from levels import Level5


HINT = "Capitol c could do the trick"


class Level5HintTests(unittest.TestCase):
    def test_fifth_lowercase_guess_reveals_hint_without_solving_the_atm(self):
        level = Level5()
        original_prompt = level.prompt
        for index in range(4):
            self.assertFalse(level.check_input("c"))
            level.react_to_wrong_input("c", now=10 + index * .01)
            self.assertNotIn(HINT, level.render())
        deadline = level.reaction_deadline
        level.react_to_wrong_input("c", now=10.04)
        self.assertEqual(level.prompt, original_prompt + "\n" + HINT)
        self.assertEqual(level.reaction_deadline, deadline)
        self.assertEqual(level.frame, 0)
        self.assertTrue(level.check_input("C"))
        self.assertFalse(level.check_input("c"))

        level.clear_reaction()
        level.idle_frame += 1
        for index in range(8):
            level.react_to_wrong_input("x", now=20 + index)
        self.assertEqual(level.wrong_guesses, 5)
        self.assertEqual(level.prompt.count(HINT), 1)
        self.assertNotIn("\n", level.render().replace("\r\n", ""))
        self.assertNotIn(HINT, Level5().render())

    def test_correct_capital_c_and_ignored_controls_do_not_count(self):
        level = Level5()
        for key in (None, "", "q", "\x03", "\x04", "\x1a", "\x1c",
                    "\x13", "\x11", "\x1b", "C"):
            level.react_to_wrong_input(key, now=10)
        self.assertEqual(level.wrong_guesses, 0)
        self.assertNotIn(HINT, level.render())
        self.assertEqual(level.required_input, ("C",))


if __name__ == "__main__":
    unittest.main()
