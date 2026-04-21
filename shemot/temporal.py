"""shemot/temporal.py — Skills 51-58 : temps et chronologie.

Datation, conversion de calendriers, timelines, anachronismes, généalogies.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from .base import Shem, ShemResult


class ParseDate(Shem):
    """#51 HChSh — Silence : parser une date multi-calendrier."""
    name = "Parse Date"
    skill_id = "parse_date"
    trigram = "החש"
    trigram_name = "HChSh"
    number = 51
    category = "temporal"
    quality = "Silence"
    description = "Parser une date dans n'importe quel format (grégorien, hébreu, hijri)"

    PATTERNS = [
        # ISO: 2025-03-15
        (r"(\d{4})-(\d{1,2})-(\d{1,2})", "iso", lambda m: {"year": int(m[1]), "month": int(m[2]), "day": int(m[3]), "calendar": "gregorian"}),
        # European: 15/03/2025 or 15.03.2025
        (r"(\d{1,2})[/.](\d{1,2})[/.](\d{4})", "european", lambda m: {"day": int(m[1]), "month": int(m[2]), "year": int(m[3]), "calendar": "gregorian"}),
        # Year only: c. 1270, ca. 1492, ~570 BCE
        (r"(?:c\.?a?\.?\s*|~\s*)?(\d{1,4})\s*(BCE|CE|AH|AM)?", "year", lambda m: {"year": int(m[1]), "era": m[2] or "CE", "calendar": "gregorian"}),
        # Hebrew month: 15 Tishrei 5785
        (r"(\d{1,2})\s+(Tishrei|Cheshvan|Kislev|Tevet|Shevat|Adar|Nisan|Iyar|Sivan|Tammuz|Av|Elul)\s+(\d{4})", "hebrew", lambda m: {"day": int(m[1]), "month": m[2], "year": int(m[3]), "calendar": "hebrew"}),
    ]

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte contenant des dates")
        dates = []
        for pattern, fmt, extractor in self.PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                try:
                    parsed = extractor(match.groups())
                    parsed["raw"] = match.group(0)
                    parsed["format"] = fmt
                    dates.append(parsed)
                except (ValueError, IndexError):
                    continue
        return self._ok(
            {"dates": dates, "count": len(dates)},
            f"{len(dates)} date(s) parsée(s)",
        )


class ConvertCalendar(Shem):
    """#52 OMM — Peuple : convertir entre calendriers."""
    name = "Convert Calendar"
    skill_id = "convert_calendar"
    trigram = "עמם"
    trigram_name = "OMM"
    number = 52
    category = "temporal"
    quality = "Peuple"
    description = "Convertir entre calendriers grégorien, hébreu (AM) et hijri (AH)"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        year = kwargs.get("year", 0)
        from_cal = kwargs.get("from_cal", "gregorian")
        if not year and text:
            match = re.search(r"(\d{3,4})", text)
            if match:
                year = int(match.group(1))
        if not year:
            return self._fail("Pas d'année (year=)")

        results = {"input_year": year, "from": from_cal}
        if from_cal == "gregorian":
            results["hebrew_am"] = year + 3760  # Approximation
            results["hijri_ah"] = round((year - 622) * (33 / 32))  # Approximation
        elif from_cal == "hebrew":
            results["gregorian"] = year - 3760
            results["hijri_ah"] = round((year - 3760 - 622) * (33 / 32))
        elif from_cal == "hijri":
            results["gregorian"] = round(year * (32 / 33) + 622)
            results["hebrew_am"] = round(year * (32 / 33) + 622) + 3760
        else:
            return self._fail(f"Calendrier inconnu: {from_cal}")

        results["note"] = "Approximation — les conversions exactes nécessitent jour/mois"
        return self._ok(results, f"{year} ({from_cal}) converti")


