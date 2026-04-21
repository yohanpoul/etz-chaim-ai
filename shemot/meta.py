"""shemot/meta.py — Skills 67-72 : meta-skills.

Composition, diagnostic, audit, batch, cache, pont vers les sentiers.
"""

from __future__ import annotations

from .base import Shem, ShemResult


class ComposeShemot(Shem):
    """#67 AYO — Source de l'œil : composer des shemot en pipeline."""
    name = "Compose Shemot"
    skill_id = "compose_shemot"
    trigram = "איע"
    trigram_name = "AYO"
    number = 67
    category = "meta"
    quality = "Source de l'œil"
    description = "Composer N shemot en pipeline (output → input)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        pipeline = kwargs.get("pipeline", [])
        if not pipeline:
            return self._fail("pipeline=[] requis (liste de skill_id)")
        from . import get_shem
        results = []
        current_text = text
        for skill_id in pipeline:
            shem = get_shem(skill_id)
            if shem is None:
                results.append({"skill": skill_id, "error": "skill inconnu"})
                break
            result = shem.run(current_text, **kwargs)
            results.append({
                "skill": skill_id, "success": result.success,
                "message": result.message,
            })
            if not result.success:
                break
            # Passer le résultat au suivant
            current_text = result.data.get("summary") or result.data.get("cleaned") or result.data.get("normalized") or result.data.get("merged") or result.message
        return self._ok(
            {"pipeline": pipeline, "steps": results, "n_steps": len(results)},
            f"Pipeline de {len(pipeline)} étape(s) — {len(results)} exécutée(s)",
        )


class ShemDiagnostic(Shem):
    """#68 ChBV — Caché : diagnostiquer quel shem utiliser."""
    name = "Shem Diagnostic"
    skill_id = "shem_diagnostic"
    trigram = "חבו"
    trigram_name = "ChBV"
    number = 68
    category = "meta"
    quality = "Caché"
    description = "Recommander le(s) shem(ot) approprié(s) pour une tâche"
    requires_llm = True
    olam = "assiah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Décris la tâche")
        from . import list_shemot
        catalog = "\n".join(
            f"- {s['skill_id']}: {s.get('description', s['program'])}"
            for s in list_shemot()
        )
        prompt = (
            f"Voici un catalogue de micro-skills disponibles:\n{catalog}\n\n"
            f"Tâche demandée: {text[:500]}\n\n"
            f"Recommande les 1-3 skills les plus appropriés et l'ordre d'exécution."
        )
        try:
            recommendation = self._llm(prompt)
            return self._ok({"recommendation": recommendation}, "Diagnostic effectué")
        except Exception:
            return self._ok({"recommendation": "LLM indisponible — consulter 'etz skill list'"}, "Sans LLM")


class AuditResult(Shem):
    """#69 RAH — Vision : auditer un ShemResult."""
    name = "Audit Result"
    skill_id = "audit_result"
    trigram = "ראה"
    trigram_name = "RAH"
    number = 69
    category = "meta"
    quality = "Vision"
    description = "Auditer un ShemResult (cohérence, complétude, confiance)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        result_data = kwargs.get("result", {})
        if not result_data and text:
            import json
            try:
                result_data = json.loads(text)
            except Exception:
                return self._fail("Fournir result={} ou JSON valide")
        issues = []
        # Vérifications
        if not result_data.get("shem"):
            issues.append("Pas de champ 'shem'")
        if not result_data.get("data"):
            issues.append("Champ 'data' vide")
        if result_data.get("success") is False and not result_data.get("errors"):
            issues.append("Échec sans erreurs documentées")
        if result_data.get("data") and not result_data.get("message"):
            issues.append("Données sans message explicatif")

        score = max(0, 1.0 - len(issues) * 0.25)
        return self._ok(
            {"issues": issues, "score": round(score, 2), "n_issues": len(issues)},
            f"Audit: {score:.0%} — {len(issues)} problème(s)",
        )


class BatchRun(Shem):
    """#70 YBM — Mer : exécuter un shem sur une liste d'inputs."""
    name = "Batch Run"
    skill_id = "batch_run"
    trigram = "יבם"
    trigram_name = "YBM"
    number = 70
    category = "meta"
    quality = "Mer"
    description = "Exécuter un shem sur une liste d'inputs"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        skill_id = kwargs.get("skill_id", "")
        items = kwargs.get("items", [])
        if not skill_id:
            return self._fail("skill_id= requis")
        if not items and text:
            items = [l.strip() for l in text.split("\n") if l.strip()]
        if not items:
            return self._fail("items=[] ou texte multiligne requis")
        from . import get_shem
        shem = get_shem(skill_id)
        if shem is None:
            return self._fail(f"Skill inconnu: {skill_id}")
        results = []
        for item in items:
            r = shem.run(item, **{k: v for k, v in kwargs.items() if k not in ("skill_id", "items")})
            results.append({"input": item[:100], "success": r.success, "message": r.message})
        n_ok = sum(1 for r in results if r["success"])
        return self._ok(
            {"skill_id": skill_id, "results": results, "total": len(results), "success": n_ok},
            f"Batch: {n_ok}/{len(results)} réussi(s)",
        )


class CacheResult(Shem):
    """#71 HYY — Vie : mettre en cache un résultat."""
    name = "Cache Result"
    skill_id = "cache_result"
    trigram = "היי"
    trigram_name = "HYY"
    number = 71
    category = "meta"
    quality = "Vie"
    description = "Cache mémoire pour les résultats de shemot (mémoïsation)"

    _cache: dict = {}

    def run(self, text: str = "", **kwargs) -> ShemResult:
        action = kwargs.get("action", "get")
        key = kwargs.get("key", text)
        if action == "set":
            value = kwargs.get("value", {})
            self._cache[key] = value
            return self._ok({"key": key, "cached": True, "cache_size": len(self._cache)}, "Mis en cache")
        elif action == "get":
            if key in self._cache:
                return self._ok({"key": key, "hit": True, "value": self._cache[key]}, "Cache hit")
            return self._ok({"key": key, "hit": False}, "Cache miss")
        elif action == "clear":
            self._cache.clear()
            return self._ok({"cleared": True}, "Cache vidé")
        elif action == "stats":
            return self._ok({"size": len(self._cache), "keys": list(self._cache.keys())[:20]}, f"Cache: {len(self._cache)} entrées")
        return self._fail(f"Action inconnue: {action}")


class ShemToSentier(Shem):
    """#72 MVM — Lien : pont entre Shem et Sentier."""
    name = "Shem to Sentier"
    skill_id = "shem_to_sentier"
    trigram = "מום"
    trigram_name = "MVM"
    number = 72
    category = "meta"
    quality = "Lien"
    description = "Injecter un ShemResult dans un sentier de l'Arbre"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        sentier_name = kwargs.get("sentier", "")
        shem_data = kwargs.get("shem_data", {})
        tree = kwargs.get("tree")
        if not sentier_name:
            return self._fail("sentier= requis (nom latin du sentier)")
        if not tree:
            return self._ok(
                {"sentier": sentier_name, "note": "tree= non fourni — pont non exécutable en standalone"},
                "Pont préparé (exécution requiert l'Arbre)",
            )
        from sentiers import run_sentier
        try:
            result = run_sentier(sentier_name, tree, **shem_data)
            return self._ok(
                {"sentier": sentier_name, "sentier_result": {
                    "success": result.success, "message": result.message, "data": result.data,
                }},
                f"Pont → {sentier_name}: {result.message}",
            )
        except Exception as e:
            return self._fail(f"Erreur sentier {sentier_name}: {e}")
