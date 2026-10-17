import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path

project = Path(__file__).resolve().parent
python = project / ".venv" / "bin" / "python"

system = platform.system()

if system == "Windows":
    terminal = shutil.which("wt.exe")
    if terminal is None:
        raise SystemExit(
            "Fullscreen launch requires Windows Terminal (wt.exe). "
            "Install it and enable its app execution alias."
        )

    # Open a new fullscreen window running Ubuntu's Python environment.
    subprocess.run(
        [
            terminal,
            "--window", "new",
            "--fullscreen",
            "new-tab",
            "--title", "Two Keys",
            "wsl.exe",
            "--distribution", "Ubuntu",
            "--cd", str(project),
            "--exec", "./.venv/bin/python",
            "game.py",
        ],
    )

elif system == "Linux" and "microsoft" in platform.release().lower():
    # WSL: open a native Windows console that runs the game back inside WSL.
    distro = os.environ.get("WSL_DISTRO_NAME", "Ubuntu")
    subprocess.Popen(
        [
            "cmd.exe", "/c", "start", "Two Keys",
            "wsl.exe",
            "--distribution", distro,
            "--cd", str(project),
            "--exec", "./.venv/bin/python",
            "game.py",
        ],
        cwd="/mnt/c",  # avoids cmd.exe's "UNC paths are not supported" warning
    )

elif system == "Linux":
    subprocess.Popen([
        "gnome-terminal",
        "--window",
        "--full-screen",
        "--title=Two Keys",
        f"--working-directory={project}",
        "--",
        str(python),
        "game.py",
    ])

elif system == "Darwin":  # macOS
    command = (
        f"cd {shlex.quote(str(project))} && "
        f"exec {shlex.quote(str(python))} game.py"
    )

    script = '''
    on run argv
        tell application "Terminal"
            do script (item 1 of argv)
            activate
        end tell
        -- Requires Accessibility permission for the app running this launcher.
        tell application "System Events"
            tell process "Terminal"
                set frontmost to true
                set value of attribute "AXFullScreen" of window 1 to true
            end tell
        end tell
    end run
    '''

    try:
        subprocess.run(
            ["osascript", "-e", script, command],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            "macOS Terminal automation failed. Allow the app running this "
            "launcher in System Settings > Privacy & Security > Accessibility, "
            "and approve any Automation prompts, then try again.\n"
            f"{error.stderr.strip()}"
        ) from error

else:
    raise SystemExit(f"Unsupported system: {system}")
