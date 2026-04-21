"""TikkunScheduler — synthèse proportionnelle aux tensions.

Machloket l'Shem Shamayim : les tensions sont du Tohu (forces sans récipients).
Les synthèses sont du Tikkun (réparation). Quand le ratio Tohu/Tikkun dépasse
un seuil par domaine, déclencher une synthèse — pas attendre le cycle quotidien.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from dissensuengine.db import DissensuEngineDB


class TikkunPriority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DomainTohuState:
    domain: str
    tensions_count: int
    syntheses_count: int
    ratio: float
    needs_tikkun: bool
    priority: TikkunPriority


# Seuils de calibration
TENSION_THRESHOLD = 10          # > 10 tensions ouvertes par domaine → synthèse
TOHU_TIKKUN_RATIO_MAX = 5.0    # ratio tensions/synthèses max acceptable


class TikkunScheduler:
    """Planificateur réactif de synthèses — Tikkun proportionnel au Tohu."""

    def __init__(
        self,
        db: DissensuEngineDB,
        tension_threshold: int = TENSION_THRESHOLD,
        ratio_max: float = TOHU_TIKKUN_RATIO_MAX,
    ):
        self.db = db
        self.tension_threshold = tension_threshold
        self.ratio_max = ratio_max

    def assess_tohu_state(self) -> dict[str, DomainTohuState]:
        """Évaluer l'état Tohu/Tikkun de chaque domaine.

        Retourne un dict domain → DomainTohuState.
        """
        tensions_by_domain = self.db.count_open_tensions_by_domain()
        syntheses_by_domain = self.db.count_syntheses_by_domain()

        all_domains = set(tensions_by_domain) | set(syntheses_by_domain)
        result = {}

        for domain in all_domains:
            t_count = tensions_by_domain.get(domain, 0)
            s_count = syntheses_by_domain.get(domain, 0)
            ratio = t_count / s_count if s_count > 0 else float(t_count)
            needs = (
                ratio > self.ratio_max or t_count > self.tension_threshold
            )

            if ratio > 10:
                priority = TikkunPriority.HIGH
            elif ratio > self.ratio_max:
                priority = TikkunPriority.MEDIUM
            else:
                priority = TikkunPriority.LOW

            result[domain] = DomainTohuState(
                domain=domain,
                tensions_count=t_count,
                syntheses_count=s_count,
                ratio=ratio,
                needs_tikkun=needs,
                priority=priority,
            )

        return result

    def schedule_tikkun(
        self,
        domains_needing_tikkun: dict[str, DomainTohuState] | None = None,
    ) -> list[str]:
        """Retourner les domaines triés par priorité décroissante.

        Le domaine avec le plus haut ratio est synthétisé en premier.
        """
        if domains_needing_tikkun is None:
            all_states = self.assess_tohu_state()
            domains_needing_tikkun = {
                d: s for d, s in all_states.items() if s.needs_tikkun
            }

        priority_order = {
            TikkunPriority.HIGH: 0,
            TikkunPriority.MEDIUM: 1,
            TikkunPriority.LOW: 2,
        }

        return sorted(
            domains_needing_tikkun,
            key=lambda d: (
                priority_order[domains_needing_tikkun[d].priority],
                -domains_needing_tikkun[d].ratio,
            ),
        )

    def should_synthesize_now(
        self, domain: str, new_tension_count: int = 0
    ) -> bool:
        """Appelé APRÈS chaque ajout de tensions.

        Si le domaine dépasse le seuil → True → synthèse immédiate.
        C'est le mécanisme RÉACTIF (pas juste le cycle quotidien).
        """
        tensions_by_domain = self.db.count_open_tensions_by_domain()
        current = tensions_by_domain.get(domain, 0) + new_tension_count

        if current > self.tension_threshold:
            return True

        syntheses_by_domain = self.db.count_syntheses_by_domain()
        s_count = syntheses_by_domain.get(domain, 0)
        ratio = current / s_count if s_count > 0 else float(current)

        return ratio > self.ratio_max
