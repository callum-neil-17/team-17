"""Pure, bounded ASCII frames for the false exit and the wizard's final panic.

Only the viewer owns clocks, keyboard input and sockets. These functions never
execute shell text and quantize animation time to twelve frames per second.
"""

import getpass
import math
import os
import socket
from textwrap import dedent, wrap

from callback_art import BOOK_ART, MUG_ART, RECEIPT_ART
from ending_config import (MAX_PANIC_WINDOWS, PANIC_DURATION as TIMELINE_DURATION,
                           panic_close, panic_start)
from levels.level1 import WIZARD


CRASH_DURATION = 2.5
PANIC_DURATION = 6.5
FRAME_RATE = 12
CLUE = "You managed to escape my curse, but you will never put an end to me."
REOPEN_TAUNT = "Closing a window won't end me."
PANIC_MESSAGES = (
    "WAIT. THAT KEY WASN'T FOR YOU.",
    "WHY ARE MY REFERENCES DISAPPEARING?",
    "DO NOT COLLECT ME.",
    "WIZARD_PROCESS_NOT_FOUND",
)


def _safe(value: object, limit: int = 200) -> str:
    """Keep untrusted local names and parent context out of terminal controls."""
    return "".join(char for char in str(value) if 32 <= ord(char) <= 126)[:limit]


def _prompt_character(shell: str) -> str:
    return "%" if shell.lower() in {"zsh", "csh", "tcsh"} else "$"


def shell_context() -> dict[str, str]:
    """Return local-looking, printable shell details; never invoke a shell."""
    try:
        username = _safe(getpass.getuser(), 32) or "player"
    except (OSError, KeyError):
        username = "player"
    try:
        hostname = _safe(socket.gethostname(), 48) or "localhost"
    except OSError:
        hostname = "localhost"
    try:
        cwd = os.getcwd()
        home = os.path.expanduser("~")
        if home != "/" and (cwd == home or cwd.startswith(home + os.sep)):
            cwd = "~" + cwd[len(home):]
        cwd = _safe(cwd, 120) or "~"
    except OSError:
        cwd = "~"
    shell = _safe(os.path.basename(os.environ.get("SHELL", "/bin/bash")), 24) or "bash"
    return {"username": username, "hostname": hostname, "cwd": cwd,
            "shell": shell, "prompt": f"{username}@{hostname}:{cwd}{_prompt_character(shell)} "}


def _time(elapsed: float, maximum: float | None = None) -> float:
    try:
        value = float(elapsed)
    except (TypeError, ValueError, OverflowError):
        value = 0.0
    if not math.isfinite(value):
        value = maximum if value > 0 and maximum is not None else 0.0
    value = min(86400.0, max(0.0, value))
    if maximum is not None:
        if value >= maximum:
            return maximum
    return math.floor(value * FRAME_RATE + 1e-7) / FRAME_RATE


def _noise(row: int, column: int, seed: int = 0) -> int:
    value = ((row + 37) * 374761393 + (column + 101) * 668265263 + seed * 1274126177) & 0xFFFFFFFF
    value = ((value ^ (value >> 13)) * 1274126177) & 0xFFFFFFFF
    return value ^ (value >> 16)


