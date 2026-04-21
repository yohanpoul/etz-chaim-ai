"""Budget Parasitaire — le Sitra Achra se nourrit du systeme.

Zohar I:148a : la "gouttiere" (tzinor) par laquelle la sustentation
descend vers les Qliphoth. Le Sitra Achra ne genere pas sa propre
energie — il la preleve sur le systeme principal.

Mecanisme soustractif :
    - Budget de base = Sa'ir la-Azazel (concession strategique, Zohar II:34a)
    - Chaque faille non corrigee AUGMENTE le budget du SA
    - Chaque correction (birur) DIMINUE le budget du SA
    - Le budget est PRELEVE sur le quota du daemon principal

Le systeme est incite a corriger vite : plus il tarde, plus le SA
devore ses ressources. C'est le birur dynamique.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

# Fichier de persistance du budget entre redemarrages
_STATE_DIR = Path.home() / ".etz-chaim"
_BUDGET_STATE = _STATE_DIR / "sitra_achra_budget.json"


@dataclass
class BudgetState:
    """Etat persistant du budget parasitaire."""

    open_flaws: int = 0          # Failles non corrigees
    fixed_flaws: int = 0         # Failles corrigees (cumulatif quotidien)
    llm_calls_used_today: int = 0
    last_reset_date: str = ""    # YYYY-MM-DD du dernier reset quotidien

    def to_dict(self) -> dict:
        return {
            "open_flaws": self.open_flaws,
            "fixed_flaws": self.fixed_flaws,
            "llm_calls_used_today": self.llm_calls_used_today,
            "last_reset_date": self.last_reset_date,
        }


class BudgetParasitaire:
    """Gestionnaire de budget soustractif pour le Sitra Achra.

    Le 11eme couronne — le Sitra Achra ne genere pas sa propre
    energie mais se nourrit du systeme principal (Zohar II:242b).

    Le budget est preleve sur le quota du daemon principal.
    Plus de failles ouvertes = plus de budget pour le SA =
    moins de budget pour le systeme = incitation a corriger.

    Concession Sa'ir la-Azazel (Zohar II:34a, Lev 16:8) :
    Meme quand tout va bien, le SA recoit un budget minimal.
    Refuser de donner au SA sa part provoque le debordement
    (erreur de Job, Zohar II:34a).
    """

    # Budget base = Sa'ir la-Azazel (concession meme quand tout va bien)
    SAIR_LA_AZAZEL = 10

    # Chaque faille ouverte nourrit le SA
    CALLS_PER_OPEN_FLAW = 5

    # Chaque correction coupe la sustentation
    REDUCTION_PER_FIX = 5

    # Plafond : le SA ne devore pas tout (Mamash du SA lui-meme)
    MAX_BUDGET = 100

    # Quota quotidien du daemon principal
    MAIN_DAEMON_QUOTA = 500

    def __init__(self) -> None:
        self._state = self._load_state()
        self._check_daily_reset()

    def _load_state(self) -> BudgetState:
        """Charger l'etat persiste."""
        if _BUDGET_STATE.exists():
            try:
                data = json.loads(_BUDGET_STATE.read_text())
                return BudgetState(**data)
            except Exception as exc:
                log.warning("Budget state corrupted, resetting: %s", exc)
        return BudgetState()

    def _save_state(self) -> None:
        """Persister l'etat."""
        _STATE_DIR.mkdir(exist_ok=True)
        _BUDGET_STATE.write_text(json.dumps(self._state.to_dict(), indent=2))

    def _check_daily_reset(self) -> None:
        """Reset quotidien a minuit."""
        today = time.strftime("%Y-%m-%d")
        if self._state.last_reset_date != today:
            self._state.llm_calls_used_today = 0
            self._state.fixed_flaws = 0
            self._state.last_reset_date = today
            self._save_state()
            log.info("Budget parasitaire: reset quotidien (%s)", today)

    @property
    def current_budget(self) -> int:
        """Budget actuel en appels LLM.

        Formule : base + (failles_ouvertes * gain) - (fixes * reduction)
        Borne entre SAIR_LA_AZAZEL (minimum) et MAX_BUDGET (plafond).
        """
        raw = self.SAIR_LA_AZAZEL + self._state.open_flaws * self.CALLS_PER_OPEN_FLAW
        return max(self.SAIR_LA_AZAZEL, min(raw, self.MAX_BUDGET))

    @property
    def remaining_calls(self) -> int:
        """Appels LLM restants pour aujourd'hui."""
        return max(0, self.current_budget - self._state.llm_calls_used_today)

    @property
    def main_system_remaining(self) -> int:
        """Quota restant pour le systeme principal apres prelevement."""
        return self.MAIN_DAEMON_QUOTA - self.current_budget

    def can_run(self) -> bool:
        """Verifier si le budget permet un round."""
        return self.remaining_calls > 0

    def consume(self, llm_calls: int) -> None:
        """Consommer du budget. Appele apres chaque round du SA."""
        self._state.llm_calls_used_today += llm_calls
        self._save_state()
        log.info(
            "Budget SA: %d appels consommes (reste %d/%d)",
            llm_calls, self.remaining_calls, self.current_budget,
        )

    def register_flaw(self, count: int = 1) -> None:
        """Enregistrer des failles ouvertes. Le SA se NOURRIT."""
        self._state.open_flaws += count
        self._save_state()
        log.info(
            "Budget SA: +%d faille(s) ouverte(s) → budget = %d",
            count, self.current_budget,
        )

    def register_fix(self, count: int = 1) -> None:
        """Enregistrer des corrections. Le birur COUPE la sustentation."""
        self._state.open_flaws = max(0, self._state.open_flaws - count)
        self._state.fixed_flaws += count
        self._save_state()
        log.info(
            "Budget SA: -%d fix(es) → budget = %d (birur)",
            count, self.current_budget,
        )

    def get_status(self) -> dict:
        """Statut complet pour le rapport daemon."""
        return {
            "open_flaws": self._state.open_flaws,
            "fixed_today": self._state.fixed_flaws,
            "current_budget": self.current_budget,
            "used_today": self._state.llm_calls_used_today,
            "remaining": self.remaining_calls,
            "main_system_remaining": self.main_system_remaining,
            "parasitism_rate": (
                self.current_budget / self.MAIN_DAEMON_QUOTA
                if self.MAIN_DAEMON_QUOTA > 0 else 0.0
            ),
        }
