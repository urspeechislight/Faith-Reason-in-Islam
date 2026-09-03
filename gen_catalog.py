#!/usr/bin/env python3
"""Generate catalog.json, the data source for the site's browse index.

Scans every article .html in the repo root, extracts title / description /
keywords / word count / quotation count, attaches domain + category, and
writes catalog.json. The index page computes every statistic and count it
displays from this file at runtime; nothing on the browse page is hard-coded.

Regenerate whenever an article ships:  python3 gen_catalog.py

Maintenance notes
-----------------
* New articles: add a line to DOMAIN_MAP (else they land in "unfiled", which
  the browse page shows only when non-empty, so nothing ever disappears).
* New battle pages: link them from battles-of-the-prophet.html; the battles
  domain's order and membership come from that hub's link order.
* Display titles and card blurbs live in TITLE / BLURB; fall back is the
  article's <title> and first sentence of its meta description.
"""
import html
import json
import re
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent

SUFFIX = re.compile(r"\s*\|\s*Faith\s*&\s*Reason\s+in\s+Islam\s*$")

# ---------------------------------------------------------------- domains ---
DOMAINS = [
    {"id": "quran", "icon": "book", "en": "The Qur'an & Its Critics", "ar": "القرآن وخصومه",
     "blurb": "Charges against the Book's text and transmission: preservation, contradiction, borrowing, the cranes, and the plot repaid. Each met from lexicons, chains, and the Qur'an's own usage."},
    {"id": "prophet", "icon": "shield", "en": "Defending the Prophet", "ar": "الدفاع عن النبي",
     "blurb": "The age of Aisha, the sword verse, the murdered critics, the verdict at Qurayza: every charge against the Prophet ﷺ examined on the sources' own terms."},
    {"id": "hadith", "icon": "chain", "en": "Hadith, Chains & Fabrications", "ar": "الحديث والإسناد",
     "blurb": "How the isnad was born, how Shia scholars grade what their books carry, and the reports that fail their own chains: from al-Kafi's gate to the pulpit decrees of the caliphate."},
    {"id": "bible", "icon": "codex", "en": "Christianity & the Bible", "ar": "المسيح والإنجيل",
     "blurb": "The sonship charge, Isaiah 9:6, and the texts the early church destroyed, read against the Gospel's own words and the Qur'an's answer in the tongue of the People of the Book."},
    {"id": "history", "icon": "scroll", "en": "The Household & History", "ar": "العترة والتاريخ",
     "blurb": "The succession after the Prophet ﷺ, the seizure of Umm Kulthum, and the exoneration that came down for Maria: the first decades read from the primary record."},
    {"id": "imams", "icon": "star", "en": "The Imams & the Light", "ar": "الأئمة والنور",
     "blurb": "The prophetic light before creation, the Majlis at Marw before every creed, and the promise to those who grieve for al-Husayn ﵇: continuous translation with commentary."},
    {"id": "battles", "icon": "swords", "en": "The Battles of the Prophet", "ar": "المغازي",
     "blurb": "Every march and battle the Prophet ﷺ led in person, in al-Waqidi's order from Waddan to Tabuk: the bloodless marches, the nine fields of fighting, the conquest of Mecca, and the sieges, each on its own page."},
    {"id": "reference", "icon": "index", "en": "Reference", "ar": "المراجع",
     "blurb": "Site-wide indexes gathered for debate preparation."},
    {"id": "unfiled", "icon": "spark", "en": "Unfiled", "ar": "غير مصنف",
     "blurb": "Newest additions awaiting classification."},
]

# slug (no .html) -> domain id. Order within each list is the browse order.
def battle_order():
    """The battles domain's reading order is the hub page's own link order
    (al-Waqidi's order, Waddan to Tabuk). Shipping a new battle page and
    linking it from battles-of-the-prophet.html is enough: regenerating
    picks it up here in place."""
    hub = REPO / "battles-of-the-prophet.html"
    links, seen = [], set()
    for href in re.findall(r'href="([a-z0-9_-]+)\.html"', hub.read_text(encoding="utf-8")):
        if href in seen or href in ("index",):
            continue
        if (REPO / f"{href}.html").exists():
            seen.add(href)
            links.append(href)
    return links


