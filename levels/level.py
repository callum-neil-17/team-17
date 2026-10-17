class Level:
    def __init__(
        self,
        number: int,
        title: str,
        required_input: tuple[str, ...],
        art: str | list[str] = "",
        prompt: str = "",
        description: str = "",
    ) -> None:
        self.number = number
        self.title = title
        self.required_input = required_input
        # Store art as a list of frames so levels can be animated later.
        self.frames = [art] if isinstance(art, str) else list(art)
        self.prompt = prompt
        self.description = description
        self.frame = 0
        self.frame_delay = 0.7
        self.layout = "center"

    def art(self, frame: int) -> str:
        # Cycle through the frames so any frame number is valid.
        return self.frames[frame % len(self.frames)].strip("\n")

    def render(self) -> str:
        sections = []
        if self.description:
            sections.append(self.description)
        sections.append(self.title)
        art = self.art(self.frame)
        if art:
            sections.append(art)
        sections.append(self.prompt)
        screen = "\n\n".join(sections) + "\n"
        # Raw mode does not translate newlines, so use explicit CRLF endings.
        return screen.replace("\n", "\r\n")

    def check_input(self, key: str) -> bool:
        return key in self.required_input
