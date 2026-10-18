"""The final End-key puzzle, owned by the original game's process.

Closing a display window never creates a new controller. Only this controller
can reopen its shell (twice), start the bounded panic, or shut everything down.
"""

from dataclasses import dataclass
import hmac
import secrets
import signal
import socket
import sys
import time
from typing import Callable

from .effects import (
    CRASH_DURATION, render_fake_crash, render_fake_shell,
    render_fallback_panic, render_true_end, shell_context,
)
from .windows import EndingWindows
from .config import MAX_PANIC_WINDOWS, PANIC_DURATION, PANIC_STAGGER, panic_close
from fight.controller import JsonPeer, terminal_size
from terminal_input import END, KeyReader


MAX_REOPENINGS = 2
HELLO_TIMEOUT = 3.5
HEARTBEAT_TIMEOUT = 5.0
FRAME_TIME = 1 / 30
TRUE_END_DURATION = 2.75


@dataclass
class Child:
    window_id: str
    role: str
    created: float
    index: int = 0
    close_at: float = 0.0
    peer: JsonPeer | None = None
    last_seen: float = 0.0
    closing: bool = False
    closed: bool = False


class FinaleController:
    def __init__(self, player_token: str, *, inline: bool = False,
                 windows: EndingWindows | None = None,
                 clock: Callable[[], float] = time.monotonic) -> None:
        self.clock = clock
        self.now = clock()
        self.player_token = player_token
        self.token = secrets.token_hex(16)
        self.context = shell_context()
        self.windows = windows if windows is not None else EndingWindows()
        self.inline = inline
        self.panic_fallback = inline
        self.phase = "new"
        self.phase_started = self.now
        self.shell_started: float | None = None
        self.reopenings = 0
        self.reopening_enabled = False
        self.solved = False
        self.typed = ""
        self.window_warning = ""
        self.shell_id: str | None = None
        self.children: dict[str, Child] = {}
        self.pending: list[tuple[JsonPeer, float]] = []
        self.panic_spawned = 0
        self.last_ping = self.now
        self.closed = False
        self.listener: socket.socket | None = None
        self.port = 0
        if not inline:
            try:
                self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.listener.bind(("127.0.0.1", 0))
                self.listener.listen(MAX_PANIC_WINDOWS + 2)
                self.listener.setblocking(False)
                self.port = self.listener.getsockname()[1]
            except OSError:
                if self.listener is not None:
                    self.listener.close()
                self.listener = None
                self.inline = self.panic_fallback = True

    @property
    def finished(self) -> bool:
        return self.phase in ("done", "aborted")

    def start(self) -> None:
        if self.phase != "new":
            return
        self.reopening_enabled = True
        if self.inline:
            self._inline_shell(self.now)
        else:
            self._launch_shell(self.now)

    def _set_phase(self, phase: str, now: float) -> None:
        self.phase, self.phase_started = phase, now

    def _launch_shell(self, now: float) -> None:
        window_id = f"s{self.reopenings}"
        self.shell_id = window_id
        self.children[window_id] = Child(window_id, "shell", now)
        self._set_phase("opening_shell", now)
        if not self.windows.launch(window_id, "shell", self.port, self.token):
            self.children[window_id].closed = True
            self._inline_shell(now)

    def _inline_shell(self, now: float) -> None:
        self.inline = True
        self.reopening_enabled = False
        for child in self.children.values():
            self._close_child(child)
        if self.shell_started is None:
            self.shell_started = now
        self._set_phase("shell", now)
        self.windows.focus_player(self.player_token)

    def _send(self, child: Child, message: dict) -> bool:
        if child.peer is None:
            return False
        try:
            child.peer.send(message)
            return True
        except (OSError, ConnectionError):
            return False

    def _close_child(self, child: Child) -> None:
        if child.closing or child.closed:
            return
        child.closing = True
        if child.peer is not None:
            self._send(child, {"type": "shutdown"})
            child.peer.close()
            child.peer = None
        self.windows.close_window(child.window_id)

    def _lost_child(self, child: Child, now: float, *, reliable: bool = True) -> None:
        if child.closing or child.closed:
            return
        self._close_child(child)
        if child.role == "shell" and child.window_id == self.shell_id:
            if self.phase == "shell" and self.reopening_enabled and reliable:
                if self.reopenings < MAX_REOPENINGS:
                    self.reopenings += 1
                    self._launch_shell(now)
                else:
                    self.abort()
            elif self.phase in ("opening_shell", "shell"):
                self._inline_shell(now)
            elif self.phase == "crash":
                self.inline = True
                self.windows.focus_player(self.player_token)
        elif child.role == "panic" and self.phase == "panic":
            self._panic_inline()

    def _panic_inline(self) -> None:
        self.panic_fallback = True
        self.panic_spawned = MAX_PANIC_WINDOWS
        for child in self.children.values():
            if child.role == "panic":
                self._close_child(child)
        self.windows.focus_player(self.player_token)

    def handle_key(self, key: str | None) -> None:
        if key == "":
            self.abort()
            return
        if key in ("\x03", "CTRL_C"):
            return
        if key == END and self.phase == "shell" and not self.solved:
            self.solved = True
            # Set this before sending or closing anything: EOF cannot reopen it.
            self.reopening_enabled = False
            self._set_phase("crash", self.now)
            if not self.inline and self.shell_id is not None:
                child = self.children[self.shell_id]
                if not self._send(child, {"type": "scene", "scene": "crash",
                                         "elapsed": 0.0, "context": self.context}):
                    self.inline = True
            return
        if self.phase != "shell" or key is None:
            return
        # Input is display data only. No command, eval or subprocess receives it.
        if key in ("\x7f", "\x08"):
            self.typed = self.typed[:-1]
        elif key in ("\r", "\n"):
            self.typed = ""
        elif len(key) == 1 and 32 <= ord(key) <= 126:
            self.typed = (self.typed + key)[-160:]

    def abort(self) -> None:
        self.reopening_enabled = False
        if self.phase != "done":
            self.phase = "aborted"

    def _hello(self, peer: JsonPeer, message: dict, now: float) -> bool:
        token = message.get("token")
        child = self.children.get(message.get("window_id"))
        pid = message.get("pid")
        if (message.get("type") != "hello" or not isinstance(token, str)
                or not hmac.compare_digest(token, self.token) or child is None
                or child.closing or child.closed or child.peer is not None
                or message.get("role") != child.role
                or not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0):
            return False
        child.peer, child.last_seen = peer, now
        self.windows.register_pid(child.window_id, pid)
        if child.role == "shell" and self.phase == "opening_shell":
            if self.shell_started is None:
                self.shell_started = now
            self._set_phase("shell", now)
            self._send(child, {"type": "scene", "scene": "shell",
                               "elapsed": max(0.0, now - self.shell_started),
                               "reopened": self.reopenings, "context": self.context})
        elif child.role == "panic" and self.phase == "panic":
            self._send(child, {"type": "scene", "scene": "panic", "elapsed": 0.0,
                               "index": child.index,
                               "duration": max(0.3, child.close_at - now)})
        else:
            self._close_child(child)
        return True

    def _message(self, child: Child, message: dict, now: float) -> None:
        child.last_seen = now
        if message.get("type") == "input":
            key = message.get("key")
            if key == "CTRL_C":
                self.handle_key(key)
            elif key == END and child.role == "shell" and child.window_id == self.shell_id:
                self.handle_key(END)
        elif message.get("type") == "finished" and child.role == "panic":
            self._close_child(child)

    def _network(self, now: float) -> None:
        if self.listener is not None:
            for _ in range(8):
                try:
                    sock, _ = self.listener.accept()
                except BlockingIOError:
                    break
                except OSError:
                    self.listener.close()
                    self.listener = None
                    if self.phase in ("opening_shell", "shell"):
                        self._inline_shell(now)
                    elif self.phase == "panic":
                        self._panic_inline()
                    break
                if len(self.pending) < 12:
                    self.pending.append((JsonPeer(sock), now))
                else:
                    sock.close()
        for peer, connected_at in list(self.pending):
            remove = False
            try:
                messages = peer.poll()
                if messages:
                    remove = True
                    if self._hello(peer, messages[0], now):
                        child = self.children[messages[0]["window_id"]]
                        for message in messages[1:]:
                            self._message(child, message, now)
                    else:
                        peer.close()
                elif peer.eof or now - connected_at > HELLO_TIMEOUT:
                    peer.close()
                    remove = True
            except (OSError, ConnectionError, ValueError, TypeError):
                peer.close()
                remove = True
            if remove:
                self.pending.remove((peer, connected_at))
        for child in list(self.children.values()):
            if child.peer is None or child.closing or child.closed:
                continue
            try:
                for message in child.peer.poll():
                    self._message(child, message, now)
                if child.peer is not None and child.peer.eof:
                    self._lost_child(child, now)
                elif now - child.last_seen > HEARTBEAT_TIMEOUT:
                    self._lost_child(child, now, reliable=False)
            except (OSError, ConnectionError, ValueError, TypeError):
                self._lost_child(child, now, reliable=False)
        if now - self.last_ping >= 0.75:
            self.last_ping = now
            for child in self.children.values():
                if not child.closing and not child.closed:
                    self._send(child, {"type": "ping"})

    def _begin_panic(self, now: float) -> None:
        self._set_phase("panic", now)
        self.panic_fallback = self.inline
        self.panic_spawned = MAX_PANIC_WINDOWS if self.panic_fallback else 0
        if self.panic_fallback:
            self.windows.focus_player(self.player_token)

    def _true_ending(self, now: float) -> None:
        self._set_phase("true_end", now)
        self.windows.focus_player(self.player_token)

    def tick(self, now: float | None = None) -> None:
        self.now = self.clock() if now is None else now
        now = self.now
        if self.closed or self.finished:
            return
        while not self.windows.events.empty():
            kind, window_id, detail = self.windows.events.get_nowait()
            child = self.children.get(window_id)
            if kind == "closed" and child is not None:
                child.closed = True
                if detail:
                    self.window_warning = "Close any remaining ending windows manually; continuing here."
                    if self.phase in ("opening_shell", "shell"):
                        self._inline_shell(now)
                    elif self.phase == "closing_shell":
                        self.inline = True
                    elif self.phase == "panic":
                        self._panic_inline()
            elif kind == "launch_error" and child is not None:
                self._lost_child(child, now, reliable=False)
        self._network(now)
        if self.finished:
            return
        if self.phase == "opening_shell" and now - self.phase_started >= HELLO_TIMEOUT:
            self._inline_shell(now)
        if self.phase == "crash" and now - self.phase_started >= CRASH_DURATION:
            if self.shell_id is not None:
                self._close_child(self.children[self.shell_id])
            if self.inline:
                self._begin_panic(now)
            else:
                self._set_phase("closing_shell", now)
        if self.phase == "closing_shell":
            child = self.children[self.shell_id]
            if child.closed:
                self._begin_panic(now)
            elif now - self.phase_started >= 2:
                # No closure acknowledgement: finish safely in the original.
                self.inline = True
                self._begin_panic(now)
        if self.phase == "panic":
            elapsed = now - self.phase_started
            while (not self.panic_fallback and self.panic_spawned < MAX_PANIC_WINDOWS
                   and elapsed >= self.panic_spawned * PANIC_STAGGER):
                index = self.panic_spawned
                self.panic_spawned += 1
                window_id = f"p{index}"
                close_at = self.phase_started + panic_close(index)
                child = Child(window_id, "panic", now, index=index, close_at=close_at)
                self.children[window_id] = child
                if (now >= close_at or not self.windows.launch(
                        window_id, "panic", self.port, self.token, index=index)):
                    child.closed = True
                    self._panic_inline()
                    break
            for child in self.children.values():
                if child.role == "panic" and not child.closing:
                    if now >= child.close_at:
                        self._close_child(child)
                    elif child.peer is None and now - child.created >= HELLO_TIMEOUT:
                        self._panic_inline()
                        break
            if elapsed >= PANIC_DURATION:
                for child in self.children.values():
                    self._close_child(child)
                self._set_phase("closing_panic", now)
        if self.phase == "closing_panic":
            if (all(child.closed for child in self.children.values())
                    or now - self.phase_started >= 4):
                self._true_ending(now)
        if self.phase == "true_end" and now - self.phase_started >= TRUE_END_DURATION:
            self.phase = "done"

    def render(self, size: tuple[int, int]) -> str:
        if self.phase in ("opening_shell", "shell"):
            elapsed = 0.0 if self.shell_started is None else self.now - self.shell_started
            return render_fake_shell(size, elapsed if self.inline else 0.0,
                                     context=self.context, reopened=self.reopenings,
                                     typed=self.typed if self.inline else "")
        if self.phase == "crash" and self.inline:
            return render_fake_crash(size, self.now - self.phase_started, context=self.context)
        if self.phase == "panic" and self.panic_fallback:
            return render_fallback_panic(size, self.now - self.phase_started,
                                         duration=PANIC_DURATION)
        if self.phase == "true_end":
            return render_true_end(size, self.now - self.phase_started)
        return "\x1b[?25l\x1b[0m\x1b[2J\x1b[H"

    def close(self) -> None:
        if self.closed:
            return
        self.closed = True
        self.reopening_enabled = False
        for child in self.children.values():
            self._close_child(child)
        for peer, _ in self.pending:
            peer.close()
        self.pending.clear()
        if self.listener is not None:
            self.listener.close()
            self.listener = None
        self.windows.close()


