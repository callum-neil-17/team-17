from textwrap import fill

from .level import Level

FALLING_TREE_ART = [
    # FRAME 1: Standing
    r"""
                             vv
                         vvv^^^^vvvvv
                     vvvvvvvvv^^vvvvvv^^vvvvv
            vvvvvvvvvvv^^^^^^^^^^^^^vvvvv^^^vvvvv
        vvvvvvv^^^^^^^^^vvv^^^^^^^vvvvvvvvvvv^^^vvv
      vvvv^^^^^^vvvvv^^^^^^^vv^^^^^^^vvvv^^^vvvvvv
     vv^^^^^^^^vvv^^^^^vv^^^^vvvvvvvvvvvv^^^^^^vv^
     vvv^^^^^vvvv^^^^^^vvvvv^^vvvvvvvvv^^^^^^vvvvv^
      vvvvvvvvvv^^^v^^^vvvvvv^^vvvvvvvvvv^^^vvvvvvvvv
       ^vv^^^vvvvvvv^^vvvvv^^^^^^^^vvvvvvvvv^^^^^^vvvvvv
         ^vvvvvvvvv^^^^vvvvvv^^^^^^vvvvvvvv^^^vvvvvvvvvv^v
            ^^^^^^vvvv^^vvvvv^vvvv^^^v^^^^^^vvvvvv^^^^vvvvv   
     vvvv^^vvv^^^vvvvvvvvvv^vvvvv^vvvvvv^^^vvvvvvv^^vvvvv^v    
    vvv^vvvvv^^vvvvvvv^^vvvvvvv^^vvvvv^v##vvv^vvvv^^vvvvv^v   
     ^vvvvvv^^vvvvvvvv^vv^vvv^^^^^^_____##^^^vvvvvvvv^^^^     
        ^^vvvvvvv^^vvvvvvvvvv^^^^/\@@@@@@\#vvvv^^^             
             ^^vvvvvv^^^^^^vvvvv/__\@@@@@@\^vvvv^v          
                 ;^^vvvvvvvvvvv/____\@@@@@@\vvvvvvv        
    /var/        ;      \_  ^\|[  -:] ||--| | _/^^        
     \           ;        \   |[   :] ||_/| |/           
    /log/        ;         \\ ||___:]______/            
      \          ;          \   ;=; /                   
       \____     ;           |  ;=;|                    
            \   ()           |  ;=;|                    
             \__             |  ;=;|                    
                \____       / / \;=;\                   
                     \_____/                             
    """,
    # FRAME 2: The Initial Cut
    r"""
                                 vv
                             vvv^^^^vvvvv
                         vvvvvvvvv^^vvvvvv^^vvvvv
                vvvvvvvvvvv^^^^^^^^^^^^^vvvvv^^^vvvvv
            vvvvvvv^^^^^^^^^vvv^^^^^^^vvvvvvvvvvv^^^vvv
          vvvv^^^^^^vvvvv^^^^^^^vv^^^^^^^vvvv^^^vvvvvv
         vv^^^^^^^^vvv^^^^^vv^^^^vvvvvvvvvvvv^^^^^^vv^
         vvv^^^^^vvvv^^^^^^vvvvv^^vvvvvvvvv^^^^^^vvvvv^
          vvvvvvvvvv^^^v^^^vvvvvv^^vvvvvvvvvv^^^vvvvvvvvv
           ^vv^^^vvvvvvv^^vvvvv^^^^^^^^vvvvvvvvv^^^^^^vvvvvv
             ^vvvvvvvvv^^^^vvvvvv^^^^^^vvvvvvvv^^^vvvvvvvvvv^v
                ^^^^^^vvvv^^vvvvv^vvvv^^^v^^^^^^vvvvvv^^^^vvvvv   
         vvvv^^vvv^^^vvvvvvvvvv^vvvvv^vvvvvv^^^vvvvvvv^^vvvvv^v    
        vvv^vvvvv^^vvvvvvv^^vvvvvvv^^vvvvv^v##vvv^vvvv^^vvvvv^v   
         ^vvvvvv^^vvvvvvvv^vv^vvv^^^^^^_____##^^^vvvvvvvv^^^^     
            ^^vvvvvvv^^vvvvvvvvvv^^^^/\@@@@@@\#vvvv^^^             
                 ^^vvvvvv^^^^^^vvvvv/__\@@@@@@\^vvvv^v          
                     ;^^vvvvvvvvvvv/____\@@@@@@\vvvvvvv        
    /var/            ;      \_  ^\|[  -:] ||--| | _/^^         *BZZZZZT*
     \               ;        \   |[   :] ||_/| |/           
    /log/            ;         \\ ||___:]______/            
      \              ;          \   ;=; /                   
       \____          \           \  ;=;|                    
            \   ()     \           \  ;=;|                    
             \__        \           \  ;=;|                    
                \____       / /      \;=;\                   
                     \_____/      /                                  
    """,
    # FRAME 3: Snapping and Leaning
    r"""
                                       vv
                                   vvv^^^^vvvvv
                               vvvvvvvvv^^vvvvvv^^vvvvv
                      vvvvvvvvvvv^^^^^^^^^^^^^vvvvv^^^vvvvv
                  vvvvvvv^^^^^^^^^vvv^^^^^^^vvvvvvvvvvv^^^vvv
                vvvv^^^^^^vvvvv^^^^^^^vv^^^^^^^vvvv^^^vvvvvv
               vv^^^^^^^^vvv^^^^^vv^^^^vvvvvvvvvvvv^^^^^^vv^
               vvv^^^^^vvvv^^^^^^vvvvv^^vvvvvvvvv^^^^^^vvvvv^
                vvvvvvvvvv^^^v^^^vvvvvv^^vvvvvvvvvv^^^vvvvvvvvv
                 ^vv^^^vvvvvvv^^vvvvv^^^^^^^^vvvvvvvvv^^^^^^vvvvvv
                   ^vvvvvvvvv^^^^vvvvvv^^^^^^vvvvvvvv^^^vvvvvvvvvv^v
                      ^^^^^^vvvv^^vvvvv^vvvv^^^v^^^^^^vvvvvv^^^^vvvvv   
               vvvv^^vvv^^^vvvvvvvvvv^vvvvv^vvvvvv^^^vvvvvvv^^vvvvv^v    
              vvv^vvvvv^^vvvvvvv^^vvvvvvv^^vvvvv^v##vvv^vvvv^^vvvvv^v   
               ^vvvvvv^^vvvvvvvv^vv^vvv^^^^^^_____##^^^vvvvvvvv^^^^     
                  ^^vvvvvvv^^vvvvvvvvvv^^^^/\@@@@@@\#vvvv^^^             
                       ^^vvvvvv^^^^^^vvvvv/__\@@@@@@\^vvvv^v          
                           ;^^vvvvvvvvvvv/____\@@@@@@\vvvvvvv        
    /var/                  ;      \_  ^\|[  -:] ||--| | _/^^         *CREAAAAK*
     \                     ;        \   |[   :] ||_/| |/           
    /log/                   ;         \\ ||___:]______/            
      \                     ;          \   ;=; /                   
       \____                 \           \  ;=;|                    
            \   ()            \           \  ;=;|                    
             \__               \           \  ;=;|                    
                \____       / /             \;=;\                   
                     \_____/      /      /                           
    """,
    # FRAME 4: Timber
    r"""
                                                . . vvv
                                              . vvvv^^^^vvvvv
                                          . . vvvvvvvvv^^vvvvvv^^vvvvv
                                     . . vvvvvvvvvvv^^^^^^^^^^^^^vvvvv^^^vvvvv
                                 . . vvvvvvv^^^^^^^^^vvv^^^^^^^vvvvvvvvvvv^^^vvv
                             . . vvvv^^^^^^vvvvv^^^^^^^vv^^^^^^^vvvv^^^vvvvvv
                         . . vv^^^^^^^^vvv^^^^^vv^^^^vvvvvvvvvvvv^^^^^^vv^
                     . . vvv^^^^^vvvv^^^^^^vvvvv^^vvvvvvvvv^^^^^^vvvvv^
                  . . vvvvvvvvvv^^^v^^^vvvvvv^^vvvvvvvvvv^^^vvvvvvvvv
                . . ^vv^^^vvvvvvv^^vvvvv^^^^^^^^vvvvvvvvv^^^^^^vvvvvv
              . . ^vvvvvvvvv^^^^vvvvvv^^^^^^vvvvvvvv^^^vvvvvvvvvv^v
            . . ^^^^vvvv^^vvvvv^vvvv^^^v^^^^^^vvvvvv^^^^vvvvv
          . . vvvv^^vvv^^^vvvvvvvvvv^vvvvv^vvvvvv^^^vvvvvvv^^vvvvv^v
        . vvv^vvvvv^^vvvvvvv^^vvvvvvv^^vvvvv^v##vvv^vvvv^^vvvvv^v
       .  ^vvvvvv^^vvvvvvvv^vv^vvv^^^^^^_____##^^^vvvvvvvv^^^^
        .    ^^vvvvvvv^^vvvvvvvvvv^^^^/\@@@@@@\#vvvv^^^
              .  ^^vvvvvv^^^^^^vvvvv/__\@@@@@@\^vvvv^v
                .    ;^^vvvvvvvvvvv/____\@@@@@@\vvvvvvv
    /var/         .  ;      \_  ^\|[  -:] ||--| | _/^^         *TIMBERRRRR*
     \             . ;        \   |[   :] ||_/| |/
    /log/           .;         \\ ||___:]______/                  *CRACK*
      \            . ;          \   ;=; /
       \____      .  ;           |  ;=;|
            \   () .             |  ;=;|
             \__ .               |  ;=;|
                \____           / / \;=;\
                     \_____/      /   /       *SNAP*
    """,
    # FRAME 5: Picking Up Speed
    r"""
                                                                 . . vvv
                                                               . vvvv^^^^vvvvv
                                                           . . vvvvvvvvv^^vvvvv
                                                      . . vvvvvvvvvvv^^^^^^^^^^
                                                  . . vvvvvvv^^^^^^^^^vvv^^^^^^
                                              . . vvvv^^^^^^vvvvv^^^^^^^vv^^^^^
                                          . . vv^^^^^^^^vvv^^^^^vv^^^^vvvvvvvvv
                                      . . vvv^^^^^vvvv^^^^^^vvvvv^^vvvvvvvvv^^^
                                   . . vvvvvvvvvv^^^v^^^vvvvvv^^vvvvvvvvvv^^^vv
                                 . . ^vv^^^vvvvvvv^^vvvvv^^^^^^^^vvvvvvvvv^^^^^
                               . . ^vvvvvvvvv^^^^vvvvvv^^^^^^vvvvvvvv^^^vvvvvvv
                             . . ^^^^vvvv^^vvvvv^vvvv^^^v^^^^^^vvvvvv^^^^vvvvv
                           . . vvvv^^vvv^^^vvvvvvvvvv^vvvvv^vvvvvv^^^vvvvvvv^^v
                         . vvv^vvvvv^^vvvvvvv^^vvvvvvv^^vvvvv^v##vvv^vvvv^^vvvv
                        .  ^vvvvvv^^vvvvvvvv^vv^vvv^^^^^^_____##^^^vvvvvvvv^^^^
                         .    ^^vvvvvvv^^vvvvvvvvvv^^^^/\@@@@@@\#vvvv^^^
                               .  ^^vvvvvv^^^^^^vvvvv/__\@@@@@@\^vvvv^v
                                 .    ;^^vvvvvvvvvvv/____\@@@@@@\vvvvvvv
    /var/                          .  ;      \_  ^\|[  -:] ||--| | _/^^     *WHOOSH*
     \                              . ;        \   |[   :] ||_/| |/
    /log/                            .;         \\ ||___:]______/                  
      \                             . ;          \   ;=; /
       \____                       .  ;           \  ;=;|
            \   ()                 .               \ ;=;|
             \__                   .                \;=;|
                \____           / /                  \=\
                     \_____/      /   /                        
    """,
    # FRAME 6: Impact
    r"""

    \ \                                                       
     \ \                                                      
      \ \                                                     
    vvvvv\v                                                   
    ^^^^^^\\                                                    
    vvvvvvv\\                                                        
    ^^^^vvvv\\                                            *CRAAAAASH*
    vv^^vvvvv\\_______                                                      
    vvv^^^^^^vvvvvvvvv\___________________________________________________________
    vvvvvvvvvvvv^^^^^^/[  -:] ||--| | _/^^\[  -:] ||_/| |/\||___:]______/\;=;\|;=;| 
    ~~~~~~~~~~~~~~~~~/____\@@@@@@\vvvvvvv/____\@@@@@@\^vvvv^v/__\@@@@@@\#vvvv^^^
      /var/ /log/ /tmp/                                                  
       *CRUSH*                                         
    """
]


