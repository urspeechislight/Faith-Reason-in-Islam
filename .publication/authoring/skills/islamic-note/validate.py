#!/usr/bin/env python3
import re, sys
from pathlib import Path

src = open(sys.argv[1]).read()
errs = []
import importlib.util
shared = Path.home() / ".agents/prose/review.py"
spec = importlib.util.spec_from_file_location("prose_review", shared)
review = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review)
try:
    authored = " ".join(b["text"] for b in review.extract(src, "md")["blocks"])
except ValueError as exc:
    print('FAIL:',exc);sys.exit(1)

fm, body = '', src
m = re.match(r'^---\n(.*?)\n---\n', src, flags=re.S)
if src.startswith('---'):
    if m: fm, body = m.group(1), src[m.end():]
    else: errs.append('frontmatter opened but not closed')

# category system (see ~/.agents/prose/article-structure.md)
mcat = re.search(r'^category:\s*(\w+)\s*$', fm, flags=re.M)
cat = mcat.group(1) if mcat else None
if cat not in ('debate', 'exegesis', 'narration', 'commentary'):
    errs.append(f'missing/invalid category frontmatter: {cat!r} (need debate|exegesis|narration|commentary)')
else:
    has_verdict = re.search(r'^##\s+Final Verdict\s*$', body, flags=re.M)
    has_reading = re.search(r'^##\s+The Reading\s*$', body, flags=re.M)
    if cat == 'debate' and not has_verdict:
        errs.append('debate note missing "## Final Verdict" section')
    if cat != 'debate' and has_verdict:
        errs.append(f'{cat} note carries "Final Verdict"; only debate notes do (exegesis closes with "The Reading", narration with its own heading)')
    if cat == 'exegesis' and not has_reading:
        errs.append('exegesis note missing "## The Reading" closing section')

ARABIC = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFC]')
HONORIFICS = set('ﷺ﵇﵍﵈﵊﵁﵀ﷻ﷿')
def has_script(text):
    return any(m.group() not in HONORIFICS for m in ARABIC.finditer(text))

# Arabic script lives only inside callout bodies (honorific ligatures in
# English prose are expected and exempt)
for i, line in enumerate(body.splitlines(), 1):
    if has_script(line) and not line.lstrip().startswith('>'):
        errs.append(f'Arabic outside a callout at line {i}: "{line.strip()[:50]}"')

# parse callout blocks: (type, title, body_lines, start_line)
lines = body.splitlines()
blocks, cur = [], None
for i, line in enumerate(lines, 1):
    m2 = re.match(r'^> ?\[\!(\w+)\](-?)\s*(.*)$', line)
    if m2 and not line.startswith('>>'):
        if cur: blocks.append(cur)
        cur = [m2.group(1).lower(), m2.group(3).strip(), [], i]
    elif cur is not None:
        if line.startswith('>'):
            cur[2].append(line.lstrip('>').strip())
        else:
            blocks.append(cur); cur = None
if cur: blocks.append(cur)

QUOTE_TYPES = ('info', 'note', 'tip', 'warning', 'quote')
TRANSLIT = re.compile(r'^\*[^*]+\*\.?$')
for t, title, blines, ln in blocks:
    if t not in QUOTE_TYPES:
        continue  # structural callouts (abstract/summary) are not quote blocks
    if not title:
        errs.append(f'quote callout at line {ln} has no citation title')
    has_ar = has_script(' '.join(blines))
    translit = [b for b in blines if TRANSLIT.match(b)]
    english = [b for b in blines if b and not ARABIC.search(b) and not TRANSLIT.match(b)]
    if not any(b.strip() for b in blines):
        errs.append(f'quote callout at line {ln} has no source text')
    elif has_ar and not english:
        errs.append(f'quote callout at line {ln} has Arabic but no translation line')
    if translit and t != 'quote':
        errs.append(f'transliteration line in [{t}] callout at line {ln}; transliteration is reserved for [!quote] (scripture)')

errs.extend(review.quote_layout.scripture.errors(src,'md'))

# narration: no transliteration inside Commentary callouts; unnamed speakers;
# archaic idioms; empty framing
if cat == 'narration':
    ci = body.find('## Commentary')
    ci_line = body[:ci].count('\n') + 1 if ci >= 0 else None
    narr = body[:ci] if ci >= 0 else body
    unnamed = re.findall(r'(?:^|\s)(?:He|he) said:', narr)
    if unnamed:
        errs.append(f'{len(unnamed)} unnamed "He said:" speaker tag(s); name every speaker')
    for pat in (r'"O [A-Z]', r'\bglad tidings\b', r'\bI adjure you\b', r'\bgive the lie\b',
                r'\bby the right of\b', r'\bwhat occurs to you\b', r'\bspake\b|\bthee\b|\bthou\b'):
        if re.search(pat, narr):
            errs.append(f'archaic idiom in narration: {pat}')
    for pat in (r'\bThe (?:reply|method|pattern|terms|standard|test|oath) (?:that|used|was|left|fixed)\b',
                r'\bTwo figures stood on offer\b', r'\bcarried its own refutation\b',
                r'\bleft no middle ground\b', r'\bRead as\b', r'\bclosed in on\b',
                r'\bno interpretation laid over\b', r'\bon his account\b',
                r'\bthe whole weight of the claim\b', r'\bcompleted the demonstration\b'):
        if re.search(pat, narr):
            errs.append(f'empty framing sentence in narration: {pat}')
    if ci_line is not None:
        for t, title, blines, ln in blocks:
            if ln > ci_line and any(TRANSLIT.match(b) for b in blines):
                errs.append(f'transliteration line inside a Commentary callout at line {ln}; commentary blocks are Arabic then translation only')

