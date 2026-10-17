import os
import select
import shutil
import sys
import termios
import time
import tty

from levels import Level, Level1, Level2, Level3, Level4, Level5, Level6, Level7, Level8


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
        if len(sections) == 4:
            description, title, art, prompt = sections
        else:
            description = ""
            title, art, prompt = sections
        description_lines = _centered_lines(description, columns) if description else []
        title_lines = _centered_lines(title, columns)
        art_lines = _centered_lines(art, columns)
        prompt_lines = _centered_lines(prompt, columns)
        # Keep the title near the top, the door centered, and the prompt low.
        description_row = 2
        title_row = description_row + len(description_lines) + (1 if description_lines else 0)
        art_row = max(title_row + len(title_lines) + 1, (rows - len(art_lines)) // 2 + 1)
        prompt_row = max(art_row + len(art_lines) + 2, rows - len(prompt_lines) - 1)
        positions = []
        if description_lines:
            positions.append((description_row, description_lines))
        positions.extend(((title_row, title_lines), (art_row, art_lines), (prompt_row, prompt_lines)))
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
    # Read directly so timed polling stays in sync with pending input.
    return os.read(fd, 1).decode("latin-1")


def play_frames(level: Level, fd: int, frame_delay: float | None = None) -> bool:
    """Play the remaining frames once; return False if terminal input closes."""
    if frame_delay is None:
        frame_delay = level.frame_delay
    for frame in range(level.frame + 1, len(level.frames)):
        level.frame = frame
        render_screen(level.render(), level.layout)
        deadline = time.monotonic() + frame_delay

        while (remaining := deadline - time.monotonic()) > 0:
            # Consume input during playback, including q and control keys.
            if read_key(fd, timeout=remaining) == "":
                return False

    return True


def main() -> None:
    levels = [Level1(), Level2(), Level3(), Level4(), Level5(), Level6(), Level7(), Level8()]
    level_index = 0
    fd = sys.stdin.fileno()
    original_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        render_screen(levels[level_index].render(), levels[level_index].layout)

        while True:
            key = read_key(fd)

            # EOF means the terminal disconnected, not that Ctrl+D was pressed.
            if key == "":
                break

            if level_index == len(levels):
                if key == "q":
                    break
                continue

            # Ctrl+C is ordinary input in raw mode: pass it to the current
            # puzzle rather than using it to exit. Other shortcuts stay ignored.
            if key in (None, "q", "\x04", "\x1a", "\x1c", "\x13", "\x11"):
                continue

            level = levels[level_index]
            previous_screen = level.render()
            if level.check_input(key):
                if not play_frames(levels[level_index], fd):
                    break
                level_index += 1
                if level_index < len(levels):
                    render_screen(levels[level_index].render(), levels[level_index].layout)
                else:
                    render_screen("Game complete! Press q to quit.\r\n")
            else:
                # A puzzle can update its scene without advancing the level.
                current_screen = level.render()
                if current_screen != previous_screen:
                    render_screen(current_screen, level.layout)

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original_settings)


if __name__ == "__main__":
    main()
