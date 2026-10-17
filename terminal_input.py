"""Read terminal keys without confusing Escape with an escape-sequence prefix."""

import errno
import math
import os
import select
import time


END = "END"
ESCAPE = "ESCAPE"

_ESC = 0x1B
_MAX_BUFFER = 4096


def _sequence_length(data: bytearray) -> int | None:
    """Return one complete event's length, or None for an incomplete sequence.

    CSI and SS3 cover cursor and function keys. String controls are consumed up
    to their terminator so an Escape inside an OSC/DCS cannot become a key.
    Malformed or excessively long input is released in bounded raw chunks.
    """
    if data[0] != _ESC:
        return 1
    if len(data) == 1:
        return None

    second = data[1]
    if second in (ord("]"), ord("P"), ord("X"), ord("^"), ord("_")):
        for index in range(2, len(data)):
            # Keep the emergency interrupt available even if a terminal sent an
            # unterminated string control before it. Deliver the prefix first.
            if data[index] == 0x03:
                return index
            if data[index] == 0x9C or (second == ord("]") and data[index] == 7):
                return index + 1
            if data[index] == ord("\\") and data[index - 1] == _ESC:
                return index + 1
        return len(data) if len(data) >= _MAX_BUFFER else None

    if second in (ord("["), ord("O")):
        start = 2
        # Linux-console F1-F5 have an extra '[' (F5 is ESC [[ E).
        if second == ord("[") and len(data) > 2 and data[2] == ord("["):
            start = 3
        for index in range(start, len(data)):
            byte = data[index]
            if 0x40 <= byte <= 0x7E:
                return index + 1
            if not 0x20 <= byte <= 0x3F:
                return index
        return len(data) if len(data) >= _MAX_BUFFER else None

    for index in range(1, len(data)):
        byte = data[index]
        if 0x30 <= byte <= 0x7E:
            return index + 1
        if not 0x20 <= byte <= 0x2F:
            # A second Escape or a raw control byte starts a separate event.
            return index
    return len(data) if len(data) >= _MAX_BUFFER else None


def _is_end(sequence: bytes) -> bool:
    if sequence[:2] not in (b"\x1b[", b"\x1bO"):
        return False
    parameters = sequence[2:-1].split(b";")
    # xterm modifiers, including the colon subparameters used by some terminals.
    if not all(part and all(value.isdigit() for value in part.split(b":"))
               for part in parameters[1:]):
        return False
    if sequence[-1:] == b"F":
        return parameters[0] in (b"", b"1")
    return (sequence[:2] == b"\x1b[" and sequence[-1:] == b"~"
            and parameters[0] in (b"4", b"8"))


class KeyReader:
    """Preserve partial terminal input across calls and return one key at a time.

    ``None`` means the caller's timeout elapsed; ``''`` means EOF. An Escape
    prefix gets an inter-byte timeout, renewed whenever more input arrives.
    Complete sequences other than End are returned unchanged as latin-1 text.
    """

    def __init__(self, fd: int, escape_timeout: float = 0.08):
        if not math.isfinite(escape_timeout) or escape_timeout < 0:
            raise ValueError("escape_timeout must be finite and nonnegative")
        self.fd = fd
        self.escape_timeout = escape_timeout
        self._buffer = bytearray()
        self._escape_deadline: float | None = None
        self._last_input_at = 0.0
        self._eof = False

    def _take(self, length: int) -> str:
        sequence = bytes(self._buffer[:length])
        del self._buffer[:length]
        self._escape_deadline = None
        if sequence == b"\x1b":
            return ESCAPE
        return END if _is_end(sequence) else sequence.decode("latin-1")

    def read(self, timeout: float | None = None) -> str | None:
        if timeout is not None and (not math.isfinite(timeout) or timeout < 0):
            raise ValueError("timeout must be finite and nonnegative")
        deadline = None if timeout is None else time.monotonic() + timeout

        while True:
            if self._buffer:
                length = _sequence_length(self._buffer)
                if length is not None:
                    return self._take(length)
                if self._escape_deadline is None:
                    self._escape_deadline = self._last_input_at + self.escape_timeout
            if self._eof:
                return self._take(len(self._buffer)) if self._buffer else ""

            now = time.monotonic()
            waits = [max(0.0, limit - now)
                     for limit in (deadline, self._escape_deadline) if limit is not None]
            wait = min(waits) if waits else None
            try:
                readable = select.select([self.fd], [], [], wait)[0]
                if readable:
                    try:
                        chunk = os.read(self.fd, _MAX_BUFFER - len(self._buffer))
                    except OSError as error:
                        # A PTY master reports its peer's closure as EIO.
                        if error.errno != errno.EIO:
                            raise
                        chunk = b""
                    if not chunk:
                        self._eof = True
                    else:
                        self._buffer.extend(chunk)
                        self._last_input_at = time.monotonic()
                        if self._buffer[0] == _ESC:
                            self._escape_deadline = self._last_input_at + self.escape_timeout
                    continue
            except (InterruptedError, BlockingIOError):
                continue

            # Check ready bytes before expiring a prefix, even when this call
            # starts after its timer. A complete buffered key remains one event.
            now = time.monotonic()
            if self._escape_deadline is not None and now >= self._escape_deadline:
                return self._take(len(self._buffer))
            if deadline is not None and now >= deadline:
                return None
