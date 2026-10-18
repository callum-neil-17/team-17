from .level import Level
from .level10 import PLAYER_WRONG_FRAMES


LEVEL11_FRAMES = [
    # Add your starting ASCII art inside this raw string.
    r"""
""",
    # Add more raw strings here for frames played after solving the puzzle.
]


class Level11(Level):
    """Undo the spell trapping the player, then send it back to the wizard."""

    def __init__(self) -> None:
        super().__init__(
            number=11,
            title="Level 11",
            required_input=("\x1a",),  # Ctrl+Z is input in the game's raw mode.
            art=LEVEL11_FRAMES,
            description="The wizard's spell is trapping you in the terminal.",
            prompt="Find a way to undo the wizard's spell trapping you in the terminal.",
            wrong_frames=PLAYER_WRONG_FRAMES,
        )
        self.wrong_guesses = 0

    def react_to_wrong_input(self, key: str | None, now: float | None = None) -> bool:
        ignored = (None, "", "q", "\x03", "\x04", "\x1a", "\x1c", "\x13", "\x11", "\x1b")
        if self.wrong_guesses < 5 and key not in ignored and key not in self.required_input:
            self.wrong_guesses += 1
            if self.wrong_guesses == 5:
                self.prompt = self.prompt.rstrip() + "\nWhats the command for undo ?"
        # Each wrong guess counts even while the existing art reaction plays.
        return super().react_to_wrong_input(key, now=now)
