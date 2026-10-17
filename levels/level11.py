from .level import Level


LEVEL11_FRAMES = [
    # Add your starting ASCII art inside this raw string.
    r"""
""",
    # Add more raw strings here for frames played after solving the puzzle.
]


class Level11(Level):
    def __init__(self) -> None:
        super().__init__(
            number=11,
            title="Level 11",
            required_input=("\r", "\n"),  # Replace with the puzzle's input.
            art=LEVEL11_FRAMES,
            description="",  # Add the background description here.
            prompt="Press Enter to continue.",  # Replace with your riddle.
        )
