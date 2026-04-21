"""EmergenceDetector — détecter les propriétés émergentes.

Le Zohar enseigne que Chokmah n'est pas produite — elle est REÇUE.
L'émergence ne se programme pas. On détecte les CONDITIONS qui
rendent l'émergence possible, et on repère les SIGNAUX quand
quelque chose d'inattendu se produit.

4 types de signaux émergents :
  1. cross_domain   — connexion entre domaines distants
  2. tension_resolved — une tension Tiferet résolue productivement
  3. non_deducible  — un résultat non déductible des entrées
  4. synergy        — la combinaison des modules produit plus que la somme

Anti-Ghagiel Nogah : signal ≠ insight. Un signal est une INDICATION,
pas une conclusion. La validation reste obligatoire.
"""

from __future__ import annotations

from insightforge.models import (
    CandidateInsight,
    EmergenceSignal,
    InsightSession,
)


# Seuils
DEFAULT_MIN_DOMAIN_DISTANCE = 2    # Domaines "distants" si >= 2 hop conceptuel
DEFAULT_MIN_SIGNAL_STRENGTH = 0.3  # Signal trop faible = bruit
DEFAULT_MAX_SIGNALS = 10           # Anti-inflation de signaux


class EmergenceDetector:
    """Détecte les propriétés émergentes du système.

    Ne PRODUIT pas d'émergence — la détecte. Chokmah apparaît
    quand elle veut. Nous pouvons seulement observer.
    """

    def __init__(
        self,
        min_signal_strength: float = DEFAULT_MIN_SIGNAL_STRENGTH,
        max_signals: int = DEFAULT_MAX_SIGNALS,
    ):
        self.min_signal_strength = min_signal_strength
        self.max_signals = max_signals

    def detect(self, session: InsightSession) -> list[EmergenceSignal]:
        """Détecter tous les signaux émergents d'une session.

        Analyse les candidats, les modules consultés, et les
        patterns dans la session pour repérer l'émergence.
        """
        signals: list[EmergenceSignal] = []

        signals.extend(self._detect_cross_domain(session))
        signals.extend(self._detect_tension_resolved(session))
        signals.extend(self._detect_non_deducible(session))
        signals.extend(self._detect_synergy(session))

        # Filtrer les signaux trop faibles
        signals = [
            s for s in signals
            if s.strength >= self.min_signal_strength
        ]

        # Trier par force décroissante
        signals.sort(key=lambda s: s.strength, reverse=True)

        # Anti-inflation : limiter le nombre de signaux
        return signals[:self.max_signals]

    def _detect_cross_domain(
        self, session: InsightSession,
    ) -> list[EmergenceSignal]:
        """Signal 1 : connexions cross-domain.

        Quand un candidat connecte des domaines qui ne sont
        normalement pas associés, c'est un signal d'émergence.
        Plus les domaines sont "distants", plus le signal est fort.
        """
        signals: list[EmergenceSignal] = []

        for candidate in session.surviving_candidates():
            domains = [d for d in candidate.connects_domains if d]
            unique = set(domains)
            if len(unique) < 2:
                continue

            # Force proportionnelle au nombre de domaines connectés
            strength = min(1.0, 0.3 + 0.2 * (len(unique) - 1))

            # Bonus si triple-validé
            validated = sum([
                candidate.binah_validated,
                candidate.gevurah_validated,
                candidate.daat_validated,
            ])
            strength = min(1.0, strength + validated * 0.1)

            signals.append(EmergenceSignal(
                signal_type="cross_domain",
                description=(
                    f"Cross-domain connection: {' ↔ '.join(sorted(unique))} "
                    f"— '{candidate.description[:80]}'"
                ),
                strength=round(strength, 2),
                modules_involved=["chesed"],
                evidence=f"Domains connected: {sorted(unique)}",
            ))

        return signals

    def _detect_tension_resolved(
        self, session: InsightSession,
    ) -> list[EmergenceSignal]:
        """Signal 2 : tensions résolues productivement.

        Quand Tiferet détecte une tension entre claims ET que cette
        tension mène à un insight candidat, c'est un signal fort.
        La résolution de contradictions est plus créative que
        l'exploration linéaire.
        """
        signals: list[EmergenceSignal] = []

        # Vérifier si Tiferet a été consulté
        if "tiferet" not in session.modules_consulted:
            return signals

        # Chercher des candidats qui résolvent des tensions
        for candidate in session.surviving_candidates():
            if candidate.source_module == "tiferet":
                strength = min(1.0, 0.5 + candidate.confidence * 0.3)
                signals.append(EmergenceSignal(
                    signal_type="tension_resolved",
                    description=(
                        f"Tension resolved: '{candidate.description[:80]}'"
                    ),
                    strength=round(strength, 2),
                    modules_involved=["tiferet"],
                    evidence="Candidate emerged from tension resolution",
                ))

        return signals

    def _detect_non_deducible(
        self, session: InsightSession,
    ) -> list[EmergenceSignal]:
        """Signal 3 : résultats non-déductibles.

        Un insight est "non-déductible" quand il ne peut pas être
        dérivé simplement des candidats individuels. C'est le signe
        que le tout est plus que la somme des parties.

        Heuristique : un candidat cross-domain à haute confiance
        qui a passé la triple validation est probablement non-déductible.
        """
        signals: list[EmergenceSignal] = []

        for candidate in session.surviving_candidates():
            domains = [d for d in candidate.connects_domains if d]
            unique_domains = set(domains)

            triple = (
                candidate.binah_validated
                and candidate.gevurah_validated
                and candidate.daat_validated
            )

            if len(unique_domains) >= 2 and triple and candidate.confidence >= 0.6:
                strength = min(1.0, 0.6 + candidate.confidence * 0.2)
                signals.append(EmergenceSignal(
                    signal_type="non_deducible",
                    description=(
                        f"Non-deducible insight: '{candidate.description[:80]}'"
                    ),
                    strength=round(strength, 2),
                    modules_involved=["binah", "gevurah", "daat"],
                    evidence=(
                        "Cross-domain, triple-validated, high-confidence "
                        "— unlikely to be trivially derived"
                    ),
                ))

        return signals

    def _detect_synergy(
        self, session: InsightSession,
    ) -> list[EmergenceSignal]:
        """Signal 4 : synergie entre modules.

        Quand plusieurs modules ont contribué à un insight qui
        n'aurait pas pu être trouvé par un seul module, c'est
        une synergie. Mesurée par le nombre de modules consultés
        vs le nombre de modules qui ont contribué aux candidats.
        """
        signals: list[EmergenceSignal] = []

        # Compter les modules contributeurs uniques
        contributing_modules = set()
        for candidate in session.surviving_candidates():
            if candidate.source_module:
                contributing_modules.add(candidate.source_module)

        consulted = len(session.modules_consulted)
        contributing = len(contributing_modules)

        # Synergie si au moins 3 modules consultés et au moins 2 contribuent
        if consulted >= 3 and contributing >= 2:
            # Force proportionnelle au ratio de contribution
            ratio = contributing / max(consulted, 1)
            strength = min(1.0, 0.3 + ratio * 0.5)

            signals.append(EmergenceSignal(
                signal_type="synergy",
                description=(
                    f"Module synergy: {contributing}/{consulted} modules "
                    f"actively contributed insights"
                ),
                strength=round(strength, 2),
                modules_involved=sorted(contributing_modules),
                evidence=(
                    f"Consulted: {sorted(session.modules_consulted)}, "
                    f"Contributing: {sorted(contributing_modules)}"
                ),
            ))

        return signals

    def has_emergence(self, session: InsightSession) -> bool:
        """Y a-t-il au moins un signal émergent significatif ?"""
        signals = self.detect(session)
        return any(s.strength >= 0.5 for s in signals)

    def strongest_signal(
        self, session: InsightSession,
    ) -> EmergenceSignal | None:
        """Le signal émergent le plus fort de la session."""
        signals = self.detect(session)
        return signals[0] if signals else None
