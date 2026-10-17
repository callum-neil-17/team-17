import os
import select
import shutil
import sys
import termios
import time
import tty

from levels import Level, Level1, Level2, Level3, Level4, Level5, Level6


def _centered_lines(section: str, columns: int) -> list[str]:
    section_lines = section.split("\n")
    width = max((len(line) for line in section_lines), default=0)
    padding = " " * max(0, (columns - width) // 2)
    return [padding + line if line else "" for line in section_lines]


def render_screen(content: str, layout: str = "center") -> None:
    columns, rows = shutil.get_terminal_size(fallback=(80, 24))
    normalized = "\n".join(content.expandtabs().splitlines())

    if layout == "level2":
        sections = normalized.split("\n\n")
        title = _centered_lines(sections[0], columns)
        art = _centered_lines(sections[1], columns)
        prompt = _centered_lines(sections[2], columns)
        # Keep the title near the top, the door centered, and the prompt low.
        art_row = max(len(title) + 2, (rows - len(art)) // 2 + 1)
        prompt_row = max(art_row + len(art) + 2, rows - len(prompt) - 1)
        positions = [(2, title), (art_row, art), (prompt_row, prompt)]
        output = "".join(
            f"\x1b[{row + offset};1H{line}"
            for row, section_lines in positions
            for offset, line in enumerate(section_lines)
        )
        sys.stdout.write("\x1b[2J\x1b[H" + output)
        sys.stdout.flush()
        return

    # Blank lines separate titles, art and prompts. Center each section as a
    # block so ASCII art keeps its original indentation and proportions.
    sections = normalized.split("\n\n")
    lines = []
    for section in sections:
        if lines:
            lines.append("")
        lines.extend(_centered_lines(section, columns))

    top = max(0, (rows - len(lines)) // 2)
    # Explicit cursor positioning avoids scrolling when content fills the screen.
    output = "".join(
        f"\x1b[{top + index + 1};1H{line}"
        for index, line in enumerate(lines)
    )
    # Clear the previous screen and return the cursor to the top left.
    sys.stdout.write("\x1b[2J\x1b[H" + output)
    sys.stdout.flush()


def read_key(fd: int, timeout: float | None = None) -> str | None:
    if not select.select([fd], [], [], timeout)[0]:
        return None
    # Read one byte directly so buffered input cannot hide a quit key from select.
    return os.read(fd, 1).decode("latin-1")


def play_frames(level: Level, fd: int, frame_delay: float = 0.35) -> bool:
    """Play the remaining frames once; return False if the player quits."""
    for frame in range(level.frame + 1, len(level.frames)):
        level.frame = frame
        render_screen(level.render(), level.layout)
        deadline = time.monotonic() + frame_delay

        while (remaining := deadline - time.monotonic()) > 0:
            if read_key(fd, timeout=remaining) in ("q", "\x03", ""):
                return False

    return True


def main() -> None:
    levels = [Level1(), Level2(), Level3(), Level4(), Level5(),Level6()]
    level_index = 0
    fd = sys.stdin.fileno()
    original_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        render_screen(levels[level_index].render(), levels[level_index].layout)

        while True:
            key = read_key(fd)

            # Raw mode delivers Ctrl+C as a character rather than a signal.
            if key in ("q", "\x03", ""):
                break

            if level_index < len(levels) and levels[level_index].check_input(key):
                if not play_frames(levels[level_index], fd):
                    break
                level_index += 1
                if level_index < len(levels):
                    render_screen(levels[level_index].render(), levels[level_index].layout)
                else:
                    render_screen("Game complete! Press q to quit.\r\n")

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original_settings)


if __name__ == "__main__":
    main()
