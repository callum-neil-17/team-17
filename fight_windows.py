"""Open a separate wizard terminal and arrange the pair when the desktop allows it."""

import os
import platform
import queue
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
MANUAL_LAYOUT = "Exit fullscreen; tile Player left and Wizard right."


def window_title(role: str, token: str) -> str:
    """Names are capabilities: never act on a generic terminal title or PID."""
    if role not in ("player", "wizard") or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", token):
        raise ValueError("Invalid game window identity")
    return f"Two Keys {role.title()} {token}"


def wizard_command(port: int, token: str) -> list[str]:
    return [sys.executable, "-B", str(PROJECT / "wizard.py"), "--port", str(port), "--token", token]


def launch_command(port: int, token: str) -> tuple[list[str], dict[str, str]]:
    """Keep both Python processes in the current WSL distribution, if applicable."""
    command = wizard_command(port, token)
    title = window_title("wizard", token)
    env = os.environ.copy()
    env.pop("GNOME_TERMINAL_SCREEN", None)
    env.pop("GNOME_TERMINAL_SERVICE", None)
    if "microsoft" in platform.release().lower() or env.get("WSL_DISTRO_NAME"):
        distro = env.get("WSL_DISTRO_NAME", "Ubuntu")
        wsl = ["wsl.exe", "--distribution", distro, "--cd", str(PROJECT), "--exec", *command]
        terminal = shutil.which("wt.exe")
        if terminal:
            return [terminal, "--window", "new", "new-tab", "--title", title,
                    "--suppressApplicationTitle", *wsl], env
        if shutil.which("cmd.exe"):
            return ["cmd.exe", "/c", "start", title, *wsl], env
        raise OSError("Cannot find Windows Terminal or cmd.exe in WSL.")
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
        if shutil.which("gnome-terminal"):
            return ["gnome-terminal", "--window", f"--title={title}",
                    f"--working-directory={PROJECT}", "--", *command], env
        if shutil.which("xterm"):
            return ["xterm", "-T", title, "-e", *command], env
    raise OSError("No supported terminal found for the wizard window.")


MAC_LAYOUT = r'''
on run argv
    set playerTitle to item 1 of argv
    set wizardTitle to item 2 of argv
    set matchingNames to {}
    tell application "Terminal"
        repeat with w in windows
            if custom title of selected tab of w is playerTitle or custom title of selected tab of w is wizardTitle then
                set end of matchingNames to name of w
            end if
        end repeat
    end tell
    tell application "System Events"
        tell process "Terminal"
            repeat with w in windows
                if matchingNames contains (name of w) then
                    if value of attribute "AXFullScreen" of w then
                        set value of attribute "AXFullScreen" of w to false
                    end if
                end if
            end repeat
        end tell
    end tell
    delay 0.5
    tell application "Finder" to set screenBounds to bounds of window of desktop
    set screenWidth to item 3 of screenBounds
    set screenHeight to item 4 of screenBounds
    set midpoint to screenWidth div 2
    set foundPlayer to false
    set foundWizard to false
    tell application "Terminal"
        repeat with w in windows
            if custom title of selected tab of w is playerTitle or name of w is playerTitle then
                set bounds of w to {0, 25, midpoint, screenHeight}
                set foundPlayer to true
            else if custom title of selected tab of w is wizardTitle or name of w is wizardTitle then
                set bounds of w to {midpoint, 25, screenWidth, screenHeight}
                set foundWizard to true
            end if
        end repeat
    end tell
    if not (foundPlayer and foundWizard) then error "Terminal windows not found"
end run
'''


