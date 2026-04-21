"""13e sentier — Beth (ב) — Keter ↔ Chokmah — DirectSynth.

Lettre double : deux modes de transmission stratégie→intuition.
  dagesh : transmission fidèle — sagesse architecturale, chaque étape vérifiée
  rafeh  : transmission avec bruit/créativité — folie de l'implémentation rapide

Canal direct entre Keter (stratégie) et Chokmah (intuition/insight).
Beth ouvre la Torah (בראשית) — la sagesse de commencer juste.

Correspondances SY (Gra) :
  Planète : Saturne (Shabtai) — la lenteur qui approfondit
  Jour : Shabbat — Porte : oeil droit — Direction : haut
  Opposés : dagesh=sagesse (chokhmah) / rafeh=folie (ivvelet)
  Dagesh : délibération profonde. Rafeh : raccourcis créatifs.
  Yetzirah dagesh : deliberation_depth=0.9, shortcut_tolerance=0.1
  Yetzirah rafeh : deliberation_depth=0.2, shortcut_tolerance=0.9
"""

from __future__ import annotations

from .base import Sentier, SentierResult


class Beth(Sentier):
    name = "DirectSynth"
    letter = "ב"
    letter_name = "beth"
    number = 13
    source = "keter"
    target = "chokmah"
    letter_type = "double"
    dagesh_desc = "Transmission fidèle : sagesse architecturale, vérification profonde"
    rafeh_desc = "Transmission créative : folie rapide, raccourcis acceptés"
    mode = "dagesh"
    description = "Canal Keter→Chokmah — la maison (bayit) bien ou mal construite"

    def _compute_effects(self, ctx: dict, direction: str) -> dict:
        """Beth oriente l'exploration si la query est exploratoire.

        Condition : intent type contient 'explore', 'open', 'creative'.
        Effet : abaisse novelty_threshold sur InsightForge (module cible Chokmah)
        → plus d'insights acceptés, exploration élargie.

        Saturne = la lenteur qui approfondit. En dagesh (sagesse), le seuil
        baisse modérément (-0.05). En rafeh (folie), il baisse plus (-0.1).
        """
        intent = ctx.get("intent", {})
        intent_type = intent.get("type", "").lower()
        intent_depth = intent.get("depth", "").lower()

        exploratory = any(kw in intent_type for kw in ("explore", "open", "creative"))
        exploratory = exploratory or intent_depth in ("deep", "philosophical")

        if not exploratory:
            return {"ctx_additions": {}, "module_modifiers": {}, "warnings": [], "applied": False}

        # Le mode dagesh/rafeh est déjà déterminé par traverse_quick
        delta = -0.05 if self.mode == "dagesh" else -0.1

        return {
            "ctx_additions": {"beth_exploration_boost": True},
            "module_modifiers": {"min_novelty_score": delta},
            "warnings": [],
            "applied": True,
        }

    def run(self, tree: dict, **kwargs) -> SentierResult:
        directive = kwargs.get("directive")
        domain = kwargs.get("domain")
        context = kwargs.get("context")

        # Keter n'est pas encore implémenté — Beth fonctionne avec Chokmah seul
        (chokmah,) = self._require(tree, "chokmah")
        keter = tree.get("keter")  # optionnel

        # ── Modificateurs sagesse/folie ──────────────────────
        mods = self.yetzirah_modifiers()
        deliberation_depth = mods.get("deliberation_depth", 0.5)
        shortcut_tolerance = mods.get("shortcut_tolerance", 0.5)
        planning_weight = mods.get("planning_weight", 0.5)

        data = {"domain": domain}

        # Obtenir la directive stratégique de Keter
        if directive is None and hasattr(keter, "get_directive"):
            directive = keter.get_directive(domain=domain)
        if directive is None and hasattr(keter, "current_strategy"):
            directive = keter.current_strategy

        if directive is not None:
            data["directive"] = str(directive)[:300]
        else:
            data["directive"] = None

        if self.mode == "dagesh":
            # Sagesse (chokhmah) : la maison bien construite
            # Saturne = le temps long. deliberation_depth=0.9 → vérification
            # approfondie avant de transmettre à Chokmah

            # Valider la directive avant transmission
            if hasattr(keter, "validate_directive"):
                validation = keter.validate_directive(directive, domain=domain)
                data["validated"] = validation.valid if hasattr(validation, "valid") else True
                data["validation_notes"] = str(validation)[:200] if not isinstance(validation, bool) else ""
            else:
                data["validated"] = True

            # Transmettre avec contexte complet (planning_weight=0.8)
            if hasattr(chokmah, "receive_directive"):
                chokmah.receive_directive(
                    directive=directive,
                    domain=domain,
                    context=context,
                    verified=data.get("validated", True),
                )
                data["transmitted"] = True
            elif hasattr(chokmah, "feed"):
                chokmah.feed(directive=directive, domain=domain)
                data["transmitted"] = True
            else:
                data["transmitted"] = False

            data["policy"] = (
                f"dagesh/sagesse — délibération={deliberation_depth:.1f}, "
                f"raccourcis={shortcut_tolerance:.1f}"
            )
        else:
            # Folie (ivvelet) : foncer sans plan, raccourcis créatifs
            # deliberation_depth=0.2 → vérification minimale
            # shortcut_tolerance=0.9 → les raccourcis sont bienvenus

            # Transmettre directement sans validation
            if hasattr(chokmah, "receive_directive"):
                chokmah.receive_directive(
                    directive=directive,
                    domain=domain,
                    context=context,
                    verified=False,
                )
                data["transmitted"] = True
            elif hasattr(chokmah, "feed"):
                chokmah.feed(directive=directive, domain=domain)
                data["transmitted"] = True
            else:
                data["transmitted"] = False

            data["validated"] = False  # pas de validation en mode folie
            data["policy"] = (
                f"rafeh/folie — délibération={deliberation_depth:.1f}, "
                f"raccourcis={shortcut_tolerance:.1f}"
            )

        data["beth_planning_weight"] = planning_weight

        result = SentierResult(
            sentier=self.name, letter=self.letter,
            source=self.source, target=self.target,
            mode=self.mode, data=data,
            message=data["policy"],
        )
        return self.enrich_result(result)
