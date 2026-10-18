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
    ______________
   /  E N T E R   \
  /     <----'     \
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
    ______________
   /  E N T E R   \
  /     <----'     \
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
    ______________
   /  E N T E R   \
  /     <----'     \
 /__________________\
""",
]


def _door_rattle_frame(shift: int, handle: str) -> str:
    rows = DOOR_FRAMES[0].strip("\n").splitlines()
    width = max(map(len, rows))
    canvas = [list(row.ljust(width)) for row in rows]
    # Only the closed leaf moves; the frame and the Enter key stay still.
    for y in (3, 4, 5, 8, 9, 10):
        canvas[y][3:19] = " " * 16
        for x in range(3, 19):
            if rows[y][x] != " ":
                canvas[y][x + shift] = rows[y][x]
    canvas[7][15:19] = " " * 4
    canvas[7][16 + shift:18 + shift] = handle
    return "\n".join("".join(row) for row in canvas)


WRONG_FRAMES = [
    _door_rattle_frame(-1, " /"),
    _door_rattle_frame(1, "--"),
    _door_rattle_frame(-1, "\\ "),
    _door_rattle_frame(1, "()"),
    _door_rattle_frame(0, "--"),
    _door_rattle_frame(0, "()"),
]


def _door_idle() -> list[str]:
    """Run a pulse along the Enter key's arrow while the door stays shut."""
    neutral = DOOR_FRAMES[0].strip("\n")
    arrows = ("<----'", "<---='", "<--=-'", "<-=--'", "<=---'", "<----'", "<----'")
    return [neutral.replace("<----'", arrow) for arrow in arrows]


IDLE_FRAMES = _door_idle()


class Level2(Level):
    def __init__(self) -> None:
        super().__init__(
            number=2,
            title="Level 2",
            required_input=("\r", "\n"),
            art=DOOR_FRAMES,
            prompt="You are waiting behind a door",
            wrong_frames=WRONG_FRAMES,
        )
        self.layout = "level2"
        self.idle_frames = IDLE_FRAMES
        self.idle_frame_delay = 0.15
