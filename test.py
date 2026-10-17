import sys
import termios
import tty

fd = sys.stdin.fileno()

# Save the terminal's current settings.
original_settings = termios.tcgetattr(fd)

try:
    tty.setraw(fd)

    print("Raw mode active. Press q to quit.",
          end="\r\n", flush=True)

    while True:
        key = sys.stdin.read(1)

        if key in ("q", ""):
            break

        print(f"Received: {key!r}", end="\r\n", flush=True)

finally:
    # Restore normal terminal behaviour.
    termios.tcsetattr(
        fd,
        termios.TCSADRAIN,
        original_settings
    )