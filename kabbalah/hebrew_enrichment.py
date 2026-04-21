"""kabbalah/hebrew_enrichment.py — Rétro-enrichissement des hebrew_word manquants.

שלמות — Complétude

Comble les hebrew_word NULL dans hybrid_embeddings en décomposant
les concept_id translitérés en tokens et en reconstruisant l'hébreu
depuis un vocabulaire multi-sources.

Sources du vocabulaire :
  1. sifrei_yesod_concepts.nom_he (660 paires)
  2. Dictionnaire canonique hardcodé (~200 termes)
  3. Abréviations kabbalistiques courantes (ak, aa, es, etc.)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


# ── Source 2 : Dictionnaire canonique hardcodé ───────────────────
# Tokens individuels : translittération → hébreu

_CANONICAL_TOKENS: dict[str, str] = {
    # ── Sefirot ──
    "keter": "כתר", "chokmah": "חכמה", "chokhmah": "חכמה",
    "binah": "בינה", "chesed": "חסד", "gevurah": "גבורה",
    "tiferet": "תפארת", "netzach": "נצח", "hod": "הוד",
    "yesod": "יסוד", "malkhut": "מלכות", "malkuth": "מלכות",
    "da_at": "דעת", "daat": "דעת",
    # ── Partzufim ──
    "atik": "עתיק", "yomin": "יומין",
    "arikh": "אריך", "anpin": "אנפין",
    "abba": "אבא", "imma": "אמא",
    "zeir": "זעיר", "nukvah": "נוקבא", "nukva": "נוקבא",
    "nukvot": "נוקבות",
    # ── Adam Kadmon ──
    "adam": "אדם", "kadmon": "קדמון",
    # ── Olamot ──
    "atzilut": "אצילות", "beriah": "בריאה",
    "yetzirah": "יצירה", "asiyah": "עשייה",
    "olam": "עולם", "olamot": "עולמות",
    # ── Lumières ──
    "ohr": "אור", "or": "אור", "orot": "אורות",
    "yashar": "ישר", "chozer": "חוזר", "hozer": "חוזר",
    "pnimi": "פנימי", "makif": "מקיף",
    "pnimiyut": "פנימיות", "hitzoniut": "חיצוניות",
    "hitzon": "חיצון", "hitzoniyut": "חיצוניות",
    # ── Kav / Tsimtsum ──
    "kav": "קו", "kavim": "קווים",
    "tzimtzum": "צמצום", "tsimtsum": "צמצום",
    "reshimu": "רשימו", "roshem": "רושם",
    "halal": "חלל", "panui": "פנוי",
    # ── Structures ──
    "igulim": "עיגולים", "igul": "עיגול",
    "yosher": "יושר",
    "rosh": "ראש", "guf": "גוף", "raglayim": "רגליים",
    "tikkun": "תיקון", "tikkunim": "תיקונים",
    "shevirah": "שבירה",
    "partzuf": "פרצוף", "partzufim": "פרצופים",
    # ── Niveaux d'âme ──
    "neshamah": "נשמה", "ruach": "רוח", "ruah": "רוח",
    "nefesh": "נפש", "hayah": "חיה", "yehidah": "יחידה",
    "naran": "נר״ן", "naranhai": "נרנח״י",
    # ── Kelim ──
    "keli": "כלי", "kelim": "כלים",
    "kotel": "כותל",
    "masakh": "מסך", "masakhim": "מסכים",
    # ── Hevel / Sens ──
    "hevel": "הבל", "hevelim": "הבלים",
    "einayim": "עיניים", "ozen": "אוזן", "oznayim": "אוזניים",
    "hotem": "חוטם", "peh": "פה",
    "metzah": "מצח",
    # ── Concepts courants ──
    "ein": "אין", "sof": "סוף",
    "eser": "עשר", "sefirot": "ספירות",
    "klipah": "קליפה", "klipot": "קליפות",
    "kelipah": "קליפה", "kelipot": "קליפות",
    "nitzotz": "ניצוץ", "nitzotzot": "ניצוצות",
    "zivvug": "זיווג",
    "mochin": "מוחין", "mohin": "מוחין",
    "katnut": "קטנות", "gadlut": "גדלות",
    "kavanah": "כוונה", "devekut": "דבקות",
    "hitbonenut": "התבוננות",
    "tzeruf": "צירוף", "gematria": "גימטריא",
    "merkavah": "מרכבה",
    "torah": "תורה", "mitzvah": "מצוה",
    "teshuvah": "תשובה",
    "ratzon": "רצון",
    "birur": "בירור",
    "levush": "לבוש", "levushim": "לבושים", "malbush": "מלבוש",
    "malbushim": "מלבושים",
    "haarah": "הארה",
    "hitlabshut": "התלבשות",
    "hitpashtut": "התפשטות",
    "histakkelut": "הסתכלות",
    "histalkut": "הסתלקות",
    "hishtalshelut": "השתלשלות",
    "shefa": "שפע",
    "hiyut": "חיות",
    # ── Anatomie du Partzuf ──
    "gulgalta": "גולגלתא", "gulgolta": "גולגלתא",
    "dikna": "דיקנא",
    "garon": "גרון",
    "hazeh": "חזה",
    "tabur": "טבור",
    "raglei": "רגלי",
    "akevayim": "עקביים",
    "shokayim": "שוקיים",
    # ── Noms divins ──
    "havayah": "הוי״ה", "yhvh": "יהו״ה",
    "ehyeh": "אהי״ה",
    "elohim": "אלהים",
    "adny": "אדנ״י", "adnut": "אדנות",
    "shaddai": "שדי",
    # ── Miluyim ──
    "miluy": "מילוי", "miluyim": "מילויים",
    "yudin": "יודין", "hehin": "ההין", "alefin": "אלפין",
    # ── Nombres comme mots ──
    "shalosh": "שלוש", "shloshah": "שלושה",
    "arba": "ארבע",
    "hamesh": "חמש", "hamishah": "חמישה",
    "shesh": "שש", "shishah": "ששה",
    "sheva": "שבע", "shivah": "שבעה",
    "shmoneh": "שמונה",
    "tesha": "תשע", "tishah": "תשעה",
    "eser": "עשר", "asarah": "עשרה",
    "meah": "מאה",
    "elef": "אלף",
    # ── Lettres comme mots ──
    "alef": "אלף", "bet": "בית", "gimel": "גימל",
    "dalet": "דלת", "heh": "ה׳", "vav": "ו׳",
    "zayin": "זין", "het": "חית", "tet": "טית",
    "yod": "יוד", "kaf": "כף", "lamed": "למד",
    "mem": "מם", "nun": "נון", "samekh": "סמך",
    "ayin": "עין", "pe": "פא", "tzadi": "צדי",
    "qof": "קוף", "resh": "ריש", "shin": "שין", "tav": "תו",
    # ── Directions / positions ──
    "elyon": "עליון", "tahton": "תחתון",
    "pnimi": "פנימי", "hitzon": "חיצון",
    "yamin": "ימין", "smol": "שמאל",
    "emtza": "אמצע", "emtzai": "אמצעי",
    "tokh": "תוך",
    "panim": "פנים", "ahor": "אחור",
    "achorayim": "אחוריים",
    "shamayim": "שמים",
    # ── Processus ──
    "ibur": "עיבור", "yenikah": "יניקה",
    "gadol": "גדול", "katan": "קטן",
    "aliyah": "עלייה", "yeridah": "ירידה",
    "hitrabut": "התרבות",
    "hakafah": "הקפה",
    "pegi_ah": "פגיעה",
    "haka_ah": "הכאה",
    # ── Relations ──
    "be": "ב", "le": "ל", "mi": "מ", "de": "ד",
    "ve": "ו", "al": "על", "ad": "עד",
    "lo": "לא", "ein": "אין", "kol": "כל",
    "zeh": "זה",
    # ── Concepts Etz Chaim spécifiques ──
    "igulei": "עיגולי",
    "nekudim": "נקודים", "nekudot": "נקודות",
    "akudim": "עקודים",
    "berudim": "ברודים",
    "tehiru": "תהירו",
    "tzahtzahot": "צחצחות",
    "hanhagah": "הנהגה", "hanhagot": "הנהגות",
    "atzmut": "עצמות",
    "ruhaniyut": "רוחניות",
    "gashmiyut": "גשמיות",
    "pashut": "פשוט",
    "dak": "דק",
    "zakh": "זך", "zak": "זך",
    "av": "עב",
    "gar": "ג״ר",
    "zat": "ז״ת",
    "nhy": "נה״י", "hgt": "חג״ת", "khbd": "חב״ד",
    "chbtm": "חב״תם",
    "sg": "ס״ג", "mah": "מ״ה", "ban": "ב״ן",
    "za": "ז״א", "zun": "זו״ן",
    "aa": "א״א", "ak": "אד״ק",
    "es": "א״ס",
    "om": "א״מ", "op": "א״פ",
    # ── Verbes / adjectifs ──
    "kolel": "כולל", "shalem": "שלם", "shaveh": "שווה",
    "shavim": "שווים",
    "rishon": "ראשון", "aharon": "אחרון",
    "gadol": "גדול", "katan": "קטן",
    "agol": "עגול",
    "sovev": "סובב", "malei": "מלא",
    "davuk": "דבוק",
    "metzumtzam": "מצומצם",
    "mugbal": "מוגבל",
    "nikhlalin": "נכללים",
    "mitpashtetet": "מתפשטת",
    "mizdakekh": "מזדכך",
    "boke_a": "בוקע",
    "over": "עובר",
    "nivla": "נבלע",
    "mehayeh": "מחיה",
    "malbish": "מלביש",
    # ── Figures bibliques / kabbalistiques ──
    "leah": "לאה", "rachel": "רחל",
    "yaakov": "יעקב", "yisrael": "ישראל",
    "moshe": "משה",
    "saba": "סבא",
    # ── Misc ──
    "seder": "סדר", "klal": "כלל", "prat": "פרט",
    "pratiyim": "פרטיים",
    "behinah": "בחינה", "behinot": "בחינות",
    "madregot": "מדרגות", "madregah": "מדרגה",
    "komah": "קומה",
    "dugmah": "דוגמה",
    "sibah": "סיבה",
    "takhlit": "תכלית",
    "koah": "כח",
    "ofen": "אופן",
    "makom": "מקום",
    "zman": "זמן",
    "middah": "מידה", "midot": "מידות",
    "shem": "שם", "shemot": "שמות",
    "otiyot": "אותיות",
    "milah": "מילה",
    "lashon": "לשון",
    "shoresh": "שורש",
    "anafim": "ענפים",
    "evarim": "אברים",
    "gidin": "גידין",
    "shasah": "שס״ה",
    "ramah": "רמ״ח",
    "dimyon": "דמיון", "dimyonot": "דמיונות",
    "mashal": "משל",
    "tziur": "ציור", "tziurim": "ציורים",
    "ma_alah": "מעלה",
    "gavo_a": "גבוה",
    "hashvaah": "השוואה",
    "kushia": "קושיא",
    "iyun": "עיון",
    "drush": "דרוש",
    "remez": "רמז",
    "sod": "סוד",
    "niflah": "נפלא",
    "mamash": "ממש",
    "bi_khlal": "בכלל",
    "stam": "סתם",
    "gamur": "גמור",
    "gemurah": "גמורה",
    # ── Nombres numériques ──
    "2": "ב׳", "3": "ג׳", "4": "ד׳", "5": "ה׳",
    "6": "ו׳", "7": "ז׳", "8": "ח׳", "9": "ט׳",
    "10": "י׳", "12": "י״ב", "13": "י״ג",
    "14": "י״ד", "15": "ט״ו", "20": "כ׳",
    "22": "כ״ב", "26": "כ״ו", "32": "ל״ב",
    "33": "ל״ג", "42": "מ״ב", "45": "מ״ה",
    "46": "מ״ו", "50": "נ׳", "52": "נ״ב",
    "58": "נ״ח", "63": "ס״ג", "72": "ע״ב",
    "89": "פ״ט", "91": "צ״א", "100": "ק׳",
    "110": "ק״י", "130": "ק״ל", "216": "רי״ו",
    "266": "רס״ו", "365": "שס״ה", "370": "ש״ע",
    "378": "שע״ח", "425": "תכ״ה",
    # ── Mots courants supplémentaires ──
    "ehad": "אחד", "ahat": "אחת",
    "rishon": "ראשון", "rishonah": "ראשונה",
    "shelemim": "שלמים", "shlemah": "שלמה",
    "galgal": "גלגל", "galgalim": "גלגלים",
    "gufa": "גופא",
    "moah": "מוח", "moha": "מוחא",
    "din": "דין",
    "nusah": "נוסח", "aher": "אחר",
    "zohar": "זוהר",
    "shema": "שמע",
    "bilti": "בלתי",
    "lev": "לב",
    "kaved": "כבד",
    "mador": "מדור",
    "ikar": "עיקר",
    "kamut": "כמות", "eikhut": "איכות",
    "yom": "יום", "laylah": "לילה",
    "hol": "חול", "shabbat": "שבת",
    "ben": "בן", "bat": "בת",
    "bya": "בי״ע",
    "briah": "בריאה",
    "la": "לא", "ha": "ה",
    "ehyeh": "אהי״ה",
    "melekh": "מלך", "melakhim": "מלכים",
    "oleh": "עולה",
    "avi": "או״א",
    "tefilot": "תפילות", "tefilah": "תפילה",
    "ketz": "קץ",
    "atar": "אתר",
    "tzadik": "צדיק", "tzaddik": "צדיק",
    "ani": "אני", "ain": "אין",
    "tikkunei": "תיקוני",
    "bein": "בין",
    "garon": "גרון",
    "noge": "נוגע",
    "kelipah": "קליפה",
    "shivah": "שבעה", "shivat": "שבעת",
    "reki": "רקיע", "rekim": "רקיעים",
    "model": "מודל",
    "nefesh_hevel_peh": "נפש הבל פה",
    "rappel": "תזכורת",
    "double": "כפול",
    "complete": "שלם",
    "total": "סה״כ",
    "secret": "סוד",
    "kitzrei": "קיצרי",
    "pratei": "פרטי",
    "asur": "אסור",
    "mutar": "מותר",
    "kodem": "קודם",
    "aharon": "אחרון",
    "tahtit": "תחתית",
    "erekh": "ערך",
    "mahut": "מהות",
    "mispar": "מספר",
    "mishkal": "משקל",
    "kitzvah": "קצבה",
    "havdalah": "הבדלה",
    "bereshit": "בראשית",
    "guf_zakh": "גוף זך",
    "dak": "דק",
    "tzurah": "צורה",
    "homer": "חומר",
    "etzem": "עצם",
    "evarim": "אברים",
    "barukh": "ברוך",
    "tov": "טוב", "ra": "רע",
    "beinoni": "בינוני",
    "perat": "פרט",
    "gashmiyut": "גשמיות",
    "gavo": "גבוה",
    "mufshat": "מופשט",
    "muvdal": "מובדל",
    "murhak": "מורחק",
    "nimratz": "נמרץ",
    "helm": "חלם",
    "seder": "סדר",
    "safed": "צפת",
    "ma_or": "מאור",
    "ne_elam": "נעלם",
    "ne_etzal": "נאצל",
    "ne_etzalim": "נאצלים",
    "hishtalshelut": "השתלשלות",
    "nitu_ah": "ניתוח",
    "sifrei": "ספרי",
    "tokhniyim": "תוכניים",
    "maamarim": "מאמרים",
    "mahloket": "מחלוקת",
    "hakirah": "חקירה",
    "sibah": "סיבה",
    "kovea": "קובע",
    "hishtatfut": "השתתפות",
    "mesugal": "מסוגל",
    "rahamim": "רחמים",
    "gevurot": "גבורות",
    "hassadim": "חסדים",
    "dinim": "דינים",
    "kelipot_hutz": "קליפות חוץ",
    "atarah": "עטרה",
    "rehem": "רחם",
    "dam": "דם",
    "besar": "בשר",
    "tapuah": "תפוח",
    "butzina": "בוצינא",
    "kardinuta": "דקרדינותא",
    "almin": "עלמין",
    "dargin": "דרגין",
    "navkhu": "נבכו",
    "nir_ah": "נראה",
    "nigleh": "נגלה",
    "ne_elam": "נעלם",
    "nashim": "נשים",
    "melakhim": "מלכים",
    "benei": "בני",
    "va_yar": "וירא",
    "va_yavdel": "ויבדל",
    "noge_a": "נוגעת",
    "barkhi": "ברכי",
    "nafshi": "נפשי",
    "ofanim": "אופנים",
    "merkavat": "מרכבת",
    "yehezkel": "יחזקאל",
    "heikhalot": "היכלות",
    "heikhal": "היכל",
    "igulei": "עיגולי",
    "olamot_kadmim": "עולמות קדמים",
    "nikpalim": "נכפלים",
    "idrot": "אדרות",
    "medabrot": "מדברות",
    "hakdamah": "הקדמה",
    "hakdamot": "הקדמות",
    "necessary": "הכרחי",
    "shulei": "שולי",
    "amah": "אמה",
    "yikhlu": "יכלו",
    "lisvol": "לסבול",
    "tsidadin": "צדדין",
    "hibur": "חיבור",
    "hithabrut": "התחברות",
    "hevelim": "הבלים",
    "mashpia": "משפיע",
    "mekabel": "מקבל",
    "nivra": "נברא",
    "notzrim": "נוצרים",
    "na_asim": "נעשים",
    "mai_in": "מיין",
    "idra": "אדרא",
    "zuta": "זוטא",
    "rabba": "רבא",
    "illat": "עילת",
    "illot": "עילות",
    "shikul": "שיקול",
    "mu_at": "מועט",
    "gadol": "גדול",
    "tamarah": "תמרה",
    "shalosh": "שלוש",
    "hevelim": "הבלים",
    "heverim": "חברים",
    "metzius": "מציאות",
    "tziyur": "ציור",
    "tziurim": "ציורים",
    "sha_ah": "שעה",
    "mishtaneh": "משתנה",
    "domeh": "דומה",
    "lekasher": "לקשר",
    "lesakekh": "לסכך",
    "shakhekh": "לשכח",
    "mehulapim": "מהולפים",
    "shonim": "שונים",
    "hitukh": "התוך",
    "otiot": "אותיות",
    "hokhmat": "חכמת",
    "tziruf": "צירוף",
    "shi_ur": "שיעור",
    "kodesh": "קודש",
    "reshet": "רשת",
    "keri_ah": "קריאה",
    "aliyat_ha_tefilot": "עליית התפילות",
    "mahshavah": "מחשבה",
    "pegi_ah": "פגיעה",
    "re_iyah": "ראייה",
    "haka_ah": "הכאה",
    "hitpashtut_ve_hit_aglut": "התפשטות והתעגלות",
    "ma_alah": "מעלה",
    # ── Batch 2 : tokens manquants identifiés ──
    "hatzi": "חצי",
    "karov": "קרוב",
    "reshit": "ראשית",
    "nekudah": "נקודה", "nekudat": "נקודת",
    "tipat": "טיפת", "tipah": "טיפה",
    "shlemut": "שלימות",
    "roshei": "ראשי", "teivot": "תיבות",
    "shtei": "שתי",
    "tamid": "תמיד", "nimtza": "נמצא",
    "elou": "אלו",
    "kulam": "כולם",
    "hitzoniim": "חיצוניים", "pnimiim": "פנימיים",
    "nekavim": "נקבים", "halonot": "חלונות",
    "mazalot": "מזלות", "kokhavim": "כוכבים",
    "malkhei": "מלכי", "edom": "אדום",
    "kolot": "קולות",
    "divrei": "דברי",
    "rashbi": "רשב״י",
    "sakkanah": "סכנה", "sakkanat": "סכנת",
    "bitul": "ביטול",
    "shlemah": "שלמה",
    "alafim": "אלפים", "revavot": "רבבות",
    "ruhaniyim": "רוחניים",
    "sefirot_pratit_pratiyot": "ספירות פרטית פרטיות",
    "galgal": "גלגל", "galgalim": "גלגלים",
    "gildei": "קליפות", "betzalim": "בצלים",
    "zakan": "זקן",
    "samukh": "סמוך",
    "mitdabek": "מתדבק",
    "nitpasim": "נתפסים",
    "kesher": "קשר", "amitz": "אמיץ",
    "tzorekh": "צורך",
    "dai": "דיי",
    "havayot": "הוויות",
    "rashim": "ראשים", "nifradim": "נפרדים",
    "reshut": "רשות",
    "haser": "חסר",
    "shemi": "שמיעה",
    "mekannena": "מקננת",
    "ofan": "אופן",
    "ofen": "אופן",
    "loven": "לובן",
    "odem": "אודם",
    "rahok": "רחוק",
    "ahar": "אחר",
    "kakh": "כך",
    "hoveh": "הווה", "yihiyeh": "יהיה",
    "hashanah": "השנה",
    "hehs": "ההי״ן",
    "inuyim": "עינויים",
    "hitparshut": "התפרשות",
    "ikveta": "עקבתא", "meshiha": "משיחא",
    "mahadura": "מהדורא", "tinyana": "תנינא",
    "nikpalim": "נכפלים",
    "kodem": "קודם", "lakol": "לכל",
    "nekevah": "נקבה", "tesovev": "תסובב",
    "merkaz": "מרכז",
    "sifra": "ספרא", "heniuta": "דצניעותא",
    "kaddur": "כדור", "aretz": "ארץ",
    "yihudim": "יחודים",
    "niknas": "נכנס",
    "mitztamtzem": "מצטמצם",
    "mekabel": "מקבל",
    "noda": "נודע",
    "helbenah": "חלבנה", "levonah": "לבונה",
    "muflah": "מופלא", "tidrosh": "תדרוש",
    "bore": "בורא",
    "revi": "רביע",
    "hakirot": "חקירות",
    # ── Aramaic/Zoharic ──
    "risha": "רישא",
    "ama": "אמה",
    "gufa": "גופא",
    "mavri": "מבריח",
    "havarta": "הבערתא",
    "sheniut": "שניות",
    "nayha": "נייחא", "ilayn": "עילאין", "tatayn": "תתאין",
    "mil": "מיל", "gaw": "גו", "bar": "בר",
    "ke": "כ", "hada": "חדא",
    "malekhu": "מלכו", "metu": "ומתו",
    "matzitz": "מציץ", "harakim": "החרכים",
    "reiyah": "ראייה", "shemiyah": "שמיעה",
    "reiha": "ריחא",
    "vayifen": "ויפן", "vakho": "וכה",
    "yahzor": "יחזור", "khamot": "חומות",
    "yaskil": "ישכיל", "yarum": "ירום",
    "nissa": "נישא", "gavah": "גבה",
    "zokheh": "זוכה", "koneh": "קונה",
    "zakhah": "זכה", "yatir": "יתיר",
    "nitzotzei": "ניצוצי", "oram": "אורם",
    "raglav": "רגליו", "har": "הר", "zeitim": "זיתים",
    # ── Verbes et formes ──
    "bara": "ברא", "yatzar": "יצר", "asah": "עשה",
    "etzil": "האציל",
    "creates": "יוצר",
    "determines": "קובע",
    "maspik": "מספיק",
    "kedei": "כדי", "tzorkham": "צרכם",
    "pnimiim": "פנימיים",
    "hitzoniim": "חיצוניים",
    # ── Français mixed terms ──
    "cascade": "מפל",
    "proportion": "יחס",
    "structure": "מבנה",
    "fractal": "פרקטלי",
    "sequential": "סדרתי",
    "alternance": "חילוף",
    "convergence": "התכנסות",
    "equilibre": "שיווי משקל",
    "fractalite": "פרקטליות",
    "hierarchy": "היררכיה",
    "emboitement": "שכבות",
    "asymmetrie": "אסימטריה",
    "paradox": "פרדוקס",
    "distance": "מרחק",
    "rencontre": "מפגש",
    "inversion": "היפוך",
    # ── Batch 3 : derniers tokens manquants ──
    "katzeh": "קצה",
    "aliyat": "עליית",
    "hitei": "חיטי",
    "ittaknu": "אתתקנו",
    "shimah": "שימה",
    "takhton": "תחתון",
    "pnimiy": "פנימי",
    "kotzo": "קוצו",
    "eleinu": "אלינו",
    "siyum": "סיום",
    "karov": "קרוב",
    "all": "כל",
    "is": "הוא",
    "another": "עוד",
    "from": "מ",
    "one": "אחד",
    "side": "צד",
    "not": "לא",
    "food": "מזון",
    "need": "צריך",
    "ko": "כה",
    "ovi": "עובי",
    "metzi": "מציאויות",
    "born": "נולד",
    "ashkenazi": "אשכנזי",
    "substance": "ממשות",
    "form": "צורה",
    "letter": "אות",
    "letters": "אותיות",
    "addition": "תוספת",
    "first": "ראשון",
    "second": "שני",
    "higher": "גבוה",
    "lower": "נמוך",
    "above": "למעלה",
    "below": "למטה",
    "between": "בין",
    "only": "בלבד",
    "also": "גם",
    "never": "לעולם לא",
    "creates": "יוצר",
    "grows": "גדל",
    "descend": "יורדים",
    "ascend": "עולים",
}


# ── Source 3 : Préfixes d'abréviations ──────────────────────────
# Ces préfixes encodent un partzuf/concept qui préfixe le concept_id

_PREFIX_MAP: dict[str, str] = {
    "ak": "אד״ק",    # Adam Kadmon
    "aa": "א״א",     # Arikh Anpin
    "es": "א״ס",     # Ein Sof
    "om": "א״מ",     # Ohr Makif
    "op": "א״פ",     # Ohr Pnimi
}


# ── Compound tokens (multi-underscore) ──────────────────────────
# Certains groupes de tokens forment un terme unique

_COMPOUND_TOKENS: dict[tuple[str, ...], str] = {
    # ── Termes fondamentaux ──
    ("ein", "sof"): "אין סוף",
    ("adam", "kadmon"): "אדם קדמון",
    ("arikh", "anpin"): "אריך אנפין",
    ("zeir", "anpin"): "זעיר אנפין",
    ("atik", "yomin"): "עתיק יומין",
    ("adam", "ehad"): "אדם אחד",
    ("adam", "ha", "elyon"): "אדם העליון",
    ("adam", "elyon"): "אדם עליון",
    # ── Lumières ──
    ("ohr", "yashar"): "אור ישר",
    ("ohr", "chozer"): "אור חוזר",
    ("ohr", "hozer"): "אור חוזר",
    ("ohr", "pnimi"): "אור פנימי",
    ("ohr", "makif"): "אור מקיף",
    ("ohr", "pashut"): "אור פשוט",
    ("ohr", "ehad"): "אור אחד",
    ("ohr", "gadol"): "אור גדול",
    ("ohr", "ayin"): "אור עין",
    ("ohr", "ve", "shefa"): "אור ושפע",
    ("ohr", "yosher"): "אור יושר",
    ("ohr", "et"): "אור א״ת",
    ("ohr", "atzmo"): "אור עצמו",
    ("ohr", "rishon"): "אור ראשון",
    ("ohr", "levanah"): "אור לבנה",
    # ── Kav ──
    ("kav", "yashar"): "קו ישר",
    ("kav", "dak"): "קו דק",
    ("kav", "ehad"): "קו אחד",
    ("kav", "emtzai"): "קו אמצעי",
    # ── Halal ──
    ("halal", "panui"): "חלל פנוי",
    ("halal", "rikani"): "חלל ריקני",
    ("halal", "agol"): "חלל עגול",
    # ── Structure ──
    ("rosh", "guf"): "ראש גוף",
    ("guf", "neshamah"): "גוף נשמה",
    ("eser", "sefirot"): "עשר ספירות",
    ("ein", "rosh"): "אין ראש",
    ("malei", "kol"): "מלא כל",
    ("lo", "tefisah"): "לא תפיסה",
    # ── Expressions composées ──
    ("ad", "ein", "ketz"): "עד אין קץ",
    ("ein", "sof", "shaveh"): "אין סוף שווה",
    ("ein", "kitzvah"): "אין קצבה",
    ("ein", "koah"): "אין כח",
    ("ein", "guf"): "אין גוף",
    ("ein", "hutzah"): "אין חוצה",
    ("ein", "reshut"): "אין רשות",
    ("ein", "avir"): "אין אויר",
    ("ein", "ohr"): "אין אור",
    ("ein", "sha_ah"): "אין שעה",
    ("ein", "yom"): "אין יום",
    ("ein", "oskim"): "אין עוסקים",
    ("ein", "hevel"): "אין הבל",
    ("ein", "yekholet"): "אין יכולת",
    # ── Processus ──
    ("re", "iyah"): "ראייה",
    ("haka", "ah"): "הכאה",
    ("haka", "at"): "הכאת",
    ("pegi", "ah"): "פגיעה",
    ("hitpashtut", "ve", "hit", "aglut"): "התפשטות והתעגלות",
    ("ma", "alah"): "מעלה",
    ("gavo", "a"): "גבוה",
    ("ne", "elam"): "נעלם",
    ("ne", "etzal"): "נאצל",
    ("ne", "etzalim"): "נאצלים",
    ("ne", "ehazim"): "נאחזים",
    ("ne", "elamim"): "נעלמים",
    ("noge", "a"): "נוגעת",
    ("nir", "ah"): "נראה",
    ("ma", "atzil"): "מאציל",
    ("me", "ir"): "מאיר",
    ("me", "od"): "מאוד",
    ("im", "tarutz"): "אם תרוץ",
    ("ma", "or"): "מאור",
    ("lo", "ad"): "לא עד",
    ("lo", "she"): "לא ש",
    ("lo", "shavim"): "לא שווים",
    ("lo", "meruba"): "לא מרובע",
    ("lo", "gorsinan"): "לא גרסינן",
    ("lo", "zaviyot"): "לא זוויות",
    ("lo", "middah"): "לא מידה",
    ("lo", "noge_a"): "לא נוגע",
    ("lo", "yitzdak"): "לא יצדק",
    ("lo", "efshar"): "לא אפשר",
    ("lo", "behinat"): "לא בחינת",
    # ── Verbes composés ──
    ("mati", "ve", "lo", "mati"): "מטי ולא מטי",
    ("zeh", "tokh", "zeh"): "זה תוך זה",
    ("zeh", "ahar", "zeh"): "זה אחר זה",
    ("zeh", "hofef", "la", "zeh"): "זה חופף לזה",
    # ── Nusah ──
    ("nusah", "aher"): "נוסח אחר",
    # ── Butzina de-Kardinuta ──
    ("butzina", "de", "kardinuta"): "בוצינא דקרדינותא",
    # ── Abréviations ──
    ("avi", "gorge"): "או״א גרון",
    ("avi", "malbish"): "או״א מלביש",
    # ── Collocations Etz Chaim ──
    ("rosh", "guf", "raglayim"): "ראש גוף רגליים",
    ("igulim", "ve", "yosher"): "עיגולים ויושר",
    ("pnimi", "hitzon"): "פנימי חיצון",
    ("pnimiyut", "hitzoniut"): "פנימיות חיצוניות",
    ("komah", "shavah"): "קומה שוואה",
    ("komah", "zekufah"): "קומה זקופה",
    ("bya", "olam", "ehad"): "בי״ע עולם אחד",
    ("ben", "nukvah"): "בן נוקבא",
    ("sod", "neshamah"): "סוד נשמה",
    ("klal", "prat"): "כלל פרט",
    ("prat", "kolel"): "פרט כולל",
    ("alef", "alafim"): "אלף אלפים",
    ("atidin", "le"): "עתידין ל",
    ("dam", "hu", "nefesh"): "דם הוא נפש",
    ("behinah", "shlemah"): "בחינה שלמה",
    ("meshubah", "makif"): "משובח מקיף",
    ("haarah", "shlemah"): "הארה שלמה",
    ("haarah", "lo", "shlemah"): "הארה לא שלמה",
    ("kol", "neshamah"): "כל נשמה",
    ("binah", "kolot"): "בינה קולות",
    ("shituf", "rahamim", "din"): "שיתוף רחמים דין",
    # ── Batch 2 : compounds manquants ──
    ("mahshavah", "ila", "ah"): "מחשבה עילאה",
    ("eikhut", "revi", "it"): "איכות רביעית",
    ("tevunah", "revi", "it"): "תבונה רביעית",
    ("nekudah", "emtza", "it"): "נקודה אמצעית",
    ("elou", "ve", "elou"): "אלו ואלו",
    ("he", "etzil", "bara", "yatzar", "asah"): "האציל ברא יצר עשה",
    ("me", "uleh"): "מעולה",
    ("me", "ulim"): "מעולים",
    ("hitzoniut", "me", "uleh"): "חיצוניות מעולה",
    ("gildei", "betzalim"): "קליפות בצלים",
    ("ikveta", "meshiha"): "עקבתא דמשיחא",
    ("hayah", "hoveh", "yihiyeh"): "היה הווה יהיה",
    ("malekhu", "u", "metu"): "מלכו ומתו",
    ("shivat", "malkhei", "edom"): "שבעת מלכי אדום",
    ("shivah", "malkhei", "edom"): "שבעה מלכי אדום",
    ("nusah", "aher", "01"): "נוסח אחר א׳",
    ("nusah", "aher", "02"): "נוסח אחר ב׳",
    ("nusah", "aher", "03"): "נוסח אחר ג׳",
    ("nusah", "aher", "04"): "נוסח אחר ד׳",
    ("nusah", "aher", "05"): "נוסח אחר ה׳",
    ("nusah", "aher", "06"): "נוסח אחר ו׳",
    ("va", "yar", "elohim"): "וירא אלהים",
    ("va", "yavdel", "kelim"): "ויבדל כלים",
    ("tipat", "loven", "hassadim"): "טיפת לובן חסדים",
    ("tipat", "odem", "malkhut"): "טיפת אודם מלכות",
    ("mi", "bara", "eleh"): "מי ברא אלה",
    ("pashut", "male", "male", "demale"): "פשוט מלא מלא דמלא",
    ("hokhmat", "shi", "ur"): "חכמת שיעור",
    ("shi", "ur", "maspik"): "שיעור מספיק",
    ("killu", "ah"): "כילוי",
    ("killu", "ah", "hevel"): "כילוי הבל",
    ("pe", "ulot", "kohot"): "פעולות כוחות",
    ("pesi", "ah"): "פסיעה",
    ("pesi", "ah", "le", "var"): "פסיעה לבר",
    ("nitu", "ah"): "ניתוח",
    ("nitu", "ah", "evarim"): "ניתוח אברים",
    ("re", "ah", "niho", "ah"): "ריח ניחוח",
    ("sibah", "noda", "at"): "סיבה נודעת",
    ("shemi", "ah", "heh"): "שמיעה ה׳",
    ("om", "eino", "boke", "a"): "א״מ אינו בוקע",
    ("op", "mu", "at"): "א״פ מועט",
    ("barkhi", "nafshi"): "ברכי נפשי",
    ("ruach", "ahar", "kakh"): "רוח אחר כך",
    ("klal", "ahar", "hathala"): "כלל אחר התחלה",
    ("etzem", "pa", "arot"): "עצם פעורות",
    ("dam", "hu", "nefesh"): "דם הוא נפש",
    ("hatzi", "ovi", "kotel"): "חצי עובי כותל",
    ("avi", "gorge", "to", "navel"): "או״א גרון לטבור",
    ("ke", "mar", "eh", "adam"): "כמראה אדם",
    ("mil", "gaw", "mil", "bar"): "מיל גו מיל בר",
    ("nayha", "ilayn", "tatayn"): "נייחא עילאין תתאין",
    ("ou", "a", "ke", "hada"): "כחדא",
    ("sifra", "de", "heniuta"): "ספרא דצניעותא",
    ("risha", "de", "ama"): "רישא דאמה",
    ("vayifen", "ko", "vakho"): "ויפן כה וכה",
    ("yaskil", "yarum", "nissa", "gavah"): "ישכיל ירום ונשא גבה",
    ("mahadura", "tinyana"): "מהדורא תנינא",
    ("ak", "mavri", "ah"): "אד״ק מבריח",
    ("ak", "sheniut"): "אד״ק שניות",
    ("garoua", "malbish", "me", "uleh"): "גרוע מלביש מעולה",
    ("shfulei", "me", "ayim"): "שפולי מעיים",
    ("ma", "amad", "zmani"): "מעמד זמני",
    ("ma", "anin", "atzilut"): "מעניין אצילות",
    ("samukh", "bilti", "mitdabek"): "סמוך בלתי מתדבק",
    ("rosh", "hashanah", "pnimiim"): "ראש השנה פנימיים",
    ("reiyah", "shemiyah", "reiha", "dibur"): "ראייה שמיעה ריחא דיבור",
    ("muflah", "al", "tidrosh"): "מופלא אל תדרוש",
    ("four", "hehs", "20"): "ד׳ ההי״ן כ׳",
    ("three", "alefs", "100"): "ג׳ אלפין ק׳",
    ("havarta", "risha"): "הבערתא רישא",
    ("helbenah", "levonah"): "חלבנה לבונה",
    ("karov", "el", "siyum"): "קרוב אל סיום",
    ("karov", "eleinu", "kelipah"): "קרוב אלינו קליפה",
    ("kelim", "na", "aseh"): "כלים נעשה",
    ("matzitz", "min", "harakim"): "מציץ מן החרכים",
    ("raglav", "har", "zeitim"): "רגליו הר זיתים",
    ("kaddur", "aretz", "nekudah"): "כדור ארץ נקודה",
    ("sefirot", "pratit", "pratiyot"): "ספירות פרטית פרטיות",
    ("shefa", "kedei", "tzorkham"): "שפע כדי צרכם",
    ("kitruk", "levanah"): "כתרוק לבנה",
    ("nekevah", "tesovev"): "נקבה תסובב",
    ("noah", "noah", "drasha"): "נוח נוח דרשא",
    ("zokheh", "koneh"): "זוכה קונה",
    ("zakhah", "yatir"): "זכה יתיר",
    ("alafim", "revavot", "olamot"): "אלפים רבבות עולמות",
    # ── Batch 3 : derniers termes mixtes anglais/français/hébreu ──
    ("kav", "from", "one", "side"): "קו מצד אחד",
    ("kav", "seul", "lien"): "קו חיבור יחיד",
    ("igulim", "as", "heavens"): "עיגולים כרקיעים",
    ("igulim", "external", "high"): "עיגולים חיצוניים גבוהים",
    ("yosher", "internal", "high"): "יושר פנימי גבוה",
    ("shalosh", "metzi", "uyot"): "שלוש מציאויות",
    ("rencontre", "au", "milieu"): "מפגש באמצע",
    ("hierarchies", "inversees"): "היררכיות הפוכות",
    ("nitrahek", "la", "tzedadim"): "נתרחק לצדדים",
    ("kolot", "not", "food"): "קולות לא מזון",
    ("hevelim", "need", "substance"): "הבלים צריכים ממשות",
    ("derivation", "8", "parts"): "גזירה ח׳ חלקים",
    ("solar", "year", "365"): "שנת חמה שס״ה",
    ("two", "parts", "descend"): "שני חלקים יורדים",
    ("three", "sg", "types"): "ג׳ סוגי ס״ג",
    ("two", "yihudim", "shema"): "שני יחודים שמע",
    ("tzimtzum", "then", "return"): "צמצום ואח״כ חזרה",
    ("resolution", "ari"): "הכרעת האר״י",
    ("ak", "has", "beginning"): "אד״ק יש לו התחלה",
    ("zt", "descend"): "ז״ת יורדים",
    ("kh", "letters", "shema"): "כ״ב אותיות שמע",
    ("external", "higher"): "חיצון גבוה",
    ("internal", "lowest"): "פנימי תחתון",
    ("remaining", "above"): "נשאר למעלה",
    ("proximity", "source"): "קרבת מקור",
    ("preservation", "asymmetry"): "שימור אסימטריה",
    ("order", "universal"): "סדר כללי",
    ("universal", "law"): "חוק כללי",
    ("root", "determines", "class"): "שורש קובע סוג",
    ("classification", "by", "purpose"): "סיווג לפי תכלית",
    ("asymmetric", "extension"): "הרחבה אסימטרית",
    ("asymmetry", "creates", "direction"): "אסימטריה יוצרת כיוון",
    ("zaviyot", "problem"): "בעיית זוויות",
}


@dataclass
class EnrichmentResult:
    """Résultat de l'enrichissement d'un seul concept."""
    concept: str
    old_hebrew: str | None
    new_hebrew: str | None
    source: str  # "sifrei_yesod" | "canonical" | "compound" | "prefix+tokens" | "tokens" | "none"
    tokens_resolved: int = 0
    tokens_total: int = 0


@dataclass
class EnrichmentStats:
    """Statistiques globales d'un run d'enrichissement."""
    total_null: int = 0
    enriched: int = 0
    by_source: dict[str, int] = field(default_factory=dict)
    failed: list[str] = field(default_factory=list)
    coverage_before: float = 0.0
    coverage_after: float = 0.0


class HebrewEnrichment:
    """Rétro-enrichissement des hebrew_word manquants.

    Stratégie en cascade :
    1. Lookup direct dans sifrei_yesod_concepts.nom_he
    2. Match compound tokens (ein_sof → אין סוף)
    3. Décomposition en tokens avec prefix handling
    4. Chaque token → lookup dans vocabulaire fusionné
    """

    def __init__(self, db_url: str = "postgresql://localhost/etz_chaim"):
        self.db_url = db_url
        self._vocab: dict[str, str] = {}
        self._sifrei_vocab: dict[str, str] = {}
        self._loaded = False

    def _get_conn(self):
        """Emprunte une conn au pool (context manager)."""
        from pool import get_conn, init_pool
        init_pool(self.db_url)  # idempotent
        return get_conn()

    def _load_vocabulary(self) -> None:
        """Charge le vocabulaire depuis toutes les sources."""
        if self._loaded:
            return

        # Source 1: sifrei_yesod_concepts
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept_id, nom_he
                    FROM sifrei_yesod_concepts
                    WHERE nom_he IS NOT NULL
                """)
                for concept_id, nom_he in cur.fetchall():
                    self._sifrei_vocab[concept_id] = nom_he

        logger.info("Loaded %d pairs from sifrei_yesod_concepts", len(self._sifrei_vocab))

        # Fuse: canonical tokens + extracted single-token pairs from sifrei
        self._vocab = dict(_CANONICAL_TOKENS)

        # Extract single-token entries from sifrei as additional vocabulary
        for concept_id, nom_he in self._sifrei_vocab.items():
            if "_" not in concept_id:
                # Single token — add to vocabulary if not already present
                if concept_id not in self._vocab:
                    self._vocab[concept_id] = nom_he

        logger.info("Total vocabulary: %d tokens", len(self._vocab))
        self._loaded = True

    def _try_compound(self, tokens: list[str]) -> str | None:
        """Try matching token sequences against compound dictionary."""
        # Try full sequence
        key = tuple(tokens)
        if key in _COMPOUND_TOKENS:
            return _COMPOUND_TOKENS[key]

        # Try subsequences of length 4, 3, then 2 (greedy, left to right)
        result_parts = []
        i = 0
        any_compound = False
        while i < len(tokens):
            matched = False
            for length in (4, 3, 2):
                if i + length <= len(tokens):
                    sub = tuple(tokens[i:i + length])
                    if sub in _COMPOUND_TOKENS:
                        result_parts.append(_COMPOUND_TOKENS[sub])
                        i += length
                        matched = True
                        any_compound = True
                        break
            if not matched:
                # Try single token
                he = self._resolve_token(tokens[i])
                if he:
                    result_parts.append(he)
                i += 1

        if any_compound and result_parts:
            return " ".join(result_parts)
        return None

    def _resolve_token(self, token: str) -> str | None:
        """Resolve a single token to Hebrew."""
        # Direct lookup
        if token in self._vocab:
            return self._vocab[token]

        # Try with common suffix variations
        for suffix_from, suffix_to in [("ei", ""), ("ot", ""), ("im", ""),
                                        ("it", ""), ("ut", "")]:
            base = token.rstrip(suffix_from) if token.endswith(suffix_from) else None
            if base and base in self._vocab:
                return self._vocab[token] if token in self._vocab else None

        # Numbers
        if token.isdigit():
            return self._vocab.get(token, token)

        return None

    def _resolve_tokens(self, tokens: list[str]) -> list[str]:
        """Resolve a list of tokens to Hebrew parts."""
        parts = []
        for t in tokens:
            resolved = self._resolve_token(t)
            if resolved:
                parts.append(resolved)
        return parts

    def find_hebrew(self, concept_id: str) -> EnrichmentResult:
        """Find Hebrew word for a concept_id.

        Cascade:
        1. Direct sifrei_yesod lookup
        1b. Direct canonical lookup (full concept_id with underscores)
        2. Compound token matching
        3. Prefix + token decomposition
        """
        self._load_vocabulary()

        # 1. Direct sifrei_yesod lookup
        if concept_id in self._sifrei_vocab:
            return EnrichmentResult(
                concept=concept_id,
                old_hebrew=None,
                new_hebrew=self._sifrei_vocab[concept_id],
                source="sifrei_yesod",
                tokens_resolved=1, tokens_total=1,
            )

        # 1b. Direct lookup in vocabulary (some entries have underscores as keys)
        if concept_id in self._vocab:
            return EnrichmentResult(
                concept=concept_id,
                old_hebrew=None,
                new_hebrew=self._vocab[concept_id],
                source="canonical",
                tokens_resolved=1, tokens_total=1,
            )

        # Split into tokens
        tokens = concept_id.split("_")
        total_tokens = len(tokens)

        # 2. Compound token matching
        compound = self._try_compound(tokens)
        if compound:
            return EnrichmentResult(
                concept=concept_id,
                old_hebrew=None,
                new_hebrew=compound,
                source="compound",
                tokens_resolved=total_tokens, tokens_total=total_tokens,
            )

        # 3. Prefix handling
        prefix_he = None
        work_tokens = list(tokens)
        if len(tokens) >= 2 and tokens[0] in _PREFIX_MAP:
            prefix_he = _PREFIX_MAP[tokens[0]]
            work_tokens = tokens[1:]

        # 4. Token-by-token resolution
        parts = []
        resolved_count = 0

        if prefix_he:
            parts.append(prefix_he)
            resolved_count += 1

        # Try compound on remaining tokens first
        if len(work_tokens) >= 2:
            sub_compound = self._try_compound(work_tokens)
            if sub_compound:
                parts.append(sub_compound)
                resolved_count += len(work_tokens)
                return EnrichmentResult(
                    concept=concept_id,
                    old_hebrew=None,
                    new_hebrew=" ".join(parts),
                    source="prefix+compound" if prefix_he else "compound",
                    tokens_resolved=resolved_count,
                    tokens_total=total_tokens,
                )

        for token in work_tokens:
            he = self._resolve_token(token)
            if he:
                parts.append(he)
                resolved_count += 1

        if not parts:
            return EnrichmentResult(
                concept=concept_id,
                old_hebrew=None,
                new_hebrew=None,
                source="none",
                tokens_resolved=0, tokens_total=total_tokens,
            )

        # Require at least 50% of tokens resolved (or all for 1-token, 50%+ for 2+)
        # For single tokens, we need 100%. For multi-token, at least 50% resolved
        # but also at least 1 kabbalistic token (not just prefix)
        kab_parts = len(parts) - (1 if prefix_he else 0)
        min_ratio = 1.0 if total_tokens == 1 else 0.4
        if resolved_count / total_tokens < min_ratio or kab_parts == 0:
            return EnrichmentResult(
                concept=concept_id,
                old_hebrew=None,
                new_hebrew=None,
                source="none",
                tokens_resolved=resolved_count, tokens_total=total_tokens,
            )

        source = "prefix+tokens" if prefix_he else "tokens"
        return EnrichmentResult(
            concept=concept_id,
            old_hebrew=None,
            new_hebrew=" ".join(parts),
            source=source,
            tokens_resolved=resolved_count,
            tokens_total=total_tokens,
        )

    def get_null_concepts(self) -> list[str]:
        """Get all concept names with NULL hebrew_word from hybrid_embeddings."""
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT concept FROM hybrid_embeddings
                    WHERE hebrew_word IS NULL
                    ORDER BY concept
                """)
                return [row[0] for row in cur.fetchall()]

    def enrich_all(self, dry_run: bool = True) -> EnrichmentStats:
        """Enrich all NULL hebrew_word concepts.

        Args:
            dry_run: if True, compute results but don't write to DB

        Returns:
            EnrichmentStats with full report
        """
        self._load_vocabulary()

        null_concepts = self.get_null_concepts()
        total_in_db = self._count_total()
        stats = EnrichmentStats(
            total_null=len(null_concepts),
            coverage_before=(total_in_db - len(null_concepts)) / total_in_db if total_in_db else 0,
        )

        results: list[EnrichmentResult] = []
        for concept in null_concepts:
            result = self.find_hebrew(concept)
            results.append(result)
            if result.new_hebrew:
                stats.enriched += 1
                stats.by_source[result.source] = stats.by_source.get(result.source, 0) + 1
            else:
                stats.failed.append(concept)

        stats.coverage_after = (total_in_db - len(null_concepts) + stats.enriched) / total_in_db if total_in_db else 0

        if not dry_run:
            self._apply_enrichment(results)

        return stats

    def _count_total(self) -> int:
        with self._get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM hybrid_embeddings")
                return cur.fetchone()[0]

    def _apply_enrichment(self, results: list[EnrichmentResult]) -> int:
        """Apply enrichment results to DB: update hebrew_word + recompute signatures."""
        from kabbalah.hybrid_embedding import KabbalisticSignature, KABBALISTIC_DIM, HYBRID_DIM

        sig_engine = KabbalisticSignature()
        conn = self._get_conn()
        updated = 0

        try:
            with conn.cursor() as cur:
                batch = []
                for r in results:
                    if not r.new_hebrew:
                        continue
                    batch.append(r)

                    if len(batch) >= 100:
                        updated += self._apply_batch(cur, batch, sig_engine)
                        conn.commit()
                        batch = []

                if batch:
                    updated += self._apply_batch(cur, batch, sig_engine)
                    conn.commit()

            logger.info("Applied enrichment: %d concepts updated", updated)
        except Exception:
            conn.rollback()
            raise

        return updated

    @staticmethod
    def _parse_pgvector(val) -> np.ndarray:
        """Parse a pgvector string '[0.1,0.2,...]' into numpy array."""
        if val is None:
            return None
        if isinstance(val, (list, np.ndarray)):
            return np.array(val, dtype=np.float32)
        # pgvector returns as string when register_vector not called
        s = str(val).strip("[]")
        return np.array([float(x) for x in s.split(",")], dtype=np.float32)

    def _apply_batch(self, cur, batch: list[EnrichmentResult],
                     sig_engine) -> int:
        """Apply a batch of enrichment results."""
        from kabbalah.hybrid_embedding import KABBALISTIC_DIM
        count = 0

        for r in batch:
            # Compute new kabbalistic signature
            new_sig = sig_engine.compute_signature(r.concept, r.new_hebrew)

            # Get existing ml_embedding and alpha/beta to recompute hybrid
            cur.execute("""
                SELECT ml_embedding FROM hybrid_embeddings
                WHERE concept = %s
            """, (r.concept,))
            row = cur.fetchone()
            if not row or row[0] is None:
                logger.warning("No ml_embedding for %s, skipping", r.concept)
                continue

            ml_embedding = self._parse_pgvector(row[0])
            alpha, beta = 0.3, 0.7
            hybrid = np.concatenate([new_sig * alpha, ml_embedding * beta])

            # Update
            cur.execute("""
                UPDATE hybrid_embeddings
                SET hebrew_word = %s,
                    kabbalistic_signature = %s,
                    hybrid_vector = %s,
                    created_at = NOW()
                WHERE concept = %s
                  AND hebrew_word IS NULL
            """, (
                r.new_hebrew,
                new_sig.tolist(),
                hybrid.tolist(),
                r.concept,
            ))

            # Also update sifrei_yesod_concepts.nom_he if it's NULL
            cur.execute("""
                UPDATE sifrei_yesod_concepts
                SET nom_he = %s, updated_at = NOW()
                WHERE concept_id = %s
                  AND nom_he IS NULL
            """, (r.new_hebrew, r.concept))

            count += 1

        return count
