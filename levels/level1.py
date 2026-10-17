from .level import Level


class Level1(Level):
    def __init__(self) -> None:
        super().__init__(number=1, title="Level 1", required_input=("\r", "\n"))
