# team-17
Hackathon Team 17.

Created a riddle based puzzle game where each level can be solved by pressing a maximum of two inputs. 

Each Level will have a different key or key combination required to proceed, you must complete all levels to escape the terminal.

Start the game from the project folder with `python3 launcher.py`.

The Python code is grouped by feature:

```text
game.py                 Main input loop and level progression
launcher.py             Opens the game terminal
terminal_input.py       Reads complete terminal key events
levels/                 Level classes, clues and ASCII artwork
fight/
    controller.py       Player-owned fight state and socket communication
    effects.py          Player poses and wizard animations
    windows.py          Opens, positions and closes fight windows
    wizard.py           Wizard display process
ending/
    controller.py       Final twist and ending progression
    effects.py          Fake shell, glitches and final screen
    windows.py          Ending window and process management
    window.py           Ending display process
    config.py           Popup limits and timing
    callback_art.py     Artwork recalled during the ending
tests/                  Automated game checks
```

To use the current terminal instead, run `python3 game.py`. The existing
shortcuts still work: `python3 game.py --fight`, `--ending`, or `--finale`.
The launcher accepts the same shortcuts.

Child terminals launch package modules with `python3 -m fight.wizard` or
`python3 -m ending.window`, passing their connection details automatically.

Run the tests from the project folder:

```sh
python3.12 -m unittest discover -s tests
```
