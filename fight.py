"""Shared drawing/protocol helpers and the player-owned wizard fight."""

import json
import os
import secrets
import shutil
import socket
import sys
import time
from textwrap import dedent, wrap

from fight_windows import MANUAL_LAYOUT, WindowPair
from fight_effects import PLAYER_HAND_ROW, PLAYER_POSES, PLAYER_WIDTH
from levels.level1 import WIZARD


SPELL = "1010011010100110"
SPEED = 20.0  # Character cells per second, in both terminals.
FRAME_TIME = 1 / 30
PLAYER = PLAYER_POSES["ready"]
STOP_X = PLAYER_WIDTH + 4
DODGE_TIME = 0.35


class JsonPeer:
    """A bounded, nonblocking NDJSON stream, including partial reads/writes."""

    def __init__(self, sock: socket.socket) -> None:
        self.socket = sock
        sock.setblocking(False)
        if getattr(sock, "family", None) in (socket.AF_INET, socket.AF_INET6):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self.incoming = bytearray()
        self.outgoing = bytearray()
        self.eof = False

    def send(self, message: dict) -> None:
        self.outgoing.extend(json.dumps(message, separators=(",", ":")).encode("ascii") + b"\n")
        if len(self.outgoing) > 65536:
            raise ConnectionError("Wizard connection is not accepting messages.")
        self.flush()

    def flush(self) -> None:
        while self.outgoing:
            try:
                sent = self.socket.send(self.outgoing)
            except BlockingIOError:
                break
            if not sent:
                raise ConnectionError("Terminal connection closed.")
            del self.outgoing[:sent]

    def poll(self) -> list[dict]:
        self.flush()
        messages = []
        # Bound the work per tick so a noisy peer cannot starve keyboard input.
        for _ in range(16):
            try:
                chunk = self.socket.recv(4096)
            except BlockingIOError:
                break
            if not chunk:
                self.eof = True
                break
            self.incoming.extend(chunk)
            while b"\n" in self.incoming:
                line, _, tail = self.incoming.partition(b"\n")
                self.incoming = bytearray(tail)
                if len(line) > 65536:
                    raise ConnectionError("Oversized terminal message.")
                try:
                    message = json.loads(line)
                except (ValueError, UnicodeError) as error:
                    raise ConnectionError("Invalid terminal message.") from error
                if not isinstance(message, dict) or not isinstance(message.get("type"), str):
                    raise ConnectionError("Invalid terminal event.")
                messages.append(message)
            if len(self.incoming) > 65536:
                raise ConnectionError("Oversized terminal message.")
        if self.eof and self.incoming:
            raise ConnectionError("Terminal closed during a message.")
        return messages

    def close(self) -> None:
        self.socket.close()


def terminal_size() -> tuple[int, int]:
    try:
        size = os.get_terminal_size(sys.stdout.fileno())
    except (OSError, ValueError):
        size = shutil.get_terminal_size(fallback=(80, 24))
    return max(4, size.columns), max(4, size.lines)


