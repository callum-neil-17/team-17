from .level import Level


LEVEL11_FRAMES = [
    # Add your starting ASCII art inside this raw string.
    r"""
""",
    # Add more raw strings here for frames played after solving the puzzle.
]


class Level11(Level):
    """Undo the wizard's final spell in the same two terminal windows."""

    def __init__(self) -> None:
        super().__init__(
            number=11,
            title="Level 11",
            required_input=("\x1a",),  # Ctrl+Z is input in the game's raw mode.
            art=LEVEL11_FRAMES,
            description="The wizard unleashes one final spell.",
            prompt="There's no taking this one back!",
        )