# corpus bucket labels are not book titles
for slug in ('sunni-tafsir', 'shia-tafsir', 'prophet-imams-biography', 'genealogy-biography',
             'sunni-hadith-general', 'shia-hadith-general', 'quran-sciences', 'history-geography'):
    if slug in src:
        errs.append(f'corpus bucket label used as citation: {slug}')

# scripture references name the book
BOOKS = r"(?:Qur'an|Quran|Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Isaiah|Jeremiah|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Psalms|Proverbs|Job|Song of Solomon|Ruth|Lamentations|Ecclesiastes|Esther|Ezra|Nehemiah|Chronicles|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation)"
_txt = ARABIC.sub(' ', body)
_txt = re.sub(r'\[\[[^\]]*\]\]', ' ', _txt)  # wikilinks
for m3 in re.finditer(r'\(([^)]*\d+:\d+[^)]*)\)', _txt):
    if not re.search(BOOKS, m3.group(1)):
        errs.append(f'scripture reference without book name: ({m3.group(1)})')

# headings: unique, spoken English
heads = re.findall(r'^#{1,6}\s+(.+?)\s*$', body, flags=re.M)
dups = sorted({h for h in heads if heads.count(h) > 1})
if dups:
    errs.append(f'duplicate heading(s) (Obsidian anchors collide): {dups}')
for h in heads:
    if ', and the ' in h:
        errs.append(f'comma-spliced heading; rewrite as spoken English: "{h[:60]}"')
if re.search(r'^#\s+The (?:Hadith|Report|Story) of .+ on ', body, flags=re.M):
    errs.append('citation-shaped title; use a plain sentence or Why-question like the sibling notes')
msum = re.search(r'^summary:\s*(.*)$', fm, flags=re.M)
if msum and re.search(r'\(d\.\d+ AH\), [^,]+, no\. \d+:', msum.group(1)):
    errs.append('provenance-first summary; write a sentence with a verb and file provenance at the end')

# prose style bans (see ~/.agents/prose/contract.md)
if '—' in authored or '–' in authored:
    errs.append('em/en dash found (banned); rewrite with a period, comma, or parentheses')
_p = re.sub(r'^>.*$', ' ', body, flags=re.M)          # callouts carry quote internals
_p = re.sub(r'\[\[[^\]]*\]\]', ' ', _p)               # wikilinks
_p = re.sub(r'https?://\S+', ' ', _p)
_p = re.sub(r'^\s*[-*]?\s*\*\*[^*]+:\*\*.*$', ' ', _p, flags=re.M)  # fact-card label lines
_p = re.sub(r'\d+:\d+', ' ', _p)                      # scripture references
_p = re.sub(r'(?i)(?:Premise \d+|Conclusion|Open question|Speaker|Chain)\s*:', ' ', _p)
_p = ARABIC.sub(' ', _p)
if ':' in _p:
    i = _p.find(':')
    ctx = re.sub(r'\s+', ' ', _p[max(0, i-60):i+40]).strip()
    errs.append(f'colon in prose (banned) near "...{ctx}..."; rewrite with a period, comma, or parentheses')
meta = sorted(set(re.findall(r'(?i)\b(?:this (?:analysis|article|note|page)|the following sections?|in this (?:analysis|article|section)|we will (?:show|deconstruct|demonstrate|examine|argue|prove))\b', authored)))
if meta: errs.append(f'meta statement(s) banned by style rules: {meta}')
narrmeta = sorted(set(re.findall(r'(?i)\bthe (?:narration|report)(?: itself)? (?:records?|stages?|answers?|closes?|gathers?|joins?|moves?|turns?|counts?|names?|accepts?|reads?|teaches?|is about)\b', authored)))
if narrmeta: errs.append(f'source-text-as-subject narration banned; make the content the subject: {narrmeta}')
pivot = sorted(set(re.findall(r"(?i)\b(?:it is not about|it['’]s not about|isn['’]t about|not merely|not simply)\b", authored)))
if pivot: errs.append(f'AI-style contrast pivot(s) banned by style rules: {pivot}')
litotes = sorted(set(re.findall(r'(?i)\b(?:not un\w+|no small|no minor|no ordinary|no little|no mere|hardly|scarcely|nothing if not|not for nothing|no stranger to)\b', authored)))
if litotes: errs.append(f'litotes found (banned); state the positive claim directly: {litotes}')
irony = sorted(set(re.findall(r'(?i)\b(?:of course|naturally|predictably|needless to say|one might almost say|how convenient|amusingly|ironically|it goes without saying)\b', authored)))
if irony: errs.append(f'irony/sarcasm marker(s) banned; rewrite as a plain statement: {irony}')