def run_finale(fd: int, player_token: str, *, inline: bool = False,
               read_input: Callable | None = None) -> bool:
    """Run inside the original raw-mode terminal; its caller restores the TTY."""
    controller = FinaleController(player_token, inline=inline)
    reader = KeyReader(fd) if read_input is None else None
    previous = None
    previous_view = None
    previous_sigint = None
    try:
        try:
            previous_sigint = signal.signal(signal.SIGINT, signal.SIG_IGN)
        except ValueError:
            # Tests may run the display loop outside Python's main thread.
            pass
        controller.start()
        while not controller.finished:
            key = (reader.read(FRAME_TIME) if reader is not None
                   else read_input(fd, timeout=FRAME_TIME))
            # A disconnected original terminal stops every owned child before
            # a simultaneous fake-shell EOF can schedule a replacement.
            if key == "":
                controller.handle_key(key)
                break
            controller.tick()
            controller.handle_key(key)
            size = terminal_size()
            view = (size, controller.phase, controller.inline, controller.panic_fallback)
            output = controller.render(size)
            if controller.window_warning and controller.phase in ("shell", "panic"):
                output += "\x1b[1;1H\x1b[2m" + controller.window_warning[:max(0, size[0] - 1)] + "\x1b[0m"
            if view != previous_view:
                sys.stdout.write("\x1b[0m\x1b[2J\x1b[H")
                previous = None
                previous_view = view
            if output != previous:
                sys.stdout.write(output)
                sys.stdout.flush()
                previous = output
        return controller.phase == "done"
    finally:
        try:
            controller.close()
        finally:
            if previous_sigint is not None:
                signal.signal(signal.SIGINT, previous_sigint)