# Windows Terminal and the legacy WSL console both support Alt+Enter fullscreen.
# Only send it to a title-matched, borderless window covering the whole monitor.
WINDOWS_LAYOUT = r'''
param($PlayerTitle, $WizardTitle)
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class FightWindows {
  public delegate bool Callback(IntPtr w, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Callback cb, IntPtr p);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr w, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr w, out Rect r);
  [DllImport("user32.dll")] public static extern int GetWindowLong(IntPtr w, int index);
  [DllImport("user32.dll")] public static extern IntPtr MonitorFromWindow(IntPtr w, int flags);
  [DllImport("user32.dll")] public static extern bool GetMonitorInfo(IntPtr m, ref MonitorInfo i);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr w, int n);
  [DllImport("user32.dll")] public static extern bool MoveWindow(IntPtr w, int x, int y, int width, int height, bool repaint);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr w);
  [DllImport("user32.dll")] public static extern void keybd_event(byte key, byte scan, int flags, IntPtr extra);
  [StructLayout(LayoutKind.Sequential)] public struct Rect { public int Left, Top, Right, Bottom; }
  [StructLayout(LayoutKind.Sequential)] public struct MonitorInfo { public int Size; public Rect Monitor, Work; public int Flags; }
}
'@
$script:player = [IntPtr]::Zero
$script:wizard = [IntPtr]::Zero
$callback = [FightWindows+Callback] {
  param($w, $unused)
  $title = New-Object System.Text.StringBuilder 1024
  [void][FightWindows]::GetWindowText($w, $title, 1024)
  if ($title.ToString() -ceq $PlayerTitle) { $script:player = $w }
  if ($title.ToString() -ceq $WizardTitle) { $script:wizard = $w }
  return $true
}
[void][FightWindows]::EnumWindows($callback, [IntPtr]::Zero)
if ($player -eq [IntPtr]::Zero -or $wizard -eq [IntPtr]::Zero) { exit 1 }
$info = New-Object FightWindows+MonitorInfo
$info.Size = [Runtime.InteropServices.Marshal]::SizeOf($info)
[void][FightWindows]::GetMonitorInfo([FightWindows]::MonitorFromWindow($player, 2), [ref]$info)
foreach ($w in @($player, $wizard)) {
  $rect = New-Object FightWindows+Rect
  [void][FightWindows]::GetWindowRect($w, [ref]$rect)
  $borderless = ([FightWindows]::GetWindowLong($w, -16) -band 0x00C00000) -eq 0
  if ($borderless -and $rect.Left -le $info.Monitor.Left -and $rect.Right -ge $info.Monitor.Right -and
      $rect.Top -le $info.Monitor.Top -and $rect.Bottom -ge $info.Monitor.Bottom) {
    if (-not [FightWindows]::SetForegroundWindow($w)) { exit 1 }
    [FightWindows]::keybd_event(0x12, 0, 0, [IntPtr]::Zero)
    [FightWindows]::keybd_event(0x0D, 0, 0, [IntPtr]::Zero)
    [FightWindows]::keybd_event(0x0D, 0, 2, [IntPtr]::Zero)
    [FightWindows]::keybd_event(0x12, 0, 2, [IntPtr]::Zero)
    Start-Sleep -Milliseconds 300
  }
  [void][FightWindows]::ShowWindow($w, 9)
}
$area = $info.Work
$half = [int](($area.Right - $area.Left) / 2)
$height = $area.Bottom - $area.Top
if (-not [FightWindows]::MoveWindow($player, $area.Left, $area.Top, $half, $height, $true)) { exit 1 }
if (-not [FightWindows]::MoveWindow($wizard, $area.Left + $half, $area.Top, $area.Right - $area.Left - $half, $height, $true)) { exit 1 }
[void][FightWindows]::SetForegroundWindow($player)
'''


def _run(command: list[str], timeout: float = 3.0) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=timeout).stdout


MAC_WINDOW_ACTION = r'''
on run argv
    set targetTitle to item 1 of argv
    set requestedAction to item 2 of argv
    tell application "Terminal"
        repeat with w in windows
            -- Terminal can append a shell name and dimensions to the window
            -- name. Compare its exact tab title, never a partial window name.
            if custom title of selected tab of w is targetTitle or name of w is targetTitle then
                if requestedAction is "close" then
                    close w
                else
                    set index of w to 1
                    activate
                end if
                return "found"
            end if
        end repeat
    end tell
    return "absent"
end run
'''


WINDOWS_WINDOW_ACTION = r'''
param($TargetTitle, $RequestedAction)
Add-Type -TypeDefinition @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public class OwnedFightWindow {
  public delegate bool Callback(IntPtr w, IntPtr p);
  [DllImport("user32.dll")] public static extern bool EnumWindows(Callback cb, IntPtr p);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr w, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr w, uint message, IntPtr wparam, IntPtr lparam);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr w, int n);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr w);
}
'@
$script:target = [IntPtr]::Zero
$callback = [OwnedFightWindow+Callback] {
  param($w, $unused)
  $title = New-Object System.Text.StringBuilder 1024
  [void][OwnedFightWindow]::GetWindowText($w, $title, 1024)
  if ($title.ToString() -ceq $TargetTitle) { $script:target = $w; return $false }
  return $true
}
[void][OwnedFightWindow]::EnumWindows($callback, [IntPtr]::Zero)
if ($target -eq [IntPtr]::Zero) { Write-Output 'absent'; exit 0 }
if ($RequestedAction -eq 'close') {
  if (-not [OwnedFightWindow]::PostMessage($target, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) { exit 1 }
} else {
  [void][OwnedFightWindow]::ShowWindow($target, 9)
  if (-not [OwnedFightWindow]::SetForegroundWindow($target)) { exit 1 }
}
Write-Output 'found'
'''


