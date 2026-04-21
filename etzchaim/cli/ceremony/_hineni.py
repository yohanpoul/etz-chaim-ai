"""Cross-platform blocking single-keypress primitive.

POSIX: switch stdin to raw mode via termios, read 1 byte, restore cooked mode.
Windows: use msvcrt.getch().
Fallback (no termios, no msvcrt): use input() which requires Enter.

Raises KeyboardInterrupt if the user presses Ctrl-C (0x03) or sends SIGINT.
"""
from __future__ import annotations

import sys


def _read_one_raw() -> str:
    """Return a single character from stdin in raw mode. May raise RuntimeError."""
    try:
        import msvcrt  # type: ignore[import-not-found]
    except ImportError:
        msvcrt = None  # type: ignore[assignment]

    if msvcrt is not None:
        # Windows path — no raw/cooked distinction, getch returns one byte.
        raw = msvcrt.getch()
        try:
            return raw.decode("utf-8", errors="replace")
        except Exception:
            return raw.decode("latin-1", errors="replace")

    try:
        import termios
        import tty
    except ImportError as e:
        raise RuntimeError("no raw-mode support on this platform") from e

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
    return ch


def wait_for_any_key() -> str:
    """Block until the user presses a key. Return the key as a string.

    Raises KeyboardInterrupt on Ctrl-C (ETX 0x03) or SIGINT.
    Falls back to ``input()`` (Enter-terminated) if raw mode is unavailable.
    """
    try:
        ch = _read_one_raw()
    except KeyboardInterrupt:
        raise
    except Exception:
        # Fallback — less visceral but always works.
        try:
            return input("  [press Enter to commit] ")
        except (EOFError, KeyboardInterrupt):
            raise KeyboardInterrupt() from None
    if ch == "\x03":  # Ctrl-C
        raise KeyboardInterrupt()
    return ch
