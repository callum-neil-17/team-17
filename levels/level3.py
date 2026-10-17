from textwrap import fill

from .level import Level


BAR_FRAMES = [
    r"""
+--------------------------------------------------------------+
|                           THE BAR                            |
|--------------------------------------------------------------|
|    _     _     _                           _     _     _     |
|   / \   / \   / \                         / \   / \   / \    |
|___|_|___|_|___|_|_________________________|_|___|_|___|_|____|
|    _     _               .----.                              |
|   / \   / \              |o  o|                              |
|___|_|___|_|___           | -- |                              |
|                       ___'----'___                           |
|                      /   |    |   \                          |
+==============================================================+
|                                                              |
+--------------------------------------------------------------+
        ______              ______              ______
       |______|            |______|            |______|
         |  |                |  |                |  |
        _|__|_              _|__|_              _|__|_
""",
    r"""
+--------------------------------------------------------------+
|                           THE BAR                            |
|--------------------------------------------------------------|
|    _     _     _                           _     _     _     |
|   / \   / \   / \                         / \   / \   / \    |
|___|_|___|_|___|_|_________________________|_|___|_|___|_|____|
|    _     _               .----.                              |
|   / \   / \              |o  o|                              |
|___|_|___|_|___           | -- |      .---.   +-----+         |
|                       ___'----'___   |~~~|)  |BILL |         |
|                      /   |    |   \  '---'   +-----+         |
+==============================================================+
|                                                              |
+--------------------------------------------------------------+
        ______              ______              ______
       |______|            |______|            |______|
         |  |                |  |                |  |
        _|__|_              _|__|_              _|__|_
""",
]


class Level3(Level):
    def __init__(self) -> None:
        super().__init__(
            number=3,
            title="Level 3",
            required_input=("\t",),
            art=BAR_FRAMES,
            description="You have entered a bar located on the planet cache. You currently do not have any money",
            prompt=fill(
                'Bartender: "Staying for a few drinks? '
                'Do you want to pay now or pay later? ',
                width=70,
            ),
        )
        self.solved = False
        self.frame_delay = 3.0

    def check_input(self, key: str) -> bool:
        if not super().check_input(key):
            return False
        if self.solved:
            return True

        self.solved = True

        # Play the drink and bill frame, then advance without another key.
        return True
