from textwrap import fill

from .level import Level


# Keep the tabletop and legs in the same positions as the book opens.
BOOK_FRAMES = [
    r"""
          __________________________________________________
         /                                                 /|
        /               ____________________________      //|
       /               / MEMORY MANAGEMENT UNIT   /|     // |
      /               /           MMU            / |    //  |
     /               /__________________________/ /    //|  |
    /                |__________________________|/    // |__|
   /                                                 //
  /                                                 //
 /_________________________________________________//
 |=================================================|/
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |__|                                           |__|
""",
    r"""
          __________________________________________________
         /                                                 /|
        /                ________                         //|
       /                /  MMU  /|_____________          // |
      /                /       / /           /|         //  |
     /                /_______/ /  -------- / |        //|  |
    /                 |       |/__________/ /         // |__|
   /                  |_______|__________|/          //
  /                                                 //
 /_________________________________________________//
 |=================================================|/
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |__|                                           |__|
""",
    r"""
          __________________________________________________
         /                                                 /|
        /          ________ ___________________           //|
       /          /       //                  /|         // |
      /          /  MMU  //  --------------- / |        //  |
     /          /       //  --------------- / /        //|  |
    /          /_______//__________________/ /        // |__|
   /           |_______||__________________|/        //
  /                                                 //
 /_________________________________________________//
 |=================================================|/
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |__|                                           |__|
""",
    r"""
          __________________________________________________
         /                                                 /|
        /     ______________ ______________________       //|
       /     /             //                     /|     // |
      /     /  MEMORY     //  MANAGEMENT UNIT     / |   //  |
     /     /  ---------  //      127.0.0.1       / /   //|  |
    /     /_____________//_____________________/ /    // |__|
   /      |_____________||_____________________|/    //
  /                                                 //
 /_________________________________________________//
 |=================================================|/
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |  |                                           |  |
 |__|                                           |__|
""",
]


def _book_reaction() -> list[str]:
    """Nudge the closed book across the fixed tabletop, then let it settle."""
    neutral = BOOK_FRAMES[0].strip("\n").splitlines()
    width = max(map(len, neutral))
    frames = []
    for shift in (0, 1, 1, 0, -1, 0, 0):
        canvas = [list(row.ljust(width)) for row in neutral]
        for row in range(2, 7):
            book = neutral[row][18:54]
            canvas[row][18:54] = " " * 36
            for column, char in enumerate(book, 18 + shift):
                if char != " ":
                    canvas[row][column] = char
        frames.append("\n".join("".join(row) for row in canvas))
    return frames


WRONG_FRAMES = _book_reaction()

# Fixed tabletop positions with staggered phases, outside the book itself.
SPARKLES = (
    (14, 1, 0), (30, 1, 3), (46, 1, 5), (12, 3, 2), (10, 5, 4),
    (52, 2, 1), (50, 5, 6), (24, 7, 2), (40, 8, 0), (8, 8, 5),
)


def _book_idle() -> list[str]:
    """Twinkle a few sparkles so the book looks worth opening."""
    rows = BOOK_FRAMES[0].strip("\n").splitlines()
    width = max(map(len, rows))
    phases = " .+*+. "
    frames = []
    for step in range(len(phases)):
        canvas = [list(row.ljust(width)) for row in rows]
        for column, row, offset in SPARKLES:
            if rows[row][column:column + 1] == " ":
                canvas[row][column] = phases[(step + offset) % len(phases)]
        frames.append("\n".join("".join(row) for row in canvas))
    return frames


IDLE_FRAMES = _book_idle()


class Level7(Level):
    def __init__(self) -> None:
        super().__init__(
            number=7,
            title="Level 7",
            required_input=("\x06",),
            art=BOOK_FRAMES,
            description=fill(
                "With the tab paid, you find the MMU "
                "book. Its pages might hold the wizard's address.",
                width=70,
            ),
            prompt="How can you find the wizards address",
            wrong_frames=WRONG_FRAMES,
        )
        self.idle_frames = IDLE_FRAMES
        self.idle_frame_delay = 0.25
        self.wrong_guesses = 0

    def react_to_wrong_input(self, key: str | None, now: float | None = None) -> bool:
        ignored = (None, "", "q", "\x03", "\x04", "\x1a", "\x1c", "\x13", "\x11", "\x1b")
        if self.wrong_guesses < 5 and key not in ignored and key not in self.required_input:
            self.wrong_guesses += 1
            if self.wrong_guesses == 5:
                self.prompt = self.prompt.rstrip() + "\nThere must be a shortcut to find it"
        # Each wrong guess counts even while the existing art reaction plays.
        return super().react_to_wrong_input(key, now=now)