# machine phrasing / note-internal narration
for pat in (r'\(\d+ cards\)', r'\bthe card states\b', r'\bthe note preserves\b',
            r'\bNo card\b', r'\bcards below\b',
            r'attached to (?:the|each) (?:promise|movement|section)'):
    if re.search(pat, src, re.I): errs.append(f'machine phrasing banned: {pat}')

# honorifics: legacy abbreviations banned on new notes
abbr = sorted(set(re.findall(r'\w \((?:s|a|as|saws|sws|pbuh)\)', src, re.I)))
if abbr: errs.append(f'legacy honorific abbreviation(s) {abbr} found; use the Unicode ligatures')

# The Facts block (debate/exegesis)
QUALIFIERS = ('stated', 'reported', 'attributed', 'likely', 'disputed')
if cat in ('debate', 'exegesis'):
    mf = re.search(r'^##\s+The Facts\s*$\n(.*?)(?=^##\s)', body, flags=re.S | re.M)
    if not mf:
        errs.append(f'{cat} note missing The Facts block ("## The Facts") after the intro')
    else:
        ftxt = mf.group(1)
        rows = re.findall(r'^\|(.+)\|\s*$', ftxt, flags=re.M)
        bodyrows = [r for r in rows if not re.match(r'^[\s:|-]+$', r)]
        # first table row is a header; separator rows dropped above
        if len(bodyrows) < 4:
            errs.append(f'The Facts block has {len(bodyrows)} table rows; need a header row plus at least 3 fact rows')
        flat = ['|'.join(c.strip() for c in r.strip('|').split('|')) for r in bodyrows]
        if bodyrows and 'Qualifier' not in bodyrows[0] and 'Status' not in bodyrows[0]:
            errs.append('Facts table missing the Qualifier column (mandatory on every table)')
        for r in flat[1:]:
            if not any(q in r for q in QUALIFIERS):
                errs.append(f'Facts row without a Qualifier cell from the taxonomy {QUALIFIERS}: "{r[:40]}..."')
        anchors = re.findall(r'\[\[#([^|]+)(?:\|[^\]]*)?\]\]', ftxt)
        if len(flat) > 1 and not anchors:
            errs.append('Facts rows carry no detail anchors ([[#heading|↗]]); no anchor, no row')
        headset = {h.strip() for h in heads}
        for a in anchors:
            if a.strip().rstrip('\\') not in headset:
                errs.append(f'Facts anchor [[#{a}]] resolves to no heading in the note')

# fixed four-beat rhythm ban (content-named subheadings instead)
sections = re.split(r'^##\s+', body, flags=re.M)[1:]
for sec in sections:
    h3s = [h.strip() for h in re.findall(r'^###\s+(.+?)\s*$', sec, flags=re.M)]
    for beat in (('Introduction', 'Example', 'Implication', 'Conclusion'),
                 ('Introduction', 'Example', 'Application', 'Conclusion')):
        if len(h3s) >= 4 and tuple(h3s[:4]) == beat:
            errs.append(f'fixed four-beat rhythm {beat} banned; name subheadings after their content')

# grade 9 gate on the note's own prose (FK; quote internals and name chains excluded)
def _syl(w):
    w = re.sub(r'[^a-z]', '', w.lower())
    if not w: return 0
    n = len(re.findall(r'[aeiouy]+', w))
    return max(1, n - (1 if w.endswith('e') and n > 1 else 0))
def _fk(text):
    sents = [s for s in re.split(r'[.!?]+', text) if s.strip()]
    sents = [s for s in sents if len(re.findall(r', from | and from ', s)) < 2]
    words = re.findall(r"[A-Za-z'’-]+", ' '.join(sents))
    if len(sents) < 3 or len(words) < 60: return None
    return 0.39 * (len(words)/len(sents)) + 11.8 * (sum(_syl(w) for w in words)/len(words)) - 15.59
prose = re.sub(r'^>.*$', ' ', body, flags=re.M)
prose = re.sub(r'^---$', ' ', prose, flags=re.M)
for lig in 'ﷺ﵇﵍﵈﵊﵁﵀ﷻ﷿':
    prose = prose.replace(lig, ' ')
g = _fk(prose)
if g is not None and g > 10.5:
    errs.append(f'note prose measures Flesch-Kincaid grade {g:.1f} (ceiling 10.5); shorten sentences and prefer everyday words')

if re.findall(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50]', src):
    errs.append('emoji found (banned)')

warnings = [e for e in errs if e.startswith(('AI-style contrast', 'litotes', 'irony/', 'source-text-as-subject')) or 'Flesch' in e]
errs = [e for e in errs if e not in warnings]
for w in warnings: print('REVIEW:', w)
for e in errs: print('FAIL:', e)
print('OK' if not errs else f'{len(errs)} problem(s)')
sys.exit(1 if errs else 0)
