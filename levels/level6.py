from .level import Level

# Door opening, one frame per string. Raw strings keep the backslashes intact.
DOOR_FRAMES = [
    r"""
 ________
|        |
|        |
|      o |
|        |
|________|
""",
    r"""
 ________
|\       |
| \      |
|  |   o |
|  |     |
|__|_____|
""",
    r"""
 ________
||       |
||       |
||       |
||       |
||_______|
""",
]


class Level6(Level):
    def __init__(self) -> None:
        super().__init__(
            number=6,
            title="Level 6",
            required_input=("\r", "\n"),
            art=DOOR_FRAMES,
            prompt="Do you want to enter? Press Enter.",
        )
