from .level import Level


class Level3(Level):
    def __init__(self) -> None:
        super().__init__(number=3, title="Level 3", required_input=("\r", "\n"))
