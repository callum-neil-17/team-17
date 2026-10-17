"""Open a game-owned terminal, preserving an existing shell for direct launches."""

import argparse
import os
import platform
import secrets
import shlex
import shutil
import subprocess
from pathlib import Path


project = Path(__file__).resolve().parent
python = project / ".venv" / "bin" / "python"


def launch(mode: str | None = None) -> None:
    token = secrets.token_hex(16)
    title = f"Two Keys Player {token}"
    game_args = ["game.py", "--owned-window", "--window-token", token]
    if mode:
        game_args.append(mode)
    system = platform.system()

    if system == "Windows":
        terminal = shutil.which("wt.exe")
        if terminal is None:
            raise SystemExit(
                "Fullscreen launch requires Windows Terminal (wt.exe). "
                "Install it and enable its app execution alias."
            )
        subprocess.run([
            terminal, "--window", "new", "--fullscreen", "new-tab",
            "--title", title, "--suppressApplicationTitle", "wsl.exe",
            "--distribution", os.environ.get("WSL_DISTRO_NAME", "Ubuntu"),
            "--cd", str(project), "--exec", "./.venv/bin/python", *game_args,
        ])

    elif system == "Linux" and (os.environ.get("WSL_DISTRO_NAME") or "microsoft" in platform.release().lower()):
        # Both the player and later wizard must use this exact distribution.
        distro = os.environ.get("WSL_DISTRO_NAME", "Ubuntu")
        wsl = ["wsl.exe", "--distribution", distro, "--cd", str(project),
               "--exec", "./.venv/bin/python", *game_args]
        terminal = shutil.which("wt.exe")
        if terminal:
            command = [terminal, "--window", "new", "--fullscreen", "new-tab",
                       "--title", title, "--suppressApplicationTitle", *wsl]
        else:
            command = ["cmd.exe", "/c", "start", title, *wsl]
        subprocess.run(command, cwd="/mnt/c", stdin=subprocess.DEVNULL)

    elif system == "Linux":
        # A new window must not inherit references to an old GNOME screen.
        launch_env = os.environ.copy()
        launch_env.pop("GNOME_TERMINAL_SCREEN", None)
        launch_env.pop("GNOME_TERMINAL_SERVICE", None)
        subprocess.Popen([
            "gnome-terminal", "--window", "--full-screen", f"--title={title}",
            f"--working-directory={project}", "--", str(python), *game_args,
        ], env=launch_env)

    elif system == "Darwin":
        command = f"cd {shlex.quote(str(project))} && exec {shlex.join([str(python), *game_args])}"
        script = '''
        on run argv
            tell application "Terminal"
                set gameTab to do script (item 1 of argv)
                set custom title of gameTab to (item 2 of argv)
                activate
            end tell
            -- Existing fullscreen behaviour requires Accessibility permission.
            tell application "System Events"
                tell process "Terminal"
                    set frontmost to true
                    set value of attribute "AXFullScreen" of window 1 to true
                end tell
            end tell
        end run
        '''
        try:
            subprocess.run(["osascript", "-e", script, command, title], check=True,
                           capture_output=True, text=True)
        except subprocess.CalledProcessError as error:
            raise SystemExit(
                "macOS Terminal automation failed. Allow the app running this "
                "launcher in System Settings > Privacy & Security > Accessibility, "
                "and approve any Automation prompts, then try again.\n"
                f"{error.stderr.strip()}"
            ) from error
    else:
        raise SystemExit(f"Unsupported system: {system}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    direct = parser.add_mutually_exclusive_group()
    direct.add_argument("--fight", action="store_true", help="Start at Level 10")
    direct.add_argument("--ending", action="store_true", help="Start at Level 11")
    args = parser.parse_args()
    launch("--ending" if args.ending else "--fight" if args.fight else None)


if __name__ == "__main__":
    main()
