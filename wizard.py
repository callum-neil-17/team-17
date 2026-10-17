"""Display-only wizard window shared by Levels 10 and 11."""

import argparse
import os
import signal
import socket
import sys
import time

from fight import FRAME_TIME, SPELL, SPEED, JsonPeer, draw_scene, terminal_size, wizard_left
from fight_effects import DEATH_DURATION, render_death


def run(port: int, token: str) -> None:
    peer = None
    try:
        sys.stdout.write(f"\x1b[?1049h\x1b[?25l\x1b]0;Two Keys Wizard {token}\x07\x1b[2J\x1b[H")
        sys.stdout.flush()
        sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        peer = JsonPeer(sock)
        size = terminal_size()
        peer.send({"type": "hello", "token": token, "columns": size[0], "rows": size[1]})
        status, note = "Waiting for the player...", ""
        level_number, description = 10, ""
        row, glyph, speed = 1, SPELL, SPEED
        state, cast_id, x = "waiting", None, None
        started = last_tick = last_seen = time.monotonic()
        ready_pending = False
        death_started = 0.0
        death_sent = False
        color = os.environ.get("TERM") != "dumb" and "NO_COLOR" not in os.environ
        while True:
            now = time.monotonic()
            elapsed = now - last_tick
            last_tick = now
            for message in peer.poll():
                last_seen = now
                kind = message["type"]
                if kind == "shutdown":
                    return
                if kind == "ping":
                    peer.send({"type": "pong"})
                elif kind == "level":
                    level_number = int(message["number"])
                    description = str(message["description"])
                    if state != "waiting":
                        state = "ready"
                    status, x = "", None
                elif kind == "layout":
                    row = int(message["row"])
                    note = str(message["note"])
                    if state == "waiting":
                        state, ready_pending = "ready", True
                elif kind == "cast" and state == "ready" and level_number == 10:
                    cast_id = message["id"]
                    glyph, row, speed = message["glyph"], int(message["row"]), float(message["speed"])
                    x = float(max(0, wizard_left(size[0]) - len(glyph)))
                    status, state = "", "casting"
                elif kind == "dodge":
                    status = ""
                elif kind == "missed":
                    status = ""
                elif (kind == "return" and level_number == 11 and state == "ready"
                      and message.get("id") == 2):
                    cast_id = 2
                    glyph, row, speed = message["glyph"], int(message["row"]), float(message["speed"])
                    state, status, x = "returning", "", -float(len(glyph))
            if peer.eof or now - last_seen > 12:
                return
            current_size = terminal_size()
            if current_size != size:
                size = current_size
                if x is not None:
                    x = min(x, size[0] - 1)
                peer.send({"type": "resize", "columns": size[0], "rows": size[1]})
            if state == "casting":
                x -= speed * elapsed
                if x <= -len(glyph):
                    x = None
                    state, status = "handed_off", ""
                    # Draw the empty edge BEFORE sending the handoff event.
                    sys.stdout.write(draw_scene("wizard", size, status, note,
                                                frame=int((now - started) / 0.35), row=row,
                                                level_number=level_number, description=description))
                    sys.stdout.flush()
                    peer.send({"type": "handoff", "id": cast_id})
            elif state == "returning":
                x += speed * elapsed
                if x >= wizard_left(size[0]) + 4:
                    state, x = "dying", None
                    death_started = now
                    peer.send({"type": "impact", "id": cast_id})
            if state == "dying":
                sys.stdout.write(render_death(size, now - death_started, color=color, row=row))
                sys.stdout.flush()
                if now - death_started >= DEATH_DURATION and not death_sent:
                    # The final fatal frame is visible before notifying the
                    # player to close this actual terminal and show its ending.
                    death_sent = True
                    peer.send({"type": "death_complete", "id": cast_id})
                time.sleep(FRAME_TIME)
                continue
            sys.stdout.write(draw_scene("wizard", size, status, note,
                                        frame=0 if level_number == 11 and state == "ready" else int((now - started) / 0.35),
                                        x=x, row=row, glyph=glyph,
                                        level_number=level_number, description=description))
            sys.stdout.flush()
            if ready_pending:
                peer.send({"type": "ready"})
                ready_pending = False
            time.sleep(FRAME_TIME)
    except (OSError, ConnectionError, ValueError, KeyError) as error:
        try:
            sys.stdout.write(f"\r\nWizard window closed: {error}\r\n")
            sys.stdout.flush()
        except OSError:
            pass
    finally:
        if peer:
            peer.close()
        try:
            sys.stdout.write("\x1b[0m\x1b[?1049l\x1b[?25h")
            sys.stdout.flush()
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--token", required=True)
    args = parser.parse_args()
    # Closing a window usually sends SIGHUP. Let finally close the socket too.
    def stop(signum: int, frame: object) -> None:
        raise KeyboardInterrupt
    for signum in (signal.SIGTERM, signal.SIGHUP):
        signal.signal(signum, stop)
    # The player's terminal owns game controls. Typing a terminal shortcut in
    # this display-only window must not terminate or suspend half of the fight.
    for signum in (signal.SIGINT, signal.SIGQUIT, signal.SIGTSTP):
        signal.signal(signum, signal.SIG_IGN)
    try:
        run(args.port, args.token)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
