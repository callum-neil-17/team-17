from .level import Level


class Level10(Level):
    """The two-window fight is driven by game.py's live event loop."""

    def __init__(self) -> None:
        super().__init__(
            number=10,
            title="Level 10",
            required_input=("\x7f", "\x08"),  # Backspace varies between terminals.
            description="The wizard is enraged you cut the tree down and is now hurling spells at you.",
            prompt="Take a back step to dodge spell.",
        )
