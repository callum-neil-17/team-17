from .level import Level


class Level4(Level):
    def __init__(self) -> None:
        super().__init__(number=4, title="Level 4", required_input=("\r", "\n"))