def _is_wsl() -> bool:
    return bool(os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().lower())


def _window_action(role: str, token: str, action: str) -> bool:
    """Bound desktop calls and return False when no supported automation exists."""
    title = window_title(role, token)
    try:
        if _is_wsl():
            import base64
            script = WINDOWS_WINDOW_ACTION.replace("param($TargetTitle, $RequestedAction)",
                f"$TargetTitle = '{title}'; $RequestedAction = '{action}'")
            encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
            result = _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], 4)
            return action == "close" or result.strip() == "found"
        if platform.system() == "Darwin":
            result = _run(["osascript", "-e", MAC_WINDOW_ACTION, title, action], 4)
            return action == "close" or result.strip() == "found"
        if os.environ.get("XDG_SESSION_TYPE") != "wayland" and shutil.which("wmctrl"):
            windows = [line.split(None, 3) for line in _run(["wmctrl", "-l"]).splitlines()]
            window = next((fields[0] for fields in windows if len(fields) == 4 and fields[3] == title), None)
            if window is None:
                return action == "close"  # Already closed is a successful close.
            _run(["wmctrl", "-ic" if action == "close" else "-ia", window])
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    return False


def close_owned_window(role: str, token: str) -> bool:
    """Close only the exact game-owned window; callers own the player flag."""
    return _window_action(role, token, "close")


def focus_player(token: str) -> bool:
    """Return focus to the matching player, including an existing shell."""
    return _window_action("player", token, "focus")


def schedule_player_close(token: str) -> bool:
    """Close a launcher-owned terminal after the game has fully exited.

    A separate, short-lived helper avoids the terminal's running-process prompt.
    The caller must check --owned-window before scheduling it.
    """
    window_title("player", token)
    try:
        subprocess.Popen(
            [sys.executable, "-B", str(Path(__file__).resolve()), "--close-player", token,
             "--after-pid", str(os.getpid())],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True, close_fds=True,
        )
    except OSError:
        return False
    return True


def _process_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)  # Signal zero queries existence; it sends no signal.
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    return True


def _close_player_after_exit(token: str, pid: int) -> None:
    window_title("player", token)
    if pid <= 0:
        raise ValueError("Invalid game process identity")
    deadline = time.monotonic() + 5
    while _process_alive(pid):
        if time.monotonic() >= deadline:
            return
        time.sleep(0.05)
    close_owned_window("player", token)


