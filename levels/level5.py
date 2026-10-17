from .level import Level


class Level5(Level):
    def __init__(self) -> None:
        super().__init__(number=5, title="Level 5", required_input=("\r", "\n"))
