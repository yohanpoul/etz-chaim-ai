#!/usr/bin/env python3
"""populate_concepts.py — Peuple les 660 concepts sifrei_yesod avec nom_he, nom_fr, description, domaine.

Déduit les champs à partir de :
- concept_id (translittération → hébreu)
- Rôles dans les assertions
- Contexte du perek de première apparition

Usage:
    python -m sifrei_yesod.pipeline.populate_concepts [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter

import psycopg2
import psycopg2.extras

DB_URL = (os.environ.get("ETZ_CHAIM_DB_URL") or os.environ.get("ETZ_CHAIM_DB", "postgresql://localhost/etz_chaim"))

# ============================================================================
# SECTION 1 — DICTIONNAIRE HÉBREU (token → hébreu)
# ============================================================================

HEBREW = {
    # --- Sefirot ---
    'keter': 'כתר', 'chokhmah': 'חכמה', 'binah': 'בינה', 'da_at': 'דעת',
    'chesed': 'חסד', 'gevurah': 'גבורה', 'tiferet': 'תפארת',
    'netzach': 'נצח', 'hod': 'הוד', 'yesod': 'יסוד', 'malkhut': 'מלכות',
    # --- Partzufim ---
    'arikh': 'אריך', 'anpin': 'אנפין', 'abba': 'אבא', 'imma': 'אמא',
    'zeir': 'זעיר', 'nukvah': 'נוקבא', 'rachel': 'רחל', 'leah': 'לאה',
    'atik': 'עתיק', 'yomin': 'יומין', 'yaakov': 'יעקב',
    # --- Ohr ---
    'ohr': 'אור', 'pnimi': 'פנימי', 'makif': 'מקיף', 'yashar': 'ישר',
    'hozer': 'חוזר', 'shefa': 'שפע', 'hiyut': 'חיות',
    # --- Processus ---
    'tzimtzum': 'צמצום', 'shevirah': 'שבירה', 'shevirat': 'שבירת',
    'tikkun': 'תיקון', 'birur': 'בירור', 'ibur': 'עיבור',
    'yenikah': 'יניקה', 'gadlut': 'גדלות', 'katnut': 'קטנות',
    'nesirah': 'נסירה', 'zivvug': 'זיווג', 'hitpashtut': 'התפשטות',
    'hitlabshut': 'התלבשות', 'histalkut': 'הסתלקות',
    # --- Mondes ---
    'atzilut': 'אצילות', 'beriah': 'בריאה', 'yetzirah': 'יצירה',
    'asiyah': 'עשייה', 'olam': 'עולם', 'olamot': 'עולמות',
    # --- Structure ---
    'keli': 'כלי', 'kelim': 'כלים', 'levush': 'לבוש', 'masakh': 'מסך',
    'parsah': 'פרסה', 'partzuf': 'פרצוף', 'partzufim': 'פרצופים',
    'nekudah': 'נקודה', 'nekudot': 'נקודות', 'kav': 'קו',
    # --- Lumières / flux ---
    'orot': 'אורות', 'nitzotzot': 'ניצוצות', 'kelipot': 'קליפות',
    'kelipah': 'קליפה', 'reshimu': 'רשימו', 'roshem': 'רושם',
    # --- Mohin ---
    'mohin': 'מוחין', 'da_at': 'דעת', 'hevel': 'הבל', 'havalim': 'הבלים',
    'neshikin': 'נשיקין', 'tzelem': 'צלם',
    # --- Noms divins ---
    'ehyeh': 'אהיה', 'havayah': 'הויה', 'elohim': 'אלהים',
    'shaddai': 'שדי', 'adni': 'אדני', 'shem': 'שם',
    # --- Lettres ---
    'yod': 'יוד', 'heh': 'הא', 'vav': 'ואו', 'nun': 'נון',
    'mem': 'מם', 'samekh': 'סמך', 'shin': 'שין', 'dalet': 'דלת',
    'lamed': 'למד', 'tzadi': 'צדי',
    # --- Corps ---
    'gulgalta': 'גולגלתא', 'dikna': 'דיקנא', 'hotma': 'חוטמא',
    'garon': 'גרון', 'hazeh': 'חזה', 'shadayim': 'שדים',
    'zeroa': 'זרוע', 'raglayim': 'רגלים',
    # --- Concepts fréquents ---
    'ratzon': 'רצון', 'elyon': 'עליון', 'devekut': 'דבקות',
    'merkavah': 'מרכבה', 'neshamah': 'נשמה', 'nefesh': 'נפש',
    'ruah': 'רוח', 'dibur': 'דיבור', 'tefilah': 'תפילה',
    'tefillin': 'תפילין', 'shabbat': 'שבת', 'torah': 'תורה',
    'panim': 'פנים', 'achor': 'אחור', 'achorayim': 'אחוריים',
    'klilut': 'כלילות', 'muvhar': 'מובחר', 'gilui': 'גילוי',
    'kisui': 'כיסוי', 'nefilah': 'נפילה', 'aliyah': 'עלייה',
    'aliyat': 'עליית', 'mayin': 'מיין', 'nukvin': 'נוקבין',
    'man': 'מ״ן', 'hassadim': 'חסדים', 'gevurot': 'גבורות',
    'dinim': 'דינים', 'hamtakah': 'המתקה', 'koah': 'כח',
    'halav': 'חלב', 'dam': 'דם', 'shekhinah': 'שכינה',
    'ein': 'אין', 'sof': 'סוף', 'ayin': 'עין',
    'radla': 'רדל״א', 'stima': 'סתימא', 'moha': 'מוחא',
    'idra': 'אדרא', 'zuta': 'זוטא', 'moshe': 'משה',
    'halakhah': 'הלכה', 'gematria': 'גימטריא',
    'shema': 'שמע', 'yisrael': 'ישראל', 'neder': 'נדר',
    'shevuah': 'שבועה', 'kippur': 'כיפור', 'yom': 'יום',
    'hamesh': 'חמש', 'eser': 'עשר', 'shivat': 'שבעת',
    'tlat': 'תלת', 'terin': 'תרין', 'arba': 'ארבע',
    'ehad': 'אחד', 'rishonah': 'ראשונה', 'tatah': 'תתאה',
    'shalem': 'שלם', 'tahton': 'תחתון', 'tedir': 'תדיר',
    'intermittent': 'לפרקים',
    'mazalot': 'מזלות', 'notzer': 'נוצר', 'nakeh': 'ונקה',
    'betisha': 'בטישא', 'piyus': 'פיוס',
    'tipat': 'טיפת', 'itrin': 'עיטרין',
    'milui': 'מילוי', 'milah': 'מילה', 'priah': 'פריעה',
    'atarah': 'עטרה', 'kotel': 'כותל', 'hefsek': 'הפסק',
    'hurban': 'חורבן', 'galut': 'גלות',
    'tanya': 'תניא', 'zohar': 'זוהר',
    'mesirat': 'מסירת', 'behirah': 'בחירה',
    'onesh': 'עונש', 'sekhar': 'שכר',
    'tzaddik': 'צדיק', 'rasha': 'רשע',
    'boneh': 'בונה', 'mayim': 'מים',
    'bokhim': 'בוכים', 'kneh': 'קנה',
    'pekiha': 'פקיחא', 'reuta': 'רעותא',
    'tala': 'טלא', 'bdolha': 'דבדולחא',
    'kruma': 'קרומא', 'avira': 'אוירא',
    'amar': 'עמר', 'naki': 'נקי',
    'kapayim': 'כפים', 'nesiat': 'נשיאת',
    'poel': 'פועל', 'kotz': 'קוץ',
    'bat': 'בת', 'ben': 'בן',
    'pikadon': 'פקדון', 'haarah': 'הארה',
    'mezuzah': 'מזוזה', 'luhot': 'לוחות',
    'zeret': 'זרת', 'middah': 'מידה',
    'gomel': 'גומל', 'dadim': 'דדים',
    'tevunah': 'תבונה', 'shekhinah': 'שכינה',
    'nes': 'נס', 'seter': 'סתר',
    'tardema': 'תרדמה', 'kushit': 'כושית',
    'tziporah': 'ציפורה', 'timna': 'תמנע',
    'shet': 'שת', 'nevuah': 'נבואה',
}

# ============================================================================
# SECTION 2 — DICTIONNAIRE FRANÇAIS (token → français)
# ============================================================================

FRENCH = {
    'keter': 'Couronne', 'chokhmah': 'Sagesse', 'binah': 'Intelligence',
    'da_at': 'Connaissance', 'chesed': 'Bonté', 'gevurah': 'Rigueur',
    'tiferet': 'Beauté', 'netzach': 'Victoire/Endurance', 'hod': 'Splendeur',
    'yesod': 'Fondement', 'malkhut': 'Royauté',
    'arikh_anpin': 'Long Visage', 'abba': 'Père', 'imma': 'Mère',
    'zeir_anpin': 'Petit Visage', 'nukvah': 'Féminin',
    'rachel': 'Rachel', 'leah': 'Léa', 'yaakov': 'Jacob',
    'atik_yomin': 'Ancien des Jours', 'moshe': 'Moïse',
    'ohr': 'Lumière', 'pnimi': 'intérieur', 'makif': 'environnant',
    'yashar': 'direct', 'hozer': 'de retour',
    'tzimtzum': 'Contraction', 'shevirah': 'Brisure', 'tikkun': 'Réparation',
    'birur': 'Clarification', 'ibur': 'Gestation', 'yenikah': 'Allaitement',
    'gadlut': 'Maturité', 'katnut': 'Petitesse',
    'nesirah': 'Sciage/Séparation', 'zivvug': 'Union',
    'atzilut': 'Émanation', 'beriah': 'Création',
    'keli': 'Réceptacle', 'kelim': 'Réceptacles', 'masakh': 'Écran',
    'partzuf': 'Configuration', 'nekudah': 'Point',
    'nitzotzot': 'Étincelles', 'kelipot': 'Écorces',
    'mohin': 'Intellects', 'neshamah': 'Âme', 'nefesh': 'Âme vitale',
    'ruah': 'Esprit', 'tefilah': 'Prière', 'tefillin': 'Phylactères',
    'shabbat': 'Sabbat', 'torah': 'Torah',
    'hassadim': 'Bontés', 'gevurot': 'Rigueurs', 'dinim': 'Jugements',
    'halav': 'Lait', 'dam': 'Sang',
    'dikna': 'Barbe', 'gulgalta': 'Crâne',
    'panim': 'Face', 'achorayim': 'Dos/Arrière',
    'shekhinah': 'Présence divine', 'devekut': 'Adhésion',
    'merkavah': 'Char divin', 'tzelem': 'Image',
    'hitpashtut': 'Déploiement', 'hitlabshut': 'Revêtement',
    'histalkut': 'Retrait', 'hamtakah': 'Adoucissement',
    'halakhah': 'Loi', 'gematria': 'Guematria',
    'mazalot': 'Flux de la Barbe', 'hevel': 'Souffle',
    'neshikin': 'Baisers', 'havalim': 'Souffles',
    'tevunah': 'Discernement',
    'tardema': 'Sommeil profond', 'nesirah': 'Sciage',
}

# ============================================================================
# SECTION 3 — DONNÉES EXPLICITES DES 660 CONCEPTS
# Format: concept_id → (nom_he, nom_fr, description, domaine)
# ============================================================================

CONCEPTS = {
    # ========================================================================
    # SHAAR 1 — KLALIM (Principes généraux)
    # ========================================================================

    # --- EC-K1-001 : Cause et finalité de la création ---
    'ratzon_elyon': ('רצון עליון', 'Volonté supérieure',
        "Cause première de la création : « quand monta dans Sa volonté » (כשעלה ברצונו). Intention divine initiale d’émaner les mondes selon le Etz Chaim.", 'sefirot'),
    'hatavah': ('הטבה', 'Bienfaisance',
        "Finalité primaire de la création : le désir divin de faire le bien (להטיב) aux créatures. Moteur téléologique du processus d’émanation.", 'sefirot'),
    'hakarat_gadluto': ('הכרת גדלותו', 'Reconnaissance de Sa grandeur',
        "Finalité secondaire : que les créatures reconnaissent la grandeur du Créateur. Requiert un sujet conscient capable de percevoir.", 'sefirot'),
    'devekut': ('דבקות', 'Adhésion mystique',
        "Finalité ultime de la création : l’union de l’âme avec le divin. Terme technique de la Kabbale pour l’attachement contemplatif à Dieu.", 'neshamah'),
    'merkavah': ('מרכבה', 'Char divin',
        "Véhicule vers la Devekut. Ézéchiel 1. Dans le Etz Chaim, moyen par lequel l’âme s’élève vers l’union divine.", 'neshamah'),

    # --- EC-K1-002 : Premier acte d’émanation ---
    'nekudah_rishonah': ('נקודה ראשונה', 'Point premier',
        "Première émanation : un point unique contenant les 10 Sefirot en puissance. État d’Akudim où tout est lié dans un seul réceptacle.", 'ohr'),
    'akudim': ('עקודים', 'Liés',
        "Premier état ontologique des Sefirot : dix lumières « liées » (עקודים) dans un seul Keli. Précède Nekudim (points séparés) et Berudim (rectifiés).", 'olamot'),
    'keli_ehad': ('כלי אחד', 'Réceptacle unique',
        "Contenant unifié de l’état d’Akudim. Les dix Sefirot ne sont pas encore différenciées en réceptacles distincts.", 'ohr'),
    'eser_sefirot': ('עשר ספירות', 'Dix Sefirot',
        "Les dix émanations divines, de Keter à Malkhut. Structure fondamentale de toute la Kabbale, contenues en puissance dans la Nekudah Rishonah.", 'sefirot'),

    # --- EC-K1-003 : Analogie des 4 éléments ---
    'arba_yesodot': ('ארבע יסודות', 'Quatre éléments',
        "Analogie (mashal) pour le mélange indistinct des Sefirot dans la Nekudah : comme les 4 éléments composent l’homme sans être distinguables.", 'autre'),
    'herkev_bilti_nikar': ('הרכב בלתי ניכר', 'Composition indiscernable',
        "Pattern de composition où les éléments constitutifs ne sont pas individuellement distinguables. Caractérise l’état pré-différencié.", 'autre'),

    # --- EC-K1-004-005 : Keter et double flux ---
    'keter': ('כתר', 'Couronne',
        "Première et suprême des dix Sefirot. Première dérivation de la Nekudah contenant les 9 autres incluses. Interface entre l’Ein Sof et le système sefirotique.", 'sefirot'),
    'shefa': ('שפע', 'Flux',
        "Influx divin distribué depuis la source vers les réceptacles inférieurs. Les 10 Sefirot tirent Shefa et Hiyut depuis la Nekudah.", 'ohr'),
    'hiyut': ('חיות', 'Vitalité',
        "Force vitale qui anime chaque Sefirah. Distincte du Shefa (influx), la Hiyut est la vie même qui maintient l’existence du réceptacle.", 'ohr'),
    'ma_atzil': ('מאציל', 'Émanateur',
        "Le divin en tant que source transcendante de l’émanation. Distinct de l’émanation elle-même (ne’etzal). Source du Shefa et de la Hiyut.", 'sefirot'),
    'keli_ve_neshamah': ('כלי ונשמה', 'Réceptacle et âme',
        "Unité structurelle fondamentale : chaque Sefirah est un Keli (contenant) habité par une Neshamah (âme/lumière intérieure).", 'ohr'),

    # --- EC-K1-006 : Mashal du Kamtza ---
    'kamtza': ('קמצא', 'Escargot',
        "Mashal zoharique : « comme l’escargot dont le vêtement vient de lui-même ». Illustre l’auto-génération du Keli à partir de l’Ohr.", 'autre'),
    'levush': ('לבוש', 'Vêtement',
        "Revêtement extérieur de la lumière. Le Keli est le Levush auto-généré par l’Ohr lui-même, non un contenant externe.", 'ohr'),
    'keli': ('כלי', 'Réceptacle',
        "Contenant qui reçoit et limite la lumière (Ohr). Le Keli est simultanément ce qui permet la réception et ce qui en fixe les bornes.", 'ohr'),

    # --- EC-K1-007 : Ohr Pnimi et Makif ---
    'ohr_pnimi': ('אור פנימי', 'Lumière intérieure',
        "Portion de lumière effectivement reçue et contenue dans le Keli. Contractée à la mesure du réceptacle. S’oppose à l’Ohr Makif.", 'ohr'),
    'ohr_makif': ('אור מקיף', 'Lumière environnante',
        "Excédent de lumière non contenu par le Keli, qui l’entoure de l’extérieur. Reste en potentialité. Exerce une pression vers l’intérieur.", 'ohr'),
    'tzimtzum_local': ('צמצום מקומי', 'Contraction locale',
        "Contraction de la lumière au niveau d’un Keli individuel, distincte du Tsimtsum cosmique initial. Cause la diminution de l’Ohr Pnimi.", 'ohr'),

    # --- EC-K1-008 : Shekhinah entre les Kerouvim ---
    'shekhinah': ('שכינה', 'Présence divine',
        "Présence immanente de Dieu, contractée entre les Kerouvim (Ex. 25:22). Preuve scripturaire que le divin se contracte pour se manifester.", 'sefirot'),
    'kerouvim': ('כרובים', 'Chérubins',
        "Figures sur l’Arche d’Alliance entre lesquelles la Shekhinah se contracte. Symbolisent les limites de la contraction divine.", 'autre'),
    'dibur': ('דיבור', 'Parole',
        "Manifestation divine dans la contraction : « Je te parlerai d’entre les Kerouvim ». La Parole opère dans l’espace contracté.", 'sefirot'),

    # --- EC-K1-009-010 : Hitpashtut et déploiement séquentiel ---
    'hitpashtut': ('התפשטות', 'Déploiement',
        "Processus d’expansion depuis la Nekudah source vers les 10 Sefirot. Chaque Sefirah se déploie par extraction du Muvhar (élu).", 'ohr'),
    'muvhar': ('מובחר', 'Élu/Sélectionné',
        "Principe de sélection dans le déploiement : de chaque ensemble, le « meilleur » (muvhar) est extrait pour former la Sefirah suivante.", 'ohr'),
    'klilut': ('כלילות', 'Inclusion',
        "Propriété d’inclusion mutuelle des Sefirot : chacune contient les autres. Le reste après extraction du Muvhar est inclus dans la Sefirah formée.", 'sefirot'),
    'chokhmah': ('חכמה', 'Sagesse',
        "Deuxième Sefirah, première à émerger après Keter. Extraite comme Muvhar du reste après la formation de Keter. Contient 8 incluses.", 'sefirot'),
    'binah': ('בינה', 'Intelligence',
        "Troisième Sefirah, extraite du reste après Chokhmah. Faculté de discernement analytique. Contient 7 Sefirot incluses.", 'sefirot'),
    'zeir_anpin': ('זעיר אנפין', 'Petit Visage',
        "Les 6 Sefirot médianes (Chesed-Yesod) en tant que configuration unifiée. Partzuf central du système lourianique, formé des Noblot de Chokhmah.", 'partzufim'),
    'malkhut': ('מלכות', 'Royauté',
        "Dixième et dernière Sefirah. Réceptacle final de toute la lumière émanée. Dernière extraction dans le déploiement séquentiel.", 'sefirot'),
    'gimel_rishonot': ('ג׳ ראשונות', 'Trois premières',
        "Keter, Chokhmah et Binah en tant que catégorie supérieure. Émetteurs internes qui transmettent aux 7 inférieures.", 'sefirot'),
    'zayin_tachtonot': ('ז׳ תחתונות', 'Sept inférieures',
        "Les 7 Sefirot de Chesed à Malkhut. Catégorie inférieure, réceptrices du flux des 3 premières.", 'sefirot'),

    # --- EC-K1-011-012 : Olam HaTohu et cascade de Makifim ---
    'olam_ha_tohu': ('עולם התוהו', 'Monde du Chaos',
        "État pré-réparation où les Sefirot existent comme points isolés sans interaction. Synonyme d’Olam HaNekudot.", 'olamot'),
    'olam_ha_nekudot': ('עולם הנקודות', 'Monde des Points',
        "Synonyme d’Olam HaTohu. Les Sefirot y sont des « points » (Nekudot) séparés, sans Partzuf, voués à la brisure.", 'olamot'),
    'nekudot': ('נקודות', 'Points',
        "Forme pré-Tikkun des Sefirot : des points isolés, non structurés en configurations (Partzufim). Fragiles, sujets à la Shevirah.", 'olamot'),
    'cascade_ohr': ('מפל אור', 'Cascade de lumière',
        "Mécanisme de transmission des Orot Makifim : chaque Sefirah hérite du Makif excédentaire de la Sefirah supérieure.", 'ohr'),
    'makif_elyon': ('מקיף עליון', 'Makif supérieur',
        "Lumière environnante héritée de la Sefirah supérieure, plus élevée en intensité que le Makif propre.", 'ohr'),
    'makif_tahton': ('מקיף תחתון', 'Makif inférieur',
        "Lumière environnante propre à la Sefirah, générée par l’excédent de son propre Keli.", 'ohr'),
    'ein_sof_makif': ('אין סוף מקיף', 'Ein Sof environnant',
        "Lumière environnante globale de l’Ein Sof qui entoure l’ensemble du système sefirotique.", 'ohr'),

    # --- EC-K1-013-014 : Koah HaKabalah et modes de transmission ---
    'koah_ha_kabalah': ('כח הקבלה', 'Capacité de réception',
        "Capacité intrinsèque de chaque Keli à recevoir la lumière. Varie d’une Sefirah à l’autre et détermine le ratio Pnimi/Makif.", 'ohr'),
    'shemesh': ('שמש', 'Soleil',
        "Mashal solaire pour les modes de transmission de la lumière : directe, par fenêtre, par écran, etc.", 'autre'),
    'chalon': ('חלון', 'Fenêtre',
        "Mode de transmission de la lumière par ouverture directe. Le Yesod fonctionne comme fenêtre entre les niveaux.", 'ohr'),
    'masakh': ('מסך', 'Écran',
        "Barrière filtrante qui atténue la lumière lors de sa transmission. En Atzilut, pas de Masakh ; en Beriah et au-dessous, Masakh présent.", 'ohr'),
    'rihuk_makom': ('ריחוק מקום', 'Éloignement spatial',
        "Mode d’atténuation par distance. Plus la Sefirah est éloignée de la source, plus la lumière est affaiblie.", 'ohr'),
    'nekev_katan': ('נקב קטן', 'Petite ouverture',
        "Mode de transmission minimale : un trou étroit qui ne laisse passer qu’une fraction infime de la lumière.", 'ohr'),

    # --- EC-K1-015-016 : Atzilut, Arikh Anpin et gradient de transmission ---
    'atzilut': ('אצילות', 'Émanation',
        "Premier et plus élevé des quatre mondes. Sans Masakh. Animé directement par Arikh Anpin. Transparence maximale.", 'olamot'),
    'arikh_anpin': ('אריך אנפין', 'Long Visage',
        "Premier Partzuf, configuration de Keter. Anime tout le monde d’Atzilut. Ses NHY s’étendent dans Abba et Imma.", 'partzufim'),
    'yesod': ('יסוד', 'Fondement',
        "Neuvième Sefirah. Organe de transmission entre niveaux. Porte la double fonction de canal (Chalon) et de filtre (Masakh).", 'sefirot'),
    'yesod_abba': ('יסוד אבא', 'Fondement du Père',
        "Le Yesod de la configuration Abba. Fenêtre moyenne — plus large que celle de ZA, plus étroite que le Chalon direct.", 'partzufim'),
    'yesod_za': ('יסוד ז״א', 'Fondement de Zeir Anpin',
        "Le Yesod du Petit Visage. Fenêtre très étroite, synthèse des 6 Havalim du corps. Canal vers Nukvah.", 'partzufim'),
    'vav_ketzavot': ('ו׳ קצוות', 'Six extrémités',
        "Les 6 Sefirot de Chesed à Yesod formant le corps de ZA, sans la tête (Keter/Chokhmah/Binah). Fenêtres égales entre elles.", 'partzufim'),
    'gradient_transmission': ('מדרג העברה', 'Gradient de transmission',
        "Pattern de diminution progressive de la lumière à travers les niveaux : AA transmet le plus, ZA le moins.", 'ohr'),

    # --- EC-K1-017-018 : Circuits et frontière ---
    'sheva_hakkafot': ('שבע הקפות', 'Sept circuits',
        "Structure de sept circuits dans le système sefirotique, correspondant aux 7 Sefirot inférieures.", 'sefirot'),
    'parsah': ('פרסה', 'Membrane/Frontière',
        "Frontière ontologique entre Atzilut et Beriah. Filtre qui transforme la nature de la lumière qui la traverse.", 'olamot'),
    'beriah': ('בריאה', 'Création',
        "Deuxième des quatre mondes, sous la Parsah. Premier monde « avec écran » (Masakh). Lumière filtrée.", 'olamot'),

    # --- EC-K1-019-021 : Panim/Achor, Abba, Imma, lettres ---
    'panim_be_panim': ('פנים בפנים', 'Face à face',
        "Mode de réception pleine : les Partzufim se font face, maximisant le flux. État optimal post-Tikkun.", 'zivvug'),
    'achor_be_achor': ('אחור באחור', 'Dos à dos',
        "Mode de réception réduite : Partzufim dos à dos, flux minimal. État pré-Tikkun ou de diminution.", 'zivvug'),
    'koah_ha_sevil': ('כח הסביל', 'Capacité à supporter',
        "Capacité d’un Partzuf à supporter l’intensité de la lumière. Insuffisante, elle cause le retournement dos à dos.", 'ohr'),
    'abba': ('אבא', 'Père',
        "Partzuf de Chokhmah. Récepteur stable de la lumière de AA. Plus résilient qu’Imma face à l’intensité lumineuse.", 'partzufim'),
    'imma': ('אמא', 'Mère',
        "Partzuf de Binah. Récepteur plus limité que Abba. Parent de ZA. Son Yesod détermine la couverture des Hassadim.", 'partzufim'),
    'tzadi': ('צדי', 'Lettre Tsadi',
        "Diagramme littéral du couple ZA-Nukvah : la lettre צ montre un Yod (Abba) lié à un Nun courbé (Imma).", 'autre'),
    'yod': ('יוד', 'Lettre Yod',
        "Représente Abba dans l’alphabet mystique. Plus petite lettre, condensation maximale de la lumière.", 'autre'),
    'nun_kefufah': ('נון כפופה', 'Noun courbé',
        "Représente Imma dans le diagramme du Tsadi. La courbure signifie l’aspect réceptif et descendant.", 'autre'),

    # --- EC-K1-022-026 : Shevirah et ses conséquences ---
    'shevirat_ha_kelim': ('שבירת הכלים', 'Brisure des réceptacles',
        "Catastrophe cosmique : les Kelim des Sefirot de Tohu ne supportent pas l’intensité de la lumière et se brisent. Événement fondateur de la Kabbale lourianique.", 'shevirah'),
    'da_at': ('דעת', 'Connaissance',
        "Sefirah intermédiaire entre Chokhmah et Binah. Premier Keli brisé selon le Etz Chaim. Union intime du savoir.", 'sefirot'),
    'bela_ben_beor': ('בלע בן בעור', 'Bela fils de Béor',
        "Correspondance biblique (Genèse 36) du premier roi d’Édom, identifié à Da’at, premier Keli brisé.", 'shevirah'),
    'shivat_melakhim': ('שבעת מלכים', 'Sept rois',
        "Les 7 rois d’Édom (Genèse 36) qui « régnèrent et moururent » — cadre narratif de la Shevirah des 7 Sefirot inférieures.", 'shevirah'),
    'shevirat_keli': ('שבירת כלי', 'Brisure du réceptacle',
        "Processus de brisure d’un Keli individuel : l’excès de lumière fait éclater le contenant, les fragments tombent.", 'shevirah'),
    'nefilah': ('נפילה', 'Chute',
        "Chute des fragments de Kelim brisés vers les mondes inférieurs. Les débris deviennent substrat des Kelipot.", 'shevirah'),
    'malkhei_edom': ('מלכי אדום', 'Rois d’Édom',
        "Les rois d’Édom comme correspondance biblique de la Shevirah. Édom = Din (rigueur) non tempérée.", 'shevirah'),
    'rihuk': ('ריחוק', 'Éloignement',
        "Facteur atténuant dans la Shevirah : l’éloignement de la source réduit l’impact de la brisure.", 'shevirah'),
    'kotan_keli': ('קוטן כלי', 'Petitesse du réceptacle',
        "Facteur aggravant de la Shevirah : plus le Keli est petit, plus il est vulnérable à la brisure.", 'shevirah'),
    'yesod_hai': ('יסוד חי', 'Fondement vivant',
        "Yesod comme survivant partiel de la Shevirah. Conserve une part de lumière même après la brisure.", 'shevirah'),
    'helek_malkhut': ('חלק מלכות', 'Part de Malkhut',
        "La portion préservée de Malkhut dans Yesod après la Shevirah. Germe du Tikkun futur.", 'shevirah'),
    'tzinor': ('צינור', 'Canal',
        "Canal intact hypothétique reliant le monde brisé à sa source. Si préservé, permettrait la réparation directe.", 'ohr'),
    'gilui': ('גילוי', 'Révélation/Exposition',
        "Exposition directe de la lumière sans filtre. Cause de la Shevirah quand les Kelim ne peuvent supporter.", 'ohr'),
    'partzuf_shalem': ('פרצוף שלם', 'Configuration complète',
        "Résultat du Tikkun : les Nekudot isolées sont réorganisées en configurations complètes et interactives.", 'tikkun'),

    # --- EC-K1-027-028 : Nitzotzot, Kelipot, Tikkun ---
    'nitzotzot': ('ניצוצות', 'Étincelles',
        "Étincelles de lumière sainte piégées dans les fragments de Kelim après la Shevirah. Leur élévation est le but du Tikkun.", 'nitzotzot'),
    'kelipot': ('קליפות', 'Écorces',
        "Résidu de la Shevirah : les fragments de Kelim brisés deviennent des « écorces » qui emprisonnent les Nitzotzot.", 'kelipot'),
    'orot_nistalkeu': ('אורות נסתלקו', 'Lumières retirées',
        "Lumières qui remontent vers leur source après la brisure de leur Keli. Ne restent pas dans les débris.", 'shevirah'),
    'ma_anin_tevirin': ('מאני תבירין', 'Vases brisés',
        "Expression araméenne du Zohar pour les Kelim brisés. Source du mal : les débris non réparés.", 'shevirah'),
    'tikkun': ('תיקון', 'Réparation',
        "Processus cosmique de réparation de la Shevirah. Réorganisation des fragments en Partzufim, élévation des Nitzotzot.", 'tikkun'),
    'tefilah': ('תפילה', 'Prière',
        "Moyen de Tikkun : la prière élève les Nitzotzot en catalysant les unions (Zivvugim) dans les mondes supérieurs.", 'tikkun'),
    'ma_asim_tovim': ('מעשים טובים', 'Bonnes actions',
        "Moyen de Tikkun : les bonnes actions dans le monde matériel élèvent les étincelles piégées dans les Kelipot.", 'tikkun'),
    'aliyat_nitzotzot': ('עליית ניצוצות', 'Élévation des étincelles',
        "Processus d’élévation des Nitzotzot par niveaux (Asiyah→Yetzirah→Beriah→Atzilut). Mécanisme central du Tikkun.", 'nitzotzot'),
    'abya': ('אבי״ע', 'ABYA (4 mondes)',
        "Acronyme des quatre mondes : Atzilut, Beriah, Yetzirah, Asiyah. Échelle d’élévation des Nitzotzot.", 'olamot'),

    # --- EC-K1-029-031 : Mayin Nukvin, Zivvug, Shevirah intentionnelle ---
    'mayin_nukvin': ('מיין נוקבין', 'Eaux féminines',
        "Eaux féminines ascendantes : les Nitzotzot élevés deviennent catalyseur (MaN) qui provoque le Zivvug en haut.", 'zivvug'),
    'nitzotzot_as_man': ('ניצוצות כמ״ן', 'Étincelles comme MaN',
        "Les Nitzotzot élevés fonctionnent comme Mayin Nukvin, catalysant l’union des Partzufim supérieurs.", 'zivvug'),
    'zivvug': ('זיווג', 'Union',
        "Union sacrée entre Partzufim masculin et féminin. Provoquée par les MaN. Produit de nouvelles lumières (Mohin).", 'zivvug'),
    'asarah_harugei_malkhut': ('עשרה הרוגי מלכות', 'Dix martyrs',
        "Application historique du Tikkun : les dix sages martyrisés par Rome élèvent des Nitzotzot par leur sacrifice.", 'tikkun'),
    'hurban': ('חורבן', 'Destruction',
        "Contexte de crise (destruction du Temple) comme moment intensif de Shevirah et d’opportunité de Tikkun.", 'shevirah'),
    'mesirat_nefesh': ('מסירת נפש', 'Don de soi',
        "Le sacrifice total comme catalyseur suprême de Tikkun. Élève les Nitzotzot les plus profondément enfouis.", 'tikkun'),
    'alah_be_mahshavah': ('עלה במחשבה', 'Monta dans la pensée',
        "L’intentionnalité divine derrière la Shevirah : Dieu « savait » que les mondes seraient brisés et reconstruits.", 'shevirah'),
    'boneh_olamot': ('בונה עולמות', 'Constructeur de mondes',
        "Pattern de construction-destruction : Dieu « construit des mondes et les détruit » avant la création finale.", 'shevirah'),
    'shevirah_intentionnelle': ('שבירה מכוונת', 'Brisure intentionnelle',
        "Doctrine selon laquelle la Shevirah fait partie du plan divin : nécessaire pour créer le libre arbitre et le Tikkun.", 'shevirah'),

    # --- EC-K1-032-034 : Tikkun HB, Achorayim, Noblot ---
    'tikkun_hb': ('תיקון ח״ב', 'Tikkun de Chokhmah-Binah',
        "Réparation des Sefirot supérieures (Chokhmah et Binah) : première étape du Tikkun, qui précède celui des inférieures.", 'tikkun'),
    'achorayim': ('אחוריים', 'Aspects postérieurs',
        "Les « dos » des Sefirot : aspects qui tombent lors de la Shevirah. Source du matériau pour les Partzufim secondaires.", 'sefirot'),
    'yaakov': ('יעקב', 'Jacob',
        "Formé des Achorayim : Jacob est le Yesod de Arikh Anpin. Aspect extérieur de la même source que Moïse.", 'partzufim'),
    'leah': ('לאה', 'Léa',
        "Partzuf de Malkhut de Tevunah, formée des Achorayim. Située du Da’at à la poitrine (Hazeh) de ZA.", 'partzufim'),
    'hashpa_ah_retroactive': ('השפעה רטרואקטיבית', 'Influence rétroactive',
        "Effet remontant : l’action du réceptacle (Mekabel) influence la source (Mashpia). Le Tikkun d’en bas affecte le haut.", 'tikkun'),
    'mekabel_magbil_mashpia': ('מקבל מגביל משפיע', 'Le récepteur limite l’émetteur',
        "Principe : la capacité du récepteur détermine ce que l’émetteur peut transmettre. Le bas conditionne le haut.", 'ohr'),
    'noblot': ('נובלות', 'Retombées',
        "Retombées créatives des Sefirot supérieures. « Noblot de Chokhmah = Torah » (Berakhot 57a). Source de ZA et Nukvah.", 'ohr'),
    'noblot_chokhmah': ('נובלות חכמה', 'Retombées de Sagesse',
        "Les retombées de Chokhmah qui forment Zeir Anpin. « La Torah est Noblot de Chokhmah. »", 'ohr'),
    'noblot_binah': ('נובלות בינה', 'Retombées d’Intelligence',
        "Les retombées de Binah qui forment Nukvah/Shekhinah.", 'ohr'),
    'nukvah': ('נוקבא', 'Féminin',
        "Partzuf féminin, configuration de Malkhut. Formée des Noblot de Binah. Réceptacle ultime du système.", 'partzufim'),
    'torah_as_za': ('תורה כז״א', 'Torah comme ZA',
        "Identification de la Torah avec Zeir Anpin : la Torah est l’aspect masculin du divin manifesté.", 'partzufim'),
    'shekhinah_as_nukvah': ('שכינה כנוקבא', 'Shekhinah comme Nukvah',
        "Identification de la Shekhinah avec Nukvah : la Présence divine est l’aspect féminin réceptif.", 'partzufim'),

    # --- EC-K1-035-036 : Cycle MaN, Zivvugim, prière ---
    'man_tzaddikim': ('מ״ן צדיקים', 'MaN des justes',
        "Force ascendante des justes qui catalyse le Zivvug dans les mondes supérieurs.", 'zivvug'),
    'man_cycle': ('מחזור מ״ן', 'Cycle de MaN',
        "Cycle ascendant : actions humaines → MaN → Zivvug ZuN → Zivvug AVI → nouvelles lumières descendantes.", 'zivvug'),
    'zivvug_zun': ('זיווג זו״ן', 'Union ZA-Nukvah',
        "Union de Zeir Anpin et Nukvah, premier niveau de Zivvug provoqué par les MaN.", 'zivvug'),
    'zivvug_avi': ('זיווג או״א', 'Union Abba-Imma',
        "Union d’Abba et Imma, deuxième niveau de Zivvug. Produit les Mohin pour ZA.", 'zivvug'),
    'fractalité': ('פרקטליות', 'Fractalité',
        "Pattern récurrent : la même structure (cause→catalyseur→union→produit) se répète à chaque niveau du système.", 'autre'),
    'nefilat_apayim': ('נפילת אפים', 'Prosternation',
        "Acte liturgique de Tikkun : la prosternation dans la prière élève les Nitzotzot de Nukvah/Rachel.", 'tikkun'),
    'rachel': ('רחל', 'Rachel',
        "Partzuf féminin inférieur, de la poitrine de ZA vers le bas. Réceptrice des MaN. Associée à la prière de jour.", 'partzufim'),
    'shema_yisrael': ('שמע ישראל', 'Écoute Israël',
        "Proclamation d’unité divine qui élève vers le niveau d’Abba-Imma. Acte de Tikkun par la parole.", 'tikkun'),

    # ========================================================================
    # SHAAR 2 — KLALIM (suite)
    # ========================================================================

    'hitpashtut_tikkun': ('התפשטות תיקון', 'Déploiement du Tikkun',
        "Expansion distributive du processus de réparation à travers les niveaux.", 'tikkun'),
    'rihuk_tikkun': ('ריחוק תיקון', 'Éloignement protecteur',
        "L’éloignement entre les niveaux protège les inférieurs de l’intensité de la lumière non filtrée.", 'tikkun'),
    'kisui': ('כיסוי', 'Couverture',
        "Couverture de la lumière par les Kelim ou les NHY d’Imma. Protège contre l’adhérence des forces extérieures.", 'ohr'),
    'kiyum': ('קיום', 'Stabilité',
        "Résultat de la couverture : la stabilité du système dépend de la protection adéquate de la lumière.", 'ohr'),
    'nekudah_to_partzuf': ('נקודה לפרצוף', 'Point vers Configuration',
        "Transformation clé du Tikkun : chaque Nekudah (point isolé) devient un Partzuf (configuration complète).", 'tikkun'),
    'koah_le_poel': ('כח לפועל', 'Potentiel vers actuel',
        "Principe philosophique : passage de la puissance (Koah) à l’acte (Poel). Sous-tend la transformation Nekudah→Partzuf.", 'autre'),
    'hamesh_partzufim': ('חמש פרצופים', 'Cinq Partzufim',
        "Structure complète du Tikkun : Arikh Anpin, Abba, Imma, Zeir Anpin, Nukvah. Cinq configurations.", 'partzufim'),
    'bat': ('בת', 'Fille',
        "Synonyme de Nukvah dans certains contextes. La « fille » comme configuration féminine.", 'partzufim'),

    # --- Shem HaVaYaH et lettres ---
    'shem_havayah': ('שם הוי״ה', 'Nom YHVH',
        "Le Tétragramme encode les 5 Partzufim : Kotz du Yod = AA, Yod = Abba, Heh = Imma, Vav = ZA, Heh = Nukvah.", 'partzufim'),
    'kotz_yod': ('קוץ יוד', 'Pointe du Yod',
        "L’épine du Yod dans le Tétragramme représente Arikh Anpin/Keter.", 'partzufim'),
    'heh_rishonah': ('ה׳ ראשונה', 'Premier Heh',
        "Le premier Heh du Tétragramme représente Imma/Binah.", 'partzufim'),
    'vav': ('ואו', 'Lettre Vav',
        "Le Vav du Tétragramme représente Zeir Anpin (valeur 6 = 6 Sefirot).", 'partzufim'),
    'heh_tatah': ('ה׳ תתאה', 'Heh inférieur',
        "Le deuxième Heh du Tétragramme représente Nukvah/Malkhut.", 'partzufim'),

    # --- Questions théologiques ---
    'kushia_shevirah': ('קושיית שבירה', 'Question de la brisure',
        "Question théologique : pourquoi Dieu, omniscient, a-t-il créé des réceptacles voués à se briser ?", 'shevirah'),
    'yediat_ma_atzil': ('ידיעת מאציל', 'Omniscience de l’Émanateur',
        "L’omniscience divine implique que la Shevirah était prévue et intentionnelle.", 'shevirah'),
    'behirah': ('בחירה', 'Libre arbitre',
        "Le libre arbitre nécessite l’existence du mal (issu de la Shevirah). Sans Shevirah, pas de choix, pas de mérite.", 'tikkun'),
    'tov_va_ra': ('טוב ורע', 'Bien et mal',
        "La dualité bien/mal, condition du libre arbitre. Issue du mélange des Nitzotzot et des Kelipot après la Shevirah.", 'tikkun'),
    'shoresh_ha_ra': ('שורש הרע', 'Racine du mal',
        "Origine du mal dans la Shevirah : les fragments non réparés deviennent les Kelipot, substrat du mal.", 'kelipot'),
    'sekhar_ve_onesh': ('שכר ועונש', 'Récompense et punition',
        "Conséquence du libre arbitre : le juste élève les Nitzotzot (récompense), le méchant les abaisse (punition).", 'tikkun'),
    'tzaddik': ('צדיק', 'Juste',
        "Le juste comme élévateur de Nitzotzot. Ses actions transforment les Kelipot en sainteté.", 'tikkun'),
    'rasha': ('רשע', 'Méchant',
        "Le méchant abaisse la lumière vers les Kelipot. Inverse du processus de Tikkun.", 'kelipot'),
    'kelipah_as_punishment': ('קליפה כעונש', 'Kelipah comme punition',
        "L’auto-punition du méchant : en se liant aux Kelipot, il s’enferme lui-même dans l’écorce.", 'kelipot'),

    # --- Malkhut originelle et Tikkun ---
    'malkhut_originelle': ('מלכות מקורית', 'Malkhut originelle',
        "Position haute de Malkhut avant la Shevirah. Objectif du Tikkun : la rétablir à sa position.", 'tikkun'),
    'ha_alaat_malkhut': ('העלאת מלכות', 'Élévation de Malkhut',
        "Objectif ultime du Tikkun : remonter Malkhut à sa position originelle élevée.", 'tikkun'),

    # --- Tlat Rishin de AA ---
    'tlat_rishin': ('תלת רישין', 'Trois têtes',
        "Structure triple d’Arikh Anpin : Radla (inconnaissable), Moha Stima’ah (cerveau scellé), Gulgalta (crâne).", 'partzufim'),
    'radla': ('רדל״א', 'Tête inconnaissable',
        "Reisha DeLo Ityada : la tête suprême d’AA, absolument inconnaissable. Au-delà de toute appréhension.", 'partzufim'),
    'ayin': ('עין', 'Néant',
        "Le Ayin (néant) comme source créative. Paradoxe : c’est du néant que jaillit l’être (Yesh me-Ayin).", 'sefirot'),
    'moha_stima_ah': ('מוחא סתימאה', 'Cerveau scellé',
        "Deuxième tête d’AA : le cerveau scellé, inaccessible directement. Source cachée de la Sagesse.", 'partzufim'),
    'atik_yomin': ('עתיק יומין', 'Ancien des Jours',
        "Aspect interne d’Arikh Anpin. L’intériorité de Keter. Daniel 7:9.", 'partzufim'),
    'atik_stam': ('עתיק סתם', 'Atik simple',
        "Atik dans ses trois Rishin : aspect le plus intérieur du système des Partzufim.", 'partzufim'),
    'pnimiyut_aa': ('פנימיות א״א', 'Intériorité d’AA',
        "L’âme (Neshamah) d’Arikh Anpin. Le niveau le plus profond du premier Partzuf.", 'partzufim'),

    # --- Tikkunei Gulgalta ---
    'tikkunei_gulgalta': ('תיקוני גולגלתא', 'Rectifications du crâne',
        "Sept rectifications du crâne d’Arikh Anpin selon l’Idra Rabba.", 'dikna'),
    'gulgalta': ('גולגלתא', 'Crâne',
        "Le crâne d’Arikh Anpin : structure externe de Keter. Contient les 3 Rishin.", 'partzufim'),
    'tala_de_bdolha': ('טלא דבדולחא', 'Rosée de cristal',
        "Rosée qui descend du crâne d’AA. Ressuscite les morts dans l’ère messianique.", 'dikna'),
    'kruma_de_avira': ('קרומא דאוירא', 'Membrane de l’air',
        "Membrane subtile entourant le crâne d’AA. Filtre entre l’intérieur et l’extérieur.", 'dikna'),
    'reuta_de_reavin': ('רעותא דרעוין', 'Volonté des volontés',
        "La volonté suprême dans le crâne d’AA. Racine de tout désir et intention.", 'dikna'),
    'amar_naki': ('עמר נקי', 'Laine pure',
        "Les cheveux d’AA comparés à la laine pure (Daniel 7:9). Canaux de transmission.", 'dikna'),
    'pekiha': ('פקיחא', 'Œil vigilant',
        "L'œil toujours ouvert d’AA : surveillance sans cesse, miséricorde permanente.", 'dikna'),
    'hotma': ('חוטמא', 'Nez',
        "Le nez d’AA : source du souffle vital qui anime les mondes inférieurs.", 'dikna'),

    # --- Extension et naissance simultanée ---
    'hitpashtut_tikkunim': ('התפשטות תיקונים', 'Extension des rectifications',
        "Les Tikkunim de la tête d’AA s’étendent vers le bas pour rectifier les niveaux de la Shevirah.", 'tikkun'),
    'ke_hada_nafkin': ('כחדא נפקין', 'Sortent ensemble',
        "Expression de l’Idra Zuta : Abba et Imma « sortent ensemble » — naissance simultanée.", 'partzufim'),
    'ke_hada_sharyan': ('כחדא שריין', 'Résident ensemble',
        "Abba et Imma résident ensemble face à face en permanence.", 'partzufim'),
    'lo_mitparshin': ('לא מתפרשין', 'Ne se séparent jamais',
        "Union permanente d’Abba et Imma : ils ne se séparent jamais l’un de l’autre.", 'zivvug'),
    'idra_zuta': ('אדרא זוטא', 'Petite assemblée',
        "Source zoharique pour la doctrine d’AVI. Dernière assemblée de Rabbi Shimon avant sa mort.", 'autre'),

    # --- Types de Zivvug ---
    'zivvug_tedir': ('זיווג תדיר', 'Union permanente',
        "Union permanente d’Abba et Imma. Ne cesse jamais, source constante de vitalité.", 'zivvug'),
    'zivvug_intermittent': ('זיווג לפרקים', 'Union intermittente',
        "Union variable de ZA et Nukvah. Dépend des MaN et des conditions.", 'zivvug'),

    # --- Zeroa et structure ---
    'zeroa_yemin': ('זרוע ימין', 'Bras droit',
        "Le bras droit d’Arikh Anpin : source d’Abba. Chesed de AA.", 'partzufim'),
    'zeroa_smol': ('זרוע שמאל', 'Bras gauche',
        "Le bras gauche d’Arikh Anpin : source d’Imma. Gevurah de AA.", 'partzufim'),
    'tlat_prakin': ('תלת פרקין', 'Trois articulations',
        "Trois segments du bras de AA, correspondant aux trois Sefirot de chaque colonne.", 'partzufim'),
    'nesiat_kapayim': ('נשיאת כפים', 'Élévation des paumes',
        "Bénédiction sacerdotale : justification hiérarchique du flux depuis les bras de AA.", 'halakhah'),

    # --- Garon et Ketarim ---
    'garon_aa': ('גרון א״א', 'Gorge d’AA',
        "La gorge d’Arikh Anpin : lieu d’émergence des Ketarim d’Abba et Imma.", 'partzufim'),
    'keter_abba': ('כתר אבא', 'Couronne d’Abba',
        "Le Keter d’Abba émerge de la gorge droite de AA.", 'partzufim'),
    'keter_imma': ('כתר אמא', 'Couronne d’Imma',
        "Le Keter d’Imma émerge de la gorge gauche de AA.", 'partzufim'),
    'kneh': ('קנה', 'Trachée',
        "La trachée de AA, canal de transmission. Double sens : canal physique et roseau (instrument).", 'partzufim'),

    # --- Mayim Tachtonim et Hitlabshut ---
    'mayim_tachtonim': ('מים תחתונים', 'Eaux inférieures',
        "NHY de AA exposées sans couverture : comme des « eaux inférieures » qui pleurent d’être séparées.", 'partzufim'),
    'bokhim': ('בוכים', 'Pleurent',
        "Les eaux inférieures « pleurent » (Tikkunei Zohar) : l’excès de lumière exposée sans couverture.", 'ohr'),
    'hitlabshut': ('התלבשות', 'Revêtement',
        "Processus par lequel un niveau supérieur se « revêt » dans un inférieur. Couverture manquante dans NHY de AA.", 'ohr'),

    # --- Tlat go Tlat et Ibur ---
    'tlat_go_tlat': ('תלת גו תלת', 'Trois dans trois',
        "Mécanisme d’inclusion : NHY remontent dans HGT, HGT dans KHB. Processus de 9 mois de gestation.", 'mohin'),
    'aliyat_orot': ('עליית אורות', 'Remontée des lumières',
        "Les lumières remontent avec les NHY dans le processus de Tlat go Tlat.", 'mohin'),
    'ibur_za': ('עיבור ז״א', 'Gestation de ZA',
        "La conception de Zeir Anpin dans le ventre d’Imma. Premier stade de formation.", 'mohin'),
    'imma_me_uberet': ('אמא מעוברת', 'Mère enceinte',
        "Imma en état de gestation, portant ZA en formation dans ses NHY.", 'mohin'),
    'hibur_avi': ('חיבור או״א', 'Union d’Abba-Imma',
        "L’union productive d’Abba et Imma qui aboutit à la conception de ZA.", 'zivvug'),

    # --- Hevel et Mohin ---
    'hevel': ('הבל', 'Souffle',
        "Souffle subtil échangé lors du Zivvug. Catalyseur de l’union entre Abba et Imma.", 'zivvug'),
    'mohin': ('מוחין', 'Intellects/Cerveaux',
        "Les « cerveaux » — lumières intellectuelles qui animent les Partzufim. Chokhmah, Binah et Da’at de chaque niveau.", 'mohin'),
    'yesod_aa': ('יסוד א״א', 'Fondement d’AA',
        "Le Yesod d’Arikh Anpin, émetteur du Hevel qui catalyse le Zivvug d’AVI.", 'partzufim'),
    'hitorerut_zivvug': ('התעוררות זיווג', 'Éveil à l’union',
        "L’éveil qui précède le Zivvug, déclenché par le Hevel du Yesod de AA.", 'zivvug'),

    # --- Zivvug sans MaN ---
    'zivvug_be_lo_man': ('זיווג בלי מ״ן', 'Union sans catalyseur',
        "Union d’AVI sans Mayin Nukvin, par pure grâce (Chesed). Fonde le monde initial.", 'zivvug'),
    'chesed_pur': ('חסד טהור', 'Bonté pure',
        "Mode de grâce inconditionnelle. Le Zivvug initial d’AVI ne requiert pas de catalyseur d’en bas.", 'zivvug'),
    'olam_chesed_yibaneh': ('עולם חסד יבנה', 'Le monde est bâti sur la bonté',
        "Psaumes 89:3. Fondement du monde : la première création est un acte de grâce pure.", 'zivvug'),

    # --- Neshikin et Havalim ---
    'neshikin': ('נשיקין', 'Baisers',
        "Les « baisers » dans le Zivvug d’AVI : échange de lumières Chokhmah entre les bouches.", 'zivvug'),
    'havalim': ('הבלים', 'Souffles',
        "Souffles échangés lors du Zivvug. Cinq Havalim correspondent aux 5 sorties de la bouche.", 'zivvug'),
    'natan_ve_kibel': ('נתן וקיבל', 'Donner et recevoir',
        "Dynamique de l’échange dans le Zivvug : chaque Partzuf donne et reçoit simultanément.", 'zivvug'),
    'hamesh_motzaot': ('חמש מוצאות', 'Cinq sorties de la bouche',
        "Les 5 organes de phonation (gorge, palais, langue, dents, lèvres) = 5 Havalim.", 'zivvug'),
    'piyus': ('פיוס', 'Persuasion',
        "La persuasion dans le Zivvug : le Hevel « persuade » le partenaire d’accepter l’union.", 'zivvug'),

    # --- Produits du Zivvug ---
    'neshamah_le_neshamah': ('נשמה לנשמה', 'Âme pour âme',
        "Plus haut produit du Zivvug d’AVI : l’âme de l’âme, issue des Neshikin.", 'neshamah'),
    'ruah_be_ruah': ('רוח ברוח', 'Esprit dans esprit',
        "Deuxième produit du Zivvug : l’esprit, issu des Havalim.", 'neshamah'),
    'nefesh': ('נפש', 'Âme vitale',
        "Troisième produit du Zivvug : l’âme vitale, issue du Dibur (parole).", 'neshamah'),
    'madregot_neshamah': ('מדרגות נשמה', 'Niveaux de l’âme',
        "Hiérarchie des trois niveaux de l’âme : Nefesh, Ruah, Neshamah, correspondant aux trois modes du Zivvug.", 'neshamah'),

    # --- Formation des Kelim de ZA ---
    'kelim_za': ('כלים ז״א', 'Réceptacles de ZA',
        "Les 6 Kelim de Zeir Anpin formés par les produits du Zivvug d’AVI.", 'partzufim'),
    'chesed_za': ('חסד ז״א', 'Chesed de ZA',
        "Le Chesed de ZA, formé des Neshikin d’Abba (côté droit).", 'partzufim'),
    'gevurah_za': ('גבורה ז״א', 'Gevurah de ZA',
        "La Gevurah de ZA, formée des Neshikin d’Imma (côté gauche).", 'partzufim'),
    'netzach_za': ('נצח ז״א', 'Netzach de ZA',
        "Le Netzach de ZA, formé du Hevel d’Abba.", 'partzufim'),
    'hod_za': ('הוד ז״א', 'Hod de ZA',
        "Le Hod de ZA, formé du Hevel d’Imma.", 'partzufim'),
    'tiferet_za': ('תפארת ז״א', 'Tiferet de ZA',
        "La Tiferet de ZA : médiatrice et harmonisatrice entre Chesed et Gevurah.", 'partzufim'),
    'klilut_reciproque': ('כלילות הדדית', 'Inclusion réciproque',
        "Inclusion mutuelle des Sefirot les unes dans les autres. Chaque Sefirah contient des aspects de toutes les autres.", 'sefirot'),
    'makhria': ('מכריע', 'Harmonisateur',
        "Tiferet comme force d’harmonisation entre les opposés Chesed et Gevurah. Ligne médiane.", 'sefirot'),
    'malkhut_za': ('מלכות ז״א', 'Malkhut de ZA',
        "La Malkhut de ZA, formée du Dibur d’Abba. Réceptacle final au sein du Petit Visage.", 'partzufim'),
    'hevel_kolel': ('הבל כולל', 'Souffle englobant',
        "Le Hevel qui englobe et synthétise tous les autres souffles dans le processus de formation.", 'zivvug'),

    # ========================================================================
    # SHAAR 3 — IBUR (Gestation)
    # ========================================================================

    'ibur': ('עיבור', 'Gestation',
        "Premier stade de développement d’un Partzuf. Contraction maximale (3 dans 3). Correspond à l’embryogenèse.", 'mohin'),
    'av_72': ('ע״ב 72', 'AV = 72',
        "Valeur du Nom divin AV (ע״ב). Milui de Yodin = 72. Correspond au côté droit (Chokhmah/Abba).", 'gematria'),
    'ryu_216': ('רי״ו 216', 'RYU = 216',
        "Valeur numérique 216. Gevurot = 216. Correspond au côté gauche.", 'gematria'),
    'ehyeh_de_yudin': ('אהי״ה דיודין', 'EHYEH de Yodin',
        "Milui de EHYEH avec des Yod = 161. Nom droit correspondant à Abba.", 'gematria'),
    'ban_de_hehin': ('ב״ן דההין', 'BaN de Hehin',
        "Milui de YHVH avec des Heh = 52. BaN gauche.", 'gematria'),
    'elohim': ('אלהים', 'Elohim',
        "Nom divin de Binah. Valeur 86 = Nature (הטבע). Gouverne la rigueur et la forme.", 'gematria'),
    'gematria_ibur': ('גימטריא עיבור', 'Guematria de Ibur',
        "Encodage numérique du processus de gestation dans les valeurs des Noms divins.", 'gematria'),

    # --- Trois types d’Ibur ---
    'ibur_7': ('עיבור ז׳', 'Gestation de 7',
        "Gestation de 7 mois : celle d’Arikh Anpin. NHY incluses dans HGT, HGT dans la partie supérieure.", 'mohin'),
    'ibur_9': ('עיבור ט׳', 'Gestation de 9',
        "Gestation de 9 mois : celle de Zeir Anpin. Ibur standard avec les 3 étapes de Tlat go Tlat.", 'mohin'),
    'ibur_12': ('עיבור י״ב', 'Gestation de 12',
        "Gestation de 12 mois : celle de Nukvah. La plus longue, incluant 3 mois supplémentaires.", 'mohin'),
    'tlat_iburim': ('תלת עיבורין', 'Trois gestations',
        "Les trois types de gestation (7, 9, 12 mois) correspondant aux trois Partzufim principaux.", 'mohin'),

    # --- Calculs et détails d’Ibur ---
    'klilut_nhy_hgt': ('כלילות נה״י בחג״ת', 'Inclusion NHY dans HGT',
        "Première étape de l’Ibur : les NHY se replient dans les HGT, contraction séquentielle.", 'mohin'),
    'ibur_7_calcul': ('חשבון עיבור ז׳', 'Calcul de l’Ibur de 7',
        "Détail du calcul de la gestation de 7 mois : inclusion séquentielle des membres.", 'mohin'),
    'tiferet_hatzi': ('תפארת חצי', 'Tiferet coupée en deux',
        "La Tiferet divisée : sa moitié supérieure est incluse dans le calcul de l’Ibur.", 'mohin'),
    'moshe': ('משה', 'Moïse',
        "Tiferet d’Arikh Anpin. Né à 7 mois (Ibur de 7). L’aspect intérieur du Yesod d’Abba.", 'partzufim'),
    'ibur_7_moshe': ('עיבור ז׳ משה', 'Naissance de Moïse à 7 mois',
        "Moïse est né à 7 mois car il correspond au niveau d’AA dont la gestation est de 7.", 'mohin'),
    'ibur_12_calcul': ('חשבון עיבור י״ב', 'Calcul de l’Ibur de 12',
        "9 mois standard plus 3 mois supplémentaires pour Nukvah = 12.", 'mohin'),
    'bat_nukvah': ('בת נוקבא', 'Fille/Nukvah',
        "Nukvah comme « dernière née » dans le processus de gestation à 12 mois.", 'partzufim'),
    've_ahar': ('ואחר', 'Et après',
        "Preuve scripturaire : « et après elle enfanta une fille » — Nukvah naît en dernier.", 'autre'),

    # --- Birur ---
    'birur': ('בירור', 'Clarification',
        "Processus de tri des lumières après la Shevirah : séparer le pur (Zak) de l’impur (Av). Central dans le Tikkun.", 'tikkun'),
    'muvhar_orot': ('מובחר אורות', 'Meilleur des lumières',
        "Les lumières les plus pures extraites en premier dans le processus de Birur.", 'tikkun'),
    'aliyat_nhy': ('עליית נה״י', 'Montée des NHY',
        "Les NHY remontent en portant les lumières clarifiées. Véhicule du Birur.", 'tikkun'),
    'nekudot_tevirin': ('נקודות תבירין', 'Points brisés',
        "Les Nekudot du monde de Tohu, brisées, source des lumières à clarifier.", 'shevirah'),
    'zak': ('זך', 'Pur/Subtil',
        "Le pur et subtil, extrait en premier dans le Birur. Devient matériau du Partzuf.", 'tikkun'),
    'av': ('עב', 'Épais/Grossier',
        "L’épais et grossier, non clarifié ou clarifié en dernier. Ce qui reste après l’extraction du Zak.", 'tikkun'),
    'birur_séquentiel': ('בירור סדרתי', 'Birur séquentiel',
        "Le tri s’opère par qualité : le plus pur d’abord, le plus grossier en dernier.", 'tikkun'),
    'partzuf_za': ('פרצוף ז״א', 'Configuration de ZA',
        "Zeir Anpin comme résultat du Birur : formé à partir des lumières clarifiées.", 'partzufim'),

    # --- Pesolet et nourriture ---
    'pesolet_le_okhel': ('פסולת לאוכל', 'Déchet devenu nourriture',
        "Ce qui est déchet pour un niveau supérieur devient nourriture pour l’inférieur. Relativité du Birur.", 'tikkun'),
    'av_for_za': ('עב לז״א', 'Épais pour ZA',
        "Le résidu grossier rejeté par Abba est acceptable au niveau de ZA.", 'tikkun'),
    'mohin_za': ('מוחין ז״א', 'Mohin de ZA',
        "Les Mohin (intellects) de ZA en état d’Ibur : tête en formation.", 'mohin'),
    'gufah_za': ('גופא ז״א', 'Corps de ZA',
        "Le corps de Zeir Anpin en formation. HGT formés avant NHY.", 'partzufim'),
    'hym_non_birur': ('חי״ם ללא בירור', 'Aspects non clarifiés',
        "Les aspects de Hod, Yesod et Malkhut non encore passés par le Birur.", 'tikkun'),
    'birur_partiel': ('בירור חלקי', 'Birur partiel',
        "Clarification incomplète : certains aspects restent mêlés aux Kelipot.", 'tikkun'),

    # --- Impuretés et purification ---
    'ahizat_kelipah': ('אחיזת קליפה', 'Adhérence de Kelipah',
        "L’adhérence des forces impures aux niveaux inférieurs. Plus on descend, plus l’adhérence est forte.", 'kelipot'),
    'tachtonim': ('תחתונים', 'Niveaux inférieurs',
        "Les niveaux inférieurs du système, plus vulnérables à l’adhérence des Kelipot.", 'olamot'),
    'difficulty_birur': ('קושי בירור', 'Difficulté du Birur',
        "La difficulté du Birur est proportionnelle à la profondeur : plus les Nitzotzot sont enfouis, plus l’extraction est ardue.", 'tikkun'),
    'dam_niddah': ('דם נידה', 'Sang menstruel',
        "Résidu (Pesolet) du processus de Birur, analogue au sang menstruel dans la Halakhah.", 'tikkun'),
    'tumat_leidah': ('טומאת לידה', 'Impureté de naissance',
        "L’impureté associée à la naissance : résidu des 7 Kelipot traversées lors du Birur.", 'halakhah'),
    'shivat_yamim': ('שבעת ימים', 'Sept jours',
        "Sept jours de purification correspondant aux 7 Kelipot des 7 Sefirot inférieures.", 'halakhah'),
    'tumat_nekevah': ('טומאת נקבה', 'Double impureté féminine',
        "L’impureté double pour une fille (14 jours) car elle inclut la Malkhut de ZA en plus.", 'halakhah'),
    'arba_esreh': ('ארבע עשרה', 'Quatorze',
        "14 jours d’impureté pour une naissance féminine = 7 + 7 (Kelipot de ZA + Nukvah).", 'halakhah'),
    'malkhut_in_za': ('מלכות בז״א', 'Malkhut incluse dans ZA',
        "La Malkhut incluse dans ZA qui double l’impureté lors de la naissance féminine.", 'partzufim'),

    # --- Yenikah (Allaitement) ---
    'yenikah': ('יניקה', 'Allaitement',
        "Deuxième stade de développement après l’Ibur. La lumière est « allaitée » — transformée de sang (Dinim) en lait (Hassadim).", 'mohin'),
    'dam_le_halav': ('דם לחלב', 'Sang en lait',
        "Transformation alchimique centrale : les Dinim (rigueurs) sont convertis en Hassadim (bontés) par l’allaitement.", 'mohin'),
    'dinim': ('דינים', 'Jugements/Rigueurs',
        "Forces de rigueur non clarifiées. Doivent être adoucies (Hamtakah) pour devenir Hassadim.", 'sefirot'),
    'halav': ('חלב', 'Lait',
        "Le lait comme Hassadim transformés : nourriture post-natale qui fait grandir le Partzuf.", 'mohin'),
    'okhel_be_pesolet': ('אוכל בפסולת', 'Bon mêlé au déchet',
        "L’état pré-Birur : le bon (Okhel) est encore mêlé au mauvais (Pesolet), requiert séparation.", 'tikkun'),

    # --- Durée et croissance ---
    'kaf_dalet_hodesh': ('כ״ד חודש', '24 mois',
        "Durée de l’allaitement : 24 mois (2 ans), 8 mois par Sefirah des 3 inférieures.", 'mohin'),
    'hamtakah': ('המתקה', 'Adoucissement',
        "Processus de transformation des Dinim en Hassadim. « Adoucir » les rigueurs.", 'tikkun'),
    'shmoneh_hodashim': ('שמונה חודשים', 'Huit mois',
        "8 mois d’allaitement par Sefirah : rythme de la Hamtakah.", 'mohin'),
    'hasserim': ('חסרים', 'Déficients',
        "État de déficience avant la Yenikah : les jambes (NHY) ne sont pas encore formées.", 'mohin'),
    'gdilat_raglayim': ('גדילת רגליים', 'Croissance des jambes',
        "La Yenikah fait croître les NHY (jambes) du Partzuf. De la dépendance à l’autonomie.", 'mohin'),
    'halakhah': ('הלכה', 'Loi/Marche',
        "Double sens : la loi juive ET la « marche » autonome. L’enfant qui marche seul = Halakhah.", 'halakhah'),

    # --- Anatomie de l’allaitement ---
    'trei_palgei_gufa': ('תרי פלגי גופא', 'Deux moitiés du corps',
        "Netzach et Hod comme deux moitiés inséparables du corps : jambe droite et gauche.", 'partzufim'),
    'netzach_hod_coupling': ('צימוד נצח־הוד', 'Couplage Netzach-Hod',
        "Couplage fonctionnel de Netzach et Hod : ils opèrent toujours ensemble comme une paire.", 'sefirot'),
    'gilui_mutneh': ('גילוי מותנה', 'Révélation conditionnée',
        "La révélation de la lumière est conditionnée par la capacité du récepteur à la supporter.", 'ohr'),
    'halav_gematria': ('חלב גימטריא', 'Guematria du lait',
        "Valeur numérique de חלב (lait) = 40. Correspond à EHYEH de Hehin.", 'gematria'),
    'ehyeh_de_hehin': ('אהי״ה דההין', 'EHYEH de Hehin',
        "Milui de EHYEH avec des Heh. Nom source du lait nourricier.", 'gematria'),
    'shadayim': ('שדיים', 'Seins',
        "Les seins d’Imma : organes de transmission du lait (Hassadim) au Partzuf en croissance.", 'partzufim'),
    'kav_emtzai': ('קו אמצעי', 'Ligne médiane',
        "La ligne centrale de l’arbre sefirotique (Keter-Tiferet-Yesod-Malkhut).", 'sefirot'),
    'dam_gematria': ('דם גימטריא', 'Guematria du sang',
        "Valeur numérique de דם (sang) = 44. Correspond aux Achorayim de EHYEH.", 'gematria'),
    'halav_from_dam': ('חלב מדם', 'Lait du sang',
        "Transformation du sang (44) en lait (40) par retrait de 4 lettres. Hamtakah numérique.", 'gematria'),
    'milui': ('מילוי', 'Remplissage',
        "Technique de développement des lettres : chaque lettre est « remplie » par l’épellation de son nom.", 'gematria'),
    'shaddai': ('שדי', 'Shaddai',
        "Nom divin associé à l’allaitement. Racine שד (sein). Protection contre les Kelipot.", 'gematria'),
    'dadim': ('דדים', 'Mamelles',
        "Les mamelles comme canaux de transmission. Cantique des Cantiques : « tes mamelles sont meilleures que le vin ».", 'partzufim'),
    'eldad_medad': ('אלדד ומידד', 'Eldad et Medad',
        "Correspondance scripturaire (Nombres 11:26-27) des deux prophètes liés aux deux mamelles.", 'autre'),
    'el_shaddai': ('אל שדי', 'El Shaddai',
        "Nom divin « Dieu Tout-Puissant » : Imma en phase d’allaitement.", 'partzufim'),
    'el_elyon': ('אל עליון', 'El Elyon',
        "Nom divin « Dieu Très-Haut » : Imma après le sevrage, revenue à son niveau supérieur.", 'partzufim'),
    'gomel': ('גומל', 'Sevrage accompli',
        "Le sevrage (Gamal) marque la fin de la Yenikah et le début de l’autonomie.", 'mohin'),
    'heh_central': ('ה׳ מרכזי', 'Heh central',
        "Le Heh central du Tétragramme comme distributeur du lait vers les deux côtés.", 'gematria'),
    'shnei_halav': ('שני חלב', 'Deux types de lait',
        "Deux types de lait : du sein droit (Hassadim) et du sein gauche (Gevurot adoucies).", 'mohin'),
    'dad_yamin': ('דד ימין', 'Mamelle droite',
        "Mamelle droite d’Imma : transmet les Hassadim purs.", 'partzufim'),
    'dad_smol': ('דד שמאל', 'Mamelle gauche',
        "Mamelle gauche d’Imma : transmet les Gevurot adoucies.", 'partzufim'),

    # ========================================================================
    # SHAAR 4 — IBUR BET et GADLUT
    # ========================================================================

    'ibur_bet': ('עיבור ב׳', 'Deuxième gestation',
        "Retour dans le « ventre » d’Imma pour recevoir les Mohin complets. Après Yenikah, avant Gadlut.", 'mohin'),
    'da_at_shalem': ('דעת שלם', 'Connaissance complète',
        "L’intellect complet (Da’at Shalem) que ZA reçoit lors de l’Ibur Bet.", 'mohin'),
    'ibur_aleph': ('עיבור א׳', 'Première gestation',
        "La première gestation (formation initiale du corps). Précède la Yenikah.", 'mohin'),
    'sequence_iby': ('סדר עי״ב', 'Séquence Ibur-Yenikah-Ibur Bet',
        "L’ordre développemental complet : Ibur Aleph → Yenikah → Ibur Bet → Gadlut.", 'mohin'),
    'hadashim_la_bekarim': ('חדשים לבקרים', 'Renouvelés chaque matin',
        "Lamentations 3:23 : les Mohin se renouvellent quotidiennement. Cycle journalier de Katnut-Gadlut.", 'mohin'),
    'mohin_hadashim': ('מוחין חדשים', 'Intellects renouvelés',
        "Les Mohin frais reçus chaque matin lors du renouvellement quotidien.", 'mohin'),
    'afkidat_ruah': ('אפקדת רוח', 'Dépôt nocturne',
        "L’âme (Ruah) déposée auprès de Dieu pendant le sommeil, restituée au réveil.", 'neshamah'),
    'aliyat_zun': ('עליית זו״ן', 'Montée de ZuN',
        "ZA et Nukvah montent dans Imma comme Mayin Nukvin, catalysant le Zivvug.", 'zivvug'),
    'man_le_binah': ('מ״ן לבינה', 'MaN pour Binah',
        "Les MaN que ZuN élèvent vers Binah, déclenchant la production de nouveaux Mohin.", 'zivvug'),
    'mohin_yordim': ('מוחין יורדים', 'Mohin descendants',
        "Les Mohin produits par le Zivvug d’AVI qui descendent vers ZA.", 'mohin'),
    'auto_catalyse': ('אוטו־קטליזה', 'Auto-catalyse',
        "Pattern où ZA provoque lui-même la descente de ses propres Mohin en montant comme MaN.", 'mohin'),

    # --- Lettres de Ibur Bet ---
    'vav_be_tokh_heh': ('ו׳ בתוך ה׳', 'Vav dans le Heh',
        "ZA (Vav) replié dans le ventre d’Imma (Heh) pendant l’Ibur Bet.", 'mohin'),
    'pesi_ah_le_bar': ('פסיעה לבר', 'Pas vers l’extérieur',
        "Le point de Malkhut qui « sort » du Heh : la Pesi’ah (pas) vers l’extérieur.", 'mohin'),
    'vav_zeira': ('ו׳ זעירא', 'Petit Vav',
        "ZA en état de Katnut : Vav diminué, sans tête (sans Mohin de Gadlut).", 'mohin'),
    'vav_nigleit': ('ו׳ נגלית', 'Vav révélé',
        "ZA après la naissance, émergeant du Heh d’Imma. Début de la vie autonome.", 'mohin'),
    'rosh_katnut': ('ראש קטנות', 'Tête de petitesse',
        "La tête de ZA en état de Katnut : intellect minimal, pas de Mohin de Gadlut.", 'mohin'),
    'karnei_hagavim': ('קרני חגבים', 'Cornes de sauterelles',
        "Métaphore des membres fins et immatures de ZA en Katnut (Nb 13:33).", 'mohin'),
    'sag_63': ('ס״ג 63', 'SaG = 63',
        "Valeur du Nom YHVH en milui de SaG = 63. Correspond à Binah.", 'gematria'),

    # --- Gadlut et Mohin ---
    'gadlut': ('גדלות', 'Maturité',
        "Troisième stade : maturité complète. ZA reçoit les Mohin de Gadlut (Chokhmah et Binah) via les NHY d’Imma.", 'mohin'),
    'nhy_imma_enters': ('נה״י אמא נכנסים', 'NHY d’Imma entrent',
        "Les NHY d’Imma pénètrent dans ZA comme force de croissance, apportant les Mohin de Gadlut.", 'mohin'),
    'katnut': ('קטנות', 'Petitesse',
        "État d’immaturité : ZA avant de recevoir les Mohin de Gadlut. Intellect minimal.", 'mohin'),
    'chokhmah_za': ('חכמה ז״א', 'Chokhmah de ZA',
        "La Chokhmah de ZA, formée des 3 Prakin de Netzach d’Imma.", 'mohin'),
    'netzach_imma': ('נצח אמא', 'Netzach d’Imma',
        "Le Netzach d’Imma : source droite des Mohin de ZA.", 'partzufim'),
    'binah_za': ('בינה ז״א', 'Binah de ZA',
        "La Binah de ZA, formée du Hod d’Imma.", 'mohin'),

    # --- Hassadim et Gevurot dans ZA ---
    'chesed_chassadim': ('חסד חסדים', 'Chesed au pluriel',
        "Formule zoharique : Chesed au singulier (Imma) vs Hassadim au pluriel (ZA). Imma donne un, ZA reçoit plusieurs.", 'sefirot'),
    'gevurah_gevurot': ('גבורה גבורות', 'Gevurah au pluriel',
        "Même pattern : Gevurah au singulier (Imma) vs Gevurot au pluriel (ZA).", 'sefirot'),
    'singulier_pluriel': ('יחיד רבים', 'Singulier vs pluriel',
        "Le passage du singulier (source, Imma) au pluriel (récepteur, ZA) marque la multiplication dans la descente.", 'sefirot'),

    # --- Mécanismes de descente ---
    'push_down': ('דחיפה למטה', 'Poussée vers le bas',
        "Mécanisme de descente : chaque nouveau Moah qui entre pousse les précédents vers le bas.", 'mohin'),
    'dehiyah': ('דחייה', 'Poussée',
        "Poussée séquentielle dans la descente des Mohin à travers le corps de ZA.", 'mohin'),
    'seder_yeridah': ('סדר ירידה', 'Ordre de descente',
        "L’ordre dans lequel les Mohin descendent et se déploient dans le corps de ZA.", 'mohin'),

    # --- Tiers et mesures ---
    'shlishim_nifradim': ('שלישים נפרדים', 'Tiers de sources différentes',
        "Les tiers qui composent les Mohin viennent de sources différentes (Abba, Imma, AA).", 'mohin'),
    'hibur_shlishim': ('חיבור שלישים', 'Combinaison de tiers',
        "La combinaison hétérogène de tiers de différentes sources pour former un Moah complet.", 'mohin'),
    'hiddur_mitzvah': ('הידור מצוה', 'Embellissement de la Mitzvah',
        "Correspondance halakhique : ajouter un tiers au-delà du minimum = Hiddur Mitzvah.", 'halakhah'),
    'tosefet_shlish': ('תוספת שליש', 'Ajout d’un tiers',
        "L’ajout d’un tiers au-delà de la mesure minimale. Quantifie la Gadlut.", 'mohin'),
    'gadlut_quantity': ('כמות גדלות', 'Quantité de Gadlut',
        "La Gadlut est quantifiable : elle correspond à l’ajout du tiers supplémentaire.", 'mohin'),
    'shlish_afar': ('שליש עפר', 'Tiers de poussière',
        "Isaïe 40:12 : « mesura la poussière par tiers ». Mesure par tiers dans la formation.", 'mohin'),
    'middah': ('מידה', 'Mesure',
        "Instrument de mesure dans la formation des Partzufim. Chaque niveau a sa mesure propre.", 'autre'),
    'zeret': ('זרת', 'Empan',
        "Mesure de la main étendue. Unité de mesure dans la formation des Kelim.", 'autre'),
    'middah_ve_zeret': ('מידה וזרת', 'Mesure et empan',
        "Les deux instruments de mesure : Middah (mesure standard) et Zeret (empan).", 'autre'),
    'beit_kibul': ('בית קיבול', 'Réceptacle',
        "Le « lieu de réception » formé par la séparation des eaux.", 'ohr'),
    'havdalat_mayim': ('הבדלת מים', 'Séparation des eaux',
        "Genèse 1:6 : la séparation des eaux supérieures et inférieures. Création de l’espace réceptif.", 'olamot'),

    # --- Sortie de Nukvah ---
    'hazeh': ('חזה', 'Poitrine',
        "Point anatomique crucial de ZA : lieu de sortie de Nukvah et frontière Leah/Rachel.", 'partzufim'),
    'shlish_elyon_tiferet': ('שליש עליון תפארת', 'Tiers supérieur de Tiferet',
        "Le tiers supérieur de Tiferet de ZA, au-dessus du Hazeh.", 'partzufim'),
    'nukvah_exit': ('יציאת נוקבא', 'Sortie de Nukvah',
        "Nukvah sort par l’arrière de ZA au niveau du Hazeh.", 'partzufim'),
    'mezuzah': ('מזוזה', 'Mézouza',
        "La Mézouza comme manifestation physique de Malkhut au seuil. Nom ADNI = 65.", 'halakhah'),
    'adni': ('אדנ״י', 'ADNI',
        "Nom divin de Malkhut. Valeur 65. Nom de la réceptivité.", 'gematria'),

    # --- Yesod et mesures ---
    'yesod_za_hasher': ('יסוד ז״א חסר', 'Yesod de ZA incomplet',
        "Le Yesod de ZA est incomplet : ne reçoit que 2/3 de la mesure complète.", 'partzufim'),
    'yesod_imma_katzer': ('יסוד אמא קצר', 'Yesod d’Imma court',
        "Le Yesod d’Imma est plus court que celui d’Abba : ne descend pas jusqu’au Yesod de ZA.", 'partzufim'),
    'shtei_shlishim': ('שתי שלישים', 'Deux tiers',
        "Le Yesod de ZA ne reçoit que deux tiers de sa mesure, le troisième manque.", 'partzufim'),
    'yosef_yatom': ('יוסף יתום', 'Joseph orphelin',
        "Le Yesod de ZA comme « orphelin » : privé du soutien maternel (Yesod d’Imma trop court).", 'partzufim'),
    'imma_ad_hod': ('אמא עד הוד', 'Imma jusqu’à Hod',
        "Limite de l’extension d’Imma : son Yesod ne descend que jusqu’au Hod de ZA, pas jusqu’au Yesod.", 'partzufim'),
    'yesod_kol': ('יסוד כל', 'Fondement de tout',
        "Le Yesod comme point de convergence de tous les flux : les 5 Hassadim s’y rassemblent.", 'sefirot'),
    'hamesh_hassadim': ('חמש חסדים', 'Cinq Hassadim',
        "Les 5 Bontés qui descendent à travers le corps de ZA et convergent dans le Yesod.", 'sefirot'),
    'haarah': ('הארה', 'Illumination',
        "Illumination indirecte : reflet de lumière plutôt que lumière directe.", 'ohr'),

    # --- Ordre de Gadlut ---
    'seder_gadlut': ('סדר גדלות', 'Ordre de Gadlut',
        "L’ordre séquentiel dans lequel la Gadlut se déploie dans les Sefirot de ZA.", 'mohin'),
    'gadlut_complete': ('גדלות שלמה', 'Gadlut complète',
        "Achèvement de la maturité : tous les Mohin sont en place, ZA fonctionne pleinement.", 'mohin'),

    # ========================================================================
    # SHAAR 5 — MOHIN, TZELEM, DIKNA
    # ========================================================================

    'terin_mazalot': ('תרין מזלות', 'Deux Mazalot',
        "Les deux flux principaux de la Dikna d’AA : Notzer Chesed (8e) et VeNakeh (13e).", 'dikna'),
    'notzer_chesed': ('נוצר חסד', 'Conservateur de bonté',
        "8e Tikkun de la Dikna d’AA. Mazal supérieur qui alimente Abba.", 'dikna'),
    've_nakeh': ('ונקה', 'Et il absout',
        "13e Tikkun de la Dikna d’AA. Mazal inférieur qui alimente Imma.", 'dikna'),
    'dikna_aa': ('דיקנא דא״א', 'Barbe d’AA',
        "Les 13 Tikkunei Dikna d’Arikh Anpin : canaux de transmission de la lumière supérieure.", 'dikna'),
    'yag_tikkunei_dikna': ('י״ג תיקוני דיקנא', '13 rectifications de la Barbe',
        "Les 13 rectifications de la Barbe d’AA selon l’Idra Rabba. Source des Mohin pour AVI.", 'dikna'),
    'abba_yonek': ('אבא יונק', 'Abba allaité',
        "Abba est alimenté par le 8e Mazal (Notzer Chesed) de la Dikna d’AA.", 'dikna'),
    'imma_yonek': ('אמא יונקת', 'Imma allaitée',
        "Imma est alimentée par le 13e Mazal (VeNakeh) de la Dikna d’AA.", 'dikna'),
    'betisha': ('בטישא', 'Impact',
        "Impact (« frappe ») entre les deux Mazalot qui produit les 5 Gevurot.", 'dikna'),
    'hamesh_gevurot': ('חמש גבורות', 'Cinq Gevurot',
        "Les 5 Rigueurs produites par l’impact des deux Mazalot. Descendent dans Da’at.", 'dikna'),
    'sod_bilti_mefurash': ('סוד בלתי מפורש', 'Secret non explicité',
        "Mystère reconnu par le texte lui-même comme non pleinement explicité.", 'autre'),

    # --- HG dans Imma ---
    'hg_be_mei_imma': ('חסדים גבורות במעי אמא', 'HG dans le ventre d’Imma',
        "Les Hassadim et Gevurot mélangés dans le ventre d’Imma avant leur distribution.", 'mohin'),
    'zivvug_avi_for_mohin': ('זיווג או״א למוחין', 'Zivvug AVI pour Mohin',
        "L’union d’Abba et Imma spécifiquement pour produire les Mohin de ZA.", 'zivvug'),
    'yb_behinot': ('י״ב בחינות', 'Douze aspects',
        "Les 12 aspects des Mohin : 4 Mohin × 3 niveaux (source, habillage, déploiement).", 'mohin'),
    'tipat_abba': ('טיפת אבא', 'Goutte d’Abba',
        "La « goutte » de Chokhmah qu’Abba transmet dans le Zivvug.", 'zivvug'),
    'tipat_imma': ('טיפת אמא', 'Goutte d’Imma',
        "La « goutte » de Binah qu’Imma transmet dans le Zivvug.", 'zivvug'),
    'terin_itrin': ('תרין עיטרין', 'Deux couronnes',
        "Les deux couronnes que ZA hérite d’AVI : couronne d’Abba (droite) et couronne d’Imma (gauche).", 'mohin'),
    'yerushat_avi': ('ירושת או״א', 'Héritage d’AVI',
        "L’héritage parental que ZA reçoit de ses « parents » Abba et Imma.", 'mohin'),
    'dalet_mohin': ('ד׳ מוחין', 'Quatre Mohin',
        "Les 4 cerveaux : Chokhmah, Binah, Da’at de Hassadim, Da’at de Gevurot.", 'mohin'),
    'mem_de_tzelem': ('מ׳ דצלם', 'Mem du Tzelem',
        "La lettre Mem (= 40) dans le mot צלם (Tzelem). Correspond aux 4 Mohin avant habillage.", 'mohin'),
    'tzelem': ('צלם', 'Image/Tzelem',
        "L’Image divine en 3 états : Tzadi (déployé dans 9 Sefirot), Lamed (3 Mohin habillés), Mem (4 Mohin sources).", 'mohin'),

    # --- Habillage des Mohin ---
    'hitlabshut_mohin': ('התלבשות מוחין', 'Habillage des Mohin',
        "Les Mohin se « revêtent » dans les NHY d’Imma avant d’entrer dans ZA.", 'mohin'),
    'chokhmah_be_netzach': ('חכמה בנצח', 'Chokhmah dans Netzach',
        "Le premier Moah (Chokhmah) s’habille dans le Netzach d’Imma.", 'mohin'),
    'binah_be_hod': ('בינה בהוד', 'Binah dans Hod',
        "Le deuxième Moah (Binah) s’habille dans le Hod d’Imma.", 'mohin'),
    'hg_be_yesod': ('חג בייסוד', 'HG dans Yesod',
        "Les 3e et 4e Mohin (Da’at de Hassadim et Gevurot) s’habillent dans le Yesod d’Imma.", 'mohin'),
    'imma_markenet': ('אמא מרכנת', 'Imma s’abaisse',
        "Imma s’abaisse (ses NHY descendent) pour introduire les Mohin dans ZA.", 'partzufim'),
    'emboitement_triple': ('שלוש שכבות', 'Trois couches d’emboîtement',
        "Triple emboîtement : Mohin dans NHY d’Imma, NHY d’Imma dans ZA.", 'mohin'),
    'mohin_in_za': ('מוחין בז״א', 'Mohin dans ZA',
        "L’entrée finale des Mohin dans Zeir Anpin après leur habillage complet.", 'mohin'),

    # --- Transformations du Tzelem ---
    'mem_4_mohin': ('מ׳ = ד׳ מוחין', 'Mem = 4 Mohin',
        "Avant l’habillage : 4 Mohin distincts = Mem (40).", 'mohin'),
    'lamed_3_mohin': ('ל׳ = ג׳ מוחין', 'Lamed = 3 Mohin',
        "Après l’habillage : les HG fusionnent dans Yesod, 4 deviennent 3 = Lamed (30).", 'mohin'),
    'tzadi_9_sefirot': ('צ׳ = ט׳ ספירות', 'Tzadi = 9 Sefirot',
        "Déployé dans ZA : les Mohin remplissent les 9 Sefirot = Tzadi (90).", 'mohin'),
    'fusion_hg': ('מיזוג חג', 'Fusion HG',
        "La fusion des Hassadim et Gevurot en un seul Moah dans le Yesod d’Imma.", 'mohin'),
    'tzadi_9': ('צדי ט׳', 'Tzadi de 9',
        "Le Tzadi du Tzelem : déploiement des Mohin dans les 9 Sefirot de ZA.", 'mohin'),
    'hitpashtut_mohin': ('התפשטות מוחין', 'Déploiement des Mohin',
        "Les Mohin se déploient depuis la tête dans tout le corps de ZA.", 'mohin'),
    'tet_tikkunei_dikna_za': ('ט׳ תיקוני דיקנא ז״א', '9 Tikkunei Dikna de ZA',
        "Les 9 rectifications de la barbe de ZA (vs 13 pour AA). Manifestation des Mohin déployés.", 'dikna'),
    'source_3x3': ('מקור ג׳ × ג׳', 'Source triple × triple',
        "Triple habillage : chaque Moah dans un NHY d’Imma = 3 × 3 = 9.", 'mohin'),

    # --- Yesodot et Atarot ---
    'yesod_abba_chesed': ('יסוד אבא חסד', 'Yesod d’Abba = Couronne droite',
        "Le Yesod d’Abba forme la couronne droite (Atarah) sur le Yesod de ZA.", 'partzufim'),
    'yesod_imma_gevurah': ('יסוד אמא גבורה', 'Yesod d’Imma = Couronne gauche',
        "Le Yesod d’Imma forme la couronne gauche sur le Yesod de ZA.", 'partzufim'),
    'malkhut_abba': ('מלכות אבא', 'Malkhut d’Abba',
        "La Malkhut d’Abba qui forme l’Atarah (couronne) du Yesod de ZA.", 'partzufim'),
    'nekudat_tzion': ('נקודת ציון', 'Point de Sion',
        "Le point du Yesod d’Imma. Sion = Yesod dans la géographie mystique.", 'partzufim'),
    'milah_priah': ('מילה פריעה', 'Circoncision et découvrement',
        "Le secret du Yesod : Milah (coupe de l’Orlah/Kelipah) et Priah (révélation de l’Atarah).", 'halakhah'),
    'atarah_hatunatoh': ('עטרה חתונתו', 'Couronne de ses noces',
        "Cantique 3:11 : la couronne des noces = les Itrin (couronnes) nécessaires au Zivvug de ZuN.", 'zivvug'),
    'itrin_for_zivvug': ('עיטרין לזיווג', 'Couronnes pour le Zivvug',
        "Condition du Zivvug de ZuN : les deux couronnes (Itrin) d’AVI doivent être présentes.", 'zivvug'),
    'fusion_en_une': ('מיזוג לאחת', 'Fusion en une',
        "Les deux couronnes fusionnent en une lors du Zivvug.", 'zivvug'),

    # --- Tefillin et Shin ---
    'tefillin': ('תפילין', 'Phylactères',
        "Les Tefillin comme manifestation physique du Tzelem : boîtiers des Mohin sur la tête.", 'halakhah'),
    'shin_4': ('שין ד׳', 'Shin à 4 branches',
        "Shin à 4 branches sur le côté gauche des Tefillin : 4 Mohin avant l’habillage.", 'halakhah'),
    'shin_3': ('שין ג׳', 'Shin à 3 branches',
        "Shin à 3 branches sur le côté droit : 3 Mohin après la fusion HG.", 'halakhah'),
    'transformation_4_3': ('שינוי ד׳ לג׳', 'Transformation 4→3',
        "Le passage de 4 Mohin à 3 par la fusion des HG dans le Yesod.", 'mohin'),
    'tefillin_shel_hkbh': ('תפילין של הקב״ה', 'Tefillin du Saint-Béni-Soit-Il',
        "Les Tefillin divins : le flux quotidien d’AVI vers ZA, source de vitalité constante.", 'halakhah'),
    'hiyut_automatic': ('חיות אוטומטית', 'Vitalité automatique',
        "La vitalité inconditionnelle que ZA reçoit constamment d’AVI, indépendamment des MaN.", 'ohr'),
    'itrin_conditional': ('עיטרין מותנים', 'Couronnes conditionnelles',
        "Les couronnes pour le Zivvug sont conditionnelles, dépendent des MaN. Contrairement à la Hiyut automatique.", 'zivvug'),

    # ========================================================================
    # SHAAR 6 — HASSADIM ET GEVUROT
    # ========================================================================

    'asarah_hg': ('עשרה חג', 'Dix HG',
        "Les 10 Hassadim et 10 Gevurot qui descendent depuis Da’at dans le corps de ZA.", 'sefirot'),
    'da_at_source': ('דעת מקור', 'Da’at source',
        "Da’at comme lieu initial des Hassadim et Gevurot avant leur distribution.", 'sefirot'),
    'hadarim': ('חדרים', 'Chambres',
        "Les « chambres » (Sefirot du corps) que les HG doivent remplir.", 'sefirot'),
    'hassadim_in_za': ('חסדים בז״א', 'Hassadim dans ZA',
        "Les 5 Hassadim se déploient dans les 5 Sefirot de Chesed à Hod de ZA.", 'sefirot'),
    'gevurot_in_yesod': ('גבורות ביסוד', 'Gevurot dans Yesod',
        "Les 5 Gevurot sont déposées en consigne (Pikadon) dans le Yesod de ZA pour Nukvah.", 'sefirot'),
    'pikadon': ('פקדון', 'Consigne/Dépôt',
        "Les Gevurot en dépôt dans le Yesod de ZA, gardées pour être transmises à Nukvah.", 'sefirot'),
    'hassadim_mekhasim': ('חסדים מכוסים', 'Hassadim couverts',
        "Hassadim couverts par le Yesod d’Imma. État protégé, pas d’adhérence des Kelipot.", 'ohr'),
    'hassadim_megulim': ('חסדים מגולים', 'Hassadim découverts',
        "Hassadim non couverts par le Yesod d’Imma : vulnérables mais plus lumineux.", 'ohr'),
    'yesod_imma_ad_tiferet': ('יסוד אמא עד תפארת', 'Yesod d’Imma jusqu’à Tiferet',
        "Le Yesod d’Imma ne descend que jusqu’à Tiferet de ZA. En dessous = Hassadim Megulim.", 'partzufim'),
    'ohr_kaful': ('אור כפול', 'Lumière doublée',
        "L’Ohr est doublé quand il est découvert (Meguleh) : plus intense car non atténué.", 'ohr'),
    'meguleh_amplifies': ('מגולה מוגבר', 'Découvert amplifié',
        "L’amplification de la lumière sans couverture : paradoxe de la vulnérabilité et de l’intensité.", 'ohr'),

    # --- Formation de Nukvah depuis le surplus ---
    'keter_nukvah': ('כתר נוקבא', 'Keter de Nukvah',
        "Le Keter de Nukvah est formé du surplus (Meguleh) de Tiferet de ZA.", 'partzufim'),
    'surplus_meguleh': ('עודף מגולה', 'Surplus découvert',
        "L’excédent de lumière découverte qui déborde et forme les niveaux de Nukvah.", 'ohr'),
    'mohin_nukvah': ('מוחין נוקבא', 'Mohin de Nukvah',
        "Les Mohin de Nukvah, formés du surplus de Netzach et Hod de ZA.", 'mohin'),
    'rosh_nukvah': ('ראש נוקבא', 'Tête de Nukvah',
        "La tête complète de Nukvah, formée des surplus des Sefirot de ZA.", 'partzufim'),

    # --- Double mouvement ---
    'yeridah_pnimi': ('ירידה פנימית', 'Descente intérieure',
        "Mouvement descendant de l’Ohr Pnimi dans le corps de ZA.", 'ohr'),
    'aliyah_makif': ('עלייה מקיפית', 'Remontée environnante',
        "Mouvement ascendant de l’Ohr Makif depuis le Yesod vers la tête.", 'ohr'),
    'kibbutz_be_yesod': ('קיבוץ ביסוד', 'Collection dans Yesod',
        "Les Gevurot convergent et se rassemblent dans le Yesod de ZA.", 'sefirot'),
    'double_mouvement': ('תנועה כפולה', 'Double mouvement',
        "Pattern de descente intérieure (Pnimi) et remontée extérieure (Makif) simultanées.", 'ohr'),
    'mekhaseh_nighleh': ('מכוסה נגלה', 'Couvert devenu découvert',
        "Transition de l’état couvert à l’état découvert au-dessous de la limite d’Imma.", 'ohr'),
    'kol_nikpalim': ('כל נכפלים', 'Tout est doublé',
        "Principe : tout ce qui est découvert est amplifié (doublé) par rapport à l’état couvert.", 'ohr'),

    # --- Surplus et Roshem ---
    'surplus_ascendant': ('עודף עולה', 'Surplus ascendant',
        "L’Ohr Makif excédentaire qui remonte depuis le bas vers les Mohin de la tête.", 'ohr'),
    'khbd_receives_makif': ('חב״ד מקבלים מקיף', 'KHB reçoivent le Makif',
        "Les Mohin (KHB) de ZA sont nourris par l’Ohr Makif qui remonte.", 'mohin'),
    'roshem': ('רושם', 'Empreinte',
        "Empreinte résiduelle laissée après le passage ou le retrait d’une lumière. Trace formatrice.", 'ohr'),
    'haarah_min_roshem': ('הארה מרושם', 'Illumination de l’empreinte',
        "L’illumination indirecte produite par l’empreinte résiduelle.", 'ohr'),
    'shlish_le_khbd': ('שליש לחב״ד', 'Un tiers pour KHB',
        "Un tiers du surplus suffit pour les Mohin de la tête.", 'mohin'),
    'shlish_va_hetzi': ('שליש וחצי', 'Un tiers et demi',
        "Un tiers et demi de surplus requis pour les HGT (corps supérieur).", 'mohin'),

    # --- Keter de ZA et Nukvah ---
    'keter_za': ('כתר ז״א', 'Keter de ZA',
        "Le Keter de ZA, formé du surplus de Tiferet d’Imma. Prioritaire sur le Keter de Nukvah.", 'partzufim'),
    'keter_nukvah_moindre': ('כתר נוקבא קטן', 'Keter moindre de Nukvah',
        "La part inférieure du surplus qui forme le Keter de Nukvah (après ZA).", 'partzufim'),
    'kedimut_za': ('קדימות ז״א', 'Priorité de ZA',
        "ZA a priorité sur Nukvah dans la réception des surplus.", 'partzufim'),
    'tiferet_imma_hatzi': ('תפארת אמא חצי', 'Moitié de Tiferet d’Imma',
        "Source additionnelle du Keter de ZA : la moitié de Tiferet d’Imma.", 'partzufim'),
    'keter_za_multiple': ('כתר ז״א מרובה', 'Sources multiples du Keter de ZA',
        "Le Keter de ZA est composé de sources multiples (surplus de Tiferet, moitié d’Imma).", 'partzufim'),

    # ========================================================================
    # SHAAR 7 — NUKVAH
    # ========================================================================

    'parallel_za_nukvah': ('מקבילה ז״א נוקבא', 'Parallèle ZA-Nukvah',
        "Pattern fractal : Nukvah reproduit la même structure que ZA, construite par les mêmes processus.", 'partzufim'),
    'nhy_za_for_nukvah': ('נה״י ז״א לנוקבא', 'NHY de ZA pour Nukvah',
        "Les NHY de ZA sont la source de croissance de Nukvah, comme les NHY d’Imma pour ZA.", 'partzufim'),
    'tiferet_za_hatzi': ('תפארת ז״א חצי', 'Moitié inf. de Tiferet de ZA',
        "La moitié inférieure de Tiferet de ZA, en dessous du Hazeh, source du Keter de Nukvah.", 'partzufim'),
    'nukvah_me_ahor': ('נוקבא מאחור', 'Nukvah de l’arrière',
        "Nukvah sort par l’arrière de ZA : formée des Achorayim, aspect rigoureux.", 'partzufim'),
    'achorayim_dinim': ('אחוריים דינים', 'Arrière = rigueurs',
        "Les Achorayim sont associés aux Dinim (rigueurs). Nukvah, sortant de l’arrière, est empreinte de Din.", 'partzufim'),
    'ahizat_hitzonim': ('אחיזת חיצונים', 'Prise des forces extérieures',
        "Les Kelipot tentent de s’attacher aux Achorayim exposés. Danger de l’exposition.", 'kelipot'),
    'hidabkut_achorayim': ('הידבקות אחוריים', 'Collage protecteur',
        "Nukvah colle à l’arrière de ZA pour protéger ses Hassadim Megulim des Kelipot.", 'partzufim'),

    # --- Protection et serments ---
    'malkhut_yamin': ('מלכות ימין', 'Malkhut est la droite',
        "Malkhut est placée à droite (Chesed) pour la protéger contre l’adhérence du mal.", 'partzufim'),
    'heshiv_ahor': ('השיב אחור', 'Placement défensif',
        "Placement de Malkhut à l’arrière comme stratégie défensive contre les Kelipot.", 'partzufim'),
    'risha_protected': ('רישא מוגנת', 'Tête protégée',
        "La tête de Nukvah est naturellement protégée par sa position élevée.", 'partzufim'),
    'megulim_vulnerable': ('מגולים פגיעים', 'Découverts vulnérables',
        "La zone découverte (sous le Yesod d’Imma) est vulnérable aux forces extérieures.", 'ohr'),
    'nukvah_covers_megulim': ('נוקבא מכסה מגולים', 'Nukvah couvre les découverts',
        "Nukvah protège la zone découverte de ZA en s’y collant par l’arrière.", 'partzufim'),
    'shevuah': ('שבועה', 'Serment',
        "Serment = Malkhut. Plus grave que le Vœu car lié à la Shekhinah elle-même.", 'halakhah'),
    'neder': ('נדר', 'Vœu',
        "Vœu = Binah. Annulable par Hatarat Nedarim car Binah est accessible.", 'halakhah'),
    'humra_shevuah': ('חומרת שבועה', 'Gravité du serment',
        "Le serment est plus grave que le vœu car Malkhut est le niveau le plus exposé.", 'halakhah'),
    'hatarat_nedarim': ('התרת נדרים', 'Annulation des vœux',
        "Rituel d’annulation des vœux. Possible car les vœux = Binah (accessible).", 'halakhah'),
    'yom_kippur': ('יום כיפור', 'Jour du Grand Pardon',
        "Jour d’accès au niveau de Binah, permettant l’annulation des vœux et le pardon.", 'halakhah'),
    'aliyah_le_binah': ('עלייה לבינה', 'Montée à Binah',
        "L’élévation au niveau de Binah à Yom Kippur. Accès au pardon.", 'halakhah'),

    # --- Construction de Nukvah ---
    'tlat_kavim_nukvah': ('תלת קווים נוקבא', 'Trois lignes de Nukvah',
        "Les trois lignes (droite, gauche, centre) de Nukvah construites à partir des NHY de ZA.", 'partzufim'),
    'netzach_za_to_yamin': ('נצח ז״א → ימין', 'Netzach de ZA → droite de Nukvah',
        "Le Netzach de ZA forme la ligne droite de Nukvah.", 'partzufim'),
    'hod_za_to_smol': ('הוד ז״א → שמאל', 'Hod de ZA → gauche de Nukvah',
        "Le Hod de ZA forme la ligne gauche de Nukvah.", 'partzufim'),
    'yesod_za_to_emtzai': ('יסוד ז״א → אמצעי', 'Yesod de ZA → centre de Nukvah',
        "Le Yesod de ZA forme la ligne centrale de Nukvah.", 'partzufim'),

    # --- Nekudah Ikarit et mesures ---
    'ma_aser': ('מעשר', 'Dîme',
        "Le dixième est saint : Malkhut (10e Sefirah) est le point essentiel propre de Nukvah.", 'halakhah'),
    'nekudah_ikarit': ('נקודה עיקרית', 'Point essentiel',
        "Le point essentiel propre de Nukvah : sa Malkhut originelle, irréductible.", 'partzufim'),
    'teshva_mi_hutz': ('תשעה מחוץ', 'Neuf de l’extérieur',
        "Les 9 Sefirot que Nukvah reçoit de ZA (extérieur), vs la 10e qui est sa racine propre.", 'partzufim'),
    'shoresh_nukvah': ('שורש נוקבא', 'Racine de Nukvah',
        "La racine propre de Nukvah, distincte de ce qu’elle reçoit de ZA.", 'partzufim'),

    # --- Mohin et Da’at de Nukvah ---
    'mohin_nukvah_source': ('מוחין נוקבא מחסדים', 'Mohin de Nukvah = surplus Hassadim',
        "Les Mohin de Nukvah proviennent du surplus de Hassadim de ZA.", 'mohin'),
    'da_at_nukvah': ('דעת נוקבא', 'Da’at de Nukvah',
        "La Da’at de Nukvah, formée des Gevurot en dépôt dans le Yesod de ZA.", 'mohin'),
    'da_at_nashim_kalah': ('דעת נשים קלה', 'La connaissance des femmes est légère',
        "Interprétation guématrique : Da’at (474) des femmes = Kalah (כלה = 55). 474/2 ≈ moitié.", 'gematria'),
    'hatzi_da_at': ('חצי דעת', 'Moitié de Da’at',
        "Nukvah ne reçoit que la moitié du Da’at de ZA.", 'mohin'),
    'kl_130': ('ק״ל 130', 'KL = 130',
        "Valeur des 5 Gevurot = 5 × 26 (YHVH) = 130 = ק״ל.", 'gematria'),

    # --- Gevurot et Dinim de Nukvah ---
    'gevurot_in_nukvah': ('גבורות בנוקבא', 'Gevurot dans Nukvah',
        "Les Gevurot se déploient dans Nukvah de Chesed à Hod.", 'partzufim'),
    'gevurot_converge_yesod': ('גבורות מתכנסות ביסוד', 'Gevurot convergent dans Yesod',
        "Les 5 Gevurot convergent dans le Yesod de Nukvah. Source des Mayin Nukvin.", 'partzufim'),
    'man_nukvah': ('מ״ן נוקבא', 'MaN de Nukvah',
        "Les Mayin Nukvin de Nukvah : les Gevurot rassemblées dans son Yesod.", 'zivvug'),
    'dinim_nukvah': ('דינים נוקבא', 'Dinim de Nukvah',
        "Profil des Dinim de Nukvah : doux en haut, durs en bas. Inversé par rapport à ZA.", 'partzufim'),
    'dinim_za': ('דינים ז״א', 'Dinim de ZA',
        "Profil des Dinim de ZA : durs en haut, doux en bas. Inversé par rapport à Nukvah.", 'partzufim'),
    'profils_inversés': ('פרופילים הפוכים', 'Profils inversés',
        "Complémentarité ZA-Nukvah : leurs profils de Dinim sont inversés, permettant la Hamtakah mutuelle.", 'zivvug'),

    # ========================================================================
    # SHAAR 8 — SEUILS DE MATURITÉ
    # ========================================================================

    'pe_utot_6': ('פעוטות ו׳', 'Petits enfants de 6',
        "Premier seuil (6 ans) : l’enfant peut faire des transactions mineures (Metaltelin).", 'mohin'),
    'biyah_9': ('ביאה ט׳', 'Union à 9',
        "Deuxième seuil (9 ans) : ZA peut avoir une relation sans conception.", 'mohin'),
    'gadol_13': ('גדול י״ג', 'Adulte à 13',
        "Troisième seuil (13 ans) : maturité complète, ZA est adulte.", 'mohin'),
    'shalosh_madregot': ('שלוש מדרגות', 'Trois seuils',
        "Les trois seuils de maturité de ZA : 6, 9 et 13 ans. Chacun correspond à un niveau de Mohin.", 'mohin'),

    # --- Calculs et phases ---
    'yeridah_6_4': ('ירידה ו׳ד', 'Six ans quatre mois',
        "Calcul du premier seuil : 6 ans et 4 mois = durée totale d’Ibur + Yenikah + début Gadlut.", 'mohin'),
    'sefirah_shanah': ('ספירה שנה', 'Une Sefirah = un an',
        "Correspondance temporelle : chaque Sefirah correspond à une année de maturation.", 'mohin'),
    'mekhasim_phase': ('מכוסים שלב', 'Phase couverte',
        "Phase où les Hassadim sont encore couverts par le Yesod d’Imma.", 'mohin'),
    'ohr_yashar': ('אור ישר', 'Lumière directe',
        "Lumière descendante directe, du haut vers le bas. Premier mouvement de l’émanation.", 'ohr'),
    'ohr_hozer': ('אור חוזר', 'Lumière de retour',
        "Lumière ascendante, de bas en haut. Réponse du récepteur à l’émetteur.", 'ohr'),
    'yb_8': ('י״ב ח׳', 'Douze ans huit mois',
        "Point de calcul dans la maturation de ZA correspondant à l’Ohr Hozer.", 'mohin'),

    # --- Yaakov et percement ---
    'yaakov_63': ('יעקב ס״ג', 'Jacob à 63',
        "Jacob reçoit la bénédiction à 63 ans. 63 = SaG = Binah. Percement de l’écran.", 'gematria'),
    'sag_63_binah': ('ס״ג בינה', 'SaG 63 = Binah',
        "Le nombre 63 (SaG) est le nombre de Binah. Correspondance avec la bénédiction de Jacob.", 'gematria'),
    'bekiah': ('בקיעה', 'Percement',
        "Percement de l’écran du Yesod d’Imma, permettant la révélation des Hassadim Megulim.", 'mohin'),
    'yivaka': ('יבקע', 'Il percera',
        "Anagramme de יעקב (Yaakov). Jacob = celui qui perce les écrans.", 'gematria'),

    # --- Modes de ZA ---
    'za_ke_beriah': ('ז״א כבריאה', 'ZA en mode couvert',
        "ZA en mode « Beriah » : Hassadim couverts, lumière filtrée.", 'mohin'),
    'za_ke_atzilut': ('ז״א כאצילות', 'ZA en mode révélé',
        "ZA en mode « Atzilut » : Hassadim découverts, lumière directe.", 'mohin'),
    'masakh_nhy': ('מסך נה״י', 'Écran des NHY',
        "L’écran formé par les NHY d’Imma qui couvre les Hassadim de ZA.", 'mohin'),
    'yotzer_ohr': ('יוצר אור', 'Formateur de lumière',
        "Bénédiction du matin : passage de ZA au mode révélé (Gilui).", 'halakhah'),

    # --- Seuils détaillés ---
    'yg_shanah_yom': ('י״ג שנה ויום', '13 ans et un jour',
        "L’âge exact de la majorité : 13 ans et un jour, pas simplement 13 ans.", 'mohin'),
    'yom_ehad': ('יום אחד', 'Un jour',
        "L’intervalle minimal d’un jour qui fait la différence entre Katnut et Gadlut complète.", 'mohin'),
    'gadlut_shlemah': ('גדלות שלמה', 'Maturité complète',
        "L’état de pleine maturité à 13 ans et un jour. Tous les Mohin sont actifs.", 'mohin'),
    'pe_ut_6_detail': ('פעוטות ו׳ פרט', 'Détail du seuil de 6 ans',
        "Calcul alternatif du premier seuil par le décompte des phases.", 'mohin'),
    'yenikah_2': ('יניקה ב׳', 'Deux ans d’allaitement',
        "La Yenikah dure 2 ans (24 mois) avant le début de l’autonomie.", 'mohin'),
    'metaltelin': ('מטלטלין', 'Biens meubles',
        "Biens mobiliers : ce qu’un enfant de 6 ans peut gérer. Niveau minimal de Da’at.", 'halakhah'),
    'da_at_minimal': ('דעת מינימלי', 'Intellect minimal',
        "Le niveau minimal de Da’at permettant des transactions basiques.", 'mohin'),
    'metaltelin_vk': ('מטלטלין ו״ק', 'Oscillation des V"K',
        "L’oscillation des 6 extrémités (Vav Ketzavot) dans l’état de Da’at minimal.", 'mohin'),
    'rahamim_din': ('רחמים דין', 'Miséricorde et rigueur',
        "L’oscillation entre miséricorde et rigueur dans l’état de pré-maturité.", 'sefirot'),
    'da_at_shalem_9': ('דעת שלם ט׳', 'Da’at complet à 9',
        "Da’at complet atteint à 9 ans : suffisant pour l’union mais pas la procréation.", 'mohin'),
    'biyah_without_ibur': ('ביאה בלי עיבור', 'Union sans conception',
        "À 9 ans, ZA peut s’unir à Nukvah mais ne peut pas encore engendrer.", 'zivvug'),
    'yarkhin': ('ירכין', 'Cuisses/Prakin supérieurs',
        "Les « cuisses » comme Prakin (articulations) supérieures du bras de AA.", 'partzufim'),
    'gadol_13_detail': ('גדול י״ג פרט', 'Détail de la majorité à 13',
        "Calcul détaillé de la maturité à 13 ans : somme de toutes les phases.", 'mohin'),
    'ohr_hozer_4': ('אור חוזר ד׳', 'Quatre ans d’Ohr Hozer',
        "Les 4 ans finaux de maturation correspondant à la remontée de l’Ohr Hozer.", 'mohin'),
    'biyah_molidat': ('ביאה מולידה', 'Union procréative',
        "À 13 ans : l’union de ZA et Nukvah peut engendrer (Neshamot).", 'zivvug'),

    # ========================================================================
    # SHAAR 9 — AA ET PROPORTIONS
    # ========================================================================

    'aa_neshamah': ('א״א נשמה', 'AA = âme d’Atzilut',
        "Arikh Anpin est l’âme (Neshamah) de tout le monde d’Atzilut. Anime tous les Partzufim.", 'partzufim'),
    'hitpashtut_aa': ('התפשטות א״א', 'Déploiement d’AA',
        "AA se déploie dans l’intégralité d’Atzilut, du sommet à la base.", 'partzufim'),
    'hitlabshut_aa': ('התלבשות א״א', 'Revêtement d’AA',
        "AA se revêt dans tous les Partzufim inférieurs, les animant de l’intérieur.", 'partzufim'),
    'neshamah_za_from_aa': ('נשמת ז״א מא״א', 'Neshamah de ZA depuis AA',
        "L’âme de ZA provient du segment Tiferet-Yesod de AA.", 'partzufim'),
    'neshamah_nukvah_from_aa': ('נשמת נוקבא מא״א', 'Neshamah de Nukvah depuis AA',
        "L’âme de Nukvah provient de l’Ateret Yesod (couronne du Yesod) de AA.", 'partzufim'),
    'ateret_yesod_aa': ('עטרת יסוד א״א', 'Couronne du Yesod d’AA',
        "Le point terminal du Yesod d’AA, source de l’âme de Nukvah.", 'partzufim'),
    'ein_sof_be_aa': ('אין סוף בא״א', 'Ein Sof dans AA',
        "Le flux de l’Ein Sof traverse AA comme canal vers tous les Partzufim.", 'ohr'),
    'mehayeh_kulam': ('מחיה כולם', 'Vivifie tous',
        "AA vivifie tous les Partzufim : la Hiyut universelle passe par lui.", 'ohr'),
    'aa_as_channel': ('א״א כצינור', 'AA comme canal',
        "AA fonctionne comme canal de l’Ein Sof vers les mondes émanés.", 'partzufim'),
    'ibur_aleph_context': ('עיבור א׳ הקשר', 'Ibur Aleph en contexte',
        "Dans le contexte de l’Ibur Aleph, AA aussi se contracte avec les autres Partzufim.", 'mohin'),
    'aa_contracts_too': ('א״א מצטמצם גם', 'AA se contracte aussi',
        "Même Arikh Anpin se contracte lors de l’Ibur Aleph. Contraction universelle.", 'mohin'),

    # --- Proportions de Nukvah ---
    'nukvah_ibur': ('נוקבא בעיבור', 'Nukvah en Ibur',
        "Nukvah en état de gestation : taille d’un Yesod seulement.", 'partzufim'),
    'yesod_israel': ('יסוד ישראל', 'Yesod appelé Israël',
        "Le Yesod de ZA est appelé « Israël » : fondement du peuple.", 'partzufim'),
    'rova_israel': ('רובע ישראל', 'Quart d’Israël',
        "Nukvah en Ibur = 1/4 de la taille d’Israël (Yesod de ZA).", 'partzufim'),
    'arba_beritot': ('ארבע בריתות', 'Quatre alliances',
        "Les 4 mesures du corps de ZA. 4 × Nukvah en Ibur = taille complète.", 'partzufim'),
    'shi_ur_gufa': ('שיעור גופא', 'Proportions du corps',
        "Les proportions du corps de ZA : rapport 16:4:1 entre les niveaux.", 'partzufim'),
    'ratio_16_4_1': ('יחס 16:4:1', 'Ratio 16:4:1',
        "Proportions : ZA complet = 16, Yesod = 4, Nukvah en Ibur = 1.", 'partzufim'),

    # --- Stades de Nukvah ---
    'nukvah_stade_1': ('נוקבא שלב א׳', 'Nukvah stade 1',
        "Premier stade de Nukvah : taille d’un Yesod (état originel post-Ibur).", 'partzufim'),
    'croissance_x4': ('צמיחה × 4', 'Quadruplement',
        "Chaque stade de développement multiplie par 4 la taille de Nukvah.", 'partzufim'),
    'nukvah_stade_2': ('נוקבא שלב ב׳', 'Nukvah stade 2',
        "Deuxième stade : taille de Tiferet (4 × stade 1). Après Yenikah.", 'partzufim'),
    'yenikah_quadruple': ('יניקה מרובעת', 'Deuxième quadruplement',
        "La Yenikah produit un deuxième quadruplement de la taille de Nukvah.", 'mohin'),
    'nukvah_stade_3': ('נוקבא שלב ג׳', 'Nukvah stade 3',
        "Troisième stade : Partzuf complet (4 × stade 2). Après Gadlut.", 'partzufim'),
    'sequence_nukvah': ('סדר נוקבא', 'Séquence de Nukvah',
        "Séquence complète : Nekudah → Ibur → Yenikah → Gadlut. Quantitatif puis qualitatif.", 'partzufim'),
    'quantitatif_to_qualitatif': ('כמותי לאיכותי', 'Quantitatif vers qualitatif',
        "Le saut de nature entre croissance quantitative (taille) et transformation qualitative (Partzuf).", 'partzufim'),

    # ========================================================================
    # SHAAR 10 — TZELEM, MOSHE, YAAKOV, NESIRAH
    # ========================================================================

    'tzelem_abba': ('צלם אבא', 'Tzelem d’Abba',
        "L’Image paternelle : les NHY d’Abba habillées dans ZA.", 'mohin'),
    'tzelem_imma': ('צלם אמא', 'Tzelem d’Imma',
        "L’Image maternelle : les NHY d’Imma habillées dans ZA.", 'mohin'),
    'shnei_tzelamim': ('שני צלמים', 'Deux Tzelamim',
        "Le double Tzelem : tout homme est créé avec l’image du père et de la mère.", 'mohin'),
    'nhy_abba': ('נה״י אבא', 'NHY d’Abba',
        "Netzach-Hod-Yesod d’Abba : l’habillage paternel dans ZA.", 'partzufim'),
    'shnei_binot': ('שתי בינות', 'Deux Binahs',
        "Les deux Binahs dans ZA : celle d’Abba et celle d’Imma.", 'mohin'),
    'shnei_chokhmot': ('שתי חכמות', 'Deux Sagesses',
        "Les deux Chokhmot : celle d’Abba et celle d’Imma dans ZA.", 'mohin'),
    'shnei_da_ot': ('שני דעות', 'Deux Da’at',
        "Les deux Da’at : masculin (d’Abba) et féminin (d’Imma).", 'mohin'),
    'nhy_abba_in_nhy_imma': ('נה״י אבא בנה״י אמא', 'NHY d’Abba dans NHY d’Imma',
        "Emboîtement : les NHY d’Abba sont habillées dans les NHY d’Imma, qui sont dans ZA.", 'mohin'),
    'nhy_imma': ('נה״י אמא', 'NHY d’Imma',
        "Netzach-Hod-Yesod d’Imma : réceptacle maternel des NHY d’Abba.", 'partzufim'),

    # --- Yesod d’Abba long ---
    'yesod_abba_arukh': ('יסוד אבא ארוך', 'Yesod d’Abba long',
        "Le Yesod d’Abba est plus long que celui d’Imma : descend plus bas dans ZA, 2/3 découverts.", 'partzufim'),
    'shnei_shlishim_megulim': ('שני שלישים מגולים', 'Deux tiers découverts',
        "Les 2/3 du Yesod d’Abba qui dépassent du Yesod d’Imma sont Megulim (découverts).", 'partzufim'),
    'hevel_havalim': ('הבל הבלים', 'Souffle des souffles',
        "Ecclésiaste 1:2. Le double souffle qui émerge du Yesod d’Abba.", 'zivvug'),

    # --- Yaakov et percements ---
    'yaakov_formation': ('יעקב התגבשות', 'Formation de Jacob',
        "Jacob est formé depuis le Yesod d’Abba, aspect extérieur de la lumière.", 'partzufim'),
    'bekiat_ohr': ('בקיעת אור', 'Percement de lumière',
        "Le percement de la lumière du Yesod d’Abba à travers l’écran d’Imma.", 'ohr'),
    'panim_za': ('פנים ז״א', 'Face avant de ZA',
        "La face avant de ZA, formée par le percement de la lumière de Jacob.", 'partzufim'),
    'yaakov_yivaka': ('יעקב יבקע', 'Jacob = perceur',
        "Anagramme : יעקב (Yaakov) ↔ יבקע (Yivaka, « il percera »). Jacob est celui qui perce.", 'gematria'),
    'shnei_bekiot': ('שני בקיעות', 'Deux percements',
        "Deux percements du Yesod d’Abba : un vers l’avant (Yaakov), un vers l’arrière (Rachel).", 'partzufim'),
    'yatza_yatza': ('יצא יצא', 'Double sortie',
        "Double sortie : « il sortit, il sortit » (Genèse 38:29). Deux lumières de la même source.", 'autre'),
    'yaakov_panim': ('יעקב פנים', 'Jacob devant ZA',
        "Jacob est la face avant de ZA, l’aspect visible et extérieur.", 'partzufim'),
    'rachel_ahor': ('רחל אחור', 'Rachel derrière ZA',
        "Rachel est la face arrière de ZA, l’aspect intérieur et réceptif.", 'partzufim'),

    # --- Moshe intérieur/extérieur ---
    'moshe_le_gaw': ('משה לגו', 'Moïse à l’intérieur',
        "Moïse comme aspect intérieur de la même source que Jacob.", 'partzufim'),
    'yaakov_le_bar': ('יעקב לבר', 'Jacob à l’extérieur',
        "Jacob comme aspect extérieur. Même source que Moïse, manifestation différente.", 'partzufim'),
    'same_source_dual': ('מקור אחד שניים', 'Même source, deux aspects',
        "Moïse et Jacob viennent de la même source (Yesod d’Abba) mais manifestent deux aspects.", 'partzufim'),

    # --- 5 aspects de Moshe ---
    'hamesh_behinot_moshe': ('חמש בחינות משה', 'Cinq aspects de Moïse',
        "Les 5 aspects de Moïse dans le système lourianique.", 'partzufim'),
    'moshe_da_at': ('משה דעת', 'Moïse = Da’at',
        "Premier aspect : Moïse comme Da’at de ZA.", 'partzufim'),
    'moshe_seter': ('משה סתר', 'Moïse = couvert',
        "Deuxième aspect : Moïse comme aspect couvert du Yesod d’Abba.", 'partzufim'),
    'moshe_nevuah': ('משה נבואה', 'Moïse = prophétie',
        "Troisième aspect : Moïse comme canal prophétique par excellence.", 'partzufim'),
    'shet': ('שת', 'Seth',
        "Quatrième aspect : Seth fils d’Adam = Yesod. Moïse comme Yesod.", 'partzufim'),
    'moshe_acronym': ('משה ר״ת', 'Moïse = acronyme',
        "מ-ש-ה : Mem, Shin, Heh — les trois lettres encodent trois niveaux.", 'gematria'),

    # --- Détournement et Nesirah ---
    'het_hevel': ('חטא הבל', 'Péché du souffle',
        "Le détournement du flux de lumière : au lieu d’aller vers Nukvah, il va vers Rachel.", 'partzufim'),
    'hitzitz_ba_shekhinah': ('הציץ בשכינה', 'Regard vers la Shekhinah',
        "Le regard interdit vers la Shekhinah nue : métaphore du flux mal dirigé.", 'kelipot'),
    'yaakov_to_rachel': ('יעקב לרחל', 'Jacob vers Rachel',
        "Le flux de Jacob dirigé vers Rachel plutôt que vers sa destination prévue.", 'partzufim'),
    'nesirah': ('נסירה', 'Sciage/Séparation',
        "Processus de séparation de Nukvah du dos de ZA pour qu’ils puissent se faire face (Panim be-Panim).", 'partzufim'),
    'kotel_ehad': ('כותל אחד', 'Mur partagé',
        "Le mur commun entre ZA et Nukvah quand elle est collée à son dos. Doit être scié.", 'partzufim'),
    'kotel_atzmit': ('כותל עצמי', 'Mur propre',
        "Le mur propre de chaque Partzuf après la Nesirah. Indépendance structurelle.", 'partzufim'),
    'hefsek': ('הפסק', 'Séparation',
        "L’espace de séparation entre ZA et Nukvah après la Nesirah. Condition du face-à-face.", 'partzufim'),
    'zivvug_pbp': ('זיווג פב״פ', 'Union face à face',
        "L’union face à face (Panim be-Panim) : état optimal, possible seulement après la Nesirah.", 'zivvug'),

    # ========================================================================
    # SHAAR 11 — DOR HAMIDBAR, BINAH/TEVUNAH, LETTRES
    # ========================================================================

    'dor_hamidbar': ('דור המדבר', 'Génération du désert',
        "La génération de Moïse dans le désert. Niveau spirituel maximal : accès au Yesod d’Abba.", 'autre'),
    'dor_de_ah': ('דור דעה', 'Génération de connaissance',
        "La génération du désert = « génération de Da’at » : accès direct à la Connaissance.", 'autre'),
    'bhinat_yaakov': ('בחינת יעקב', 'Aspect de Jacob',
        "L’aspect Jacob comme source dans le Yesod d’Abba.", 'partzufim'),
    'bhinat_zun': ('בחינת זו״ן', 'Aspect de ZuN',
        "L’aspect provenant de ZA et Nukvah ensemble.", 'partzufim'),
    'torah_from_yesod_abba': ('תורה מיסוד אבא', 'Torah depuis Yesod d’Abba',
        "La Torah émane du Yesod d’Abba, source de la Sagesse divine.", 'partzufim'),
    'arba_im_shanah': ('ארבעים שנה', 'Quarante ans',
        "Les 40 ans dans le désert : durée de maturation complète.", 'autre'),
    'anshei_hayil': ('אנשי חיל', 'Hommes de valeur',
        "Les hommes de valeur du désert : ceux qui ont accès aux Mohin élevés.", 'autre'),
    'ein_nevonim': ('אין נבונים', 'Pas de Binah',
        "L’absence de Binah propre dans la génération du désert (tout vient directement d’Abba).", 'autre'),

    # --- Binah et Tevunah ---
    'binah_propre': ('בינה עצמה', 'Binah proprement dite',
        "L’aspect supérieur d’Imma : Binah en union constante avec Abba.", 'partzufim'),
    'tevunah': ('תבונה', 'Discernement',
        "L’aspect inférieur d’Imma. Tevunah opère séparément, s’habille dans ZA.", 'partzufim'),
    'shnei_partzufei_imma': ('שני פרצופי אמא', 'Deux configurations d’Imma',
        "Imma se divise en deux : Binah (unie à Abba) et Tevunah (descend vers ZA).", 'partzufim'),
    'dalet_rabati_zeira': ('ד׳ רבתי זעירא', 'Grand et petit Dalet',
        "Parallèle entre Léa/Rachel et le grand/petit Dalet dans le שמע.", 'autre'),
    'shalosh_behinot_binah': ('שלוש בחינות בינה', 'Trois états de Binah',
        "Les trois états : Binah (avec Abba), Tevunah (seule), Tevunah (dans ZA).", 'partzufim'),
    'binah_state': ('בינה מצב', 'Binah en état',
        "Binah dans son état avec Abba : union permanente, niveau le plus élevé.", 'partzufim'),
    'tevunah_alone': ('תבונה לבד', 'Tevunah seule',
        "Tevunah séparée d’Abba, opérant de manière autonome.", 'partzufim'),
    'tevunah_in_za': ('תבונה בז״א', 'Tevunah dans ZA',
        "Tevunah habillée dans ZA, lui fournissant les Mohin.", 'partzufim'),
    'ish_tevunot': ('איש תבונות', 'Homme de discernement',
        "ZA quand il « élève » Tevunah en lui, devenant un homme de discernement.", 'partzufim'),

    # --- Lettres Samekh et Mem ---
    'samekh_binah': ('סמך בינה', 'Samekh = Binah unie',
        "La lettre Samekh (fermée, circulaire) = Binah unie avec Abba.", 'autre'),
    'mem_stumah': ('מם סתומה', 'Mem fermée',
        "Mem finale (□) = Binah en mode réceptrice, fermée sur elle-même.", 'autre'),
    'mem_petuhah': ('מם פתוחה', 'Mem ouverte',
        "Mem ordinaire (מ) = Binah en mode donatrice, ouverte vers le bas.", 'autre'),
    'stumah_petuhah': ('סתומה פתוחה', 'Fermée et ouverte',
        "Les deux modes de Binah : réceptrice (fermée) et donatrice (ouverte).", 'partzufim'),

    # --- Vav avec/sans tête ---
    'vav_dalet_order': ('ו׳ ד׳ סדר', 'Ordre Vav-Dalet',
        "L’ordre change selon le niveau : Vav-Dalet ou Dalet-Vav.", 'autre'),
    'vav_with_head': ('ו׳ עם ראש', 'Vav avec tête',
        "Le Vav avec une tête = ZA actif, flux descendant activé.", 'autre'),
    'vav_without_head': ('ו׳ בלי ראש', 'Vav sans tête',
        "Le Vav sans tête = ZA inactif ou en Katnut.", 'autre'),

    # --- Tables de la Loi ---
    'mem_samekh_luhot': ('מם סמך לוחות', 'Mem-Samekh des Tables',
        "Le miracle des lettres Mem et Samekh dans les Tables de la Loi : elles tiennent sans support.", 'halakhah'),
    'luhot_nh': ('לוחות נ״ה', 'Tables = Netzach-Hod',
        "Les deux Tables de la Loi correspondent à Netzach et Hod.", 'halakhah'),
    'nes_110': ('נס 110', 'Miracle 110',
        "MaH (45) + ADNI (65) = 110 = נס (miracle). Soutien miraculeux.", 'gematria'),
    'hatzi_mem': ('חצי מם', 'Demi Mem',
        "Le demi-Mem qui soutient tout : la moitié suffit pour porter l’ensemble.", 'autre'),

    # --- Genre relationnel ---
    'imma_nukvah': ('אמא נוקבא', 'Imma = féminin (face à Abba)',
        "Imma est féminine par rapport à Abba : réceptrice de sa lumière.", 'partzufim'),
    'imma_dokhrah': ('אמא דוכרא', 'Imma = masculin (face aux enfants)',
        "Imma est masculine par rapport à ZA : elle donne et transmet.", 'partzufim'),
    'gender_relational': ('מין יחסי', 'Genre relationnel',
        "Le genre est relationnel, non absolu : on est masculin ou féminin selon qu’on donne ou reçoit.", 'partzufim'),

    # --- Souffle et soutien ---
    'hevel_peh_imma': ('הבל פה אמא', 'Souffle de la bouche d’Imma',
        "Le souffle nourricier de la bouche d’Imma qui soutient ZA et Nukvah.", 'partzufim'),
    'histalkut_imma': ('הסתלקות אמא', 'Retrait d’Imma',
        "Le retrait d’Imma : quand son souffle cesse, ZA et Nukvah sont en danger.", 'partzufim'),
    'nes_mah_adni': ('נס מ״ה אדנ״י', 'Miracle de MaH-ADNI',
        "Le miracle de soutien quand Imma se retire : les Noms MaH et ADNI prennent le relais.", 'gematria'),
    'shem_mah_45': ('שם מ״ה 45', 'Nom MaH = 45',
        "Le Nom YHVH en milui de Aleph = 45. Soutien de ZA quand Imma se retire.", 'gematria'),
    'shem_adni_65': ('שם אדנ״י 65', 'Nom ADNI = 65',
        "Le Nom ADNI = 65. Soutien de Nukvah.", 'gematria'),
    'moshe_samekh': ('משה סמך', 'Moïse = Samekh',
        "Moïse accède au niveau supérieur (Samekh = Binah unie avec Abba).", 'partzufim'),
    'yaakov_mem': ('יעקב מם', 'Jacob = Mem',
        "Jacob accède au niveau inférieur (Mem = Tevunah).", 'partzufim'),

    # ========================================================================
    # SHAAR 12 — LEAH, RACHEL, TEFILLIN
    # ========================================================================

    'malkhut_tevunah': ('מלכות תבונה', 'Malkhut de Tevunah',
        "La Malkhut de Tevunah (aspect inférieur de Binah). Source de Léa.", 'partzufim'),
    'da_at_za': ('דעת ז״א', 'Da’at de ZA',
        "La Da’at de Zeir Anpin, lieu de formation de Léa.", 'partzufim'),
    'tahton_niknas_rishon': ('תחתון נכנס ראשון', 'Le bas entre en premier',
        "Principe : ce qui est plus bas entre en premier. Léa se forme avant Rachel.", 'mohin'),
    'kesher_tefillin': ('קשר תפילין', 'Nœud des Tefillin',
        "Léa correspond au nœud des Tefillin de la tête, à l’arrière.", 'halakhah'),
    'batei_tefillin': ('בתי תפילין', 'Boîtiers des Tefillin',
        "Les boîtiers contenant les 4 sections = les 4 Mohin.", 'halakhah'),
    'arba_parshiyot': ('ארבע פרשיות', 'Quatre sections',
        "Les 4 sections des Tefillin = 4 Mohin (Chokhmah, Binah, Da’at × 2).", 'halakhah'),
    'or_leah': ('עור לאה', 'Cuir = Léa',
        "Léa est le cuir des Tefillin (structure externe), pas le parchemin (Mohin).", 'halakhah'),
    'nimin_aa': ('נימין א״א', 'Cheveux d’AA',
        "Les cheveux d’Arikh Anpin : canaux de lumière qui « frappent » par l’arrière.", 'dikna'),
    'hakaat_nimin': ('הכאת נימין', 'Frappe des cheveux',
        "Les cheveux d’AA frappent l’arrière de ZA, formant les compartiments des Tefillin.", 'dikna'),
    'arba_batim': ('ארבע בתים', 'Quatre compartiments',
        "Les 4 compartiments des Tefillin de la tête, formés par les Nimin d’AA.", 'halakhah'),
    'tefillin_mechanism': ('מנגנון תפילין', 'Mécanisme des Tefillin',
        "Le mécanisme de formation des Tefillin par l’interaction des Nimin et des Mohin.", 'halakhah'),

    # --- Position de Leah et Rachel ---
    'leah_ad_hazeh': ('לאה עד חזה', 'Léa du Da’at à la poitrine',
        "Léa occupe l’espace du Da’at de ZA jusqu’à sa poitrine (Hazeh).", 'partzufim'),
    'rachel_me_hazeh': ('רחל מחזה', 'Rachel de la poitrine vers le bas',
        "Rachel occupe l’espace de la poitrine de ZA jusqu’en bas.", 'partzufim'),
    'ein_malkhut_noga_at': ('אין מלכות נוגעת', 'Pas de chevauchement',
        "Léa et Rachel ne se chevauchent jamais : frontière stricte au Hazeh.", 'partzufim'),
    'anavah_leah': ('ענוה לאה', 'Humilité = Léa',
        "Léa correspond à l’humilité (Anavah) : l’aspect caché, intérieur.", 'partzufim'),
    'yirah_rachel': ('יראה רחל', 'Crainte = Rachel',
        "Rachel correspond à la crainte (Yirah) : l’aspect manifeste.", 'partzufim'),
    'ekev_atarah': ('עקב עטרה', 'Le talon devient couronne',
        "Le talon (Ekev) de Léa devient la couronne (Atarah) de Rachel. Le bas d’un niveau = le haut du suivant.", 'partzufim'),

    # --- Sources de Leah et Rachel ---
    'leah_from_hgt': ('לאה מחג״ת', 'Léa des HGT',
        "Léa est formée des bras (HGT) de ZA : Chesed, Gevurah, Tiferet.", 'partzufim'),
    'rachel_from_nhy': ('רחל מנה״י', 'Rachel des NHY',
        "Rachel est formée des jambes (NHY) de ZA : Netzach, Hod, Yesod.", 'partzufim'),

    # --- Zivvugim et prières ---
    'zivvug_leah_nuit': ('זיווג לאה לילה', 'Union de Léa = nuit',
        "L’union avec Léa a lieu la nuit (Arvit). Aspect caché, intérieur.", 'zivvug'),
    'zivvug_rachel_jour': ('זיווג רחל יום', 'Union de Rachel = jour',
        "L’union avec Rachel a lieu le jour (Shaharit/Minhah). Aspect manifeste.", 'zivvug'),
    'shaharit_chesed': ('שחרית חסד', 'Shaharit = Chesed',
        "La prière du matin correspond à Chesed (ligne droite). Union avec Rachel.", 'halakhah'),
    'minhah_gevurah': ('מנחה גבורה', 'Minhah = Gevurah',
        "La prière de l’après-midi correspond à Gevurah (ligne gauche).", 'halakhah'),
    'arvit_reshut_hovah': ('ערבית רשות חובה', 'Arvit : facultative devenue obligatoire',
        "La prière du soir, initialement facultative, est devenue obligatoire car le Zivvug avec Léa est nécessaire.", 'halakhah'),

    # --- Dinim de Leah et Rachel ---
    'leah_dinim': ('לאה דינים', 'Dinim de Léa',
        "Les Dinim de Léa sont non adoucis : elle est formée des Achorayim purs.", 'partzufim'),
    'rachel_nihin': ('רחל ניחין', 'Rachel = Dinim adoucis',
        "Les Dinim de Rachel sont adoucis par sa position plus basse et sa construction des NHY.", 'partzufim'),
    'zivvug_le_hamtakah': ('זיווג להמתקה', 'Union pour adoucir',
        "Le Zivvug avec Léa a pour but d’adoucir ses Dinim non tempérés.", 'zivvug'),
    'hurban_effect': ('חורבן השפעה', 'Effet de la Destruction',
        "La Destruction (Hurban) renforce les Dinim de Léa. Galut = aggravation.", 'shevirah'),

    # --- Tefillin et Shabbat ---
    'tefillin_lamed': ('תפילין ל׳', 'Tefillin = Lamed',
        "Les Tefillin au-dessus de la tête correspondent au Lamed du Tzelem (3 Mohin habillés).", 'halakhah'),
    'tefillin_tzadi': ('תפילין צ׳', 'Tefillin = Tzadi',
        "Les Tefillin sur la tête correspondent au Tzadi du Tzelem (9 Sefirot).", 'halakhah'),
    'tefillin_shabbat': ('תפילין שבת', 'Tefillin et Shabbat',
        "Les Mohin qui descendent le Shabbat rendent les Tefillin superflus.", 'halakhah'),
    'panim_hadashot': ('פנים חדשות', 'Faces nouvelles',
        "Les faces nouvelles du Shabbat : Mohin supérieurs qui descendent spontanément.", 'mohin'),
    'shabbat_no_tefillin': ('שבת בלי תפילין', 'Shabbat sans Tefillin',
        "Pas de Tefillin le Shabbat : les Mohin sont intériorisés (Pnimi), pas extérieurs (Makif).", 'halakhah'),
    'makif_to_pnimi': ('מקיף לפנימי', 'Makif vers Pnimi',
        "Le Shabbat, les Orot Makifim deviennent Pnimim : transition de l’extérieur vers l’intérieur.", 'ohr'),

    # --- Ordre des Tefillin ---
    'tefillin_yad': ('תפילין יד', 'Tefillin du bras',
        "Tefillin du bras = Rachel. Se met d’abord (le bas précède le haut).", 'halakhah'),
    'tefillin_rosh': ('תפילין ראש', 'Tefillin de la tête',
        "Tefillin de la tête = ZA. Se met après le bras.", 'halakhah'),
    'rachel_from_leah': ('רחל מלאה', 'Rachel prend de Léa',
        "Rachel reçoit de Léa : le talon de Léa est la couronne de Rachel.", 'partzufim'),
    'seder_tefillin': ('סדר תפילין', 'Ordre des Tefillin',
        "L’ordre est : bras (Rachel) d’abord, tête (ZA) ensuite. Le bas construit le haut.", 'halakhah'),

    # ========================================================================
    # SHAAR 13 — TARDEMA, NESIRAH, ZIVVUG
    # ========================================================================

    'tardema': ('תרדמה', 'Sommeil profond',
        "Le sommeil profond d’Adam (Genèse 2:21). Retrait des Mohin de ZA pour les transférer à Nukvah.", 'mohin'),
    'mohin_to_nukvah': ('מוחין לנוקבא', 'Mohin vers Nukvah',
        "Les Mohin retirés de ZA passent à Nukvah pour lui donner une structure indépendante.", 'mohin'),
    'histalkut_mohin': ('הסתלקות מוחין', 'Retrait des Mohin',
        "Le retrait des intellects de ZA pendant la Tardema. ZA revient temporairement en Katnut.", 'mohin'),
    'leah_be_rachel': ('לאה ברחל', 'Léa incluse dans Rachel',
        "Pendant la Tardema, Léa est incluse dans Rachel : unification des deux Nukvot.", 'partzufim'),
    'rachel_olah': ('רחל עולה', 'Rachel monte',
        "Rachel monte au niveau supérieur pendant la Nesirah, incorporant Léa.", 'partzufim'),
    'ihud_nukvot': ('איחוד נוקבות', 'Unification des Nukvot',
        "L’unification de Léa et Rachel en une seule Nukvah complète pendant la Nesirah.", 'partzufim'),
    'mohin_hadashim_elyonim': ('מוחין חדשים עליונים', 'Mohin supérieurs nouveaux',
        "Les Mohin supérieurs que ZA et Nukvah reçoivent après la Tardema. Plus élevés qu’avant.", 'mohin'),
    'dormita_as_upgrade': ('תרדמה כשדרוג', 'Tardema comme amélioration',
        "Paradoxe : le sommeil/retrait est en réalité une amélioration. On perd pour mieux recevoir.", 'mohin'),
    'zivvug_elyon': ('זיווג עליון', 'Union supérieure',
        "L’union supérieure d’AVI qui se produit grâce à la Tardema, produisant de nouveaux Mohin.", 'zivvug'),

    # --- Nesirah complète ---
    'nesirah_complete': ('נסירה שלמה', 'Nesirah complète',
        "La séquence complète : dos-à-dos → sciage → séparation → retournement → face-à-face.", 'partzufim'),
    'va_yevi_eha': ('ויביאה', 'Et Il l’amena',
        "Genèse 2:22 : « Il l’amena vers Adam » — Dieu amène Nukvah face à face avec ZA après la Nesirah.", 'zivvug'),
    'kelim_me_ahor': ('כלים מאחור', 'Kelim formés par l’arrière',
        "Les Kelim de Nukvah sont formés depuis les Achorayim de ZA, puis retournés.", 'partzufim'),
    'partzuf_shalem_nukvah': ('פרצוף שלם נוקבא', 'Nukvah en Partzuf complet',
        "Nukvah en tant que configuration complète et indépendante après la Nesirah.", 'partzufim'),

    # --- Péché et restauration ---
    'het_adam': ('חטא אדם', 'Péché d’Adam',
        "Le péché d’Adam cause le retour à l’état dos-à-dos. Perte du face-à-face.", 'shevirah'),
    'hurban_aba': ('חורבן אב״א', 'État post-destruction',
        "L’état dos-à-dos qui résulte de la Destruction. Retour périodique au face-à-face.", 'shevirah'),
    'shabbat_pbp': ('שבת פב״פ', 'Shabbat face à face',
        "Le Shabbat restaure le face-à-face entre ZA et Nukvah.", 'zivvug'),
    'tefilah_pbp': ('תפילה פב״פ', 'Prière → face à face',
        "La prière ramène le face-à-face : chaque Amidah reconstitue la Nesirah.", 'zivvug'),
    'hassidim_rishonim': ('חסידים ראשונים', 'Premiers pieux',
        "Les premiers pieux méditaient une heure avant la prière pour préparer le face-à-face.", 'halakhah'),

    # --- Sefirot Atzmiyot ---
    'sefirot_atzmiyot': ('ספירות עצמיות', 'Sefirot essentielles',
        "Les Sefirot essentielles, irréductibles, de chaque Partzuf. Ne peuvent pas être « incluses ».", 'sefirot'),
    'haarot_nilvot': ('הארות נלוות', 'Illuminations secondaires',
        "Illuminations dérivées des Sefirot principales. Peuvent être incluses dans d’autres.", 'ohr'),
    'klilut_secondaire': ('כלילות משנית', 'Inclusion secondaire',
        "L’inclusion ne porte que sur les Haarot Nilvot, jamais sur les Sefirot Atzmiyot.", 'sefirot'),

    # --- Tziporah, Kushit, Timna ---
    'tziporah': ('ציפורה', 'Tsippora',
        "Femme de Moïse = Malkhut d’Abba en Gadlut. Niveau élevé, oiseau (Tzipor) du divin.", 'partzufim'),
    'kushit': ('כושית', 'Kushite',
        "Malkhut d’Abba en Katnut. Nombres 12:1 : « la femme kushite ». État diminué.", 'partzufim'),
    'timna': ('תמנע', 'Timna',
        "Malkhut d’Imma en Katnut. Genèse 36:12. Concubine = niveau inférieur.", 'partzufim'),
    'dehiyat_dinim': ('דחיית דינים', 'Repoussement des rigueurs',
        "Le repoussement des Dinim par les Hassadim. Fonction protectrice.", 'tikkun'),

    # --- Types de Zivvug ---
    'zivvug_hb_tedir': ('זיווג ח״ב תדיר', 'Zivvug HB permanent',
        "L’union permanente de Chokhmah et Binah (Abba-Imma). Ne cesse jamais.", 'zivvug'),
    'zivvug_tm_intermittent': ('זיווג ת״מ לפרקים', 'Zivvug TM intermittent',
        "L’union intermittente de Tiferet et Malkhut (ZA-Nukvah). Dépend des conditions.", 'zivvug'),
    'arba_sefirot_zivvug': ('ד׳ ספירות זיווג', 'Quatre Sefirot de Zivvug',
        "Les 4 lieux d’union : HB permanent + TM intermittent = 4 Sefirot engagées.", 'zivvug'),
    'leshon_zahav': ('לשון זהב', 'Langue d’or',
        "Expression de l’ARI pour un enseignement autographe, de première main.", 'autre'),

    # --- Produits des Zivvugim ---
    'zivvug_hb_produces': ('זיווג ח״ב מוליד', 'Zivvug HB produit',
        "Le Zivvug permanent d’AVI produit des anges et de la vitalité constante.", 'zivvug'),
    'zivvug_tm_produces': ('זיווג ת״מ מוליד', 'Zivvug TM produit',
        "Le Zivvug intermittent de ZuN produit des Neshamot (âmes humaines).", 'zivvug'),
    'hiyut_tedirah': ('חיות תדירה', 'Vitalité constante',
        "La vitalité constante produite par le Zivvug permanent d’AVI.", 'ohr'),
    'neshamot_le_frakim': ('נשמות לפרקים', 'Âmes intermittentes',
        "Les âmes humaines produites de manière intermittente par le Zivvug de ZuN.", 'neshamah'),

    # --- Galut et manque ---
    'galut_zivvug': ('גלות זיווג', 'Zivvug en exil',
        "En état d’exil (Galut), le Zivvug de ZuN est incomplet : manquent les couronnes.", 'zivvug'),
    'hiyut_lo_poseget': ('חיות לא פוסקת', 'Vitalité incessante',
        "Même en Galut, la vitalité d’AVI ne cesse jamais. Soutien minimal garanti.", 'ohr'),
    'itrin_haserot': ('עיטרין חסרות', 'Couronnes manquantes',
        "En Galut, les couronnes (Itrin) nécessaires au Zivvug complet de ZuN font défaut.", 'zivvug'),
}

# ============================================================================
# SECTION 4 — CLASSIFICATION DE DOMAINE (fallback)
# ============================================================================

DOMAIN_KEYWORDS = {
    'sefirot': ['keter', 'chokhmah', 'binah', 'chesed', 'gevurah', 'tiferet',
                'netzach', 'hod', 'yesod', 'malkhut', 'sefirot', 'sefirah',
                'sefir', 'hassadim', 'gevurot', 'klilut', 'kav'],
    'ohr': ['ohr', 'orot', 'shefa', 'hiyut', 'makif', 'pnimi', 'yashar',
            'hozer', 'gilui', 'kisui', 'haarah', 'roshem', 'cascade',
            'megulim', 'mekhasim', 'kaful', 'surplus', 'gradient'],
    'partzufim': ['arikh', 'abba', 'imma', 'zeir', 'anpin', 'nukvah',
                  'rachel', 'leah', 'yaakov', 'moshe', 'atik', 'partzuf',
                  'partzufim', 'bat', 'za', 'zun', 'avi', 'aa',
                  'garon', 'hazeh', 'yesod_abba', 'yesod_imma', 'yesod_za',
                  'tziporah', 'kushit', 'timna', 'yosef'],
    'olamot': ['olam', 'atzilut', 'beriah', 'yetzirah', 'asiyah', 'tohu',
               'nekudot', 'akudim', 'parsah', 'abya', 'olamot'],
    'zivvug': ['zivvug', 'neshikin', 'havalim', 'hevel', 'mayin', 'nukvin',
               'man', 'panim_be_panim', 'achor_be_achor', 'pbp', 'itrin',
               'tipat', 'hibur', 'piyus'],
    'shevirah': ['shevirah', 'shevirat', 'nefilah', 'hurban', 'tevirin',
                 'melakhim', 'edom', 'brisure', 'intentionnelle'],
    'tikkun': ['tikkun', 'birur', 'aliyat', 'hamtakah', 'tefilah',
               'ma_asim', 'mesirat', 'nefilat_apayim', 'hashpa',
               'pesolet', 'zak', 'dehiyat'],
    'kelipot': ['kelipot', 'kelipah', 'ahizat', 'hitzonim', 'rasha',
                'shoresh_ha_ra', 'punishment'],
    'nitzotzot': ['nitzotzot', 'nitzotzot_as', 'aliyat_nitzotzot'],
    'mohin': ['mohin', 'ibur', 'yenikah', 'gadlut', 'katnut', 'da_at',
              'tardema', 'histalkut', 'hitpashtut_mohin', 'rosh', 'tzelem',
              'nhy_imma', 'mem_de', 'lamed', 'tlat_go', 'dormita',
              'hadashim', 'mohin_hadashim', 'seder_gadlut', 'push_down',
              'vav_be_tokh', 'pe_ut', 'biyah', 'gadol', 'bekiah'],
    'dikna': ['dikna', 'tikkunei', 'gulgalta', 'mazalot', 'notzer',
              'nakeh', 'tala', 'bdolha', 'kruma', 'pekiha', 'hotma',
              'nimin', 'amar_naki', 'betisha'],
    'neshamah': ['neshamah', 'nefesh', 'ruah', 'madregot', 'devekut',
                 'neshamot', 'afkidat'],
    'gematria': ['gematria', 'milui', 'av_72', 'ryu', 'sag', 'ban',
                 'ehyeh', 'adni', 'shem_mah', 'shem_adni', 'kl_130',
                 'nes_110', 'halav_gematria', 'dam_gematria', 'acronym',
                 'moshe_acronym', 'yaakov_yivaka', 'yivaka'],
    'halakhah': ['tefillin', 'mezuzah', 'shabbat', 'halakhah', 'hiddur',
                 'mitzvah', 'nesiat_kapayim', 'luhot', 'yom_kippur',
                 'shevuah', 'neder', 'hatarat', 'arvit', 'shaharit',
                 'minhah', 'hassidim_rishonim', 'milah', 'priah',
                 'tumat', 'shivat_yamim', 'ma_aser'],
}


def classify_domain(concept_id: str, roles: set[str]) -> str:
    """Classify a concept into a domain based on its ID and roles."""
    cid = concept_id.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in cid:
                return domain
    # Fallback based on roles
    role_str = ' '.join(roles).lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for kw in keywords:
            if kw in role_str:
                return domain
    return 'autre'


# ============================================================================
# SECTION 5 — GÉNÉRATION AUTOMATIQUE (fallback pour concepts hors dict)
# ============================================================================

def compose_hebrew(concept_id: str) -> str:
    """Compose Hebrew name from concept_id tokens."""
    # Try full match first
    if concept_id in HEBREW:
        return HEBREW[concept_id]
    # Try compound lookup
    parts = concept_id.split('_')
    he_parts = []
    for p in parts:
        if p in HEBREW:
            he_parts.append(HEBREW[p])
        else:
            # Try two-part compounds
            found = False
            for i in range(1, len(parts)):
                compound = '_'.join(parts[:i+1])
                if compound in HEBREW:
                    return HEBREW[compound]
            if not found:
                he_parts.append(p)  # Keep transliteration
    return ' '.join(he_parts) if he_parts else concept_id


def compose_french(concept_id: str, roles: set[str]) -> str:
    """Compose French name from concept_id and roles."""
    if concept_id in FRENCH:
        return FRENCH[concept_id]
    # Use first role as basis
    if roles:
        role = sorted(roles)[0]
        return role.replace('_', ' ').capitalize()
    # Fallback: humanize concept_id
    return concept_id.replace('_', ' ').capitalize()


def generate_description(concept_id: str, roles: set[str], assertion_text: str) -> str:
    """Generate a description from concept_id, roles, and assertion context."""
    role_desc = ', '.join(sorted(roles)[:3]).replace('_', ' ')
    nom_fr = compose_french(concept_id, roles)
    # Use first 150 chars of assertion as context
    ctx = (assertion_text or '')[:150].strip()
    if ctx:
        return f"{nom_fr} : {role_desc}. Contexte : {ctx}..."
    return f"{nom_fr} : {role_desc}."


# ============================================================================
# SECTION 6 — MISE À JOUR DE LA BASE
# ============================================================================

def populate(db_url: str = DB_URL, dry_run: bool = False) -> dict:
    """Populate all concepts with nom_he, nom_fr, description, domaine."""
    # Pipeline batch standalone — connexion DIRECTE volontaire
    # (audit cycle 4, C5). Long-lived avec contrôle transactionnel
    # manuel (commit/rollback explicite). Le pool est pour le code
    # daemon-actif ; ces scripts sont CLI/pipelines one-shot.

    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    # 1. Read all concepts
    cur.execute("SELECT concept_id, premiere_apparition FROM sifrei_yesod_concepts ORDER BY id")
    concepts = cur.fetchall()
    total = len(concepts)
    print(f"Total concepts en base : {total}")

    # 2. Read all assertion roles
    cur.execute("SELECT assertion_id, assertion, concepts FROM sifrei_yesod_assertions")
    assertions = cur.fetchall()

    role_map: dict[str, set[str]] = {}
    assertion_map: dict[str, str] = {}
    for aid, assertion_text, concepts_json in assertions:
        assertion_map[aid] = assertion_text or ''
        if isinstance(concepts_json, list):
            for c in concepts_json:
                if isinstance(c, dict):
                    cid = c.get('id', '')
                    role = c.get('role', '')
                    if cid:
                        if cid not in role_map:
                            role_map[cid] = set()
                        if role:
                            role_map[cid].add(role)

    # 3. Generate and update
    updated = 0
    domain_counts: Counter = Counter()
    examples = []

    for concept_id, premiere in concepts:
        roles = role_map.get(concept_id, set())
        assertion_text = assertion_map.get(premiere or '', '')

        if concept_id in CONCEPTS:
            nom_he, nom_fr, description, domaine = CONCEPTS[concept_id]
        else:
            nom_he = compose_hebrew(concept_id)
            nom_fr = compose_french(concept_id, roles)
            description = generate_description(concept_id, roles, assertion_text)
            domaine = classify_domain(concept_id, roles)

        domain_counts[domaine] += 1

        if updated < 5 or (concept_id in CONCEPTS and len(examples) < 10):
            examples.append((concept_id, nom_he, nom_fr, domaine, description[:80]))

        if not dry_run:
            cur.execute("""
                UPDATE sifrei_yesod_concepts
                SET nom_he = %s, nom_fr = %s, description = %s, domaine = %s,
                    updated_at = NOW()
                WHERE concept_id = %s
            """, (nom_he, nom_fr, description, domaine, concept_id))

        updated += 1

    # 4. Nullify embeddings for regeneration
    if not dry_run:
        cur.execute("UPDATE sifrei_yesod_concepts SET embedding = NULL")
        print(f"Embeddings nullifiés pour régénération.")
        conn.commit()
    else:
        print("[DRY RUN] Aucune modification en base.")

    cur.close()
    conn.close()

    # 5. Report
    explicit_count = sum(1 for c, _ in concepts if c in CONCEPTS)
    auto_count = total - explicit_count

    report = {
        'total': total,
        'updated': updated,
        'explicit': explicit_count,
        'auto_generated': auto_count,
        'domains': dict(domain_counts.most_common()),
        'examples': examples,
    }

    print(f"\n{'='*60}")
    print(f"RAPPORT DE PEUPLEMENT")
    print(f"{'='*60}")
    print(f"Total concepts    : {total}")
    print(f"Mis à jour        : {updated}")
    print(f"Explicites        : {explicit_count}")
    print(f"Auto-générés      : {auto_count}")
    print(f"\nRépartition par domaine :")
    for dom, count in domain_counts.most_common():
        bar = '█' * (count // 3)
        print(f"  {dom:15s} : {count:4d} {bar}")
    print(f"\nExemples :")
    for cid, he, fr, dom, desc in examples[:10]:
        print(f"  {cid:30s} | {he:20s} | {fr:25s} | {dom}")
        print(f"    → {desc}")

    return report


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Peuple les concepts sifrei_yesod")
    parser.add_argument('--dry-run', action='store_true', help="Affiche sans modifier la base")
    args = parser.parse_args()
    populate(dry_run=args.dry_run)