class BuildTimeline(Shem):
    """#53 NNA — Germe : construire une chronologie."""
    name = "Build Timeline"
    skill_id = "build_timeline"
    trigram = "ננא"
    trigram_name = "NNA"
    number = 53
    category = "temporal"
    quality = "Germe"
    description = "Construire une chronologie ordonnée à partir de texte"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Extrais tous les événements datés ou datables de ce texte et "
            f"ordonne-les chronologiquement. Format:\n"
            f"[date] — [événement]\n\n{text[:3000]}"
        )
        try:
            timeline = self._llm(prompt)
            return self._ok({"timeline": timeline}, "Chronologie construite")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class DetectAnachronism(Shem):
    """#54 NYTh — Inclinaison : détecter un anachronisme."""
    name = "Detect Anachronism"
    skill_id = "detect_anachronism"
    trigram = "נית"
    trigram_name = "NYTh"
    number = 54
    category = "temporal"
    quality = "Inclinaison"
    description = "Détecter les anachronismes dans un texte historique"
    requires_llm = True
    olam = "briah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        epoch = kwargs.get("epoch", "")
        ctx = f" Le texte est censé dater de {epoch}." if epoch else ""
        prompt = (
            f"Analyse ce texte pour détecter d'éventuels anachronismes "
            f"(concepts, vocabulaire, références à des événements postérieurs).{ctx}\n\n"
            f"{text[:3000]}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok({"analysis": analysis}, "Analyse d'anachronisme")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class PeriodicityDetect(Shem):
    """#55 MBH2 — Abondance : détecter des cycles."""
    name = "Periodicity Detect"
    skill_id = "periodicity_detect"
    trigram = "מבה"
    trigram_name = "MBH2"
    number = 55
    category = "temporal"
    quality = "Abondance"
    description = "Détecter des cycles et périodicités dans des données temporelles"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        values = kwargs.get("values", [])
        if not values and text:
            values = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+", text)]
        if len(values) < 4:
            return self._fail("Au moins 4 valeurs numériques requises")
        # Détection simple par autocorrélation
        n = len(values)
        mean = sum(values) / n
        centered = [v - mean for v in values]
        var = sum(x * x for x in centered) / n
        if var == 0:
            return self._ok({"periods": [], "note": "Série constante"}, "Pas de périodicité")
        autocorr = []
        for lag in range(1, n // 2):
            corr = sum(centered[i] * centered[i + lag] for i in range(n - lag)) / (n * var)
            autocorr.append({"lag": lag, "correlation": round(corr, 4)})
        # Pics d'autocorrélation
        peaks = [a for a in autocorr if a["correlation"] > 0.3]
        return self._ok(
            {"autocorrelation": autocorr[:20], "peaks": peaks, "n_values": n},
            f"{len(peaks)} période(s) potentielle(s) détectée(s)",
        )


class EpochContext(Shem):
    """#56 POY — Salut : contexte historique d'une époque."""
    name = "Epoch Context"
    skill_id = "epoch_context"
    trigram = "פעי"
    trigram_name = "POY"
    number = 56
    category = "temporal"
    quality = "Salut"
    description = "Donner le contexte historique d'une date ou époque"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de date/époque")
        prompt = (
            f"Donne le contexte historique et intellectuel de cette période. "
            f"Quels penseurs étaient actifs ? Quels événements majeurs ? "
            f"Quel était le paysage intellectuel ?\n\nÉpoque: {text[:500]}"
        )
        try:
            context = self._llm(prompt)
            return self._ok({"context": context}, "Contexte historique")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class GenealogyParse(Shem):
    """#57 NMM — Consolation : parser une généalogie intellectuelle."""
    name = "Genealogy Parse"
    skill_id = "genealogy_parse"
    trigram = "נמם"
    trigram_name = "NMM"
    number = 57
    category = "temporal"
    quality = "Consolation"
    description = "Parser et structurer une généalogie intellectuelle maître→élève"
    requires_llm = True
    olam = "yetzirah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Parse la généalogie intellectuelle dans ce texte. "
            f"Format structuré:\n"
            f"- Maître: [nom] ([dates]) → Élève: [nom] ([dates])\n"
            f"- Indiquer le type de relation (enseignement direct, influence, lecture)\n\n"
            f"{text[:2500]}"
        )
        try:
            genealogy = self._llm(prompt)
            return self._ok({"genealogy": genealogy}, "Généalogie parsée")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")


class SynchronicityDetect(Shem):
    """#58 YYL — Jubilé : détecter des convergences temporelles."""
    name = "Synchronicity Detect"
    skill_id = "synchronicity_detect"
    trigram = "ייל"
    trigram_name = "YYL"
    number = 58
    category = "temporal"
    quality = "Jubilé"
    description = "Détecter des convergences temporelles entre traditions"
    requires_llm = True
    olam = "briah"

    def run(self, text: str = "", **kwargs) -> ShemResult:
        if not text:
            return self._fail("Pas de texte")
        prompt = (
            f"Identifie les synchronicités historiques dans ce texte — "
            f"événements parallèles dans des traditions ou régions différentes "
            f"qui se produisent à la même époque. "
            f"Distingue coïncidence, influence directe, et cause commune.\n\n{text[:3000]}"
        )
        try:
            analysis = self._llm(prompt)
            return self._ok({"synchronicities": analysis}, "Synchronicités analysées")
        except Exception as e:
            return self._fail(f"LLM indisponible: {e}")
