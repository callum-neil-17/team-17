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

Solve the puzzles through Level 11, then leave through the ending screen.
During gameplay, `q` and ordinary terminal quit/suspend shortcuts stay ignored.
Control keys can be puzzle input: Ctrl+Z solves Level 11 without suspending the
process. The final epilogue waits for Escape. Level 12 remains available as a
template file, but the finished wizard fight leads directly to the epilogue.

On Level 2, Enter plays the door-opening frames once before advancing. Input is
ignored while the door opens. Frame playback and timing are handled in
`game.py`; the drawings are stored in `levels/level2.py`.

Level 3 is a bar puzzle with 13 frames stored in `levels/level3.py`, like the
door frames in Level 2. The scene includes lamps, stocked shelves, a bartender,
a panelled counter and stools. Solving it makes the bartender pick up a bottle,
pour a foamy drink and slide it across the counter. The serving frames last
0.2 seconds; the finished scene stays visible for 0.6 seconds before
automatically advancing to Level 4, for a total of about 2.8 seconds.
Other levels keep their existing
timing, with a default frame delay of 0.7 seconds.

Level 5 is the Bank of Cache ATM puzzle, with frames stored in
`levels/level5.py`. Solving it raises the displayed lowercase letter to a
capital, holds that frame for 3 seconds, then advances to Level 6.

Level 6 closes the bill with a cheque that gets ticked off before Level 7.
Its frames and text are in `levels/level6.py`. The checked cheque stays visible
for 3 seconds before advancing.

Level 7 shows a Memory Management Unit (MMU) book lying on a table. Its artwork
is stored in `BOOK_FRAMES` in `levels/level7.py`. Ctrl+F opens the book and
advances to Level 8's bus journey. In Level 9, Ctrl+X cuts down the directory
tree; once its falling frames finish, Level 10 starts automatically.

Level 10 opens a separate wizard terminal and keeps the existing terminal for
the player. The wizard faces left, using the original Level 1 frames, and the
armoured player faces right. A stream of binary digits moves off the wizard
terminal's left edge, then enters the player terminal from the right. It stops
just before the player and waits for Backspace. The player screen says "Take a
back step to dodge spell." The wizard screen explains that he is enraged after
you cut the tree down and is now hurling spells at you. Backspace makes the
player step back and away from the spell's lane so it passes by. Both raw
Backspace encodings (`\x7f` and `\x08`) work; Enter does not solve this puzzle.
Each process animates locally;
newline-delimited JSON over an OS-assigned `127.0.0.1` TCP port coordinates
readiness, resizing, casting, handoff, dodging, level changes and shutdown. The player owns the fight
state and keyboard input.

To test the fight directly, bypassing earlier puzzles:

```sh
python3.12 game.py --fight
```

After the spell misses, the game automatically advances to Level 11 using the same two windows
and socket connection. The wizard waits without casting another projectile.
The clue is "Find a way to undo the wizard's spell trapping you in the
terminal." Ctrl+Z (`\x1a`) undoes the trapping spell and launches a green binary
stream from the player toward the wizard. One press is enough; an early press
is remembered until both windows are ready, and repeated presses cannot start
overlapping endings. The stream travels right through the player window, then
enters the wizard window from the left and strikes him. Both parts animate
locally, using socket handoff events. Routine spell-travel messages are hidden;
the level clue remains above the artwork.

The wizard's eight-second death sequence includes impact particles and a brief
amber flash, recoil, corrupted and missing body sections, falling fragments,
and increasingly dense simulated errors. Its final fatal frame is visible
before the wizard process exits and its actual terminal window closes. Focus
returns to the player, its terminal returns to fullscreen, and a separate
epilogue displays "There's only one way to
leave the terminal." with a
subtle blinking cursor. Escape (`\x1b`) exits; arrow-key escape sequences do not.
The player has ready, recoil and victory poses, with a face, outfit, hands and
boots. Effects use bounded frames at 30 FPS; `NO_COLOR=1` disables their colour.

To test just Level 11 and its ending in an existing shell:

```sh
python3.12 game.py --ending
```

Press Ctrl+Z once to send the spell, watch the death sequence, then press Escape.
Direct execution returns to that shell and never closes its terminal window.
To also test launcher-owned player-window closure:

```sh
python3.12 launcher.py --ending
```

The launcher passes a unique window token and ownership flag. After Escape,
terminal settings are restored before a detached helper closes only that owned
player window after its game process exits. The helper never kills an entire
terminal application or targets generic window titles. Wizard windows always
belong to the game. On desktops without window automation, normal terminal
exit-on-command-completion behavior closes them; a profile configured to keep
exited windows open may need manual closure.

During the fight, keyboard input is still polled. If the wizard
window cannot connect, stops responding or is closed, the player can press
Enter to retry. Closing the player window disconnects the wizard and ends it.
Raw mode is enabled once in `game.py` and restored in `finally`, including on
exceptions or termination signals. The wizard does not change terminal modes.
Both windows use the terminal's alternate screen so game frames do not build
up in scrollback. On exit, including after errors, the previous screen and
visible cursor are restored. Terminal-app scrolling shortcuts may still depend
on the terminal's own settings.

Window positioning is best effort and never replaces the two actual windows:

- Linux Mint/X11: GNOME Terminal (or xterm) opens the wizard window. If `wmctrl`
  is available, both windows leave fullscreen and move into the screen's left
  and right halves. Without desktop automation, including on Wayland, exit
  fullscreen with F11 and use the desktop's left/right tiling shortcuts or drag
  each window to its screen edge. No extra Python packages are needed.
- macOS: a second Terminal window opens using AppleScript. Positioning uses
  Terminal, Finder and System Events; existing Automation/Accessibility grants
  are required for automatic fullscreen exit and positioning. If denied or
  running the player in another terminal app, leave fullscreen using the green
  window button, then tile Player left and Wizard right using the window menu.
- Windows/WSL: the wizard starts inside the player's `WSL_DISTRO_NAME`, using
  the same Python executable and project directory. Windows Terminal opens
  a new window (with the existing `cmd.exe`/WSL approach as a fallback).
  PowerShell tries to leave fullscreen and position the two title-matched
  windows. If this is unavailable, use Alt+Enter to leave fullscreen, then
  Win+Left for Player and Win+Right for Wizard. The launcher still starts the
  original fullscreen game window as before. See the official
  [Windows Terminal CLI reference](https://learn.microsoft.com/en-us/windows/terminal/command-line-arguments).

Both terminals use the same spell glyph, speed and character row. Their
contents are clipped to the current terminal dimensions without line wrapping;
resizing updates the shared row. Use matching font sizes for the closest visual
alignment across the window boundary. Very small windows clip character art.
The player screen shows manual tiling instructions when automation fails.

The implementation lives in `fight.py` (player state, protocol and epilogue),
`wizard.py` (wizard display loop), `fight_effects.py` (poses and scripted death),
and `fight_windows.py` (window launching, placement and owned-window lifecycle).
`levels/level10.py` declares the dodge puzzle and `levels/level11.py` declares
the undo puzzle; `game.py` owns input, raw mode and the shared event loop.

Run the standard-library checks with:

```sh
python3.12 -B -m unittest discover -s tests -v
```

These cover partial socket messages/writes, a real wizard subprocess in a PTY,
spell handoff, both Backspace encodings, one-action Ctrl+Z reversal and the full
wizard death, epilogue controls, safe owned-window closure, resizing,
disconnects, earlier-level progression and raw-mode cleanup after exceptions.
Linux Mint/Cinnamon X11 has also been checked with real terminal windows,
including the full ending, focus return, automatic closure of a held-open
owned player window, and leaving a direct-launch terminal open after Escape.
macOS and Windows/WSL desktop automation require testing on those operating systems;
their launch and ownership command construction is covered by tests.

`levels/level.py` defines the shared `Level` class. Each of `levels/level1.py`
through `levels/level12.py` configures a separate level and can later override
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