class _Canvas:
    def __init__(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self.rows = [[" "] * width for _ in range(height)]
        self.styles = [""] * height

    def put(self, text: str, left: int, top: int, style: str = "") -> None:
        if 0 <= top < self.height:
            for offset, char in enumerate(_safe(text, self.width + max(0, -left))):
                if 0 <= left + offset < self.width:
                    self.rows[top][left + offset] = char
            if style:
                self.styles[top] = style

    def center(self, text: str, top: int, style: str = "") -> None:
        self.put(text, max(0, (self.width - len(text)) // 2), top, style)


def _canvas(size: tuple[int, int]) -> tuple[_Canvas, int, int]:
    columns, rows = max(1, int(size[0])), max(1, int(size[1]))
    width, height = max(1, min(239, columns - 1)), min(80, rows)
    return _Canvas(width, height), (max(1, columns - 1) - width) // 2 + 1, (rows - height) // 2 + 1


def _emit(canvas: _Canvas, left: int, top: int) -> str:
    color = os.environ.get("TERM") != "dumb" and "NO_COLOR" not in os.environ
    palette = {"dim": "\x1b[2m", "wizard": "\x1b[36m", "error": "\x1b[31m"}
    output = ["\x1b[?25l"]
    for index, row in enumerate(canvas.rows):
        output.append(f"\x1b[{top + index};{left}H")
        style = palette.get(canvas.styles[index], "") if color else ""
        output.append(style + "".join(row) + ("\x1b[0m" if style else ""))
    return "".join(output)


def _prompt(context: dict[str, str]) -> str:
    return _safe(context.get("prompt", "player@localhost:~$ "), 180)


def _shell_base(canvas: _Canvas, context: dict[str, str], typed: str = "",
                *, blinking: bool = True, elapsed: float = 0) -> int:
    prompt = _prompt(context)
    # A long real working directory must not push the apparent exit offscreen.
    short_prompt = _prompt_character(str(context.get("shell", "bash"))) + " "
    display_prompt = prompt if len(prompt) < canvas.width - 5 else short_prompt
    canvas.put(display_prompt + "python3 game.py", 0, 0)
    canvas.put("[Process exited with status 0]", 0, min(1, canvas.height - 1), "dim")
    row = min(3, canvas.height - 1)
    line = display_prompt + _safe(typed, 256)
    if not blinking or int(elapsed * 2) % 2 == 0:
        line += "_"
    canvas.put(line, 0, row)
    return row


def _shell_clue(canvas: _Canvas, row: int, text: str, *, reopened: int = 0) -> int:
    text_lines = wrap(text, canvas.width) or [""]
    text_top = max(0, min(row + (4 if reopened else 3), canvas.height - len(text_lines) - 1))
    canvas.put("[wizard]", 0, text_top, "wizard")
    for offset, line in enumerate(text_lines):
        canvas.put(line, 0, text_top + 1 + offset, "wizard")
    return text_top


def _interference(canvas: _Canvas, elapsed: float, intensity: float, seed: int,
                  *, top: int = 2, bottom: int | None = None) -> None:
    """Break a few local rows into binary fragments; never flash the whole frame."""
    bottom = min(canvas.height, canvas.height if bottom is None else bottom)
    top = max(0, top)
    if top >= bottom or intensity <= 0:
        return
    tick = int(elapsed * 4)
    fragments = ("01001011 //", "[0x????]", "//REF_LOST", "10110#001", "<NULL>_%")
    count = 1 + int(min(1.0, intensity) * 5)
    for index in range(count):
        row = top + _noise(index, seed, tick) % (bottom - top)
        column = int(_noise(index, seed + 7, tick) % (canvas.width + 9)) - 4
        fragment = fragments[_noise(index, seed + 13, tick) % len(fragments)]
        canvas.put(fragment, column, row, "dim")
        if intensity > 0.5 and index % 2 == 0:
            canvas.put("_", (column + len(fragment) + tick) % canvas.width,
                       top + (row - top + 2) % (bottom - top), "dim")


def _tear_rows(canvas: _Canvas, elapsed: float, intensity: float, index: int,
               *, top: int, bottom: int) -> None:
    """Misalign small horizontal bands and leave displaced, broken row echoes."""
    bottom = min(canvas.height, bottom)
    top = max(1, top)
    if bottom <= top or intensity <= 0:
        return
    tick = int(elapsed * 4)
    for band in range(1 + int(intensity * 2)):
        row = top + _noise(index, band, tick) % (bottom - top)
        source = "".join(canvas.rows[row])
        shift = (-1 if (tick + band) % 2 else 1) * (2 + index % 3)
        canvas.rows[row] = [" "] * canvas.width
        canvas.put(source, shift, row, "dim")
        # Copy only scattered pieces, so a recognizable figure remains behind
        # the horizontal tear rather than becoming a second solid silhouette.
        echo = "".join(char if column % 7 < 3 else " "
                       for column, char in enumerate(source))
        canvas.put(echo, -shift, min(bottom - 1, row + 1), "dim")


def render_fake_shell(size: tuple[int, int], elapsed: float, *,
                      context: dict[str, str], reopened: int = 0,
                      typed: str = "") -> str:
    """An apparent successful exit, then a quietly returning wizard's clue."""
    canvas, left, top = _canvas(size)
    elapsed = _time(elapsed)
    row = _shell_base(canvas, context, typed, elapsed=elapsed)
    if 0.85 <= elapsed < 1.25:
        canvas.put(".", min(canvas.width - 1, 11), min(row + 1, canvas.height - 1), "dim")
    if reopened:
        for offset, line in enumerate(wrap(REOPEN_TAUNT, canvas.width) or [""]):
            canvas.put(line, 0, min(row + 2, canvas.height - 1) + offset, "wizard")
    began = 1.8
    if elapsed >= began:
        text = CLUE[:max(0, int((elapsed - began) * 27))]
        _shell_clue(canvas, row, text, reopened=reopened)
    return _emit(canvas, left, top)


def render_fake_crash(size: tuple[int, int], elapsed: float, *,
                      context: dict[str, str]) -> str:
    """Freeze the wizard's completed clue, fragment it, then draw a fake trace."""
    canvas, left, top = _canvas(size)
    elapsed = _time(elapsed, CRASH_DURATION)
    row = _shell_base(canvas, context, blinking=False)
    clue_top = _shell_clue(canvas, row, CLUE)
    if elapsed >= 0.45:
        canvas.put("[shell session: reference lost]", 0, min(row + 2, canvas.height - 1), "dim")
        damage = min(95, 18 + int((elapsed - 0.45) * 90))
        for line_index, line in enumerate(wrap(CLUE, canvas.width)):
            damaged = list(line)
            for chunk_index, start in enumerate(range(0, len(line), 8)):
                if chunk_index != 3 and _noise(line_index, chunk_index, 29) % 100 >= damage:
                    continue
                fragment = line[start:start + 8]
                if chunk_index % 3 == 1:
                    replacement = "".join("#%?/"[_noise(line_index, start + i, 11) % 4]
                                          if char != " " else " "
                                          for i, char in enumerate(fragment))
                else:
                    replacement = " " * len(fragment)
                damaged[start:start + len(fragment)] = replacement
                if chunk_index % 3 == 2:
                    # Detached chunks slide away from the line they belonged to.
                    canvas.put(fragment, min(canvas.width - 1, start + 3),
                               clue_top + 2 + line_index + chunk_index % 2, "dim")
            canvas.put(" " * canvas.width, 0, clue_top + 1 + line_index)
            canvas.put("".join(damaged), 0, clue_top + 1 + line_index, "wizard")
    if elapsed >= 1.25:
        _interference(canvas, elapsed, min(1.0, elapsed - 1.1), 53,
                      top=max(0, canvas.height - 6))
        trace = (
            "Traceback (most recent curse last):",
            '  File "<wizard/curse>", line 0, in keep_alive',
            "    self.world = references[0]",
            "ReferenceError: spell owner no longer exists",
            "  while handling WIZARD_UNEXPECTED_END",
            "FATAL: wizard runtime lost its root reference",
            f"[recovery fork requested: {MAX_PANIC_WINDOWS} copies]",
        )
        visible = min(len(trace), 1 + int((elapsed - 1.25) * 5))
        trace_top = max(0, min(clue_top + 4, canvas.height - visible))
        for offset, line in enumerate(trace[:visible]):
            canvas.put(line, 0, trace_top + offset, "error")
    if elapsed >= 1.45:
        tick = int(elapsed * FRAME_RATE)
        for offset in range(min(canvas.width, 18)):
            x = _noise(offset, 7, tick // 3) % canvas.width
            canvas.put("#%?/"[_noise(offset, 1, 4) % 4], x,
                       min(row + 1, canvas.height - 1), "dim")
    return _emit(canvas, left, top)


def _sprite(width: int, height: int, index: int) -> list[str]:
    source = dedent(WIZARD[index % len(WIZARD)]).strip("\n").splitlines()
    source_width = max(map(len, source), default=1)
    if len(source) > height:
        source = [source[min(len(source) - 1, int(row * len(source) / height))]
                  for row in range(height)]
    if source_width > width:
        source = ["".join(line[min(source_width - 1, int(column * source_width / width))]
                          if int(column * source_width / width) < len(line) else " "
                          for column in range(width)) for line in source]
    return source


def _panic_message(progress: float) -> str:
    if progress < 0.34:
        return PANIC_MESSAGES[0]
    if progress < 0.61:
        return PANIC_MESSAGES[1]
    if progress < 0.88:
        return PANIC_MESSAGES[2]
    return PANIC_MESSAGES[3]


def _panic_memory(canvas: _Canvas, progress: float, index: int,
                  art_left: int, footer_top: int) -> None:
    """Recall an earlier scene's object, then lose its reference with the wizard."""
    if not 0.46 <= progress < 0.86:
        return
    source = (MUG_ART, RECEIPT_ART, BOOK_ART)[index % 3].splitlines()
    width = max(map(len, source), default=0)
    height = len(source)
    if width > canvas.width or height + 1 > footer_top:
        return
    # Keep the small memory beside the collapsing figure and above its plea.
    left = ((art_left - width) // 2 if art_left >= width + 2
            else max(0, canvas.width - width - 1))
    top = max(1, footer_top - height - 1)
    damage = max(0.0, (progress - 0.64) / 0.22)
    for row, original in enumerate(source):
        line = original
        if damage:
            line = "".join(
                (" " if _noise(row, column, index + 9) % 3 else "#%?"[column % 3])
                if char != " " and _noise(row, column, index + 43) % 100 < damage * 120
                else char for column, char in enumerate(original)
            )
        target_row = top + row + int(damage * 2)
        if target_row < footer_top:
            shift = int(damage * (2 if row % 2 else -2))
            canvas.put(line, left + shift, target_row, "dim")


def _panic_picture(canvas: _Canvas, elapsed: float, index: int, duration: float) -> None:
    progress = min(1.0, elapsed / max(0.1, duration))
    tick = int(elapsed * 6)
    canvas.put(f"wizard@local / reference {index + 1:02d}", 0, 0, "dim")
    message = _panic_message(progress)
    message_lines = wrap(message, canvas.width) or [""]
    art_height = max(1, canvas.height - len(message_lines) - 3)
    sprite = _sprite(max(1, canvas.width - 4), art_height, index)
    sprite_width = max(map(len, sprite), default=1)
    art_left = max(0, (canvas.width - sprite_width) // 2)
    art_top = max(1, (canvas.height - len(message_lines) - len(sprite)) // 2)
    footer_top = canvas.height - len(message_lines) - 1
    if progress >= 0.2:
        _interference(canvas, elapsed, (progress - 0.2) / 0.8, index + 17,
                      top=2, bottom=footer_top)
    if 0.23 <= progress < 0.7:
        # A displaced outline slips out of sync with its original. Sparse
        # samples keep it readable and avoid filling the screen with a flash.
        direction = 1 if (tick + index) % 2 else -1
        for row, line in enumerate(sprite):
            if row % 3 != tick % 3:
                continue
            ghost = "".join(char if column % 4 < 2 else " "
                            for column, char in enumerate(line))
            canvas.put(ghost, art_left + direction * (3 + index % 3),
                       art_top + row + (index % 2), "dim")
    collapse = max(0.0, min(1.0, (progress - 0.64) / 0.3))
    for row, line in enumerate(sprite):
        if progress >= 0.35 and _noise(row, index, 31) % 100 < (progress - 0.35) * 95:
            continue
        shift = 0 if progress < 0.17 else int(_noise(row // 3, index, tick) % 5) - 2
        if progress >= 0.38:
            line = "".join("#%?x/=+"[_noise(row, col, tick + index) % 7]
                           if char != " " and _noise(row, col, tick // 2 + index) % 100
                           < (progress - 0.38) * 95 else char
                           for col, char in enumerate(line))
        if collapse:
            # Rows squeeze into each other; sparse fragments survive the fall.
            target_row = art_top + int(row * (1 - collapse)) + int(collapse * len(sprite) * 0.62)
            line = line[::max(1, 1 + int(collapse * 3))]
            target_left = art_left + int(sprite_width * collapse * 0.35) + shift
        else:
            target_row, target_left = art_top + row, art_left + shift
        if progress < 0.96:
            canvas.put(line, target_left, target_row, "wizard" if progress < 0.38 else "dim")
    if progress >= 0.27:
        _tear_rows(canvas, elapsed, min(1.0, (progress - 0.27) / 0.5), index,
                   top=art_top, bottom=footer_top)
    _panic_memory(canvas, progress, index, art_left,
                  footer_top)
    if progress >= 0.88:
        canvas.center("[ no live references ]", max(1, canvas.height // 2), "dim")
    for offset, line in enumerate(message_lines):
        canvas.center(line, canvas.height - len(message_lines) - 1 + offset, "error")


def render_panic(size: tuple[int, int], elapsed: float, *, index: int = 0,
                 duration: float = PANIC_DURATION) -> str:
    """One recognizable wizard copy shakes, loses rows, and folds away."""
    canvas, left, top = _canvas(size)
    duration = min(8.0, max(0.1, float(duration)))
    _panic_picture(canvas, _time(elapsed, duration), int(index) % MAX_PANIC_WINDOWS, duration)
    return _emit(canvas, left, top)


def render_fallback_panic(size: tuple[int, int], elapsed: float,
                          duration: float = TIMELINE_DURATION) -> str:
    """Mirror staggered window births and retirements with overlapping panels."""
    canvas, left, top = _canvas(size)
    duration = min(8.0, max(0.1, float(duration)))
    elapsed = _time(elapsed, duration)
    # The default eight-second timeline matches the desktop controller. Scale
    # the whole schedule together if a caller supplies another total duration.
    timeline = elapsed * TIMELINE_DURATION / duration
    panel_width = min(canvas.width, max(18, min(62, canvas.width * 3 // 4)))
    panel_height = min(canvas.height, max(10, min(32, canvas.height * 4 // 5)))
    for index in range(MAX_PANIC_WINDOWS):
        started = panic_start(index)
        closes = panic_close(index)
        if timeline < started or timeline >= closes:
            continue
        panel_left = (canvas.width - panel_width) * index // (MAX_PANIC_WINDOWS - 1)
        panel_top = (canvas.height - panel_height) * index // (MAX_PANIC_WINDOWS - 1)
        inner = _Canvas(max(1, panel_width - 2), max(1, panel_height - 2))
        _panic_picture(inner, timeline - started, index, closes - started)
        canvas.put("+" + "-" * max(0, panel_width - 2) + "+", panel_left, panel_top, "dim")
        for row in range(1, panel_height - 1):
            canvas.put("|" + "".join(inner.rows[row - 1]) + "|", panel_left,
                       panel_top + row, inner.styles[row - 1])
        canvas.put("+" + "-" * max(0, panel_width - 2) + "+", panel_left,
                   panel_top + panel_height - 1, "dim")
    # Keep the final plea legible even when the panels cover one another.
    message = _panic_message(elapsed / duration)
    footer = (wrap(message, canvas.width) or [""])[-canvas.height:]
    for offset, line in enumerate(footer):
        row = canvas.height - len(footer) + offset
        canvas.put(" " * canvas.width, 0, row)
        canvas.center(line, row, "error")
    return _emit(canvas, left, top)


def render_true_end(size: tuple[int, int], elapsed: float) -> str:
    """Hold a quiet blank beat before the final, centered title."""
    canvas, left, top = _canvas(size)
    if _time(elapsed) >= 0.75:
        canvas.center("THE END", canvas.height // 2)
    return _emit(canvas, left, top)
