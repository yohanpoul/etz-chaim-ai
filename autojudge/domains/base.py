"""Classe abstraite DomainJudge — chaque domaine implémente sa 'loss function'.

Le DomainJudge est l'interface que chaque domaine doit implémenter :
- generate_hypothesis : Chokmah — former une hypothèse d'amélioration
- apply_modification : Yetzirah — appliquer la modification
- evaluate : Gevurah — juger le résultat
- get_loss_description : Hod — expliquer la métrique
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from autojudge.models import DomainScore


class DomainJudge(ABC):
    """Interface abstraite — chaque domaine implémente sa propre 'loss function'."""

    @abstractmethod
    def generate_hypothesis(self, current_state: str) -> str:
        """Chokmah : générer une hypothèse d'amélioration.

        Analyse l'état actuel et propose une modification.
        """

    @abstractmethod
    def apply_modification(self, content: str, hypothesis: str) -> str:
        """Yetzirah : appliquer la modification au contenu.

        Retourne le contenu modifié selon l'hypothèse.
        """

    @abstractmethod
    def evaluate(self, original: str, modified: str) -> DomainScore:
        """Gevurah : évaluer le résultat.

        Compare original et modified, retourne un DomainScore.
        quality > 0.5 signifie amélioration, < 0.5 signifie régression.
        """

    @abstractmethod
    def get_loss_description(self) -> str:
        """Hod : décrire la métrique utilisée en langage humain."""
