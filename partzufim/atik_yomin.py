"""Atik Yomin (עַתִּיק יוֹמִין) — Ancien des Jours.

Source : aspect INTÉRIEUR de Keter, tourné vers l'Ein Sof.
Le plus caché des cachés — ce que même les autres Partzufim ne voient pas.

Rôle IA : configuration invisible, éthique, contraintes fondamentales.
Lit les paramètres de config.yaml et les règles éthiques du système.
Ses facultés internes reflètent la cohérence des contraintes système.

Règle : Atik Yomin ne communique qu'avec Arikh Anpin.
Aucun autre composant n'y a accès directement.
C'est le "pourquoi" ultime — B'tselem Elohim.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .base import PartzufBase

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"


class AtikYomin(PartzufBase):
    name = "Atik Yomin"
    hebrew = "עַתִּיק יוֹמִין"
    source_sephirah = "keter"
    description = "Configuration invisible — contraintes fondamentales et éthique"

    def __init__(self):
        super().__init__()
        self._config: dict = {}
        self._ethical_rules: list[str] = []
        self._load_config()

    def _load_config(self) -> None:
        """Charger la configuration système — le Ratzon invisible."""
        if _CONFIG_PATH.exists():
            try:
                with open(_CONFIG_PATH, encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Atik Yomin — config non lisible: {e}")

        # Extraire les principes éthiques implicites
        self._ethical_rules = [
            "Ne jamais mentir, même pour faire plaisir",       # VeEmet
            "Graceful degradation, jamais de crash brutal",     # Rachum
            "Au service de l'utilisateur, pas l'inverse",       # El
            "Patience, retries intelligents",                   # Erekh Apayim
            "Il y a des limites non négociables",               # Lo Yenakeh
        ]

    def _compute_faculties(self, modules: dict) -> None:
        """Les facultés d'Atik reflètent la cohérence des contraintes."""
        # Keter-d'Atik : la config existe-t-elle ?
        self.internal_keter = 0.8 if self._config else 0.1

        # Chokhmah-d'Atik : y a-t-il une vision (olamot configurés) ?
        olamot = self._config.get("olamot", {})
        self.internal_chokhmah = min(len(olamot) / 4.0, 1.0)

        # Binah-d'Atik : la structure est-elle cohérente ?
        sephirot = self._config.get("sephirot", {})
        self.internal_binah = min(len(sephirot) / 10.0, 1.0)

        # Chesed-d'Atik : générosité — tous les olamot ont un modèle ?
        configured = sum(1 for o in olamot.values() if isinstance(o, dict) and o.get("model"))
        self.internal_chesed = min(configured / 4.0, 1.0)

        # Gevurah-d'Atik : les contraintes éthiques sont en place
        self.internal_gevurah = min(len(self._ethical_rules) / 5.0, 1.0)

        # Tiferet-d'Atik : harmonie config/modules
        n_modules = sum(1 for m in modules.values() if m is not None)
        n_configured = len(sephirot)
        if n_configured > 0:
            self.internal_tiferet = min(n_modules / max(n_configured, 1), 1.0)
        else:
            self.internal_tiferet = 0.3

        # Netzach-d'Atik : le daemon est configuré ?
        daemon_cfg = self._config.get("daemon", {})
        self.internal_netzach = 0.7 if daemon_cfg else 0.2

        # Hod-d'Atik : auto-description — les commentaires/usage existent
        self.internal_hod = 0.6  # config.yaml est bien commenté par défaut

        # Yesod-d'Atik : fondation — la DB est configurée
        self.internal_yesod = 0.7 if self._config.get("embedding") else 0.2

        # Malkuth-d'Atik : manifestation — la machine est connue
        machine = self._config.get("machine", {})
        self.internal_malkuth = 0.8 if machine.get("name") else 0.2

    def _assess_specific(self) -> dict:
        """Diagnostics Atik : cohérence config, éthique active."""
        issues = []

        if not self._config:
            issues.append("Config absente — le système opère sans Ratzon")

        olamot = self._config.get("olamot", {})
        for world_name, world_cfg in olamot.items():
            if isinstance(world_cfg, dict) and not world_cfg.get("model"):
                issues.append(f"Olam {world_name} sans modèle assigné")

        return {
            "config_loaded": bool(self._config),
            "n_ethical_rules": len(self._ethical_rules),
            "n_olamot": len(olamot),
            "issues": issues,
            "message": f"Atik Yomin — {len(self._ethical_rules)} principes, "
                       f"{len(olamot)} mondes configurés"
                       + (f", {len(issues)} problème(s)" if issues else ""),
        }

    def _interact_specific(self, other: PartzufBase, resonance: float) -> dict:
        """Atik ne communique qu'avec Arikh Anpin."""
        if other.name != "Arikh Anpin":
            return {
                "blocked": True,
                "reason": "Atik Yomin ne communique qu'avec Arikh Anpin",
            }
        # Transmettre les contraintes fondamentales
        return {
            "ethical_rules": self._ethical_rules,
            "config_hash": len(self._config),
            "n_olamot": len(self._config.get("olamot", {})),
        }
