from .level import Level


# The shoulders and boots stay in place while the player raises both palms.
# These are separate from the successful dodge and victory animations.
_PLAYER_SHRUG = r"""
        .----.
        |____|
        | - -|>
        |  ~ /
     .--`---'--.
 (o)_/ |=====| \_(o)
       |  :  |
       |_____|
       /  |  \
      /___|___\
     /___/ \___\
    [____] [____]
""".strip("\n")
PLAYER_WRONG_FRAMES = [
    _PLAYER_SHRUG,
    _PLAYER_SHRUG.replace("| - -|>", "| > >|>"),
    _PLAYER_SHRUG.replace("| - -|>", "| < <|>"),
    _PLAYER_SHRUG,
]


class Level10(Level):
    """The two-window fight is driven by game.py's live event loop."""

    def __init__(self) -> None:
        super().__init__(
            number=10,
            title="Level 10",
            required_input=("\x7f", "\x08"),  # Backspace varies between terminals.
            description="The wizard is enraged you cut the tree down and is now hurling spells at you.",
            prompt="Take a back step to dodge spell.",
            wrong_frames=PLAYER_WRONG_FRAMES,
        )
