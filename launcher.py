import os
import platform
import shlex
import subprocess
from pathlib import Path

project = Path(__file__).resolve().parent
python = project / ".venv" / "bin" / "python"

system = platform.system()

if system == "Windows":
    # Run the game using Ubuntu's Python environment.
    subprocess.Popen(
        [
            "wsl.exe",
            "--distribution", "Ubuntu",
            "--cd", str(project),
            "--exec", "./.venv/bin/python",
            "game.py",
        ],
        creationflags=subprocess.CREATE_NEW_CONSOLE,
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
    end run
    '''

    subprocess.run(
        ["osascript", "-e", script, command],
        check=True,
    )

else:
    raise SystemExit(f"Unsupported system: {system}")