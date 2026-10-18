# team-17
Hackathon Team 17.

Use Python 3.12 in a terminal on Linux Mint, macOS, or Ubuntu in WSL.

Run directly in the current terminal:

```sh
python3.12 game.py
```

To open a separate fullscreen window using the platform-specific launcher:

```sh
python3.12 launcher.py
```

No extra Python packages are required. If using a virtual environment, activate
it and run `python launcher.py`; Linux, macOS and WSL children use that active
Python executable. On Windows, run the launcher inside your WSL distribution;
Windows Terminal and all game processes use that same distribution and project
directory. A launcher run from native Windows uses the configured default WSL
distribution and its `python3.12`. On macOS, approve Automation prompts and grant
Accessibility permission to the app running the launcher if requested.

Solve the puzzles through Level 11, then continue through the Escape screen
and the final twist.
During gameplay, `q` and ordinary terminal quit/suspend shortcuts stay ignored.
Control keys can be puzzle input: Ctrl+Z solves Level 11 without suspending the
process. The epilogue waits for Escape; Escape begins the false exit below.
Ctrl+C stays ignored during the finale, including its animations. The false
shell waits for End and the final animation finishes automatically. Level 12
remains available as a template file, but the finished
wizard fight leads directly to the epilogue and finale.

Wrong guesses in Levels 1-11 trigger brief animations in the ASCII drawings:
the door rattles, the bartender reacts, the ATM flickers, and other objects
move within their scenes. These reactions add no dialogue and do not advance the puzzle.
Repeated keys cannot restart an animation while it is playing; correct answers
interrupt it immediately and play the usual success sequence. During the
fight, both the player and the wizard react locally to one socket event.
Edit the frames passed as `wrong_frames` in each level file to change its
reaction artwork; `wrong_frame_delay` controls its timing independently of the
success animation.

The scenes follow a connected story: the drink leads to an unpaid bar tab,
the ATM provides the payment, and the MMU book reveals the bus destination
127.0.0.1. Each scene shows its own artwork without carried-item displays.

During the final wizard-copy breakdown, the earlier mug, paid tab and MMU
book briefly reappear as memories, then fragment and disappear before
`WIZARD_PROCESS_NOT_FOUND` and `THE END`. The callback is shared by real panic
windows and the inline fallback, without adding time or another key press.
`callback_art.py` holds the small drawings used only by this final callback.

Level 1 has a gently blinking star field around the wizard while it waits for
input. Star positions stay fixed and their brightness changes every 0.4 seconds.
The wizard artwork shared with the final fight stays the same.

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
`levels/level5.py`. Shift+C raises the displayed lowercase letter to a
capital, then plays the cash withdrawal animation before advancing to Level 6.

Level 6 returns to the same bar as Level 3. Ctrl+W makes the player hand over
100 credits, then the bartender marks the balance paid and closes the tab.
Its payment frames and text are in `levels/level6.py`; they reuse Level 3's
bar artwork. The finished scene stays visible for 1.2 seconds before advancing
automatically to Level 7. The whole payment animation takes about 2.45 seconds.

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
epilogue displays "There's only one way to leave the terminal." while the
terminal appears to fall apart. Its border cracks, sections slip downward and
ASCII code fragments fall into a heap around the readable clue and blinking
cursor. The collapse builds over a few seconds, then continues with drifting
debris until Escape. These are scripted effects at 12 FPS; Escape (`\x1b`)
works throughout, and End, arrow and function-key escape sequences do not count
as a standalone Escape.
The player has ready, recoil and victory poses, with a face, outfit, hands and
boots. Effects use bounded frames at 30 FPS; `NO_COLOR=1` disables their colour.

To test just Level 11 and its ending in an existing shell:

```sh
python3.12 game.py --ending
```

Press Ctrl+Z once to send the spell, watch the death sequence, then press Escape
to reach the false shell. Solve that puzzle with End to finish the game.
To also test launcher-owned player-window closure:

```sh
python3.12 launcher.py --ending
```

The launcher passes a unique window token and ownership flag. After the finale,
terminal settings are restored before a detached helper closes only that owned
player window after its game process exits. The helper never kills an entire
terminal application or targets generic window titles. Wizard windows always
belong to the game. On desktops without window automation, normal terminal
exit-on-command-completion behavior closes them; a profile configured to keep
exited windows open may need manual closure.

The false exit opens its own real terminal while the original game process
stays in control. It shows a successful exit, a prompt based on the local user,
hostname, directory and shell, and a blinking cursor. After a short pause, the
wizard types: "You managed to escape my curse, but you will never put an end
to me." This prompt never executes commands. Press the **End key** to solve it;
typing the letters `end` does nothing. Closing this fake terminal reopens the
same puzzle at most twice, with "Closing a window won't end me." Closing the
third instance exits. Ctrl+C in the original or any finale terminal is ignored
without pausing the animation. Closing the original game window still stops
the game and cleans up its children.

