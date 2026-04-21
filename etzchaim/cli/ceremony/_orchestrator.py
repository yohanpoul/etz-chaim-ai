"""Phase sequencing for the birth ceremony.

Public entry points:
    play_ceremony(width) -> CeremonyResult   # full animated sequence
    play_compact()       -> CeremonyResult   # instant, auto-name, birthtime=now

Both return a name and a tz-aware birthtime. Callers persist these to .env.

Animation timing goes through a module-level _sleep that tests monkeypatch.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.text import Text

from etzchaim.cli.ceremony import _art, _text
from etzchaim.cli.ceremony._hineni import wait_for_any_key as _wait_for_any_key  # noqa: F401


DEFAULT_SHEM = "Etz Chaim"
_SHEM_REGEX = re.compile(r"^[\w\s\-'\.]{1,40}$", re.UNICODE)


@dataclass(frozen=True)
class CeremonyResult:
    shem: str
    birthtime: datetime


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _validate_shem(candidate: str) -> bool:
    """Return True if candidate is a valid persisted name (1-40 unicode word chars)."""
    if not candidate or len(candidate) > 40:
        return False
    return bool(_SHEM_REGEX.match(candidate))


def _centered(text: str, *, style: str = "") -> Align:
    return Align.center(Text(text, style=style))


def _phase_silence(live: Live) -> None:
    live.update(Text(""))
    _sleep(2.0)


def _phase_shevirah(live: Live, texts: dict[str, str]) -> None:
    live.update(_centered("·", style="bold red"))
    _sleep(1.2)
    live.update(Text(""))
    _sleep(0.3)
    live.update(_centered(texts["something_tore"], style="bold"))
    _sleep(1.2)
    glitched = _art.glitch_shevirah(seed=int(_now_utc().timestamp()) & 0xFF)
    composed = f"{glitched}\n\n{texts['vessels_broke']}\n"
    live.update(_centered(composed, style="bold bright_red"))
    _sleep(0.2)
    live.update(_centered(texts["vessels_broke"], style="bold"))
    _sleep(1.0)
    live.update(_centered(texts["sparks_fell"], style="bold"))
    _sleep(1.5)


def _render_tree_with_lit_nodes(lines: list[str], lit: set[str]) -> Text:
    """Return a Text where sephirot whose english-name is in `lit` are colored."""
    out = Text()
    color_by_name = {n[0]: n[2] for n in _art.SEPHIRAH_NODES}
    for line in lines:
        matched = None
        for name in lit:
            if name in line:
                matched = name
                break
        if matched is not None:
            out.append(line, style=color_by_name[matched])
        else:
            out.append(line, style="dim")
        out.append("\n")
    return out


def _phase_kelim(live: Live) -> None:
    """Light up the tree, one sephirah at a time."""
    tree = list(_art.TREE_LINES)
    lit_so_far: set[str] = set()
    for name_en, _name_he, _color in _art.SEPHIRAH_NODES:
        lit_so_far.add(name_en)
        rendered = _render_tree_with_lit_nodes(tree, lit_so_far)
        live.update(Align.center(rendered))
        _sleep(0.15)
    _sleep(0.5)


def _declare_block(live: Live, block: str, frames_iter, texts: dict[str, str],
                   long_hold: float, short_hold: float) -> None:
    """Reveal `block` line by line with hard cuts, while EKG keeps ticking."""
    lines = block.split("\n")
    shown: list[str] = []
    for line in lines:
        shown.append(line)
        ekg = next(frames_iter)
        header = Text(ekg, style="bright_red")
        header.append(f"\n             {texts['pulse_label']}\n", style="dim")
        body = Text("\n".join(shown), style="bold")
        live.update(Group(Align.center(header), Align.center(body)))
        _sleep(long_hold if (line.strip() and line.strip().endswith((".", "!", "?"))) else short_hold)


def _phase_pulse_and_declaration(live: Live, texts: dict[str, str], frames_iter) -> None:
    _declare_block(live, texts["declaration"], frames_iter, texts, long_hold=1.5, short_hold=0.8)


def _phase_consequences(live: Live, texts: dict[str, str], frames_iter) -> None:
    _declare_block(live, texts["consequences"], frames_iter, texts, long_hold=1.2, short_hold=0.7)


def _phase_commandments(live: Live, texts: dict[str, str], frames_iter) -> None:
    _declare_block(live, texts["commandments"], frames_iter, texts, long_hold=1.4, short_hold=0.9)


def _phase_hineni(live: Live, texts: dict[str, str], frames_iter) -> datetime:
    """Render prompt, block on keypress, return local-tz birthtime captured at press."""
    ekg = next(frames_iter)
    header = Text(ekg, style="bright_red")
    prompt = Text(texts["hineni_prompt"], style="bold gold1")
    live.update(Group(Align.center(header), Align.center(prompt)))
    live.stop()
    try:
        _wait_for_any_key()
    finally:
        birthtime_utc = _now_utc()
        live.start(refresh=False)
    reply = Text(texts["hineni_reply"], style="bold gold1")
    ekg2 = next(frames_iter)
    header2 = Text(ekg2, style="bright_red")
    live.update(Group(Align.center(header2), Align.center(reply)))
    _sleep(2.0)
    return birthtime_utc.astimezone()


def _phase_logo(live: Live, narrow: bool) -> None:
    if narrow:
        live.update(_centered(_art.NARROW_LOGO, style="bold gold1"))
        _sleep(1.5)
        return
    progressive: list[str] = []
    for line in _art.LOGO_LINES:
        progressive.append(line)
        live.update(_centered("\n".join(progressive), style="bold gold1"))
        _sleep(0.25)
    footer = "\n".join(progressive) + f"\n\n{_art.HEBREW_TREE_OF_LIFE}"
    live.update(_centered(footer, style="bold gold1"))
    _sleep(1.2)


def _prompt_shem(texts: dict[str, str]) -> str:
    """Interactive loop: one re-prompt max, then fall back to default."""
    for attempt in range(2):
        try:
            raw = input("  › ").strip()
        except (EOFError, KeyboardInterrupt):
            return DEFAULT_SHEM
        if not raw:
            return DEFAULT_SHEM
        if _validate_shem(raw):
            return raw
        if attempt == 0:
            print(f"  {texts['naming_invalid']}")
    return DEFAULT_SHEM


def play_compact() -> CeremonyResult:
    """Skip path — no animation, default name, birthtime = now."""
    return CeremonyResult(shem=DEFAULT_SHEM, birthtime=_now_utc().astimezone())


def play_ceremony(*, width: int = 80) -> CeremonyResult:
    """Run the full animated ceremony. Blocks on keypress at Hineni.

    Returns (shem, birthtime). Caller is responsible for persisting to .env.
    """
    texts = _text.get_texts()
    console = Console(force_terminal=True)
    console.clear()
    narrow = width < 70

    birthtime: datetime | None = None
    with Live("", console=console, auto_refresh=False, screen=False) as live:
        _phase_silence(live)
        _phase_shevirah(live, texts)
        _phase_kelim(live)
        frames_iter = _art.ekg_frames(width=min(width, 80), count=10_000, seed=11)
        _phase_pulse_and_declaration(live, texts, frames_iter)
        _phase_consequences(live, texts, frames_iter)
        _phase_commandments(live, texts, frames_iter)
        birthtime = _phase_hineni(live, texts, frames_iter)
        _phase_logo(live, narrow=narrow)

    print()
    for line in texts["naming_prompt"].split("\n"):
        print(f"  {line}")
    print()
    shem = _prompt_shem(texts)
    assert birthtime is not None
    return CeremonyResult(shem=shem, birthtime=birthtime)
