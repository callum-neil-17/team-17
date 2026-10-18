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

# A blinking cursor waits after the lowercase character on the ATM screen.
IDLE_FRAMES = [
    ATM_FRAMES[0],
    ATM_FRAMES[0].replace("         c          ", "         c_         "),
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
        self.idle_frames = IDLE_FRAMES
        self.idle_frame_delay = 0.5
        self.wrong_guesses = 0

    def react_to_wrong_input(self, key: str | None, now: float | None = None) -> bool:
        ignored = (None, "", "q", "\x03", "\x04", "\x1a", "\x1c", "\x13", "\x11", "\x1b")
        if self.wrong_guesses < 5 and key not in ignored and key not in self.required_input:
            self.wrong_guesses += 1
            if self.wrong_guesses == 5:
                self.prompt = self.prompt.rstrip() + "\nCapitol c could do the trick"
        # Each wrong guess counts even while the existing art reaction plays.
        return super().react_to_wrong_input(key, now=now)
