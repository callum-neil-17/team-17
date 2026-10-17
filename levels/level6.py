from .level import Level

class Level6(Level):
    def __init__(self) -> None:
        super().__init__(
            number=6,
            title="Level 6",
            required_input=("\r", "\n"),
        )
