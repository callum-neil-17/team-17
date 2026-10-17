from .level import Level

# Door opening, one frame per string. Raw strings keep the backslashes intact.
DOOR_FRAMES = [
    r"""
 ______________
|              |
|              |
|              |
|              |
|           o  |
|              |
|              |
|              |
|______________|
""",
    r"""
 ______________
|\             |
| \            |
|  \           |
|   |          |
|   |       o  |
|   |          |
|   |          |
|   |          |
|___|__________|
""",
    r"""
 ______________
||             |
||             |
||             |
||             |
||             |
||             |
||             |
||             |
||_____________|
""",
]


class Level2(Level):
    def __init__(self) -> None:
        super().__init__(
            number=2,
            title="Level 2",
            required_input=("\r", "\n"),
            art=DOOR_FRAMES,
            prompt="You are waiting behind a door",
        )
        self.layout = "level2"
