"""Launch and retire the small, explicitly owned terminals used by the finale.

Terminal launchers commonly exit while their terminal is still open.  Their
return codes are useful for reporting launch errors, never for deciding whether
an ending child is alive; the controller owns that decision through its socket.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import base64
import os
import platform
import queue
import re
import shlex
import shutil
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

import fight_windows
from ending_config import MAX_PANIC_WINDOWS


PROJECT = Path(__file__).resolve().parent
MAX_WINDOWS = MAX_PANIC_WINDOWS
_ROLES = {"shell": "player", "panic": "wizard"}
_WINDOW_IDS = {"shell": re.compile(r"s[0-2]\Z"), "panic": re.compile(r"p[0-9]\Z")}
_LAUNCH_GRACE = 0.12
_CLOSE_JOIN_SECONDS = 5.0
_CLEANUP_DELAYS = (0.0, 0.15)
_DESKTOP_TIMEOUT = 0.8
_SELF_CLOSE_WAIT = 0.6


def ending_title(token: str, window_id: str, role: str) -> str:
    """Return an exact, validated capability title understood by fight_windows."""
    if (not isinstance(role, str) or role not in _ROLES or not isinstance(window_id, str)
            or not _WINDOW_IDS[role].fullmatch(window_id)
            or not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", token)):
        raise ValueError("Invalid ending window identity")
    return fight_windows.window_title(_ROLES[role], token + "_" + window_id)


def ending_command(port: int, token: str, window_id: str, role: str, index: int = 0) -> list[str]:
    ending_title(token, window_id, role)
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("Invalid ending controller port")
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < MAX_WINDOWS:
        raise ValueError("Invalid ending window index")
    return [sys.executable, "-B", str(PROJECT / "ending_window.py"),
            "--port", str(port), "--token", token, "--window-id", window_id,
            "--role", role, "--index", str(index)]


def launch_command(port: int, token: str, window_id: str, role: str,
                   index: int = 0) -> tuple[list[str], dict[str, str]]:
    """Use the active interpreter and distribution, without shell input."""
    command = ending_command(port, token, window_id, role, index)
    title = ending_title(token, window_id, role)
    env = os.environ.copy()
    env.pop("GNOME_TERMINAL_SCREEN", None)
    env.pop("GNOME_TERMINAL_SERVICE", None)
    if env.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().lower():
        distro = env.get("WSL_DISTRO_NAME")
        if not distro or not distro.strip():
            raise OSError("Cannot identify the active WSL distribution (WSL_DISTRO_NAME is missing).")
        if not shutil.which("powershell.exe"):
            raise OSError("PowerShell is unavailable for closing the exact ending windows.")
        wsl = ["wsl.exe", "--distribution", distro, "--cd", str(PROJECT), "--exec", *command]
        terminal = shutil.which("wt.exe")
        if terminal:
            return [terminal, "--window", "new", "new-tab", "--title", title,
                    "--suppressApplicationTitle", *wsl], env
        terminal = shutil.which("cmd.exe")
        if terminal:
            return [terminal, "/c", "start", title, *wsl], env
        raise OSError("Cannot find Windows Terminal or cmd.exe in the active WSL distribution.")
    if platform.system() == "Darwin":
        script = '''
on run argv
    tell application "Terminal"
        set gameTab to do script (item 1 of argv)
        set custom title of gameTab to (item 2 of argv)
    end tell
end run
'''
        return ["osascript", "-e", script, "exec " + shlex.join(command), title], env
    if platform.system() == "Linux":
        if env.get("XDG_SESSION_TYPE") == "wayland" or not shutil.which("wmctrl"):
            raise OSError("Ending windows need an X11 desktop with wmctrl for exact window cleanup.")
        terminal = shutil.which("gnome-terminal")
        if terminal:
            return [terminal, "--window", f"--title={title}",
                    f"--working-directory={PROJECT}", "--", *command], env
        terminal = shutil.which("xterm")
        if terminal:
            return [terminal, "-T", title, "-e", *command], env
    raise OSError("No supported terminal is available for the ending windows.")


def close_ending_window(token: str, window_id: str, role: str) -> bool:
    """Quickly schedule this child's exact terminal to close after it exits.

    This helper never opens a terminal.  Waiting until the child exits also
    avoids Terminal profiles asking to close a window with a running process.
    The detached helper is finite: at most 0.6s waiting for this child, followed
    by one bounded desktop action. It cannot launch any game window or child.
    """
    ending_title(token, window_id, role)
    try:
        subprocess.Popen([sys.executable, "-B", str(Path(__file__).resolve()),
                          "--close", token, window_id, role, "--after-pid", str(os.getpid())],
                         cwd=PROJECT, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, close_fds=True, start_new_session=True)
    except OSError:
        return False
    return True


def _close_after_exit(token: str, window_id: str, role: str, pid: int) -> None:
    ending_title(token, window_id, role)
    if pid <= 1:
        raise ValueError("Invalid ending child process")
    deadline = time.monotonic() + _SELF_CLOSE_WAIT
    while fight_windows._process_alive(pid):
        if time.monotonic() >= deadline:
            return
        time.sleep(0.04)
    _desktop_action(_ROLES[role], token + "_" + window_id, "close")


def _desktop_action(role: str, token: str, action: str) -> bool:
    """Reuse exact title scripts with short, kill-and-reap subprocess timeouts."""
    title = fight_windows.window_title(role, token)
    try:
        if fight_windows._is_wsl():
            script = fight_windows.WINDOWS_WINDOW_ACTION.replace(
                "param($TargetTitle, $RequestedAction)",
                f"$TargetTitle = '{title}'; $RequestedAction = '{action}'")
            encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
            result = fight_windows._run(["powershell.exe", "-NoProfile", "-NonInteractive",
                                         "-EncodedCommand", encoded], _DESKTOP_TIMEOUT)
            return action == "close" or result.strip() == "found"
        if platform.system() == "Darwin":
            result = fight_windows._run(["osascript", "-e", fight_windows.MAC_WINDOW_ACTION,
                                         title, action], _DESKTOP_TIMEOUT)
            return action == "close" or result.strip() == "found"
        if os.environ.get("XDG_SESSION_TYPE") != "wayland" and shutil.which("wmctrl"):
            windows = [line.split(None, 3) for line in
                       fight_windows._run(["wmctrl", "-l"], _DESKTOP_TIMEOUT).splitlines()]
            window_id = next((fields[0] for fields in windows
                              if len(fields) == 4 and fields[3] == title), None)
            if window_id is None:
                return action == "close"
            fight_windows._run(["wmctrl", "-ic" if action == "close" else "-ia", window_id],
                                _DESKTOP_TIMEOUT)
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    return False


def _same_command(actual: tuple[str, ...], expected: tuple[str, ...]) -> bool:
    if not actual or actual[1:] != expected[1:]:
        return False
    try:
        return Path(actual[0]).resolve() == Path(expected[0]).resolve()
    except OSError:
        return False


def _proc_birth(pid: int) -> str:
    # The command field can contain spaces and parentheses; fields after its
    # last closing parenthesis start at stat field 3.  starttime is field 22.
    return (Path("/proc") / str(pid) / "stat").read_text().rsplit(")", 1)[1].split()[19]


def _process_identity(pid: int, expected: tuple[str, ...]) -> tuple[str, ...] | None:
    """Read both the exact child command and a process birth marker.

    On macOS ps is deliberately bounded.  An unreadable identity means that we
    leave the process alone and rely on the exact window title/socket shutdown.
    """
    try:
        if platform.system() == "Linux":
            before = _proc_birth(pid)
            data = (Path("/proc") / str(pid) / "cmdline").read_bytes()
            actual = tuple(os.fsdecode(part) for part in data.split(b"\0") if part)
            if not _same_command(actual, expected) or _proc_birth(pid) != before:
                return None
            return (before, *actual)
        if platform.system() == "Darwin":
            result = subprocess.run(["ps", "-ww", "-p", str(pid), "-o", "lstart=", "-o", "command="],
                                    check=True, capture_output=True, text=True,
                                    stdin=subprocess.DEVNULL, timeout=0.4)
            fields = result.stdout.strip().split(None, 5)
            if len(fields) == 6 and fields[5] == " ".join(expected):
                return (" ".join(fields[:5]), *expected)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        pass
    return None


@dataclass
class _Window:
    window_id: str
    role: str
    token: str
    child_command: tuple[str, ...]
    command: list[str]
    env: dict[str, str]
    cancelled: threading.Event = field(default_factory=threading.Event)
    launch_done: threading.Event = field(default_factory=threading.Event)
    cleanup_lock: threading.Lock = field(default_factory=threading.Lock)
    active: bool = True
    pid: int | None = None
    identity: tuple[str, ...] | None = None
    pidfd: int | None = None
    closed_reported: bool = False
    launcher: subprocess.Popen | None = None
    cleanup_started: bool = False
    index: int = 0


class EndingWindows:
    """Keep desktop work away from gameplay and bound outstanding windows.

    ``launched`` means that the desktop accepted a launch request.  It is not a
    child hello or proof that a terminal is still open.  ``register_pid`` must
    only be called after the controller authenticates that child's socket hello.
    """

    def __init__(self) -> None:
        self.events: queue.SimpleQueue[tuple[str, str, str]] = queue.SimpleQueue()
        self._lock = threading.RLock()
        self._closed = False
        self._windows: dict[str, _Window] = {}
        self._threads: set[threading.Thread] = set()

    def _spawn(self, target, *args) -> None:
        def work() -> None:
            try:
                target(*args)
            finally:
                with self._lock:
                    self._threads.discard(threading.current_thread())
        with self._lock:
            thread = threading.Thread(target=work, daemon=True, name="ending-desktop")
            self._threads.add(thread)
            thread.start()

    def launch(self, window_id: str, role: str, port: int, token: str, index: int = 0) -> bool:
        child = tuple(ending_command(port, token, window_id, role, index))
        with self._lock:
            if (self._closed or window_id in self._windows
                    or sum(window.active for window in self._windows.values()) >= MAX_WINDOWS):
                return False
            try:
                command, env = launch_command(port, token, window_id, role, index)
            except OSError as error:
                self.events.put(("launch_error", window_id, str(error)))
                return False
            window = _Window(window_id, role, token, child, command, env, index=index)
            self._windows[window_id] = window
            self._spawn(self._launch, window)
        return True

    def _launch(self, window: _Window) -> None:
        try:
            if window.cancelled.is_set():
                return
            process = subprocess.Popen(window.command, cwd=PROJECT, env=window.env,
                                       stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, close_fds=True,
                                       start_new_session=True)
            with self._lock:
                window.launcher = process
            if window.cancelled.is_set():
                self._stop_launcher(window)
            # An early nonzero exit is an actionable launch error.  Zero is
            # normal for GNOME, Terminal.app, and Windows Terminal dispatchers.
            window.cancelled.wait(_LAUNCH_GRACE)
            status = process.poll()
            if status is not None and status != 0:
                if not window.cancelled.is_set():
                    self.events.put(("launch_error", window.window_id,
                                     f"Terminal launcher exited with status {status}."))
                window.cancelled.set()
            elif not window.cancelled.is_set():
                self.events.put(("launched", window.window_id, ""))
        except (OSError, subprocess.SubprocessError) as error:
            if not window.cancelled.is_set():
                self.events.put(("launch_error", window.window_id, str(error)))
            window.cancelled.set()
        finally:
            window.launch_done.set()
            # Covers cancellation while Popen was dispatching a desktop call.
            if window.cancelled.is_set():
                self._request_cleanup(window)

    def register_pid(self, window_id: str, pid: int) -> None:
        if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 1 or pid == os.getpid():
            return
        with self._lock:
            window = self._windows.get(window_id)
            if window is None or window.pid is not None:
                return
            if not self._closed:
                # Reserve the worker under the same lock used by close(), so
                # shutdown cannot miss a registration about to start.
                self._spawn(self._register_pid, window, pid)
                return
        # A late authenticated hello after shutdown must not create a worker
        # which can outlive close(). Verify and retire it on the caller thread.
        self._register_pid(window, pid)

    def _register_pid(self, window: _Window, pid: int) -> None:
        identity = _process_identity(pid, window.child_command)
        if identity is None:
            return
        pidfd = None
        if hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal"):
            try:
                pidfd = os.pidfd_open(pid, 0)
                if _process_identity(pid, window.child_command) != identity:
                    os.close(pidfd)
                    return
            except OSError:
                if pidfd is not None:
                    os.close(pidfd)
                pidfd = None
        with self._lock:
            if window.pid is not None:
                if pidfd is not None:
                    os.close(pidfd)
                return
            window.pid, window.identity, window.pidfd = pid, identity, pidfd
            cancelled = window.cancelled.is_set()
        if cancelled:
            # A late authenticated hello must be retired even if an earlier
            # cleanup found no PID/window yet.  Serialize with that cleanup.
            try:
                self._stop_child(window)
                _desktop_action(_ROLES[window.role], window.token + "_" + window.window_id, "close")
            finally:
                self._release_pidfd(window)
        else:
            self._arrange_window(window)

    def _arrange_window(self, window: _Window) -> None:
        """Focus the pretend shell, or scatter exact panic windows on X11."""
        if window.cancelled.is_set():
            return
        if window.role == "shell":
            _desktop_action("player", window.token + "_" + window.window_id, "focus")
            return
        if (platform.system() != "Linux" or fight_windows._is_wsl()
                or os.environ.get("XDG_SESSION_TYPE") == "wayland" or not shutil.which("wmctrl")):
            return
        try:
            title = ending_title(window.token, window.window_id, window.role)
            windows = [line.split(None, 3) for line in
                       fight_windows._run(["wmctrl", "-l"], _DESKTOP_TIMEOUT).splitlines()]
            identifier = next((parts[0] for parts in windows if len(parts) == 4 and parts[3] == title), None)
            if identifier is None or window.cancelled.is_set():
                return
            desktop = next(line for line in fight_windows._run(["wmctrl", "-d"], _DESKTOP_TIMEOUT).splitlines()
                           if " * " in line)
            area = re.search(r"\bWA:\s*(-?\d+),(-?\d+)\s+(\d+)x(\d+)", desktop)
            if area is None:
                return
            left, top, available_width, available_height = map(int, area.groups())
            width = min(700, available_width, max(300, available_width * 2 // 3))
            height = min(420, available_height, max(180, available_height * 2 // 3))
            columns = 3
            rows = (MAX_WINDOWS + columns - 1) // columns
            x = left + (available_width - width) * (window.index % columns) // (columns - 1)
            y = top + (available_height - height) * (window.index // columns) // max(1, rows - 1)
            if not window.cancelled.is_set():
                fight_windows._run(["wmctrl", "-ir", identifier, "-e", f"0,{x},{y},{width},{height}"],
                                    _DESKTOP_TIMEOUT)
        except (OSError, ValueError, StopIteration, subprocess.SubprocessError):
            pass

    def _signal_child(self, window: _Window, requested_signal: int) -> bool:
        with self._lock:
            pid, identity, pidfd = window.pid, window.identity, window.pidfd
        if pid is None or identity is None or _process_identity(pid, window.child_command) != identity:
            return False
        with self._lock:
            try:
                # Closing a pidfd is serialized with sending through it, so a
                # reused file descriptor can never become a signal target.
                if window.pidfd is not None and hasattr(signal, "pidfd_send_signal"):
                    signal.pidfd_send_signal(window.pidfd, requested_signal)
                else:
                    os.kill(pid, requested_signal)
                return True
            except OSError:
                return False

    def _stop_child(self, window: _Window) -> None:
        if self._signal_child(window, signal.SIGTERM):
            time.sleep(0.12)
            # Recheck identity after the grace period, including before a kill.
            self._signal_child(window, signal.SIGKILL)
            deadline = time.monotonic() + 0.25
            while (window.pid is not None
                   and _process_identity(window.pid, window.child_command) == window.identity):
                if time.monotonic() >= deadline:
                    break
                time.sleep(0.015)

    def _release_pidfd(self, window: _Window) -> None:
        with self._lock:
            if window.pidfd is not None:
                os.close(window.pidfd)
                window.pidfd = None

    def _stop_launcher(self, window: _Window) -> None:
        """Reap only the exact Popen child created for this launch request."""
        with self._lock:
            process = window.launcher
        if process is None:
            return
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=0.12)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=0.25)
            else:
                process.wait(timeout=0)
        except (OSError, subprocess.SubprocessError):
            # Another cleanup worker may already have reaped this exact child.
            pass

    def _request_cleanup(self, window: _Window) -> None:
        with self._lock:
            if not window.cleanup_started:
                window.cleanup_started = True
                self._spawn(self._cleanup, window)

    def _cleanup(self, window: _Window) -> None:
        window.launch_done.wait()
        with window.cleanup_lock:
            self._stop_launcher(window)
            self._stop_child(window)
            # A dispatched request can materialize shortly after the launcher
            # exits.  Retrying exact titles is safe; generic title matching is
            # never used.  The child also exits on controller socket loss.
            confirmed = False
            for delay in _CLEANUP_DELAYS:
                if delay:
                    time.sleep(delay)
                try:
                    confirmed = _desktop_action(
                        _ROLES[window.role], window.token + "_" + window.window_id, "close") or confirmed
                except (OSError, subprocess.SubprocessError):
                    pass
            self._stop_child(window)
            self._stop_launcher(window)
            with self._lock:
                # If desktop automation failed, conservatively reserve its
                # slot: an unconfirmed old window must not exceed the cap.
                window.active = not confirmed
                self._release_pidfd(window)
                if not window.closed_reported:
                    window.closed_reported = True
                    detail = "" if confirmed else "Close the ending terminal manually if it remains open."
                    self.events.put(("closed", window.window_id, detail))

    def close_window(self, window_id: str) -> None:
        with self._lock:
            window = self._windows.get(window_id)
            if window is None or window.cancelled.is_set():
                return
            window.cancelled.set()
            self._request_cleanup(window)

    def focus_player(self, player_token: str) -> None:
        fight_windows.window_title("player", player_token)
        with self._lock:
            if not self._closed:
                self._spawn(_desktop_action, "player", player_token, "focus")

    def close(self) -> None:
        """Cancel launches, retire owned processes, and drain bounded desktop work.

        Cleanups run in parallel. Desktop commands have individual
        timeouts and are killed/reaped by subprocess.run on expiry. A terminal
        dispatch still returning from Popen rechecks cancellation before it can
        publish a successful launch, and immediately retires that owned process.
        """
        with self._lock:
            if self._closed:
                return
            self._closed = True
            for window_id in self._windows:
                self.close_window(window_id)
        deadline = time.monotonic() + _CLOSE_JOIN_SECONDS
        while True:
            with self._lock:
                pending = [thread for thread in self._threads if thread is not threading.current_thread()]
            if not pending:
                break
            for thread in pending:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                thread.join(min(remaining, 0.05))
            if time.monotonic() >= deadline:
                break
        # Also cover a launch or authenticated registration completing at the
        # edge of the join deadline. These act only on exact owned processes.
        for window in self._windows.values():
            self._stop_launcher(window)
            self._stop_child(window)
            self._release_pidfd(window)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Close one exact ending terminal after its child exits.")
    parser.add_argument("--close", nargs=3, metavar=("TOKEN", "WINDOW_ID", "ROLE"), required=True)
    parser.add_argument("--after-pid", type=int, required=True)
    args = parser.parse_args()
    _close_after_exit(*args.close, args.after_pid)
