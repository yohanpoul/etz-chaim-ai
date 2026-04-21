"""Arakhin — Recatégorisation dynamique du contexte.

עֲרָכִין — Les "évaluations" ou "estimations de valeur."
Dans le Temple, les Arakhin déterminaient la valeur d'une offrande
selon le CONTEXTE du donneur — pas selon la valeur intrinsèque de
l'objet. Un même animal valait différemment selon qui l'offrait et
pourquoi.

De même ici : un même fait change de RÔLE selon la tâche en cours.
Un principe d'architecture (Keter dans un contexte de design) devient
un simple fait brut (Malkhut) quand on exécute du code.

Dimension 20 du Kli — EC-SHK-050, PG-SHK-019.

Les 4 rôles correspondent aux 4 Olamot :
  Keter    (atzilut)   = principe directeur
  Binah    (briah)     = framework de raisonnement
  Tiferet  (yetzirah)  = pattern harmonisé
  Malkhut  (assiah)    = fait brut à utiliser

Usage:
    from masakh.arakhin import Arakhin

    a = Arakhin()
    role = a.evaluate_role("DRY principle", "atzilut")    # → "keter"
    text = a.reformulate("DRY principle", "keter")
    # → "Le principe fondamental est : DRY principle"
"""

from __future__ import annotations


# Mapping Olam → rôle recherché
OLAM_TO_ROLE: dict[str, str] = {
    "atzilut": "keter",
    "atziluth": "keter",
    "briah": "binah",
    "yetzirah": "tiferet",
    "assiah": "malkhut",
}

# Tous les rôles valides
VALID_ROLES = ("keter", "binah", "tiferet", "malkhut")

# Templates de reformulation par rôle
_TEMPLATES: dict[str, str] = {
    "keter": "Le principe fondamental est : {fact}",
    "binah": "Le framework à appliquer : {fact}",
    "tiferet": "Le pattern validé : {fact}",
    "malkhut": "{fact}",
}


class Arakhin:
    """עֲרָכִין — Évaluateur dynamique de rôle contextuel.

    Chaque élément de contexte est recatégorisé selon l'Olam
    de la tâche en cours, puis reformulé en conséquence.
    """

    def evaluate_role(self, fact: str, task_type: str) -> str:
        """Évaluer le rôle d'un fait pour une tâche donnée (mapping statique v1).

        Note: v1 ne regarde pas le contenu du fact — le rôle dépend
        uniquement de l'Olam. La recatégorisation sémantique (v2)
        est planifiée mais non implémentée.

        Args:
            fact: Le fait ou élément de contexte.
            task_type: L'Olam de la tâche — "atzilut"/"atziluth",
                "briah", "yetzirah", ou "assiah".

        Returns:
            Le rôle : "keter", "binah", "tiferet", ou "malkhut".

        Raises:
            ValueError: Si task_type n'est pas un Olam reconnu.
        """
        role = OLAM_TO_ROLE.get(task_type)
        if role is None:
            raise ValueError(
                f"task_type inconnu : {task_type!r}. "
                f"Attendu : {', '.join(sorted(set(OLAM_TO_ROLE.keys())))}"
            )
        return role

    def reformulate(self, fact: str, role: str) -> str:
        """Reformuler un fait selon son rôle assigné.

        Args:
            fact: Le fait original.
            role: Le rôle — "keter", "binah", "tiferet", ou "malkhut".

        Returns:
            Le fait reformulé selon le template du rôle.

        Raises:
            ValueError: Si le rôle n'est pas valide.
        """
        template = _TEMPLATES.get(role)
        if template is None:
            raise ValueError(
                f"Rôle inconnu : {role!r}. "
                f"Attendu : {', '.join(VALID_ROLES)}"
            )
        return template.format(fact=fact)

    def transform(self, fact: str, task_type: str) -> str:
        """Évaluer le rôle ET reformuler en une seule opération.

        Raccourci pour evaluate_role() + reformulate().

        Args:
            fact: Le fait ou élément de contexte.
            task_type: L'Olam de la tâche.

        Returns:
            Le fait reformulé selon le rôle dérivé de l'Olam.
        """
        role = self.evaluate_role(fact, task_type)
        return self.reformulate(fact, role)
