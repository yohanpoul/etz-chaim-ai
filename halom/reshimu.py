"""Reshimu (רשימו) — persistence layer for the Halom.

The Reshimu is the trace left behind after the primordial vessels
shattered (Shevirat HaKelim). Persistent record of every dream cycle,
every candidate explored, every discovery made.

All I/O goes to the halom/output/ directory. JSON and Markdown files.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from halom.models import CycleReport, DreamResult
from halom.gilgul import Genome, GilgulReport


class Reshimu:
    """Manages all persistence for the Halom dream agent."""

    def __init__(self, base_dir: Path):
        self._base = base_dir

    def init_structure(self) -> None:
        """Create the HALOM/ directory structure. Idempotent."""
        for subdir in ["cycles", "trouvailles", "rejets", "etat"]:
            (self._base / subdir).mkdir(parents=True, exist_ok=True)

    def get_next_cycle_number(self) -> int:
        """Return the next cycle number (1-indexed)."""
        cycles_dir = self._base / "cycles"
        if not cycles_dir.exists():
            return 1
        existing = [d for d in cycles_dir.iterdir() if d.is_dir()]
        return len(existing) + 1

    def save_cycle(self, report: CycleReport) -> Path:
        """Save a full cycle report to HALOM/cycles/. Returns the cycle directory path."""
        cycle_dir = self._base / "cycles" / f"{report.date}_cycle_{report.cycle_number:03d}"
        cycle_dir.mkdir(parents=True, exist_ok=True)

        meta = {
            "cycle_number": report.cycle_number,
            "date": report.date,
            "candidates_generated": report.candidates_generated,
            "pre_filter_survivors": report.pre_filter_survivors,
            "adversaire_survivors": report.adversaire_survivors,
            "ratio": report.ratio,
            "thompson_state": report.thompson_state,
            "duration_seconds": report.duration_seconds,
        }
        (cycle_dir / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))

        lines = [
            f"# Halom — Cycle #{report.cycle_number} — {report.date}\n",
            f"## Statistiques",
            f"- Candidats générés : {report.candidates_generated}",
            f"- Survivants pré-filtre : {report.pre_filter_survivors}",
            f"- Survivants adversaire : {report.adversaire_survivors}",
            f"- Ratio : {report.ratio:.1%}",
            f"- Durée : {report.duration_seconds:.0f}s\n",
        ]

        if report.results:
            lines.append("## Découvertes\n")
            for i, r in enumerate(report.results, 1):
                c = r.candidate
                lines.append(f"### Rêve {i} — {c.mechanism.value.capitalize()}")
                lines.append(f"**{c.concept_k}** ↔ **{c.concept_ia}**\n")
                lines.append(f"Structure commune : {c.structure_commune}\n")
                lines.append(f"Prédiction : {c.prediction}\n")
                lines.append(f"Score : {c.score_brut:.2f}")
                lines.append(f"Verdict adversaire : {r.adversaire_verdict}\n")

        (cycle_dir / "rapport.md").write_text("\n".join(lines), encoding="utf-8")

        for r in report.results:
            self.add_to_history(r.candidate.concept_k, r.candidate.concept_ia)

        return cycle_dir

    def _history_path(self) -> Path:
        return self._base / "etat" / "historique.json"

    def load_history(self) -> list[dict[str, str]]:
        path = self._history_path()
        if not path.exists():
            return []
        return json.loads(path.read_text())

    def add_to_history(self, concept_k: str, concept_ia: str) -> None:
        history = self.load_history()
        history.append({
            "concept_k": concept_k,
            "concept_ia": concept_ia,
            "timestamp": datetime.now().isoformat(),
        })
        self._history_path().parent.mkdir(parents=True, exist_ok=True)
        self._history_path().write_text(json.dumps(history, indent=2, ensure_ascii=False))

    def _thompson_path(self) -> Path:
        return self._base / "etat" / "thompson.json"

    def save_thompson(self, state: dict[str, Any]) -> None:
        self._thompson_path().parent.mkdir(parents=True, exist_ok=True)
        self._thompson_path().write_text(json.dumps(state, indent=2))

    def load_thompson(self) -> dict[str, Any]:
        path = self._thompson_path()
        if not path.exists():
            return {}
        return json.loads(path.read_text())

    # --- Gilgul (Ouroboros) persistence ---

    def _gilgulim_dir(self) -> Path:
        return self._base / "gilgulim"

    def save_genome(self, genome: Genome) -> None:
        """Save the active genome."""
        d = self._gilgulim_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "genome.json").write_text(
            json.dumps(genome.to_dict(), indent=2, ensure_ascii=False)
        )

    def load_genome(self) -> Genome | None:
        """Load the active genome, or None if not yet created."""
        path = self._gilgulim_dir() / "genome.json"
        if not path.exists():
            return None
        return Genome.from_dict(json.loads(path.read_text()))

    def save_baseline_genome(self, genome: Genome) -> None:
        """Save the immutable baseline genome (v1)."""
        d = self._gilgulim_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "genome_v1.json").write_text(
            json.dumps(genome.to_dict(), indent=2, ensure_ascii=False)
        )

    def load_baseline_genome(self) -> Genome | None:
        """Load the immutable baseline genome."""
        path = self._gilgulim_dir() / "genome_v1.json"
        if not path.exists():
            return None
        return Genome.from_dict(json.loads(path.read_text()))

    def get_next_gilgul_number(self) -> int:
        """Return the next gilgul number (1-indexed)."""
        d = self._gilgulim_dir()
        if not d.exists():
            return 1
        existing = [x for x in d.iterdir() if x.is_dir() and x.name.startswith("gilgul_")]
        return len(existing) + 1

    def save_gilgul(self, report: GilgulReport) -> Path:
        """Save a full gilgul cycle report. Returns the gilgul directory path."""
        gilgul_dir = self._gilgulim_dir() / f"gilgul_{report.gilgul_number:03d}"
        gilgul_dir.mkdir(parents=True, exist_ok=True)

        # Save mutant genome
        (gilgul_dir / "genome_mutant.json").write_text(
            json.dumps(report.genome_mutant.to_dict(), indent=2, ensure_ascii=False)
        )

        # Save verdict
        lines = [
            f"# Gilgul #{report.gilgul_number} — Verdict\n",
            f"**Date** : {report.date}",
            f"**Verdict** : {report.verdict}\n",
            f"## Rationale\n",
            report.verdict_rationale,
            "",
            f"## Stats",
            f"- Mutations generees : {report.mutations_generated}",
            f"- Mutations survivantes : {report.mutations_survivors}",
        ]
        (gilgul_dir / "verdict.md").write_text("\n".join(lines), encoding="utf-8")

        return gilgul_dir

    def save_lignee(self, lignee: dict) -> None:
        """Save the lineage tree."""
        d = self._gilgulim_dir()
        d.mkdir(parents=True, exist_ok=True)
        (d / "lignee.json").write_text(
            json.dumps(lignee, indent=2, ensure_ascii=False)
        )

    def load_lignee(self) -> dict:
        """Load the lineage tree, or empty dict if not yet created."""
        path = self._gilgulim_dir() / "lignee.json"
        if not path.exists():
            return {}
        return json.loads(path.read_text())