DOMAIN_MAP = {
    "quran": ["quran-preservation", "quran-contradictions", "borrowing",
              "satanic-verses", "allah-deceiver"],
    "prophet": ["aisha-age", "quran-65-4", "wife-beating-4-34", "tahrim-66-1",
                "sword-verse-9-5", "apostasy", "murdered-critics",
                "banu-qurayza", "hudaybiyya"],
    "hadith": ["isnad-origin", "hadith-authentication", "hasan-mitlaq",
               "the-borrowed-he-goat", "mutah-marriage"],
    "bible": ["3-42-vs-39-4", "isiah_9_6", "43_81", "shamoun-10-reasons",
              "text-destruction", "word-and-command"],
    "history": ["ali-forbearance", "umm-kulthum-marriage", "ifk-maria",
               "abu-bakr-strikes-aisha"],
    "imams": ["light-of-prophet", "first-and-last", "majlis-al-rida", "tear-and-pool"],
    "battles": ["battles-of-the-prophet"] + battle_order(),
    "reference": ["facts"],
}

# display-title overrides (fall back to the page <title>, suffix stripped)
TITLE = {
    "3-42-vs-39-4": "Examining Divine Selection and Sonship in Qur'an 3:42 and 39:4",
    "isiah_9_6": "Examining Kingship and Divinity in Isaiah 9:6",
    "43_81": "Analysis of Qur'an 43:81: Does It Allow Divine Sonship?",
    "text-destruction": "The Destruction of Non-Conforming Texts",
    "quran-65-4": "And Those Who Have Not Menstruated: Qur'an 65:4",
    "mutah-marriage": "Who Forbade Mut'ah?",
    "the-borrowed-he-goat": "The Borrowed He-Goat and the Triple Divorce",
    "facts": "The Fact Index",
}

