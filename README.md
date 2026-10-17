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

Solve each level to advance through seven levels. Most current levels use Enter.
During gameplay, `q` and terminal control keys such as Ctrl+Z and Ctrl+D are
ignored. Ctrl+C is available as puzzle input and does not exit the game. After
completion, press `q` to quit; the completion screen stays visible until then.

On Level 2, Enter plays the door-opening frames once before advancing. Input is
ignored while the door opens. Frame playback and timing are handled in
`game.py`; the drawings are stored in `levels/level2.py`.

Level 3 is a bar puzzle with frames stored in `levels/level3.py`, like the door
frames in Level 2. Solving it displays a drink and a bill on the counter, then
automatically advances to Level 4. Frames last 0.7
seconds by default; the Level 3 response stays visible for 3 seconds.

Level 5 is the Bank of Cache ATM puzzle, with frames stored in
`levels/level5.py`. Solving it raises the displayed lowercase letter to a
capital, holds that frame for 3 seconds, then advances to Level 6.

Level 6 closes the bill with a cheque that gets ticked off before Level 7.
Its frames and text are in `levels/level6.py`. The checked cheque stays visible
for 3 seconds before advancing.

Level 7 shows a Memory Management Unit (MMU) book lying on a table. Its artwork
is stored in `BOOK_FRAMES` in `levels/level7.py`. The `description=` and `prompt=`
strings are blank for you to fill in. Enter is the temporary continue key;
change `required_input=` when you choose its puzzle. Completing Level 7 shows
the final completion screen.

`levels/level.py` defines the shared `Level` class. Each of `levels/level1.py`
through `levels/level5.py` configures a separate level and can later override
`render()` or `check_input()`. Keyboard reading, terminal setup and restoration,
and progression remain in `game.py`.

Each screen is centered using the current terminal size whenever it is rendered.
Separate titles, art and prompts with a blank line to center each section
independently. Lines within each art section keep their relative indentation.
Content larger than the window starts at the top or left edge; enlarge the
terminal to see it fully.

To describe a level's background, pass `description=` when constructing it. For
example, Level 3 uses `description="A quiet bar waits in the warm light."`.
The description is rendered above that level's title; edit the string in the
level file whenever you want different text.
