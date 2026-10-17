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