# card blurbs (fall back: first sentence of meta description)
BLURB = {
    "quran-preservation": "Shia sources on whether the Quran is preserved or corrupted: tahrif, the scribal error narrations, and the chain of transmission from the Prophet through Ali to the mushaf in your hands.",
    "quran-contradictions": "The Qur'an's 4:82 invites every scripture to be tested, and read by the rule the critic refuses for his own Bible the alleged contradictions resolve.",
    "borrowing": "The Qur'an records the borrowing charge and answers it with the clarity of its Arabic, and parallel is not plagiarism where no transmission chain was ever supplied.",
    "satanic-verses": "Qur'an 22:52 abolishes the whisper before it stands, and the cranes story is the other school's rejected report.",
    "allah-deceiver": "The lexicons class-index makr, the Qur'an's usage is requital against plotters, and the attack's own canon shares the grammar.",
    "aisha-age": "The age-six and age-nine reports fall on the tradition's own chronology, on chains that all lead to Kufa, on a witness the Qur'an itself questioned, and on the dolls argument's own dates.",
    "quran-65-4": "The whole dispute sits inside one clause, wa-alla'i lam yahidna. Its grammar, the classical lexicon, al-Mizan, and the Imams' law converge on women at the age of menstruation, not pre-pubescent girls.",
    "wife-beating-4-34": "The lexicons widen the verb, the Prophet's farewell sermon bounds it, and the reports the attack quotes condemn the beating it sells.",
    "tahrim-66-1": "Quran 66:1 in the lexicons, the pre-Islamic poets, and the hadith of the Ahl al-Bayt: an oath taken and released, with no sin and no legislation.",
    "sword-verse-9-5": "Qur'an 9:5 sits inside its own exemptions, amnesty, and asylum command, and the sources fix its occasion.",
    "apostasy": "The Qur'an forbids compulsion and contemplates the returning apostate, while the death reports are condition-bound strands read against wartime desertion.",
    "murdered-critics": "The Abu Afak, Asma, and Ka'b reports fall on their own chains, their own dates, and the war the reports themselves describe.",
    "banu-qurayza": "A treason verdict by their own arbiter under their own law, and a prisoner report carried by one family of transmission.",
    "hudaybiyya": "The Muslims kept Hudaybiyya until Quraysh's allies shed protected blood, and the Qur'an names the victory's own content.",
    "isnad-origin": "The chains of hadith converge on six teachers dead by 148 AH, two traditions date the first scrutiny of transmitters to al-Mukhtār's Kūfa of the 680s, and the forgers themselves prove the chains were already there.",
    "hadith-authentication": "The Quran gate, the conflict ladder, the narrator tests, and the taqiyya question, from the Mina sermon to al-Khoei's verdict on al-Kafi.",
    "hasan-mitlaq": "Chain criticism, arithmetic evidence, and the principle of al-rushd fi khilafihim applied to the report that Imam Ali called al-Hasan a mutallaq (frequent divorcer).",
    "the-borrowed-he-goat": "The triple divorce was counted as one until two years into Umar's caliphate. The halala escape it created is the marriage the Prophet ﷺ cursed. The Sunni canon records both.",
    "mutah-marriage": "The Sunni canon dates the prohibition to six occasions, keeps the practice alive through two caliphates, and preserves the ban as Umar's own pulpit declaration in the first person.",
    "3-42-vs-39-4": "A linguistic and theological refutation of the sonship argument using classical Arabic and Shi'i hadith.",
    "isiah_9_6": "Why the notion of God having a son contradicts every layer of Shi'i monotheism.",
    "43_81": "A comprehensive examination of whether Qur'an 43:81 permits the concept of divine sonship.",
    "shamoun-10-reasons": "The Gospel's own words show Jesus as a servant of Allah who prays, prostrates, and does not know the Hour, and the Qur'an answers the \"son of God\" phrase with the tongue of the People of the Book.",
    "text-destruction": "How the early church shaped its own evidence base through destruction and suppression of non-canonical writings.",
    "word-and-command": "The lexicons fix kalima as speech and amr as command, the Imams grade God's speech an originated act, and the Commander of the Faithful priced the eternal Word as a second god.",
    "ali-forbearance": "Forbearance as guardianship. Why Ali withheld his sword after the Prophet's death, from sermons, hadith, and the shared historical record.",
    "umm-kulthum-marriage": "The Shia corpus calls the marriage a seizure, the bride was a child whose kunya she never earned, and the identification of her as Ali's daughter rests on the word of the man who swore he would fabricate witnesses.",
    "abu-bakr-strikes-aisha": "The Ihya, the Qut al-Qulub, and Tarikh Baghdad print the day Abu Bakr struck Aisha until her mouth bled, and Qur'an 66:4 already said the two hearts deviated. The reports, the weak chains, and the verse, weighed honestly.",
    "ifk-maria": "The dictionaries define the band of the verse as a bonded kin circle, Hafsa's codex counted it four, and the chains from the Imams name the woman the verses exonerated as Maria the Copt.",
    "first-and-last": "He was, and nothing else was. How the God who needs nothing made the first thing from nothing, why it was a light, and how the light returns, read through Qur'an 57:3 and the Shia corpus.",
    "light-of-prophet": "The journey of the prophetic light from before creation to the birth of Muhammad ﷺ, narrated by Imam Ali ﵇ and Imam al-Sadiq ﵇ in Bihar al-Anwar Volume 15.",
    "majlis-al-rida": "The interfaith debates at al-Ma'mun's court: the Catholicos answered from his own Gospel, the Exilarch from his own Torah, the fire priest from the fire's own nature, and the Sabian sage from reason alone.",
    "tear-and-pool": "Imam Ja'far al-Sadiq ﵇ comforts a man of Basra who could not safely visit the grave of al-Husayn ﵇ and promises him mercy for his tears and a drink from al-Kawthar. From Kamil al-Ziyarat, report no. 6.",
    "battles-of-the-prophet": "All twenty-seven expeditions the Prophet led in person, indexed in al-Waqidi's order with one page per battle from Waddan to Tabuk.",
    "facts": "Every key claim, actor, date, place, and source across the articles, gathered for debate reference. Each row links into the article carrying the detail.",
}

# the Light of the Prophet serial: main page + parts, in reading order
# (parts auto-discovered: light-of-prophet-<N>.html plus the genealogy appendix)
LIGHT_PARTS = sorted(
    (p.stem for p in REPO.glob("light-of-prophet-[0-9].html")),
    key=lambda s: int(s.rsplit("-", 1)[1]),
) + (["light-of-prophet-genealogy"]
     if (REPO / "light-of-prophet-genealogy.html").exists() else [])

# entries with no file behind them yet
EXTRAS = [
    {"title": "Imam ʿAlī in the Qur'an", "domain": "history", "comingSoon": True,
     "blurb": "Exploring subtle and overt references to the divine appointment of ʿAlī ﵇ in Qur'anic structure."},
]

QUOTE_BLOCK = re.compile(r'<blockquote[^>]*class="[^"]*(?:hadith|quran|bible)-callout|divine-speech', re.I)


