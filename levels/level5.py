from .level import Level


ATM_FRAMES = [
    r"""
+------------------------------+
|        BANK OF CACHE         |
|------------------------------|
|    +--------------------+    |
|    |                    |    |
|    |         p          |    |
|    |                    |    |
|    +--------------------+    |
|                              |
|    1 2 3         [CARD]      |
|    4 5 6                     |
|    7 8 9                     |
|      0     [____________]    |
|                              |
+------------------------------+
""",
    r"""
+------------------------------+
|        BANK OF CACHE         |
|------------------------------|
|    +--------------------+    |
|    |                    |    |
|    |         P          |    |
|    |                    |    |
|    +--------------------+    |
|                              |
|    1 2 3         [CARD]      |
|    4 5 6                     |
|    7 8 9                     |
|      0     [____________]    |
|                              |
+------------------------------+
""",
]


class Level5(Level):
    def __init__(self) -> None:
        super().__init__(
            number=5,
            title="Level 5",
            required_input=("P",),  # Ctrl+C is a raw input byte.
            art=ATM_FRAMES,
            description="You need some money to pay the tab, so you head to an ATM.",
            prompt="Broke? Raise some capital.",
        )
        self.frame_delay = 3.0
