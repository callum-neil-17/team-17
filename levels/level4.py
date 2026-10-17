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
            prompt="You take a drink... ahhh, how refreshing!",
        )
        self.recent_keys = ""

    def check_input(self, key: str) -> bool:
        # Keep only enough characters to hold the longest F5 sequence.
        self.recent_keys = (self.recent_keys + key)[-5:]
        return self.recent_keys.endswith(self.required_input)
