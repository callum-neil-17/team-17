from textwrap import fill

from .level import Level
from .level3 import BAR_FRAMES, _bartender_reaction_frame


PLAYER_AT_BAR = r"""
    .---.
    |o o|
    | - |
 .--'---'--.
 / /|YOU|\ \
(o) |___| (o)
    /| |\
   [_] [_]
""".strip("\n")

CASH = r"""
+--------+
| 100 CR |
+--------+
""".strip("\n")


def _payment_frame(cash_x: int | None, *, handed_over: bool = False,
                   paid: bool = False, closed: bool = False) -> str:
    """Draw payment in front of the same bar used in Level 3."""
    canvas = [list(line.ljust(68)) for line in BAR_FRAMES[0].strip("\n").splitlines()]

    def put(sprite: str, left: int, top: int, *, foreground: bool = False) -> None:
        for offset, line in enumerate(sprite.splitlines()):
            margin = len(line) - len(line.lstrip(" ")) if foreground else 0
            text = line.strip(" ") if foreground else line
            start = left + margin
            if foreground:
                # A one-cell gap separates the character from shelf/counter lines.
                first, last = max(0, start - 1), min(68, start + len(text) + 1)
                canvas[top + offset][first:last] = " " * (last - first)
            canvas[top + offset][start:start + len(text)] = text

    balance = "BALANCE: 0 CR" if paid else "TAB: 100 CR"
    status = "TAB CLOSED [v]" if closed else "PAID [v]" if paid else "OPEN [ ]"
    ledger = "\n".join((
        "+-------------------+",
        "|" + balance.center(19) + "|",
        "|" + status.center(19) + "|",
        "+-------------------+",
    ))
    put(ledger, 45, 8)

    player = PLAYER_AT_BAR
    if cash_x is not None and not handed_over:
        # The player's raised arm follows the note across the counter.
        reach = cash_x - 10
        player = "\n".join((
            "    .---.",
            "    |o o|",
            "    | - |" + " " * reach + "(o)",
            " .--'---'" + "_" * reach + "/ /",
            " / /|YOU|" + "_" * reach + "/",
            "(o) |___|",
            "    /| |\\",
            "   [_] [_]",
        ))
    if paid:
        player = player.replace("| - |", r"|\_/|")
        put(r"| \_/|", 29, 8)
    # The player stands in front of the left stool; the other stools stay visible.
    for row in range(15, 18):
        canvas[row][6:18] = " " * 12
    put(player, 3, 10, foreground=True)

    if cash_x is not None:
        put(CASH, cash_x, 9)
        if handed_over:
            # The bartender grips the note while the player lowers his hand.
            put("(o)", cash_x + 8, 11)

    return "\n".join("".join(row).rstrip() for row in canvas)


PAYMENT_FRAMES = [
    _payment_frame(18),  # Return to the bar with cash and an open tab.
    _payment_frame(22),
    _payment_frame(26),
    _payment_frame(30),
    _payment_frame(30, handed_over=True),
    _payment_frame(None, paid=True),
    _payment_frame(None, paid=True, closed=True),
]


WRONG_FRAMES = [
    _bartender_reaction_frame(PAYMENT_FRAMES[0], shift, wave)
    for shift, wave in ((-1, -1), (1, 1), (-1, -1), (1, 1), (0, 0))
] + ["\n".join(row.ljust(68) for row in PAYMENT_FRAMES[0].splitlines())]


def _payment_idle() -> list[str]:
    """Blink the open tab's checkbox while both characters wait."""
    neutral = "\n".join(row.ljust(68) for row in PAYMENT_FRAMES[0].splitlines())
    frames = []
    for step in range(12):
        frame = neutral.replace("OPEN [ ]", "OPEN [_]") if step % 2 else neutral
        if step == 4:
            frame = frame.replace("|o  o|", "|-  -|")
        elif step == 9:
            frame = frame.replace("|o o|", "|- -|")
        frames.append(frame)
    return frames


IDLE_FRAMES = _payment_idle()


class Level6(Level):
    def __init__(self) -> None:
        super().__init__(
            number=6,
            title="Level 6",
            required_input=("\x17",),  # Ctrl+W is a raw input byte.
            art=PAYMENT_FRAMES,
            description=fill(
                "You return to the bar with 100 credits to settle the tab.",
                width=70,
            ),
            prompt="you can close your tab now",
            wrong_frames=WRONG_FRAMES,
        )
        self.frame_delay = 0.25
        self.frame_delays[len(self.frames) - 1] = 1.2
        self.idle_frames = IDLE_FRAMES
        self.idle_frame_delay = 0.3
