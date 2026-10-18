import argparse
import errno
import secrets
import signal
import shutil
import sys
import termios
import time
import tty

from fight.controller import FRAME_TIME, PlayerFight
from ending.controller import run_finale
from fight.windows import schedule_player_close, window_title
from terminal_input import ESCAPE, KeyReader
from levels import (
    Level,
    Level1,
    Level2,
    Level3,
    Level4,
    Level5,
    Level6,
    Level7,
    Level8,
    Level9,
    Level10,
    Level11,
    Level12,
)


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


_key_reader: KeyReader | None = None


def read_key(fd: int, timeout: float | None = None) -> str | None:
    global _key_reader
    if _key_reader is None or _key_reader.fd != fd:
        _key_reader = KeyReader(fd)
    return _key_reader.read(timeout)


def play_frames(level: Level, fd: int, frame_delay: float | None = None) -> bool:
    """Play the remaining frames once; return False if terminal input closes."""
    for frame in range(level.frame + 1, len(level.frames)):
        level.frame = frame
        render_screen(level.render(), level.layout)
        delay = frame_delay if frame_delay is not None else level.frame_delays.get(frame, level.frame_delay)
        deadline = time.monotonic() + delay

        while (remaining := deadline - time.monotonic()) > 0:
            # Consume input during playback, including q and control keys.
            if read_key(fd, timeout=remaining) == "":
                return False

    return True


def escape_pressed(fd: int, key: str | None) -> bool:
    """The buffered input reader has already distinguished key sequences."""
    return key == ESCAPE


def play_fight(fd: int, *, start_level: int = 10, window_token: str | None = None) -> bool:
    """Run Levels 10 and 11 together without replacing either fight window."""
    fight = None
    error = ""
    retry_requested = False
    previous_output = None
    try:
        while True:
            if fight is None and not error:
                try:
                    fight = PlayerFight(start_level=start_level, window_token=window_token)
                    sys.stdout.write(f"\x1b]0;Two Keys Player {fight.token}\x07\x1b[2J\x1b[H")
                    sys.stdout.flush()
                    fight.open_window()
                except OSError as exc:
                    error = f"Cannot start the fight: {exc}. Press Enter to retry."
            if fight:
                fight.tick()
                if retry_requested and (fight.windows is None or fight.cleanup_complete):
                    # The old exact-title wizard must be gone before reusing a
                    # launcher identity for another attempt.
                    fight, error, retry_requested = None, "", False
                    continue
                if fight.state == "complete":
                    fight.begin_level(Level11())
                    start_level = 11
                output = fight.render()
                if output != previous_output:
                    sys.stdout.write(output)
                    sys.stdout.flush()
                    previous_output = output
            elif error:
                render_screen(error)
            key = read_key(fd, timeout=FRAME_TIME)
            if key == "":
                return False
            if fight and fight.state == "epilogue" and escape_pressed(fd, key):
                return True
            # Backspace only solves Level 10 once the spell has paused.
            if fight:
                fight.handle_key(key)
            # q and control bytes keep the game's existing behavior. Enter
            # retries a failed connection.
            if key in ("\r", "\n"):
                if error or (fight and fight.state == "failed"):
                    if fight:
                        start_level = fight.level.number
                        fight.close()
                        retry_requested = True
                    else:
                        error = ""
    finally:
        if fight:
            fight.close()
        try:
            sys.stdout.write("\x1b[?25h\x1b[0m")
            sys.stdout.flush()
        except OSError:
            pass


