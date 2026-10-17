from .level import Level


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
        )
