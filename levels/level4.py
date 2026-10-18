from textwrap import fill

from .level import Level

# Pint glass draining, one frame per string. Raw strings keep the backslashes intact.
DRINK_FRAMES = [
    r"""
 _________
|~~~~~~~~~|__
|#########|  \
|#########|   |
|#########|   |
|#########|__/
|#########|
'---------'
""",
    r"""
 _________
|         |__
|         |  \
|#########|   |
|#########|   |
|#########|__/
|#########|
'---------'
""",
    r"""
 _________
|         |__
|         |  \
|         |   |
|         |   |
|#########|__/
|#########|
'---------'
""",
    r"""
 _________
|         |__
|         |  \
|         |   |
|         |   |
|         |__/
|         |
'---------'
""",
]


def _drink_reaction_frame(bubble_y: int | None, bubble_x: int = 4) -> str:
    rows = DRINK_FRAMES[0].strip("\n").splitlines()
    width = max(map(len, rows))
    canvas = [list(row.ljust(width)) for row in rows]
    if bubble_y is not None:
        canvas[bubble_y][bubble_x] = "o" if bubble_y % 2 else "O"
        canvas[1][1:10] = ("~~^~~~~~~" if bubble_y % 2 else "~~~~~~^~~")
    return "\n".join("".join(row) for row in canvas)


WRONG_FRAMES = [
    _drink_reaction_frame(6, 3),
    _drink_reaction_frame(5, 4),
    _drink_reaction_frame(4, 5),
    _drink_reaction_frame(3, 4),
    _drink_reaction_frame(2, 5),
    _drink_reaction_frame(None),
]


def _drink_idle() -> list[str]:
    """Send small bubbles up through the full pint."""
    rows = DRINK_FRAMES[0].strip("\n").splitlines()
    width = max(map(len, rows))
    frames = []
    for step in range(5):
        canvas = [list(row.ljust(width)) for row in rows]
        # Two staggered bubbles climb from the bottom row to the top of the drink.
        canvas[6 - step][3] = "."
        canvas[6 - (step + 2) % 5][7] = "o"
        frames.append("\n".join("".join(row) for row in canvas))
    return frames


IDLE_FRAMES = _drink_idle()

# F5 arrives as an escape sequence, one character at a time. Most terminals
# send the first form; the Linux console sends the second.
F5_SEQUENCES = ("\x1b[15~", "\x1b[[E")
# Ctrl+R also means refresh, and works on macOS where F5 is often unavailable.
CTRL_R = "\x12"


class Level4(Level):
    def __init__(self) -> None:
        super().__init__(
            number=4,
            title="Level 4",
            required_input=(*F5_SEQUENCES, CTRL_R),
            art=DRINK_FRAMES,
            description=fill(
                "The bartender hands you a drink.",
                width=70,
            ),
            prompt="You take a drink... ahhh, how refreshing!",
            wrong_frames=WRONG_FRAMES,
        )
        self.recent_keys = ""
        self.idle_frames = IDLE_FRAMES
        self.idle_frame_delay = 0.3

    def check_input(self, key: str) -> bool:
        # Keep only enough characters to hold the longest F5 sequence.
        self.recent_keys = (self.recent_keys + key)[-5:]
        return self.recent_keys.endswith(self.required_input)
