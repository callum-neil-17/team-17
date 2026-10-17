from .level import Level


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
      ||
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
      ||
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
      ||
"""
]

# Fixed positions and staggered phases keep the stars still as they twinkle.
# Coordinates stay outside the wizard's silhouette.
STARS = (
    (3, 1, 0), (12, 0, 2), (7, 4, 4), (15, 7, 1),
    (2, 11, 3), (10, 14, 0), (5, 18, 2), (15, 20, 4),
    (56, 0, 1), (64, 3, 3), (54, 6, 0), (62, 9, 2),
    (57, 12, 4), (65, 15, 1), (54, 18, 3), (62, 20, 0),
)


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
        self.idle_frame_delay = 0.4

    def art(self, frame: int) -> str:
        wizard = super().art(frame).splitlines()
        width = 68
        wizard_width = max(len(line) for pose in WIZARD for line in pose.strip("\n").splitlines())
        left = (width - wizard_width) // 2
        canvas = [list(" " * width) for _ in wizard]
        for row, line in enumerate(wizard):
            canvas[row][left:left + len(line)] = line

        phases = " .+*+. "
        for column, row, offset in STARS:
            if canvas[row][column] == " ":
                canvas[row][column] = phases[(self.idle_frame + frame + offset) % len(phases)]

        # Keep the width fixed so centring doesn't shift as stars disappear.
        return "\n".join("".join(row) for row in canvas)
