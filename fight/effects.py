"""Local, time-based ASCII effects for the final two-terminal fight.

No frame sleeps or socket work belong here. The fight loop supplies elapsed
time, so keyboard handling and peer heartbeats continue during the cinematic.
"""

import math
from textwrap import dedent, wrap

from levels.level1 import WIZARD


PLAYER_POSES = {
    "ready": r"""
        .----.
        |____|
        | o o|>
        |  - /
     .--`---'--.
    / /|=====|\ \
   (o/ |  :  | \o)
       |_____|
       /  |  \
      /___|___\
     /___/ \___\
    [____] [____]
""".strip("\n"),
    "recoil": r"""
    .----.
    |____|
    | o o|>
    |  o /
 .--`---'--.
 \ \|=====|\\_
 (o)|  :  | \o)
    |_____|
     / |  \___
    /__|__    \
   [___] \____/
          [____]
""".strip("\n"),
    "victory": r"""
    (o)       (o)
     \ \     / /
      \ .---. /
       \|___|/
        |^ ^|>
        | v /
        `---'
       |=====|
       |  :  |
       |_____|
      /___|___\
     [____] [____]
""".strip("\n"),
}
PLAYER_HAND_ROW = 6
PLAYER_WIDTH = max(len(line) for pose in PLAYER_POSES.values() for line in pose.splitlines())

DEATH_DURATION = 8.0
ERRORS = (
    "ERR_SPELL_ROLLBACK",
    "ROOT_ACCESS_REVOKED",
    "NULL_WAND_REFERENCE: 0x00000000",
    "STACK_OVERFLOW in wizard.cast()",
    "SEGMENTATION_FAULT at 0xDEAD",
    "ROLLBACK FAILED: spell ownership lost",
    "ERROR: corrupted wizard memory",
    "KERNEL: wizard process cannot recover",
)
FATAL_ERROR = "FATAL: wizard.exe has stopped responding"

_RESET = "\x1b[0m"
_PALETTE = {"normal": "", "impact": "\x1b[1;33m", "magic": "\x1b[36m",
            "error": "\x1b[31m", "dim": "\x1b[2;31m", "fatal": "\x1b[1;31m"}


def _noise(row: int, column: int, seed: int = 0) -> int:
    """Stable integer noise: no random state or differences between processes."""
    value = ((row + 37) * 374761393 + (column + 101) * 668265263 + seed * 1274126177) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    return value ^ (value >> 16)


def _sprite(width: int, height: int) -> list[str]:
    """Fit the established wizard, preserving the whole silhouette when small."""
    source = dedent(WIZARD[0]).strip("\n").splitlines()
    if len(source) > height:
        source = [source[min(len(source) - 1, int(index * len(source) / height))]
                  for index in range(height)]
    source_width = max(map(len, source), default=1)
    if source_width > width:
        source = ["".join(line[min(source_width - 1, int(index * source_width / width))]
                          if int(index * source_width / width) < len(line) else " "
                          for index in range(width)) for line in source]
    return source


