"""Locally animated, authenticated display window for the final wizard scene."""

import argparse
import math
import os
import signal
import socket
import sys
import termios
import time
import tty

from ending_effects import (CRASH_DURATION, FRAME_RATE, PANIC_DURATION,
                            render_fake_crash, render_fake_shell, render_panic,
                            shell_context)
from ending_windows import ending_title
from fight import JsonPeer, terminal_size
from terminal_input import END, KeyReader


HEARTBEAT_TIMEOUT = 5.0


def _number(value: object, default: float = 0.0, maximum: float = 86400.0) -> float:
    try:
        value = float(value)
        return min(maximum, max(0.0, value)) if math.isfinite(value) else default
    except (TypeError, ValueError, OverflowError):
        return default


def run(port: int, token: str, window_id: str, role: str, index: int = 0) -> None:
    """Draw locally while keeping input, parent messages and cleanup responsive."""
    peer = None
    saved_tty = None
    stdin_fd = None
    entered_screen = False
    stopped = False
    interrupted = False
    old_handlers = {}
    title = ending_title(token, window_id, role)

    def stop(signum: int, frame: object) -> None:
        nonlocal stopped
        stopped = True

    def interrupt(signum: int, frame: object) -> None:
        nonlocal interrupted
        interrupted = True

    try:
        # run() is also usable by tests outside the main thread.
        for signum, handler in ((signal.SIGHUP, stop), (signal.SIGTERM, stop),
                                (signal.SIGINT, interrupt),
                                (signal.SIGQUIT, signal.SIG_IGN),
                                (signal.SIGTSTP, signal.SIG_IGN)):
            try:
                old_handlers[signum] = signal.signal(signum, handler)
            except ValueError:
                pass
        sock = socket.create_connection(("127.0.0.1", port), timeout=2.5)
        peer = JsonPeer(sock)
        try:
            stdin_fd = sys.stdin.fileno()
        except (AttributeError, OSError, ValueError):
            pass
        if stdin_fd is not None and os.isatty(stdin_fd):
            saved_tty = termios.tcgetattr(stdin_fd)
            tty.setraw(stdin_fd, termios.TCSANOW)
        reader = KeyReader(stdin_fd) if stdin_fd is not None else None
        sys.stdout.write(f"\x1b[?1049h\x1b[?25l\x1b]0;{title}\x07\x1b[2J\x1b[H")
        sys.stdout.flush()
        entered_screen = True
        peer.send({"type": "hello", "token": token, "window_id": window_id,
                   "role": role, "pid": os.getpid()})
        scene = None
        context = shell_context()
        duration = PANIC_DURATION
        reopened = 0
        elapsed_offset = 0.0
        scene_started = last_seen = time.monotonic()
        next_frame = 0.0
        rendered_size = None
        clear_pending = True
        finished = False
        end_sent = False
        cancellation_sent = False
        while not stopped:
            now = time.monotonic()
            for message in peer.poll():
                last_seen = now
                kind = message["type"]
                if kind == "shutdown":
                    return
                if kind == "ping":
                    peer.send({"type": "pong"})
                elif kind == "scene" and message.get("scene") in ("shell", "crash", "panic"):
                    if scene != message["scene"]:
                        clear_pending = True
                    scene = message["scene"]
                    supplied_context = message.get("context")
                    if isinstance(supplied_context, dict):
                        # Renderers sanitize values before they reach the terminal.
                        context = {str(key): str(value)[:256] for key, value in
                                   list(supplied_context.items())[:12]}
                    elapsed_offset = _number(message.get("elapsed"))
                    reopened = int(_number(message.get("reopened"), maximum=1000))
                    index = int(_number(message.get("index", index), maximum=5))
                    duration = max(0.1, _number(message.get("duration", PANIC_DURATION),
                                               PANIC_DURATION, maximum=8.0))
                    scene_started = now
                    next_frame = 0.0
                    finished = False
                    end_sent = False
            if peer.eof or now - last_seen > HEARTBEAT_TIMEOUT:
                return
            if interrupted:
                interrupted = False
                if not cancellation_sent:
                    peer.send({"type": "input", "key": "CTRL_C"})
                    cancellation_sent = True
            # Sending Ctrl+C does not close this window. The parent first closes
            # the whole ending, so cancellation cannot look like a shell close.
            size = terminal_size()
            size_changed = size != rendered_size
            if (scene is not None and not cancellation_sent and now >= next_frame
                    and (not finished or size_changed or clear_pending)):
                elapsed = elapsed_offset + now - scene_started
                if scene == "shell":
                    screen = render_fake_shell(size, elapsed, context=context, reopened=reopened)
                elif scene == "crash":
                    screen = render_fake_crash(size, elapsed, context=context)
                else:
                    screen = render_panic(size, elapsed, index=index, duration=duration)
                if clear_pending or size_changed:
                    sys.stdout.write("\x1b[2J\x1b[H")
                sys.stdout.write(screen)
                sys.stdout.flush()
                clear_pending = False
                rendered_size = size
                next_frame = now + 1 / FRAME_RATE
                limit = CRASH_DURATION if scene == "crash" else duration if scene == "panic" else None
                if not finished and limit is not None and elapsed >= limit:
                    # Notify only after the final frame was flushed.
                    finished = True
                    peer.send({"type": "finished", "scene": scene})
            if reader is None:
                time.sleep(0.02)
                continue
            key = reader.read(0.02)
            if key == "":
                # A pipe can close while the parent is still connected. It is
                # safe to keep the display alive until shutdown or heartbeat loss.
                reader = None
            elif key == "\x03" and not cancellation_sent:
                peer.send({"type": "input", "key": "CTRL_C"})
                cancellation_sent = True
            elif key == END and scene == "shell" and not end_sent and not cancellation_sent:
                peer.send({"type": "input", "key": "END"})
                end_sent = True
            # All other input is inert: this is a drawing, never a real shell.
    except (OSError, ConnectionError, ValueError, TypeError, termios.error):
        # A closing terminal or refused connection is a normal owned-window exit.
        pass
    finally:
        if saved_tty is not None and stdin_fd is not None:
            try:
                termios.tcsetattr(stdin_fd, termios.TCSANOW, saved_tty)
            except (OSError, termios.error):
                pass
        if entered_screen:
            try:
                sys.stdout.write("\x1b[0m\x1b[?25h\x1b[?1049l")
                sys.stdout.flush()
            except (OSError, ValueError):
                pass
        if peer is not None:
            peer.close()
        for signum, handler in old_handlers.items():
            try:
                signal.signal(signum, handler)
            except ValueError:
                pass
        # The platform helper closes only this exact token-and-ID title. It also
        # covers terminal profiles which retain a tab after its command exits.
        try:
            from ending_windows import close_ending_window
            close_ending_window(token, window_id, role)
        except (ImportError, OSError, ValueError):
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    parser.add_argument("--window-id", required=True)
    parser.add_argument("--role", choices=("shell", "panic"), required=True)
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()
    run(args.port, args.token, args.window_id, args.role, args.index)


if __name__ == "__main__":
    main()
