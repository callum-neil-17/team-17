from textwrap import fill

from .level import Level


ATM_FRAMES = [
    r"""
+------------------------------+
|        BANK OF CACHE         |
|------------------------------|
|    +--------------------+    |
|    |                    |    |
|    |         c          |    |
|    |                    |    |
|    +--------------------+    |
|                              |
|    1 2 3         [CARD]      |
|    4 5 6                     |
|    7 8 9                     |
|      0     [____________]    |
|                              |
+------------------------------+
""",
    r"""
+------------------------------+
|        BANK OF CACHE         |
|------------------------------|
|    +--------------------+    |
|    |                    |    |
|    |         C          |    |
|    |                    |    |
|    +--------------------+    |
|                              |
|    1 2 3         [CARD]      |
|    4 5 6                     |
|    7 8 9                     |
|      0     [____________]    |
|                              |
+------------------------------+
""",
    r"""
+------------------------------+
|        BANK OF CACHE         |
|------------------------------|
|    +--------------------+    |
|    |   TRANSACTION      |    |
|    |    APPROVED        |    |
|    |                    |    |
|    +--------------------+    |
|                              |
|    1 2 3         [CARD]      |
|    4 5 6                     |
|    7 8 9                     |
|      0     [____====____]    |
|               | $$$$ |       |
+------------------------------+
""",
    r"""
+------------------------------+
|        BANK OF CACHE         |
|------------------------------|
|    +--------------------+    |
|    |   PLEASE TAKE      |    |
|    |    YOUR CASH       |    |
|    |                    |    |
|    +--------------------+    |
|                              |
|    1 2 3         [CARD]      |
|    4 5 6                     |
|    7 8 9                     |
|      0     [____________]    |
|             | $$$$$$$$ |     |
+-------------|__________|-----+
"""
]


def _atm_reaction_frame(flash: bool, key: tuple[int, int] | None = None) -> str:
    rows = ATM_FRAMES[0].strip("\n").splitlines()
    width = max(map(len, rows))
    canvas = [list(row.ljust(width)) for row in rows]
    if flash:
        # A rejection flicker surrounds the unchanged lowercase character.
        canvas[4][13], canvas[4][17] = "\\", "/"
        canvas[5][14], canvas[5][16] = "[", "]"
        canvas[6][13], canvas[6][17] = "/", "\\"
    if key is not None:
        y, x = key
        canvas[y][x] = "*"
    return "\n".join("".join(row) for row in canvas)


WRONG_FRAMES = [
    _atm_reaction_frame(True, (9, 5)),
    _atm_reaction_frame(False, (10, 7)),
    _atm_reaction_frame(True, (11, 9)),
    _atm_reaction_frame(False, (10, 7)),
    _atm_reaction_frame(True),
    _atm_reaction_frame(False),
]


class Level5(Level):
    def __init__(self) -> None:
        super().__init__(
            number=5,
            title="Level 5",
            required_input=("C",),  # Shift+C types an uppercase C.
            art=ATM_FRAMES,
            description=fill(
                "With an unpaid tab, you head to the Bank of Cache.",
                width=70,
            ),
            prompt="Broke? Raise some capital.",
            wrong_frames=WRONG_FRAMES,
        )
        self.frame_delay = 1
