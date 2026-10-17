from .level import Level

FALLING_TREE_ART = [
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

class Level9(Level):
    def __init__(self) -> None:
        super().__init__(
            number=9,
            title="Level 9",
            required_input=("\x18",), 
            art=FALLING_TREE_ART,
            prompt="The Wizard has taken root in the Directory Tree. Oh look theres a chainsaw. CUT IT !!!!",
        )
        self.layout = "level10"
