from .level import Level


CHEQUE_FRAMES = [

    r"""
+--------------------------------------------------------------+
| BANK OF CACHE                            CHEQUE No. 0001     |
|                                                              |
| Date: ______________                                         |
|                                                              |
| Pay to: THE BAR                                              |
| Amount: _____________________________ cache credits          |
|                                                              |
| Memo: Drinks                                                 |
| Signature: __________________________                        |
|                                                              |
| Tab closed: [ ]                                              |
+--------------------------------------------------------------+
""",

    r"""
+--------------------------------------------------------------+
| BANK OF CACHE                            CHEQUE No. 0001     |
|                                                              |
| Date: 17 Oct 2026___                                         |
|                                                              |
| Pay to: THE BAR                                              |
| Amount: _____________________________ cache credits          |
|                                                              |
| Memo: Drinks                                                 |
| Signature: __________________________                        |
|                                                              |
| Tab closed: [ ]                                              |
+--------------------------------------------------------------+
""",

    r"""
+--------------------------------------------------------------+
| BANK OF CACHE                            CHEQUE No. 0001     |
|                                                              |
| Date: 17 Oct 2026___                                         |
|                                                              |
| Pay to: THE BAR                                              |
| Amount: One Hundred _________________ cache credits          |
|                                                              |
| Memo: Drinks                                                 |
| Signature: __________________________                        |
|                                                              |
| Tab closed: [ ]                                              |
+--------------------------------------------------------------+
""",

    r"""
+--------------------------------------------------------------+
| BANK OF CACHE                            CHEQUE No. 0001     |
|                                                              |
| Date: 17 Oct 2026___                                         |
|                                                              |
| Pay to: THE BAR                                              |
| Amount: One Hundred _________________ cache credits          |
|                                                              |
| Memo: Drinks                                                 |
| Signature: ~~~~~~X~~~~~~_____________                        |
|                                                              |
| Tab closed: [ ]                                              |
+--------------------------------------------------------------+
""",

    r"""
+--------------------------------------------------------------+
| BANK OF CACHE                            CHEQUE No. 0001     |
|                                                              |
| Date: 17 Oct 2026___                                         |
|                                                              |
| Pay to: THE BAR                                              |
| Amount: One Hundred _________________ cache credits          |
|                                                              |
| Memo: Drinks                                                 |
| Signature: ~~~~~~X~~~~~~_____________                        |
|                                                              |
| Tab closed: [v]                                              |
+--------------------------------------------------------------+
""",

    r"""
+--------------------------------------------------------------+
| BANK OF CACHE                            CHEQUE No. 0001     |
|                                                              |
| Date: 17 Oct 2026___                   ***********           |
|                                        *  PAID   *           |
| Pay to: THE BAR                        ***********           |
| Amount: One Hundred _________________ cache credits          |
|                                                              |
| Memo: Drinks                                                 |
| Signature: ~~~~~~X~~~~~~_____________                        |
|                                                              |
| Tab closed: [v]                                              |
+--------------------------------------------------------------+
"""
]


class Level6(Level):
    def __init__(self) -> None:
        super().__init__(
            number=6,
            title="Level 6",
            required_input=("\x17",),  # Ctrl+W is a raw input byte.
            art=CHEQUE_FRAMES,
            description="You go back to the bar now since you have the money", 
            prompt="you can close your tab now",
        )
        self.frame_delay = 0.4
