# team-17
Hackathon Team 17.

Use Python 3.12 in a terminal on Linux Mint, macOS, or Ubuntu in WSL.

Run directly in the current terminal:

```sh
python3.12 game.py
```

To open a separate window using the existing platform-specific launcher, first
create the virtual environment if needed, then launch:

```sh
python3.12 -m venv .venv
python3.12 launcher.py
```

On Windows, the launcher uses Windows Terminal and the Ubuntu WSL distribution's
`.venv`; create that environment from Ubuntu first. On macOS, approve Automation
prompts and grant Accessibility permission to the app running the launcher if
requested.

Press Enter to advance through five levels. Other keys are ignored, except `q`
or Ctrl+C, which exit at any time. The completion screen stays visible until you
quit.

`levels/level.py` defines the shared `Level` class. Each of `levels/level1.py`
through `levels/level5.py` configures a separate level and can later override
`render()` or `check_input()`. Keyboard reading, terminal setup and restoration,
and progression remain in `game.py`.
