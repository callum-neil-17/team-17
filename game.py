import shutil
import sys
import termios
import tty

from levels import Level1, Level2, Level3, Level4, Level5, Level6


def render_screen(content: str) -> None:
    columns, rows = shutil.get_terminal_size(fallback=(80, 24))
    # Blank lines separate titles, art and prompts. Center each section as a
    # block so ASCII art keeps its original indentation and proportions.
    sections = "\n".join(content.expandtabs().splitlines()).split("\n\n")
    lines = []
    for section in sections:
        section_lines = section.split("\n")
        width = max(len(line) for line in section_lines)
        padding = " " * max(0, (columns - width) // 2)
        if lines:
            lines.append("")
        lines.extend(padding + line if line else "" for line in section_lines)

    top = max(0, (rows - len(lines)) // 2)
    # Explicit cursor positioning avoids scrolling when content fills the screen.
    output = "".join(
        f"\x1b[{top + index + 1};1H{line}"
        for index, line in enumerate(lines)
    )
    # Clear the previous screen and return the cursor to the top left.
    sys.stdout.write("\x1b[2J\x1b[H" + output)
    sys.stdout.flush()


def main() -> None:
    levels = [Level1(), Level2(), Level3(), Level4(), Level5(),Level6()]
    level_index = 0
    fd = sys.stdin.fileno()
    original_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        render_screen(levels[level_index].render())

        while True:
            key = sys.stdin.read(1)

            # Raw mode delivers Ctrl+C as a character rather than a signal.
            if key in ("q", "\x03", ""):
                break

            if level_index < len(levels) and levels[level_index].check_input(key):
                level_index += 1
                if level_index < len(levels):
                    render_screen(levels[level_index].render())
                else:
                    render_screen("Game complete! Press q to quit.\r\n")

    except KeyboardInterrupt:
        pass
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, original_settings)


if __name__ == "__main__":
    main()