def main(start_fight: bool = False, start_ending: bool = False,
         owned_window: bool = False, window_token: str | None = None,
         start_finale: bool = False, inline_ending: bool = False) -> None:
    global _key_reader
    levels = [
        Level1(),
        Level2(),
        Level3(),
        Level4(),
        Level5(),
        Level6(),
        Level7(),
        Level8(),
        Level9(),
        Level10(),
        Level11(),
        Level12(),
    ]
    level_index = 9 if start_fight or start_ending else 0
    if owned_window and window_token is None:
        raise ValueError("An owned terminal requires its launcher window token.")
    player_token = window_token or secrets.token_hex(16)
    sys.stdout.write(f"\x1b]0;{window_title('player', player_token)}\x07")
    sys.stdout.flush()
    fd = sys.stdin.fileno()
    original_settings = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        _key_reader = KeyReader(fd)
        # Keep game frames out of the shell's screen and scrollback history.
        sys.stdout.write("\x1b[?1049h\x1b[?25l")
        sys.stdout.flush()
        if start_finale:
            run_finale(fd, player_token, inline=inline_ending, read_input=read_key)
            return
        if not isinstance(levels[level_index], Level10):
            render_screen(levels[level_index].render(), levels[level_index].layout)
        next_idle_frame = time.monotonic() + (levels[level_index].idle_frame_delay or 0)

        while True:
            if level_index < len(levels) and isinstance(levels[level_index], Level10):
                escaped = play_fight(fd, start_level=11 if start_ending else 10,
                                     window_token=player_token)
                if escaped:
                    run_finale(fd, player_token, inline=inline_ending, read_input=read_key)
                break
            level = levels[level_index] if level_index < len(levels) else None
            timeout = None
            if level is not None:
                now = time.monotonic()
                redraw = level.update_reaction(now)
                deadlines = []
                if level.idle_frame_delay is not None and now >= next_idle_frame:
                    level.idle_frame += 1
                    next_idle_frame = now + level.idle_frame_delay
                    redraw = True
                if redraw:
                    render_screen(level.render(), level.layout)
                if level.idle_frame_delay is not None:
                    deadlines.append(next_idle_frame)
                if level.reaction_deadline is not None:
                    deadlines.append(level.reaction_deadline)
                if deadlines:
                    timeout = max(0.0, min(deadlines) - now)
            key = read_key(fd, timeout=timeout)

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
                level.clear_reaction()
                if not play_frames(levels[level_index], fd):
                    break
                level_index += 1
                if level_index < len(levels):
                    next_idle_frame = time.monotonic() + (levels[level_index].idle_frame_delay or 0)
                if level_index < len(levels) and not isinstance(levels[level_index], Level10):
                    render_screen(levels[level_index].render(), levels[level_index].layout)
                elif level_index == len(levels):
                    render_screen("Game complete! Press q to quit.\r\n")
            else:
                level.react_to_wrong_input(key)
                # A puzzle can update its scene without advancing the level.
                current_screen = level.render()
                if current_screen != previous_screen:
                    render_screen(current_screen, level.layout)

    except KeyboardInterrupt:
        pass
    except OSError as error:
        if error.errno not in (errno.EIO, errno.EPIPE, errno.ENXIO, errno.EBADF):
            raise
    finally:
        _key_reader = None
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, original_settings)
        except termios.error:
            # There is nothing left to restore if the terminal was disconnected.
            pass
        try:
            sys.stdout.write("\x1b[0m\x1b[?1049l\x1b[?25h")
            if not owned_window:
                sys.stdout.write("\x1b]0;Two Keys\x07")
            sys.stdout.flush()
        except OSError:
            pass
        if owned_window:
            schedule_player_close(window_token)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Two Keys terminal game")
    direct = parser.add_mutually_exclusive_group()
    direct.add_argument("--fight", action="store_true", help="start directly at the Level 10 wizard fight")
    direct.add_argument("--ending", action="store_true", help="start directly at the Level 11 ending")
    direct.add_argument("--finale", action="store_true", help="start directly at the final End-key twist")
    parser.add_argument("--inline-ending", action="store_true", help="show the final twist in this terminal")
    parser.add_argument("--owned-window", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--window-token", help=argparse.SUPPRESS)
    args = parser.parse_args()
    def stop(signum: int, frame: object) -> None:
        raise KeyboardInterrupt
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, stop)
    if args.owned_window and not args.window_token:
        parser.error("--owned-window requires --window-token")
    main(start_fight=args.fight, start_ending=args.ending,
         owned_window=args.owned_window, window_token=args.window_token,
         start_finale=args.finale, inline_ending=args.inline_ending)
