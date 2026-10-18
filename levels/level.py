import time

REACTION_COOLDOWN = 0.75
_IGNORED_GUESSES = {"", "q", "\x04", "\x1a", "\x1c", "\x13", "\x11", "\x1b"}


class Level:
    def __init__(
        self,
        number: int,
        title: str,
        required_input: tuple[str, ...],
        art: str | list[str] = "",
        prompt: str = "",
        description: str = "",
        wrong_frames: list[str] | tuple[str, ...] = (),
    ) -> None:
        self.number = number
        self.title = title
        self.required_input = required_input
        # Store art as a list of frames so levels can be animated later.
        self.frames = [art] if isinstance(art, str) else list(art)
        self.prompt = prompt
        self.description = description
        self.wrong_frames = list(wrong_frames)
        self.wrong_frame_delay = 0.12
        self.reaction_frame: int | None = None
        self._reaction_started = 0.0
        self._reaction_last_at = float("-inf")
        self.frame = 0
        self.frame_delay = 0.7
        # A level can hold selected frames longer than its normal animation.
        self.frame_delays: dict[int, float] = {}
        # Opt in to background animation while waiting for puzzle input.
        self.idle_frame = 0
        self.idle_frame_delay: float | None = None
        # Optional scenes that loop in place of the first frame until solved.
        self.idle_frames: list[str] = []
        self.layout = "center"

    def art(self, frame: int) -> str:
        if self.reaction_frame is not None:
            return self.wrong_frames[self.reaction_frame].strip("\n")
        if frame == 0 and self.idle_frames:
            return self.idle_frames[self.idle_frame % len(self.idle_frames)].strip("\n")
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

    @property
    def reaction_deadline(self) -> float | None:
        if self.reaction_frame is None:
            return None
        return self._reaction_started + (self.reaction_frame + 1) * self.wrong_frame_delay

    def react_to_wrong_input(self, key: str | None, now: float | None = None) -> bool:
        """Start a short art reaction without changing puzzle progress."""
        if (key is None or key in _IGNORED_GUESSES or key in self.required_input
                or not self.wrong_frames):
            return False
        now = time.monotonic() if now is None else now
        if self.reaction_frame is not None or now - self._reaction_last_at < REACTION_COOLDOWN:
            return False
        self.reaction_frame = 0
        self._reaction_started = now
        self._reaction_last_at = now
        return True

    def update_reaction(self, now: float | None = None) -> bool:
        """Advance to the current local frame, then restore the normal scene."""
        if self.reaction_frame is None:
            return False
        now = time.monotonic() if now is None else now
        elapsed = max(0.0, now - self._reaction_started)
        frame = int((elapsed + 1e-9) / self.wrong_frame_delay)
        previous = self.reaction_frame
        self.reaction_frame = frame if frame < len(self.wrong_frames) else None
        return self.reaction_frame != previous

    def clear_reaction(self) -> None:
        self.reaction_frame = None
        self._reaction_started = 0.0
        self._reaction_last_at = float("-inf")
