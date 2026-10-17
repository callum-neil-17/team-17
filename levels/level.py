class Level:
    def __init__(
        self, number: int, title: str, required_input: tuple[str, ...]
    ) -> None:
        self.number = number
        self.title = title
        self.required_input = required_input

    def render(self) -> str:
        # Raw mode does not translate newlines, so use explicit CRLF endings.
        return f"{self.title}\r\nPress Enter to continue.\r\n"

    def check_input(self, key: str) -> bool:
        return key in self.required_input