def spell_row(player_rows: int, wizard_rows: int) -> int:
    # Both windows use exactly the same character row, even at different heights.
    return max(1, (min(player_rows, wizard_rows) - 4) // 2)


def wizard_sprite(frame: int) -> list[str]:
    return dedent(WIZARD[frame % len(WIZARD)]).strip("\n").splitlines()


def wizard_left(columns: int) -> int:
    return max(1, columns - 3 - max(len(line) for frame in range(len(WIZARD))
                                  for line in wizard_sprite(frame)))


def draw_scene(role: str, size: tuple[int, int], status: str, note: str = "",
               frame: int = 0, x: float | None = None, row: int = 10,
               glyph: str = SPELL, level_number: int = 10,
               description: str = "", player_step: float = 0.0,
               pose: str = "ready", spell_lane: int | None = None) -> str:
    columns, rows = size
    # Leave the last column unused to avoid terminal autowrap in raw mode.
    width = max(1, columns - 1)
    canvas = [[" "] * width for _ in range(rows)]

    def put(text: str, left: int, top: int) -> None:
        if 0 <= top < rows:
            for offset, char in enumerate(text):
                if 0 <= left + offset < width:
                    canvas[top][left + offset] = char

    put(f"Level {level_number} - " + ("Player" if role == "player" else "Wizard"), 0, 0)
    heading = wrap(description, width)[:max(0, rows - 5)]
    for index, line in enumerate(heading):
        put(line, 0, index + 2)
    art_top = max(1, len(heading) + 3) if heading else 1
    footer = (wrap(status, width) + wrap(note, width))[:min(4, rows - 2)]
    floor = rows - len(footer) - 1
    if role == "wizard":
        sprite = wizard_sprite(frame)
        # Keep the wand near the shared spell lane, including in tall windows.
        left = wizard_left(columns)
        top = max(art_top, min(row - 4, floor - len(sprite)))
    else:
        sprite = PLAYER_POSES[pose].splitlines()
        # A back step moves left and away from the spell's original lane.
        left = 2 - round(2 * player_step)
        top = max(art_top, min(row - PLAYER_HAND_ROW + round(3 * player_step), floor - len(sprite)))
    for offset, line in enumerate(sprite):
        if top + offset < floor:
            put(line, left, top + offset)
    if x is not None:
        lane = row if spell_lane is None else spell_lane
        put(glyph, int(x), min(max(1, lane), max(1, floor - 1)))
    for index, line in enumerate(footer):
        put(line, 0, rows - len(footer) + index)
    return "\x1b[?25l" + "".join(
        f"\x1b[{index + 1};1H\x1b[2K{''.join(line).rstrip()}"
        for index, line in enumerate(canvas)
    )


def draw_epilogue(size: tuple[int, int], now: float, *, clear: bool = True) -> str:
    columns, rows = size
    title = "ESCAPE TERMINAL"
    rule = "=" * len(title)
    cursor = "_" if int(now / 0.65) % 2 == 0 else " "
    lines = [rule, title, rule, "", f"Press Escape to leave. {cursor}"]
    top = max(0, (rows - len(lines)) // 2)
    output = []
    for index, line in enumerate(lines):
        line = line[:max(1, columns - 1)]
        row = top + index + 1
        if row <= rows:
            left = max(1, (columns - len(line)) // 2 + 1)
            output.append(f"\x1b[{row};{left}H{line}")
    return "\x1b[?25l" + ("\x1b[2J\x1b[H" if clear else "") + "".join(output)


class PlayerFight:
    """The player is the authority; the wizard only draws requested events."""

    def __init__(self, start_level: int = 10, window_token: str | None = None) -> None:
        from levels.level10 import Level10
        from levels.level11 import Level11

        self.level = Level11() if start_level == 11 else Level10()
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.listener.bind(("127.0.0.1", 0))
            self.listener.listen(1)
            self.listener.setblocking(False)
        except BaseException:
            self.listener.close()
            raise
        self.port = self.listener.getsockname()[1]
        self.token = window_token or secrets.token_hex(8)
        self.peer: JsonPeer | None = None
        self.windows: WindowPair | None = None
        self.state = "connecting"
        self.status = "Opening the wizard's window..."
        self.note = MANUAL_LAYOUT
        self.size = terminal_size()
        self.wizard_size = self.size
        self.row = spell_row(self.size[1], self.wizard_size[1])
        self.started = time.monotonic()
        self.last_seen = self.started
        self.last_ping = self.started
        self.flight_started = 0.0
        self.player_x = 0.0
        self.last_tick = self.started
        self.wizard_ready = False
        self.layout_ready = False
        self.settle_until = self.started
        self.dodge_started = 0.0
        self.player_step = 0.0
        self.undo_requested = False
        self.cast_id = 2 if self.level.number == 11 else 1
        self.closing_started = 0.0
        self.window_cleanup_started = False
        self.cleanup_complete = False
        self.epilogue_cleared = False

    def open_window(self) -> None:
        self.windows = WindowPair(self.port, self.token)

    def _layout(self) -> None:
        self.row = spell_row(self.size[1], self.wizard_size[1])
        if self.peer:
            self.peer.send({"type": "layout", "row": self.row, "note": self.note})

    def _send_level(self) -> None:
        if self.peer:
            self.peer.send({"type": "level", "number": self.level.number,
                            "description": self.level.description})

    def begin_level(self, level) -> None:
        """Cast the final spell using the existing peer and terminal windows."""
        self.level = level
        self.cast_id = 2
        self.undo_requested = False
        self.player_step = 0.0
        self._send_level()
        self._cast(self.last_tick)

    def _cast(self, now: float) -> None:
        self.state = "wizard_spell"
        self.status = "The wizard casts a spell..."
        self.flight_started = now
        self.peer.send({"type": "cast", "id": self.cast_id, "glyph": SPELL,
                        "row": self.row, "speed": SPEED})

    def _reverse(self) -> None:
        self.state = "return_player"
        self.status = "Undo. The spell reverses!"

    def _disconnect(self) -> None:
        if self.peer:
            try:
                self.peer.send({"type": "shutdown"})
            except OSError:
                pass
            self.peer.close()
            self.peer = None
        self.listener.close()

    def _finish_wizard(self, now: float) -> None:
        self.state = "closing_wizard"
        self.status = "The wizard has been defeated."
        self.closing_started = now
        self._disconnect()
        if self.windows:
            self.window_cleanup_started = True
            self.windows.finish_wizard(self.token)
        else:
            self.state = "epilogue"

    def handle_key(self, key: str | None) -> None:
        if (self.level.number == 11 and not self.undo_requested
                and self.state in ("connecting", "preparing", "wizard_spell", "player_spell", "awaiting_undo")
                and self.level.check_input(key)):
            self.undo_requested = True
            if self.state in ("player_spell", "awaiting_undo"):
                self._reverse()
            return
        if self.state == "awaiting_dodge" and self.level.check_input(key):
            self.state = "dodging"
            self.dodge_started = self.last_tick
            self.status = "You take a back step..."
            try:
                self.peer.send({"type": "dodge", "id": 1})
            except OSError as error:
                self.fail(str(error))

    def _message(self, message: dict, now: float) -> None:
        kind = message["type"]
        if kind == "hello" and self.state == "connecting":
            if message.get("token") != self.token:
                raise ConnectionError("Unexpected wizard connection.")
            self.wizard_size = self._dimensions(message)
            self.state = "preparing"
            self._send_level()
            self._layout()
            if self.windows:
                self.windows.arrange(self.token)
            else:
                self.layout_ready = True
        elif kind == "ready" and self.state == "preparing":
            self.wizard_ready = True
            self.status = "Preparing the two windows..."
        elif kind == "resize":
            self.wizard_size = self._dimensions(message)
            self.settle_until = now + 0.5
            self._layout()
        elif kind == "handoff" and self.state == "wizard_spell" and message.get("id") == self.cast_id:
            self.state = "player_spell"
            self.status = "The spell crosses into your window..."
            self.player_x = self.size[0] - 1
        elif kind == "impact" and self.state == "return_wizard" and message.get("id") == 2:
            self.state = "defeating"
            self.flight_started = now
            self.status = "The wizard's spell turns against him."
        elif kind == "death_complete" and self.state == "defeating" and message.get("id") == 2:
            self._finish_wizard(now)
        elif kind == "closed":
            raise ConnectionError("The wizard window closed.")

    @staticmethod
    def _dimensions(message: dict) -> tuple[int, int]:
        columns, rows = message.get("columns"), message.get("rows")
        if not isinstance(columns, int) or not isinstance(rows, int) or not (4 <= columns <= 10000 and 4 <= rows <= 10000):
            raise ConnectionError("Invalid wizard terminal size.")
        return columns, rows

    def tick(self, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        elapsed = max(0.0, now - self.last_tick)
        self.last_tick = now
        try:
            if self.windows:
                while not self.windows.events.empty():
                    kind, value = self.windows.events.get_nowait()
                    if kind == "error":
                        raise ConnectionError(value)
                    if kind == "wizard_closed":
                        self.cleanup_complete = True
                        if self.state == "closing_wizard":
                            self.state = "epilogue"
                        continue
                    self.note = value
                    self.layout_ready = True
                    self.settle_until = now + 0.5
                    self._layout()
            if self.state == "failed":
                self.size = terminal_size()
                return
            size = terminal_size()
            if self.size != size:
                self.size = size
                self.epilogue_cleared = False
                self.player_x = min(self.player_x, size[0] - 1)
                self.settle_until = now + 0.5
                self._layout()
            if self.state in ("closing_wizard", "epilogue"):
                # Closing desktop APIs have bounded timeouts; never wait forever
                # to give the player their Escape screen if automation fails.
                if self.state == "closing_wizard" and now - self.closing_started > 12:
                    self.state = "epilogue"
                return
            if self.peer is None:
                try:
                    sock, _ = self.listener.accept()
                except BlockingIOError:
                    pass
                else:
                    self.peer = JsonPeer(sock)
            if self.peer:
                messages = self.peer.poll()
                for message in messages:
                    self.last_seen = now
                    self._message(message, now)
                if self.peer and self.peer.eof:
                    raise ConnectionError("The wizard window closed.")
                if self.peer and now - self.last_ping > 2:
                    self.peer.send({"type": "ping"})
                    self.last_ping = now
            if self.state in ("closing_wizard", "epilogue"):
                return
            if (self.state == "preparing" and self.wizard_ready and self.layout_ready
                    and now >= self.settle_until):
                self._cast(now)
            if self.state in ("connecting", "preparing") and now - self.started > 20:
                raise ConnectionError("The wizard window did not connect in time.")
            if self.state not in ("connecting", "preparing") and now - self.last_seen > 10:
                raise ConnectionError("The wizard stopped responding.")
            if self.state == "wizard_spell" and now - self.flight_started > 60:
                raise ConnectionError("The wizard's spell did not arrive.")
            if self.state == "return_wizard" and now - self.flight_started > 60:
                raise ConnectionError("The reversed spell did not reach the wizard.")
            if self.state == "defeating" and now - self.flight_started > 15:
                raise ConnectionError("The wizard's final animation stopped responding.")
            if self.state == "player_spell":
                self.player_x -= SPEED * elapsed
                if self.player_x <= STOP_X:
                    self.player_x = STOP_X
                    self.state = "awaiting_undo" if self.level.number == 11 else "awaiting_dodge"
                    self.status = "The spell hangs in the air."
                    if self.level.number == 11 and self.undo_requested:
                        self._reverse()
            elif self.state == "return_player":
                self.player_x += SPEED * elapsed
                if self.player_x >= self.size[0] - 1:
                    self.state = "return_wizard"
                    self.flight_started = now
                    # Render the clear player edge before the wizard starts its
                    # local rightward animation; no frames travel over TCP.
                    if sys.stdout.isatty():
                        sys.stdout.write(self.render())
                        sys.stdout.flush()
                    self.peer.send({"type": "return", "id": 2, "glyph": SPELL[::-1],
                                    "row": self.row, "speed": SPEED})
            if self.state == "dodging":
                self.player_step = min(1.0, (now - self.dodge_started) / DODGE_TIME)
                if self.player_step >= 1:
                    self.player_x -= SPEED * elapsed
                if self.player_x <= -len(SPELL):
                    self.state = "complete"
                    self.status = "Spell dodged. Press Enter to continue."
                    self.peer.send({"type": "missed", "id": 1})
        except (OSError, ConnectionError) as error:
            self.fail(str(error))

    def fail(self, reason: str) -> None:
        self.state = "failed"
        self.status = reason + " Press Enter to retry."
        self.close()

    def render(self) -> str:
        if self.state == "epilogue":
            output = draw_epilogue(self.size, self.last_tick, clear=not self.epilogue_cleared)
            self.epilogue_cleared = True
            return output
        pose = "ready"
        if self.state in ("player_spell", "awaiting_undo", "return_player", "return_wizard", "dodging"):
            pose = "recoil"
        if self.state in ("defeating", "closing_wizard"):
            pose = "victory"
        # The larger character needs visible clearance: after the back step,
        # the missed Level 10 stream passes above the player's head.
        visible_row = self.row
        if self.state == "dodging":
            visible_row -= round((PLAYER_HAND_ROW + 1) * self.player_step)
        return draw_scene("player", self.size, self.status, self.note,
                          x=self.player_x if self.state in ("player_spell", "awaiting_dodge", "dodging", "awaiting_undo", "return_player") else None,
                          row=self.row, level_number=self.level.number,
                          description=self.level.prompt, player_step=self.player_step,
                          glyph=SPELL[::-1] if self.state == "return_player" else SPELL, pose=pose,
                          spell_lane=visible_row)

    def close(self) -> None:
        self._disconnect()
        if self.windows:
            if not self.window_cleanup_started:
                self.window_cleanup_started = True
                self.windows.finish_wizard(self.token)
            self.windows.close()