End immediately disables reopening. The cursor freezes, the clue fragments,
and fictional tracebacks build over 2.5 seconds. The fake shell closes and up
to ten real wizard terminals appear in a staggered burst. Each uses the existing
wizard drawing before torn rows, offset ghost outlines, binary fragments and
error trails break it apart. Their panic lasts
about eight seconds overall; copies close in sequence. Once cleanup completes,
the original terminal comes forward where supported, stays blank for 0.75
seconds, then shows `THE END` for two seconds. Direct execution returns to the
existing real shell and preserves its window. Only launcher-owned player
windows close automatically.

To test just the new twist, without replaying the fight:

```sh
python3.12 game.py --finale
```

Or use `python3.12 launcher.py --finale` to test the dedicated player-window
lifecycle. To force the complete single-terminal fallback:

```sh
python3.12 game.py --finale --inline-ending
```

The fallback keeps the same End solution, fake crash, eight-second panic and
true ending, drawing ten overlapping fake terminal panels. It is selected
automatically if a window cannot launch or its connection/closure cannot be
established reliably. On Linux, the extra ending windows require an X11
session, GNOME Terminal or xterm, and `wmctrl`; Wayland and desktops without
those tools use the fallback. On macOS, Terminal Automation permissions are
needed for extra windows and exact-title closure. WSL uses the active
`WSL_DISTRO_NAME` and PowerShell for exact window cleanup. Placement and focus
are best effort; failure to focus never blocks completion. If desktop closure
fails after a window has opened, the game stops that owned child, continues
inline, and asks you to close any retained ending windows manually.

The decoder accepts common End encodings: `ESC[F`, `ESCOF`, `ESC[4~` and
`ESC[8~`, including modifiers. It buffers split escape sequences before deciding
whether a lone Escape was pressed. On a MacBook, try **Fn+Right Arrow**; Apple
identifies this combination as End, but forwarding depends on terminal settings.
See [Apple's keyboard shortcuts](https://support.apple.com/en-us/102650).
If it scrolls instead, open **Terminal > Settings > Profiles > your active
profile > Keyboard** and add or edit End with modifier None to send `ESC[4~`:
an actual Escape byte followed by `[4~` (hex `1b 5b 34 7e`), not the letters
`ESC`. Other terminal apps have their own key mapping settings. See
[Apple's custom function key guide](https://support.apple.com/guide/terminal/create-custom-function-keys-trml108/mac).

During the fight, keyboard input is still polled. If the wizard
window cannot connect, stops responding or is closed, the player can press
Enter to retry. Closing the player window disconnects the wizard and ends it.
Raw mode is enabled once in `game.py` and restored in `finally`, including on
exceptions or termination signals. The wizard does not change terminal modes.
All game windows use the terminal's alternate screen so frames do not build
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
The new finale is separate: `ending.py` owns its state and authenticated local
TCP connection, `ending_window.py` displays each child, `ending_effects.py`
renders its bounded 12 FPS animations, `ending_windows.py` manages only its
token-labelled windows and verified child processes, and `terminal_input.py`
decodes buffered key events. Children never launch other game windows. Socket
messages coordinate scenes, input and health checks, rather than every frame.
Cleanup is idempotent; no controller or respawning service is left behind.

Run the standard-library checks with:

```sh
python3.12 -B -m unittest discover -s tests -v
```

These cover partial socket messages/writes, a real wizard subprocess in a PTY,
spell handoff, both Backspace encodings, one-action Ctrl+Z reversal and the full
wizard death, epilogue controls, safe owned-window closure, resizing,
disconnects, earlier-level progression and raw-mode cleanup after exceptions.
Finale checks cover split End/Escape decoding, inert shell input, the two-reopen
limit, ten-window cap, failed launches, socket timeouts, ignored Ctrl+C,
disconnected-parent cleanup, child/process ownership and complete inline
progression. `ending_config.py` shares the window limit and timing between
the controller, desktop manager and inline effects.
Linux Mint/Cinnamon X11 has also been checked with real terminal windows,
including wizard defeat, focus return, owned player-window closure, both
permitted fake-shell reopenings, ten simultaneous panic copies and cleanup after
completion or parent-window closure. Real PTY checks cover the full inline
ending, inert typed `end`, a split End sequence, the quiet final pause,
ignored Ctrl+C with continued playback, and exact terminal-settings restoration.
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