def _tree_reaction() -> list[str]:
    """Sway the upper branches; the trunk and wizard's house stay rooted."""
    neutral = FALLING_TREE_ART[0].strip("\n").splitlines()
    width = max(map(len, neutral))
    frames = []
    for shift in (0, 1, 2, 0, -2, -1, 0):
        canvas = [list(row.ljust(width)) for row in neutral]
        for row in range(13):
            sway = shift if row < 8 else (1 if shift > 0 else -1 if shift < 0 else 0)
            canvas[row] = list(" " * width)
            for column, char in enumerate(neutral[row]):
                if char != " " and 0 <= column + sway < width:
                    canvas[row][column + sway] = char
        frames.append("\n".join("".join(row) for row in canvas))
    return frames


WRONG_FRAMES = _tree_reaction()


def _tree_idle() -> list[str]:
    """Rock the treetop a single column, gentler than the reaction's sway."""
    neutral = FALLING_TREE_ART[0].strip("\n").splitlines()
    width = max(map(len, neutral))
    frames = []
    for shift in (0, 1, 1, 0, -1, -1):
        canvas = [list(row.ljust(width)) for row in neutral]
        for row in range(7):
            canvas[row] = list(" " * width)
            for column, char in enumerate(neutral[row]):
                if char != " " and 0 <= column + shift < width:
                    canvas[row][column + shift] = char
        frames.append("\n".join("".join(row) for row in canvas))
    return frames


