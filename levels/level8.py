from textwrap import fill

from .level import Level

# Bus driving to the 127.0.0.1 stop, one frame per string. The first frame shows
# while the player decides; the rest play after they press "." to stop.
BUS_FRAMES = [
    r"""
      ______________________                      .-----------.
 ==  | [_]  [_]  [_]  [_] | \                     | 127.0.0.1 |
  == |     MEMORY BUS     |  \                    '-----+-----'
 ==  |____________________|___|                         |
        (O)          (O)  (O)                           |
==================================================================
""",
    r"""
              ______________________              .-----------.
         ==  | [_]  [_]  [_]  [_] | \             | 127.0.0.1 |
          == |     MEMORY BUS     |  \            '-----+-----'
         ==  |____________________|___|                 |
                (O)          (O)  (O)                   |
==================================================================
""",
    r"""
                     ______________________       .-----------.
                    | [_]  [_]  [_]  [_] | \      | 127.0.0.1 |
                    |     MEMORY BUS     |  \     '-----+-----'
                    |____________________|___|          |
                       (O)          (O)  (O)            |
==================================================================
""",
    r"""
                     ______________________       .-----------.
                    | [_]  [_]  [_]  [_] | \      | 127.0.0.1 |
                    |     MEMORY BUS     |  \  o/ '-----+-----'
                    |____________________|___|/|        |
                       (O)          (O)  (O)  / \       |
==================================================================
""",
    r"""
                                                  .-----------.
                                                  | 127.0.0.1 |
                                               o/ '-----+-----'
                                              /|        |
                                              / \       |
==================================================================
""",
]


def _bus_reaction() -> list[str]:
    """Spin the bus wheels in place, leaving its stop and road untouched."""
    neutral = BUS_FRAMES[0].strip("\n").splitlines()
    width = max(map(len, neutral))
    frames = []
    for spoke in ("O", "/", "-", "\\", "|", "/", "O"):
        canvas = [row.ljust(width) for row in neutral]
        canvas[4] = canvas[4].replace("(O)", "(" + spoke + ")")
        frames.append("\n".join(canvas))
    return frames


WRONG_FRAMES = _bus_reaction()


class Level8(Level):
    def __init__(self) -> None:
        super().__init__(
            number=8,
            title="Level 8",
            required_input=(".",),  # A full stop to get off at your stop.
            art=BUS_FRAMES,
            description=fill(
                "The MMU book points to 127.0.0.1. You board the Memory Bus "
                "to reach the wizard's address.",
                width=70,
            ),
            prompt="You must get off at your stop.",
            wrong_frames=WRONG_FRAMES,
        )
        self.frame_delay = 1.0
        self.layout = "level9"
