"""Hitlabshut — Enclothement contextuel des principes.

הִתְלַבְּשׁוּת — L'enclothement (Hitlabshut) est le processus par
lequel une lumière supérieure se "revêt" dans un Kli inférieur.
Le principe ne disparaît pas — il devient OPÉRANT à travers
l'instruction concrète.

EC-SHK-048, PG-SHK-018 — Dimension 19 du Kli.

Le Etz Chaim distingue deux types de lumière :
  Or Pnimi (אוֹר פְּנִימִי) = lumière intérieure, ENCLOTHÉE dans le Kli
  Or Makif (אוֹר מַקִּיף) = lumière environnante, qui ENTOURE le Kli

Un principe listé séparément est Or Makif — il entoure l'instruction
sans la pénétrer. Un principe ENCLOTHE dans l'instruction est Or Pnimi
— il agit de l'intérieur.

v1 : enclothement par TEMPLATE (simple concaténation structurée).
v2 (Phase 4) : enclothement par LLM (reformulation organique).

Usage:
    from masakh.hitlabshut import Hitlabshut

    h = Hitlabshut()
    result = h.enclothe(
        principle="Rigueur : chaque concept doit être fonctionnellement opérant",
        instruction="Implémente la fonction de filtrage",
    )
    # → "Implémente la fonction de filtrage — en appliquant le principe :
    #    Rigueur : chaque concept doit être fonctionnellement opérant"
"""

from __future__ import annotations


# Template v1 — concaténation structurée
_TEMPLATE = "{instruction} — en appliquant le principe : {principle}"


class Hitlabshut:
    """הִתְלַבְּשׁוּת — Enclothement des principes dans les instructions.

    Transforme un principe abstrait (Or Makif) en directive intégrée
    à l'instruction (Or Pnimi).
    """

    def enclothe(self, principle: str, instruction: str) -> str:
        """Enclothe un principe dans une instruction.

        Args:
            principle: Le principe abstrait (ex: "Rigueur : chaque
                concept doit être fonctionnellement opérant").
            instruction: L'instruction concrète (ex: "Implémente
                la fonction de filtrage").

        Returns:
            L'instruction avec le principe enclothe dedans.

        Raises:
            ValueError: Si principle ou instruction est vide.
        """
        if not principle or not principle.strip():
            raise ValueError("Le principe ne peut pas être vide")
        if not instruction or not instruction.strip():
            raise ValueError("L'instruction ne peut pas être vide")

        return _TEMPLATE.format(
            instruction=instruction.strip(),
            principle=principle.strip(),
        )

    def enclothe_many(
        self,
        principles: list[str],
        instruction: str,
    ) -> str:
        """Enclothe plusieurs principes dans une instruction.

        Les principes sont listés séparément dans un bloc dédié,
        plutôt qu'imbriqués séquentiellement (qui produisait des
        instructions illisibles avec N > 2 principes).

        Args:
            principles: Liste de principes à enclothe.
            instruction: L'instruction concrète.

        Returns:
            L'instruction enrichie de tous les principes.
        """
        if not principles:
            return instruction

        principles_block = "\n".join(f"- {p.strip()}" for p in principles if p.strip())
        return f"{instruction}\n\n[PRINCIPES DIRECTEURS]\n{principles_block}\n[/PRINCIPES DIRECTEURS]"
