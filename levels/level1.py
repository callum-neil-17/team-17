from .level import Level


class Level1(Level):
    def __init__(self) -> None:
        super().__init__(number=1, title="Level 1", required_input=("\r", "\n"))

WIZARD = [
    r"""
        *         _,-'|    .
               ,-'._  |
     .||,      |####\ |       *
    \.`',/     \####| |   .
    = ,. =      |###| |
    / || \    ,-'\#/,'`.    *
      ||     ,'   `,,. `.
      ,|____,' , ,;' \| |
     (3|\    _/|/'   _| | .
      ||/,-''  | >-'' _,\\
      ||'      ==\ ,-'  ,'
      ||       |  V \ ,|     *
      ||       |    |` |
      ||       |    |   \
      ||       |    \    \
      ||       |     |    \
      ||       |      \_,-'
      ||       |___,,--")_\
      ||         |_|   ccc/
      ||        ccc/
      ||                hjm
""",
    r"""
      \ | /       _,-'|  *
    -- * --    ,-'._  |      .
      / | \    |####\ |  *
       ||      \####| |
       ||       |###| |    +
       ||     ,-'\#/,'`.
       ||    ,'   `,,. `.       *
       ||___,' , ,;' \| |
      (3|    _/|/'   _| |
      ||/,-''  | >-'' _,\\   .
      ||'      ==\ ,-'  ,'
      ||       |  V \ ,|
      ||       |    |` |
      ||       |    |   \   *
      ||       |    \    \
      ||       |     |    \
      ||       |      \_,-'
      ||       |___,,--")_\
      ||         |_|   ccc/
      ||        ccc/
      ||                hjm
""",
    r"""
    .             _,-'|     +
          *    ,-'._  |
       _       |####\ | *
     /   \     \####| |
     \ * /      |###| |      .
      \ /     ,-'\#/,'`.
       ||    ,'   `,,. `. *
       ||___,' , ,;' \| |
     (3|\    _/|/'   _| |       *
      ||/,-''  | >-'' _,\\
      ||'      ==\ ,-'  ,'
      ||       |  V \ ,|  .
      ||       |    |` |
      ||       |    |   \
      ||       |    \    \      *
      ||       |     |    \
      ||       |      \_,-'
      ||       |___,,--")_\
      ||         |_|   ccc/
      ||        ccc/
      ||                hjm
"""
]

class Level1(Level):
    def __init__(self) -> None:
        super().__init__(
            number=1,
            title="Level 1",
            required_input=("y", "\n"),
            art=WIZARD,
            prompt="I have trapped You in the terminal. You cannot esc. You must solve each riddle using an input(/s) on your keypad. Press 'Y' to continue ",
        )
        self.layout = "level2"