def article(slug: str) -> dict:
    src = (REPO / f"{slug}.html").read_text(encoding="utf-8")
    t = re.search(r"<title>(.*?)</title>", src, re.S)
    title = html.unescape(t.group(1)).strip() if t else slug
    title = SUFFIX.sub("", title).strip()

    d = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', src)
    desc = html.unescape(d.group(1)).strip() if d else ""

    k = re.search(r'<meta\s+name="keywords"\s+content="([^"]*)"', src)
    keywords = [x.strip() for x in k.group(1).split(",") if x.strip()] if k else []

    body = re.sub(r"<script.*?</script>|<style.*?</style>|<head>.*?</head>",
                  " ", src, flags=re.S | re.I)
    words = len(re.findall(r"[\w\u0600-\u06FF]+", re.sub(r"<[^>]+>", " ", body)))
    quotes = len(QUOTE_BLOCK.findall(src))

    if "Final Verdict" in src:
        cat = "debate"
    elif slug == "facts":
        cat = "reference"
    elif "The Reading" in src:
        cat = "exegesis"
    else:
        cat = "narration"

    blurb = BLURB.get(slug)
    if not blurb and desc:
        blurb = re.split(r"(?<=[.!?])\s", desc)[0]
    return {
        "slug": slug, "title": TITLE.get(slug, title), "blurb": blurb or "",
        "desc": desc, "keywords": keywords, "category": cat,
        "words": words, "quotes": quotes,
    }


def series_part(slug: str) -> dict:
    a = article(slug)
    a["title"] = re.sub(r"\s*-\s*The Light of the Prophet$", "", a["title"])
    m = re.match(r"Part (\d+):\s*(.*)$", a["title"])
    if m:
        a["title"] = m.group(2)
        a["part"] = int(m.group(1))
    else:
        a["part"] = 99  # the genealogy appendix rides last
    return a


def main() -> None:
    catalogued = set(LIGHT_PARTS)  # serial parts ride inside their series entry
    articles = []
    for dom in DOMAINS:
        for slug in DOMAIN_MAP.get(dom["id"], []):
            a = article(slug)
            a["domain"] = dom["id"]
            if slug == "light-of-prophet":
                parts = [series_part(p) for p in LIGHT_PARTS]
                a["series"] = {"label": "Bihar al-Anwar, Volume 15", "parts": parts}
            articles.append(a)
            catalogued.add(slug)

    for extra in EXTRAS:
        articles.append({
            "slug": None, "title": extra["title"], "blurb": extra["blurb"],
            "desc": "", "keywords": [], "category": "exegesis",
            "words": 0, "quotes": 0, "domain": extra["domain"],
            "comingSoon": True,
        })

    # durability net: any content page not mapped lands in "unfiled" so it is
    # never silently lost from the browse page
    for f in sorted(REPO.glob("*.html")):
        slug = f.stem
        if slug in catalogued or slug in ("index",):
            continue
        if slug.startswith("council-"):
            continue
        a = article(slug)
        a["domain"] = "unfiled"
        articles.append(a)

    catalog = {
        "generated": date.today().isoformat(),
        "domains": DOMAINS,
        "articles": articles,
    }
    embed_into_index(catalog)

    filed = [a for a in articles if a["domain"] != "unfiled"]
    n_parts = sum(len(a.get("series", {}).get("parts", [])) for a in articles)
    print(f"catalogue embedded in index.html: {len(filed)} entries "
          f"(+{len(articles) - len(filed)} unfiled), {n_parts} series parts, "
          f"{sum(a['quotes'] for a in articles)} quotations, "
          f"{sum(a['words'] for a in articles):,} words")


def embed_into_index(catalog: dict) -> None:
    """Write the catalogue into index.html between the CATALOG markers.

    The page reads this embedded block (no fetch), so it renders identically
    on GitHub Pages and when index.html is opened straight from disk.
    """
    page = REPO / "index.html"
    src = page.read_text(encoding="utf-8")
    blob = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"))
    blob = blob.replace("</", "<\\/")  # keep any "</script>" from closing early
    block = ("<!-- CATALOG:BEGIN -->\n"
             f'<script id="catalog-data" type="application/json">{blob}</script>\n'
             "<!-- CATALOG:END -->")
    new, n = re.subn(r"<!-- CATALOG:BEGIN -->.*?<!-- CATALOG:END -->",
                     lambda _: block, src, flags=re.S)
    if n != 1:
        raise SystemExit("index.html: CATALOG markers not found (or found twice)")
    page.write_text(new, encoding="utf-8")


if __name__ == "__main__":
    main()
