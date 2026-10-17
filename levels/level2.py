from .level import Level

# Door opening, one frame per string. Raw strings keep the backslashes intact.
DOOR_FRAMES = [
    r"""
 ____________________
|  ________________  |
| |                | |
| |  ____________  | |
| | |            | | |
| | |____________| | |
| |                | |
| |             () | |
| |  ____________  | |
| | |            | | |
| | |____________| | |
| |________________| |
|____________________|
   /  PLEASE 'ENTER'  \ 
  /__________________\
""",
    r"""
 ____________________
|\                   |
| \                  |
|  \                 |
|   \                |
|    |               |
|    |               |
|  ()|               |
|    |               |
|    |               |
|    |               |
|____|_______________|
|____________________|
   /  PLEASE 'ENTER'  \ 
  /__________________\
""",
    r"""
 ____________________
||                   |
||                   |
||                   |
||                   |
||                   |
||                   |
||                   |
||                   |
||                   |
||                   |
||___________________|
|____________________|
   /  PLEASE 'ENTER'  \ 
  /__________________\
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
