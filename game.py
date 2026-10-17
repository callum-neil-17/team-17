import sys
import termios
import tty

from levels import Level1, Level2, Level3, Level4, Level5


def render_screen(content: str) -> None:
    # Clear the previous screen and return the cursor to the top left.
    sys.stdout.write("\x1b[2J\x1b[H" + content)
    sys.stdout.flush()


def main() -> None:
    levels = [Level1(), Level2(), Level3(), Level4(), Level5()]
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