IDLE_FRAMES = _tree_idle()


class Level9(Level):
    def __init__(self) -> None:
        super().__init__(
            number=9,
            title="Level 9",
            # \x18 is the standard ASCII hex code for Ctrl+X
            required_input=("\x18",), 
            art=FALLING_TREE_ART,
            description=fill(
                "The address leads you to the wizard's Directory Tree.",
                width=70,
            ),
            prompt="The Wizard has taken root in the Directory Tree. Oh look theres a chainsaw. CUT IT DOWN !!!!",
            wrong_frames=WRONG_FRAMES,
        )
        self.layout = "level10"
        self.idle_frames = IDLE_FRAMES
        self.idle_frame_delay = 0.4
        self.wrong_guesses = 0

    def react_to_wrong_input(self, key: str | None, now: float | None = None) -> bool:
        ignored = (None, "", "q", "\x03", "\x04", "\x1a", "\x1c", "\x13", "\x11", "\x1b")
        if self.wrong_guesses < 5 and key not in ignored and key not in self.required_input:
            self.wrong_guesses += 1
            if self.wrong_guesses == 5:
                self.prompt = self.prompt.rstrip() + "\nwhat could the command for cut be ?"
        # Each wrong guess counts even while the existing art reaction plays.
        return super().react_to_wrong_input(key, now=now)
