from .level import Level


LEVEL10_FRAMES = [
    # Add your starting ASCII art inside this raw string.
    r"""
""",
    # Add more raw strings here for frames played after solving the puzzle.
]


class Level10(Level):
    def __init__(self) -> None:
        super().__init__(
            number=10,
            title="Level 10",
            required_input=("\r", "\n"),  # Replace with the puzzle's input.
            art=LEVEL10_FRAMES,
            description="",  # Add the background description here.
            prompt="Press Enter to continue.",  # Replace with your riddle.
        )