def _tile_x11(player_title: str, wizard_title: str) -> None:
    windows = _run(["wmctrl", "-lG"]).splitlines()
    ids = []
    for title in (player_title, wizard_title):
        window = next((line.split()[0] for line in windows
                       if len(line.split(None, 7)) == 8 and line.split(None, 7)[7] == title), None)
        if window is None:
            raise OSError("Waiting for terminal window titles")
        ids.append(window)
    desktop = next(line for line in _run(["wmctrl", "-d"]).splitlines() if " * " in line)
    fields = desktop.split()
    area = fields.index("WA:")
    x, y = map(int, fields[area + 1].split(","))
    width, height = map(int, fields[area + 2].split("x"))
    # On a multi-monitor desktop use the monitor containing the player, rather
    # than splitting the entire virtual desktop across both displays.
    if shutil.which("xrandr"):
        try:
            player = next(line.split() for line in windows if line.startswith(ids[0]))
            cx, cy = int(player[2]) + int(player[4]) // 2, int(player[3]) + int(player[5]) // 2
            monitors = _run(["xrandr", "--listactivemonitors"])
            for mw, mh, mx, my in re.findall(r"(\d+)/\d+x(\d+)/\d+([+-]\d+)([+-]\d+)", monitors):
                mw, mh, mx, my = map(int, (mw, mh, mx, my))
                if mx <= cx < mx + mw and my <= cy < my + mh:
                    right, bottom = min(x + width, mx + mw), min(y + height, my + mh)
                    x, y = max(x, mx), max(y, my)
                    width, height = right - x, bottom - y
                    break
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    for window in ids:
        _run(["wmctrl", "-ir", window, "-b", "remove,fullscreen"])
        _run(["wmctrl", "-ir", window, "-b", "remove,maximized_vert,maximized_horz"])
    time.sleep(0.15)  # Let the WM restore decorations before measuring them.
    for index, window in enumerate(ids):
        left = x + index * (width // 2)
        half = width // 2 if index == 0 else width - width // 2
        border_x = border_y = 0
        if shutil.which("xprop"):
            try:
                result = _run(["xprop", "-id", window, "_NET_FRAME_EXTENTS"])
                borders = list(map(int, result.split("=", 1)[1].split(",")))
                border_x, border_y = sum(borders[:2]), sum(borders[2:])
            except (OSError, subprocess.SubprocessError, ValueError, IndexError):
                pass
        _run(["wmctrl", "-ir", window, "-e",
              f"0,{left},{y},{max(1, half - border_x)},{max(1, height - border_y)}"])
    _run(["wmctrl", "-ia", ids[0]])


class WindowPair:
    """Desktop automation runs off the keyboard/event loop and may fail harmlessly."""

    def __init__(self, port: int, token: str) -> None:
        self.events: queue.SimpleQueue[tuple[str, str]] = queue.SimpleQueue()
        self.closed = threading.Event()
        self.finishing = threading.Event()
        self.thread = threading.Thread(target=self._open, args=(port, token), daemon=True)
        self.thread.start()

    def _open(self, port: int, token: str) -> None:
        try:
            command, env = launch_command(port, token)
            if self.closed.is_set():
                return
            # Terminal launchers may return before their window closes. The TCP
            # connection, rather than this helper's PID, owns the wizard lifetime.
            subprocess.Popen(command, cwd=PROJECT, env=env, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError as error:
            self.events.put(("error", str(error)))

    def arrange(self, token: str) -> None:
        threading.Thread(target=self._arrange, args=(token,), daemon=True).start()

    def _arrange(self, token: str) -> None:
        player, wizard = window_title("player", token), window_title("wizard", token)
        for _ in range(8):
            if self.closed.wait(0.25):
                return
            try:
                if os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().lower():
                    import base64
                    # -EncodedCommand avoids POSIX/Windows shell quote translation.
                    script = WINDOWS_LAYOUT.replace("param($PlayerTitle, $WizardTitle)",
                        f"$PlayerTitle = '{player}'; $WizardTitle = '{wizard}'")
                    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
                    _run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded], 8)
                elif platform.system() == "Darwin":
                    _run(["osascript", "-e", MAC_LAYOUT, player, wizard], 8)
                elif os.environ.get("XDG_SESSION_TYPE") != "wayland" and shutil.which("wmctrl"):
                    _tile_x11(player, wizard)
                else:
                    break
            except (OSError, subprocess.SubprocessError, ValueError, StopIteration):
                continue
            self.events.put(("layout", ""))
            return
        self.events.put(("layout", MANUAL_LAYOUT))

    def finish_wizard(self, token: str) -> None:
        """Only one ending worker may close the wizard and return player focus."""
        if self.finishing.is_set():
            return
        self.finishing.set()
        threading.Thread(target=self._finish_wizard, args=(token,), daemon=True).start()

    def _finish_wizard(self, token: str) -> None:
        details = []
        try:
            # Let the wizard consume shutdown and restore its tty before a WM
            # close request, including profiles which keep exited tabs open.
            time.sleep(0.15)
            if not close_owned_window("wizard", token):
                details.append("Close the wizard window manually if it remains open.")
            if not focus_player(token):
                details.append("Select the player's terminal to continue.")
        finally:
            # A missing desktop API must never strand the game in its ending.
            self.events.put(("wizard_closed", " ".join(details)))

    def close(self) -> None:
        self.closed.set()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Close a game-owned player terminal after exit.")
    parser.add_argument("--close-player", required=True)
    parser.add_argument("--after-pid", required=True, type=int)
    args = parser.parse_args()
    _close_player_after_exit(args.close_player, args.after_pid)
