from .level import Level


class Level2(Level):
    def __init__(self) -> None:
        super().__init__(number=2, title="Level 2", required_input=("\r", "\n"))
