from .level import Level


LEVEL12_FRAMES = [
    # Add your starting ASCII art inside this raw string.
    r"""
""",
    # Add more raw strings here for frames played after solving the puzzle.
]


class Level12(Level):
    def __init__(self) -> None:
        super().__init__(
            number=12,
            title="Level 12",
            required_input=("\r", "\n"),  # Replace with the puzzle's input.
            art=LEVEL12_FRAMES,
            description="",  # Add the background description here.
            prompt="Press Enter to continue.",  # Replace with your riddle.
        )
