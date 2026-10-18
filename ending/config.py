"""Shared, bounded timing for the real and inline finale windows."""

MAX_PANIC_WINDOWS = 10
PANIC_DURATION = 8.0
PANIC_STAGGER = 0.18
FIRST_PANIC_CLOSE = 5.0
PANIC_CLOSE_STEP = 0.3


def _panic_index(index: int) -> int:
    if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < MAX_PANIC_WINDOWS:
        raise ValueError("Invalid panic window index")
    return index


def panic_start(index: int) -> float:
    """Seconds into the finale when this numbered copy first appears."""
    return _panic_index(index) * PANIC_STAGGER


def panic_close(index: int) -> float:
    """Seconds into the finale when this numbered copy starts closing."""
    return FIRST_PANIC_CLOSE + _panic_index(index) * PANIC_CLOSE_STEP