def render_death(size: tuple[int, int], elapsed: float, *, color: bool = True,
                 row: int | None = None) -> str:
    """Render one bounded frame of the wizard's eight-second malfunction.

    Stages: impact 0-.55s; recoil .55-1.65s; corruption 1.65-3.6s;
    collapse 3.6-5.1s; system failure 5.1-8s. At/after eight seconds the
    fatal frame is held, allowing the caller to flush it before window closure.
    One terminal column is reserved to avoid autowrap in raw mode. Extremely
    large terminals are capped at 240 by 80 characters to bound frame output.
    Pass the shared spell row to retain the live fight's wizard position.
    """
    width, height = max(1, min(239, size[0] - 1)), max(1, min(80, size[1]))
    elapsed = max(0.0, min(DEATH_DURATION, elapsed))
    canvas = [[(" ", "normal")] * width for _ in range(height)]

    def put(text: str, left: int, top: int, style: str = "normal") -> None:
        if 0 <= top < height:
            for offset, character in enumerate(text):
                if 0 <= left + offset < width:
                    canvas[top][left + offset] = (character, style)

    def centre(text: str, top: int, style: str = "normal") -> None:
        put(text, max(0, (width - len(text)) // 2), top, style)

    put("Level 11 - Wizard", 0, 0)
    art_height = max(1, height - 4)
    sprite = _sprite(max(1, width - 4), art_height)
    sprite_width = max(map(len, sprite), default=1)
    if row is None:
        left, top = max(0, (width - sprite_width) // 2), min(2, height - 1)
    else:
        full_width = max(len(line) for frame in WIZARD
                         for line in dedent(frame).strip("\n").splitlines())
        left = max(1, min(size[0], width + 1) - 3 - full_width)
        # Level 11 has one description row and a short status footer. This is
        # the same spell-lane anchoring used by the live draw_scene renderer.
        art_top = min(4, height - 1)
        top = max(art_top, min(row - 4, height - 2 - len(sprite)))
    centre_x, centre_y = left + sprite_width // 2, top + max(0, len(sprite) // 3)
    tick = int(elapsed * 12)

    if elapsed < 0.55:
        # One short amber flash, followed by an expanding ASCII particle ring.
        flash = "impact" if elapsed < 0.12 else "normal"
        for index, line in enumerate(sprite):
            put(line, left, top + index, flash)
        for index in range(32):
            angle = index * math.tau / 32
            distance = 1 + elapsed * (9 + index % 7)
            px = centre_x + round(math.cos(angle) * distance * 1.5)
            py = centre_y + round(math.sin(angle) * distance * 0.7)
            put("*+.'"[index % 4], px, py, "impact" if index % 2 else "magic")
        centre("SPELL REBOUND", height - 1, "magic")
    elif elapsed < 1.65:
        progress = (elapsed - 0.55) / 1.1
        shake = round(math.sin((elapsed - 0.55) * 31) * (2.5 - progress))
        for index, line in enumerate(sprite):
            # The upper body recoils farther than the boots; the staff wavers.
            stagger = round(progress * 3 * (1 - index / max(1, len(sprite))))
            put(line, left + shake + stagger, top + index + int(progress > 0.6))
        centre("WAND CONTROL LOST", height - 1, "error")
    elif elapsed < 3.6:
        progress = (elapsed - 1.65) / 1.95
        symbols = "#%?01"
        for row, line in enumerate(sprite):
            # Whole horizontal slices jump before individual cells corrupt.
            offset = (_noise(row // 3, 0, tick) % 7 - 3) if row % 4 else 0
            offset = round(offset * min(1.0, progress * 2))
            for column, char in enumerate(line):
                if char == " ":
                    continue
                noise = _noise(row, column, tick)
                if noise % 100 < progress * 23:
                    continue
                corrupt = noise % 100 < progress * 92
                put(symbols[noise % len(symbols)] if corrupt else char,
                    left + column + offset, top + row, "magic" if corrupt else "normal")
        centre("ERR_SPELL_ROLLBACK", height - 1, "error")
    elif elapsed < 5.1:
        progress = elapsed - 3.6
        for row, line in enumerate(sprite):
            for column, char in enumerate(line):
                if char == " ":
                    continue
                noise = _noise(row, column)
                age = max(0, progress - (noise % 450) / 1000)
                fall = round(age * age * (8 + noise % 10))
                drift = round(age * ((noise >> 8) % 5 - 2))
                # Pieces settle into a ragged heap rather than leaving at once.
                floor = max(0, height - 3 - (noise % 2))
                py = min(floor, top + row + fall)
                px = left + column + drift
                put(char if age < 0.5 else "#%?01"[noise % 5], px, py,
                    "normal" if age < 0.6 else "dim")
        centre("ROOT_ACCESS_REVOKED", height - 1, "error")
    else:
        progress = min(1.0, (elapsed - 5.1) / (DEATH_DURATION - 5.1))
        available = max(0, height - 2)
        count = min(available, 1 + int(progress * available * 1.7))
        for index in range(count):
            error = ERRORS[(index + int(progress * 7)) % len(ERRORS)]
            # Short repeated fragments fill holes as the error storm builds.
            text = error
            if progress > 0.4:
                text += " | " + ERRORS[(index + 3) % len(ERRORS)]
            put(text, 0, index + 1, "error" if index % 4 == 0 else "dim")
        if elapsed >= 7.05:
            fatal = wrap(FATAL_ERROR, width) or [FATAL_ERROR[:width]]
            fatal_top = max(1 if height > 1 else 0, (height - len(fatal)) // 2)
            for index in range(max(0, fatal_top - 1), min(height, fatal_top + len(fatal) + 1)):
                put(" " * width, 0, index)
            for index, line in enumerate(fatal):
                centre(line, fatal_top + index, "fatal")
            centre("CACHE FLUSH COMPLETE", height - 2, "magic")
            centre("PROCESS TERMINATED", height - 1, "error")
        else:
            centre("SYSTEM FAILURE", height - 1, "error")

    output = ["\x1b[?25l"]
    if color:
        output.append(_RESET)
    for row, cells in enumerate(canvas):
        output.append(f"\x1b[{row + 1};1H\x1b[2K")
        while cells and cells[-1][0] == " ":
            cells.pop()
        active = "normal"
        for character, style in cells:
            if color and style != active:
                output.append(_RESET + _PALETTE[style])
                active = style
            output.append(character)
        if color and active != "normal":
            output.append(_RESET)
    return "".join(output)


def render_terminal_collapse(size: tuple[int, int], elapsed: float, *,
                             color: bool = True, clear: bool = True) -> str:
    """Crumble the final screen around its protected exit clue at 12 FPS.

    Time is supplied by the game loop; no sleeps, terminal modes or real errors
    are involved. A bounded canvas remains centred even on very large screens.
    """
    columns, rows = max(1, size[0]), max(1, size[1])
    width, height = max(1, min(239, columns - 1)), min(80, rows)
    left, top = max(0, (columns - 1 - width) // 2), (rows - height) // 2
    tick = int(max(0.0, elapsed) * 12)
    elapsed = tick / 12
    progress = min(1.0, elapsed / 5)
    canvas = [[" "] * width for _ in range(height)]

    def put(text: str, x: int, y: int) -> None:
        if 0 <= y < height:
            for offset, char in enumerate(text):
                if 0 <= x + offset < width:
                    canvas[y][x + offset] = char

    def fragment(char: str, x: int, y: int, group: int) -> None:
        delay = 0.8 + (_noise(group, y // 3) % 4500) / 1000
        age = max(0.0, elapsed - delay)
        if age < 2.0:
            drift = round(age * (_noise(group, 1) % 3 - 1))
            fall = int(age * age * max(4, height / 3))
            put(char, x + drift, y + fall)

    # A terminal-shaped frame loses short sections rather than vanishing at once.
    if width >= 14 and height >= 8:
        for x in range(1, width - 1):
            char = "+" if x in (1, width - 2) else "-"
            fragment(char, x, 1, x // 5)
            fragment(char, x, height - 2, 100 + x // 5)
        for y in range(2, height - 2):
            fragment("|", 1, y, 200 + y // 3)
            fragment("|", width - 2, y, 300 + y // 3)

    # Cracks spread inward, then slip down and out of the screen.
    crack_length = int(min(height // 2, width // 4) * progress)
    crack_fall = int(max(0.0, elapsed - 4) ** 2 * 2)
    for side in (0, 1):
        for step in range(crack_length):
            x = 3 + step * 2
            x = x if side == 0 else width - 1 - x
            y = 2 + step + crack_fall
            put("/" if (step + side) % 3 else "\\", x, y)
            if step % 3 == 0:
                put("--", x - 1, y + 1)

    # Small, staggered streams continue falling until the player escapes.
    scraps = ("01", "1010", "{}", "[]", "//", "_", "#%", "\\|/", "==", "+")
    for index in range(min(72, max(8, width // 2))):
        delay = 0.5 + (_noise(index, 4) % 3000) / 1000
        if elapsed < delay:
            continue
        age = (elapsed - delay) % 4.5
        cycle = int((elapsed - delay) / 4.5)
        seed = _noise(index, cycle, 19)
        x = seed % width + round(age * (seed % 3 - 1))
        y = int((seed % max(1, height // 4)) + age * (2 + seed % 4) + age * age * 2)
        put(scraps[seed % len(scraps)], x, y)

    # A sparse heap remains at the bottom after the frame breaks apart.
    for x in range(width):
        seed = _noise(x, 7)
        if seed % 100 < progress * 45:
            y = height - 1 - seed % min(2, height)
            put("_./\\#01"[(seed + tick // 12) % 7], x, y)

    message = "There's only one way to leave the terminal."
    lines = wrap(message, max(1, width - 6))[:height]
    if len(lines) < height:
        lines.append("_" if int(elapsed / 0.65) % 2 == 0 else " ")
    message_top = max(0, (height - len(lines)) // 2)
    message_width = max(map(len, lines), default=1)
    # Clear a quiet area so falling debris never obscures the clue or cursor.
    quiet_left = max(0, (width - message_width) // 2 - 3)
    quiet_right = min(width, (width + message_width) // 2 + 4)
    for y in range(max(0, message_top - 1), min(height, message_top + len(lines) + 1)):
        canvas[y][quiet_left:quiet_right] = " " * (quiet_right - quiet_left)
    bright = {}
    for offset, line in enumerate(lines):
        x, y = max(0, (width - len(line)) // 2), message_top + offset
        put(line, x, y)
        bright[y] = (x, x + len(line))

    dim = "\x1b[2;36m"
    output = ["\x1b[?25l"]
    if clear:
        output.append("\x1b[2J\x1b[H")
    if color:
        output.append(_RESET + dim)
    for y, cells in enumerate(canvas):
        line = "".join(cells).rstrip()
        if color and y in bright:
            start, end = bright[y]
            line = line[:start] + "\x1b[0;37m" + line[start:end] + dim + line[end:]
        output.append(f"\x1b[{top + y + 1};{left + 1}H\x1b[2K{line}")
    if color:
        output.append(_RESET)
    return "".join(output)
