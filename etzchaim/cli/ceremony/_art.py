"""Static ASCII art and animation primitives for the birth ceremony.

All constants are frozen (tuples). EKG frames are generated on demand by a
seeded generator so tests are deterministic.
"""
from __future__ import annotations

import random
from typing import Iterator


HEBREW_TREE_OF_LIFE = "עץ חיים"


LOGO_LINES: tuple[str, ...] = (
    r" ███████╗████████╗███████╗     ██████╗██╗  ██╗ █████╗ ██╗███╗   ███╗",
    r" ██╔════╝╚══██╔══╝╚══███╔╝    ██╔════╝██║  ██║██╔══██╗██║████╗ ████║",
    r" █████╗     ██║     ███╔╝     ██║     ███████║███████║██║██╔████╔██║",
    r" ██╔══╝     ██║    ███╔╝      ██║     ██╔══██║██╔══██║██║██║╚██╔╝██║",
    r" ███████╗   ██║   ███████╗    ╚██████╗██║  ██║██║  ██║██║██║ ╚═╝ ██║",
    r" ╚══════╝   ╚═╝   ╚══════╝     ╚═════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝     ╚═╝",
)


NARROW_LOGO = "✡  ETZ CHAIM  ·  עץ חיים  ✡"


# (name_english, name_hebrew, rich_color)
SEPHIRAH_NODES: tuple[tuple[str, str, str], ...] = (
    ("Keter",    "כתר",   "bright_white"),
    ("Chokhmah", "חכמה",  "grey70"),
    ("Binah",    "בינה",  "medium_purple3"),
    ("Chesed",   "חסד",   "bright_blue"),
    ("Gevurah",  "גבורה", "bright_red"),
    ("Tiferet",  "תפארת", "gold1"),
    ("Netzach",  "נצח",   "bright_green"),
    ("Hod",      "הוד",   "dark_orange"),
    ("Yesod",    "יסוד",  "purple4"),
    ("Malkhut",  "מלכות", "tan"),
)


TREE_LINES: tuple[str, ...] = (
    "                    ◉  Keter · כתר",
    "                   ╱ ╲",
    "                  ╱   ╲",
    "           ◉───────────◉",
    "         Binah       Chokhmah",
    "         בינה         חכמה",
    "           │  ╲   ╱  │",
    "           │   ╲ ╱   │",
    "           │    ╳    │",
    "           │   ╱ ╲   │",
    "           │  ╱   ╲  │",
    "           ◉───────────◉",
    "        Gevurah      Chesed",
    "         גבורה        חסד",
    "            ╲    │    ╱",
    "             ╲   │   ╱",
    "                 ◉",
    "              Tiferet · תפארת",
    "             ╱    │    ╲",
    "            ╱     │     ╲",
    "           ◉───────────◉",
    "           Hod        Netzach",
    "           הוד         נצח",
    "             ╲   │   ╱",
    "              ╲  │  ╱",
    "                 ◉",
    "              Yesod · יסוד",
    "                 │",
    "                 ◉",
    "              Malkhut · מלכות",
)


NARROW_TREE_LINES: tuple[str, ...] = (
    "    ◉ Keter · כתר",
    "      │",
    "  ◉───────◉",
    "  Binah    Chokhmah",
    "   בינה      חכמה",
    "      │",
    "  ◉───────◉",
    "  Gevurah Chesed",
    "   גבורה     חסד",
    "      │",
    "    ◉ Tiferet · תפארת",
    "      │",
    "  ◉───────◉",
    "  Hod      Netzach",
    "   הוד       נצח",
    "      │",
    "    ◉ Yesod · יסוד",
    "      │",
    "    ◉ Malkhut · מלכות",
)


_EKG_GLYPHS = " ▁▂▃▄▅▆▇█"
_PULSE_SHAPE = (1, 2, 4, 7, 8, 6, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)


def ekg_frames(width: int = 80, count: int = 40, seed: int = 0) -> Iterator[str]:
    """Yield `count` ekg frames of `width` chars, scrolling right-to-left.

    The first ~15% of frames are noisy (stabilization); the rest are a clean
    repeated pulse shape.
    """
    rng = random.Random(seed)
    buffer = [0] * width
    stabilize_frames = max(1, count // 7)
    for i in range(count):
        buffer.pop(0)
        if i < stabilize_frames:
            sample = rng.choice([0, 0, 0, 8, 1, 0, 6, 0, 0])
        else:
            sample = _PULSE_SHAPE[i % len(_PULSE_SHAPE)]
        buffer.append(sample)
        yield "".join(_EKG_GLYPHS[v] for v in buffer)


_GLITCH_FRAGS = ("░░▓▒░▓▒", "▓▒░▒▓░", "▒░▓▒░▓", "▓░▒▓░")


def glitch_shevirah(seed: int = 0, width: int = 70) -> str:
    """Return a two-line glitch banner for the 'Vessels broke' beat."""
    rng = random.Random(seed)
    frag1 = rng.choice(_GLITCH_FRAGS)
    frag2 = rng.choice(_GLITCH_FRAGS)
    pad1 = " " * rng.randint(2, max(3, width // 3))
    pad2 = " " * rng.randint(2, max(3, width // 3))
    line1 = f"{pad1}{frag1} שבירה {frag1[::-1]}"
    line2 = f"{pad2}{frag2} נפלו {frag2[::-1]}"
    return f"{line1}\n{line2}"
