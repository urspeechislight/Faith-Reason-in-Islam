#!/usr/bin/env python3
"""Structural validator for Faith & Reason in Islam article pages.

Usage:
    python3 validate.py <file.html>     validate one page (exit 1 on any FAIL)
    python3 validate.py --register haddad <file.html>
                                        validate in the Haddad prose register:
                                        waives ONLY the grade-9 prose gates
                                        (em/en dash ban, colon ban, 35-word
                                        sentence cap, FK ceiling, FRE floor).
                                        Structure, callouts, honorifics,
                                        citations, and all other gates still
                                        run. Only for pages the user has
                                        explicitly commissioned in that
                                        register.
    python3 validate.py --selftest      prove every gate fires (exit 1 on any fixture failure)
    python3 validate.py --format json <file.html>
                                        emit machine-readable validation output

This file is the single source of truth for mechanically testable page
requirements in the Faith & Reason workflow. Research quality, source
fidelity, translation fidelity, and argumentative completeness still need
the shared review procedure in ~/.agents/prose/editorial.md. Never paste this script into a shell
heredoc. Run this versioned file so one validator governs every page.

Maintenance contract: when a check changes, update the corresponding skill
rule, add or update a selftest fixture that proves both the failure and its
documented exceptions, and keep the publishing skill synchronized when it
uses the same gate.
"""
import argparse
import html
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from html.parser import HTMLParser


VOID_TAGS = {
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
    'meta', 'param', 'source', 'track', 'wbr',
}


def _plain_text(fragment):
    """Return normalized visible text from a small HTML fragment."""
    fragment = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', fragment, flags=re.S | re.I)
    fragment = re.sub(r'<!--.*?-->', ' ', fragment, flags=re.S)
    fragment = re.sub(r'<[^>]+>', ' ', fragment)
    return re.sub(r'\s+', ' ', html.unescape(fragment)).strip()


class HTMLIndex(HTMLParser):
    """Small standard-library DOM index for element spans and attributes.

    The validator still reports malformed nesting separately. This index exists
    only so structural gates do not use non-nesting-aware regexes for sections.
    """

    def __init__(self, src):
        super().__init__(convert_charrefs=False)
        self.src = src
        self.stack = []
        self.nodes = []
        self._line_starts = [0]
        for m in re.finditer(r'\n', src):
            self._line_starts.append(m.end())

    def _abspos(self):
        line, col = self.getpos()
        return self._line_starts[line - 1] + col

    @staticmethod
    def _attrs(attrs):
        return {k: (v if v is not None else '') for k, v in attrs}

    def handle_starttag(self, tag, attrs):
        start = self._abspos()
        raw = self.get_starttag_text() or ''
        node = {
            'tag': tag,
            'attrs': self._attrs(attrs),
            'start': start,
            'content_start': start + len(raw),
            'content_end': start + len(raw),
            'end': start + len(raw),
        }
        if tag in VOID_TAGS:
            self.nodes.append(node)
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        start = self._abspos()
        raw = self.get_starttag_text() or ''
        self.nodes.append({
            'tag': tag,
            'attrs': self._attrs(attrs),
            'start': start,
            'content_start': start + len(raw),
            'content_end': start + len(raw),
            'end': start + len(raw),
        })

    def handle_endtag(self, tag):
        if not self.stack:
            return
        # The balance gate reports mismatches. Recover enough here to index the
        # nearest matching open element instead of making later checks cascade.
        match = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]['tag'] == tag:
                match = i
                break
        if match is None:
            return
        node = self.stack.pop(match)
        end_start = self._abspos()
        end = self.src.find('>', end_start)
        node['content_end'] = end_start
        node['end'] = len(self.src) if end < 0 else end + 1
        self.nodes.append(node)

    def by_id(self, value):
        matches = [n for n in self.nodes if n['attrs'].get('id') == value]
        if not matches:
            return None
        return min(matches, key=lambda n: n['end'] - n['start'])

    def first(self, tag):
        matches = [n for n in self.nodes if n['tag'] == tag]
        return min(matches, key=lambda n: n['start']) if matches else None

    def enclosing(self, pos, tags=('article', 'section')):
        matches = [
            n for n in self.nodes
            if n['tag'] in tags and n['start'] <= pos < n['end']
        ]
        return min(matches, key=lambda n: n['end'] - n['start']) if matches else None

    def inner(self, node):
        return self.src[node['content_start']:node['content_end']]

    def outer(self, node):
        return self.src[node['start']:node['end']]

    def headings(self):
        out = []
        for n in self.nodes:
            if re.fullmatch(r'h[1-6]', n['tag']):
                out.append((_plain_text(self.inner(n)), n))
        return sorted(out, key=lambda x: x[1]['start'])


def _check(src, register='standard'):
    """Run every gate on one page's HTML; return the list of failures.

    register='haddad' waives only the grade-9 prose gates (dash ban, colon
    ban, sentence cap, FK, FRE) for pages commissioned in the Haddad
    dossier register; every structural, citation, honorific, and anatomy
    gate still runs."""
    errs = []
    haddad = (register == 'haddad')

    # landing pages (index.html, facts.html): exempt from the prose gates
    # that fire on mirrored titles and rows; everything else still runs.
    is_landing = ('data-category="facts-index"' in src) or ('id="facts-index"' in src) or (src.count('card bg-white border border-gray-200') > 3 and 'data-category' not in src)

    VOID = VOID_TAGS
    class P(HTMLParser):
        def __init__(self):
            super().__init__(); self.stack=[]
        def handle_starttag(self,t,a):
            if t not in VOID: self.stack.append((t,self.getpos()[0]))
        def handle_startendtag(self,t,a):
            pass  # self-closing (<meta ... /> etc.): balanced by definition
        def handle_endtag(self,t):
            if t in VOID: return
            if self.stack and self.stack[-1][0]==t: self.stack.pop()
            else: errs.append(f'MISMATCH </{t}> at line {self.getpos()[0]}')

    p = P(); p.feed(src)
    for t,line in p.stack: errs.append(f'UNCLOSED <{t}> opened at line {line}')

    index = HTMLIndex(src)
    index.feed(src)

    ids = re.findall(r'id="([^"]+)"', src)
    counts = Counter(ids)
    dups = sorted(i for i, n in counts.items() if n > 1)
    if dups: errs.append(f'DUPLICATE ids: {dups}')
    idset = set(ids)
    # attribute scans run on script-stripped markup (JS string templates trip them)
    noscript = re.sub(r'<script.*?</script>', ' ', src, flags=re.S)
    for attr in ('data-target', 'aria-controls'):
        for v in re.findall(attr + r'="([^"]+)"', noscript):
            target = v[1:] if v.startswith('#') else v
            if target and target not in idset:
                errs.append(f'{attr}="{v}" has no matching id')
    for v in re.findall(r'href="#([^"]*)"', noscript):
        if v and v not in idset:
            errs.append(f'internal anchor href="#{v}" has no matching id')
    # headers missing aria-controls entirely (content must be reachable)
    headers = re.findall(r'<div class="accordion-header[^>]*>', src)
    missing = [h for h in headers if 'aria-controls' not in h]
    if missing: errs.append(f'{len(missing)} accordion-header(s) missing aria-controls')

    if '{{' in src: errs.append('unsubstituted {{PLACEHOLDER}} remains')
    if re.search(r'<[a-z0-9]+[^>]*>\s*\.\.\.\s*</[a-z0-9]+>', src):
        errs.append('template filler element containing only "..." remains')

    # The shared extractor protects source quotations from prose rewrites.
    import importlib.util
    bundled = Path(__file__).resolve().with_name('review.py')
    shared = bundled if bundled.is_file() else Path.home() / '.agents/prose/review.py'
    spec = importlib.util.spec_from_file_location('prose_review', shared)
    review = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(review)
    try:
        authored = ' '.join(b['text'] for b in review.extract(src, 'html')['blocks'])
    except ValueError:
        authored = _plain_text(src)  # malformed markup already fails structure
    # prose style bans (see ~/.agents/prose/contract.md). The dash and colon
    # bans are grade-9 prose gates, waived in the Haddad register (whose
    # codex uses dashes for attributions and colons before quotations).
    if not haddad and ('—' in authored or '–' in authored):
        errs.append('em/en dash found (banned); rewrite with a period, comma, or parentheses')
    # no colons in prose: strip script/style, URLs, scripture refs, template
    # labels, verbatim Arabic, cite lines, label spans, and section headings
    # (h2-h6 may use a colon as a label separator, "1. The Problem: ...";
    # body prose keeps the ban); any remaining colon in text content is a
    # failure. Landing pages are exempt: their mirrored article titles may
    # legally carry colons.
    _txt = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', src, flags=re.S)
    _txt = re.sub(r'<blockquote\b[^>]*>.*?</blockquote>', ' ', _txt, flags=re.S)
    _txt = re.sub(r'https?://[^\s"<>]+', ' ', _txt)
    _txt = re.sub(r'<p class="rtl font-amiri[^"]*"[^>]*>.*?</p>', ' ', _txt, flags=re.S)  # verbatim Arabic keeps its punctuation
    _txt = re.sub(r'<h[2-6][^>]*>.*?</h[2-6]>', ' ', _txt, flags=re.S)  # section headings may carry label colons
    _txt = re.sub(r'<cite[^>]*>.*?</cite>', ' ', _txt, flags=re.S)  # bibliographic
    _txt = re.sub(r'<strong[^>]*>\s*(?:(?:Premise \d+|Conclusion|Open question|Source|Speaker|Chain|Dating|Claim|Verse|Locus|Method|Reports|Place|Actor|Date)\s*:)\s*</strong>', ' ', _txt, flags=re.I)
    _txt = re.sub(r'</?strong[^>]*>', '', _txt)  # preserve bold prose; remove markup only
    _txt = re.sub(r'<[^>]+>', ' ', _txt)
    _txt = re.sub(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFC]', ' ', _txt)  # stray Arabic/honorific glyphs
    _txt = re.sub(r'\d+:\d+', ' ', _txt)  # scripture references keep colons
    _txt = re.sub(r'(?i)(?:Premise \d+|Conclusion|Open question|Speaker|Chain)\s*:', ' ', _txt)
    if not haddad and ':' in _txt and not is_landing:
        i = _txt.find(':')
        ctx = re.sub(r'\s+', ' ', _txt[max(0,i-60):i+40]).strip()
        errs.append(f'colon in prose (banned) near "...{ctx}..."; rewrite with a period, comma, or parentheses')
    meta = sorted(set(re.findall(r'(?i)\b(?:this (?:analysis|article|page|note|section)|the following sections?|the sections? that follow|in this (?:analysis|article|section)|we will (?:show|deconstruct|demonstrate|examine|argue|prove)|carr(?:y|ies) this premise|the previous section|gathered so far)\b', authored)))
    if meta: errs.append(f'meta statement(s) banned by style rules: {meta}')
    # source text narrating its own moves (see "No meta statements")
    narrmeta = sorted(set(re.findall(r'(?i)\bthe (?:narration|report)(?: itself)? (?:records?|stages?|answers?|closes?|gathers?|joins?|moves?|turns?|counts?|names?|accepts?|reads?|teaches?|is about)\b', authored)))
    if narrmeta: errs.append(f'source-text-as-subject narration banned; make the content the subject: {narrmeta}')
    # preamble openers: announcement-shaped first sentences (home: "Prose style",
    # user-directed 2026-09-07). A paragraph opener must carry a claim, evidence,
    # or qualification, never the paragraph's shape.
    pream = sorted(set(re.findall(r'(?i)\b(?:the page speaks|the page has shown|the page examines|moves in layers|each layer feeds the next|the dispute turns on|leans on is real|what the \w+ does to the)\b', authored)))
    if pream: errs.append(f'preamble opener(s) banned; delete the announcement and start with the content: {pream}')
    # apparatus voice: the article never narrates its own editing or citation
    # handling (home: "Prose style" / apparatus ban, user-directed 2026-09-07).
    apparatus = sorted(set(re.findall(r'(?i)\b(?:cited here with|cited with that status|cited for what it shows|kept as printed|chain note is kept|quotes them in full|the first section quotes)\b', authored)))
    if apparatus: errs.append(f'apparatus voice banned; state the content, not the citation handling: {apparatus}')
    # "below" navigation pointers toward the page's own furniture
    belownav = sorted(set(re.findall(r'(?i)\b(?:dictionaries|verses|witness(?:es)?|exhibits?|cards?|table|sections?) below\b|\b(?:show|decide|carry|appear) below\b', authored)))
    if belownav: errs.append(f'"below" navigation banned; name the evidence where it stands: {belownav}')
    # double titles: an article with exactly one analysis subheading and at most
    # one quoted callout carries a redundant h5 (home: "Titles, subtitles, and
    # headings", user-directed 2026-09-07).
    # transliterations belong to scripture (quran-callout) blocks only
    # (home: "Step 2e: assemble", user-directed 2026-09-07)
    for hm in re.finditer(r'<blockquote class="hadith-callout">.*?</blockquote>', src, re.S):
        if re.search(r'class="italic transliteration"', hm.group(0)):
            errs.append('hadith/tafsir/lexicon/poetry callout carries a transliteration; transliterations are scripture-only')
            break
        # AI-register tells (humanizer canon, user-directed 2026-09-07)
    aireg = sorted(set(re.findall(r"(?i)\b(?:serves? as|stands? as a|boasts? a|at its core|the real question is|the deeper issue|heart of the matter|let's (?:dive|explore|break)|here's what you need to know|and that's (?:okay|fine))\b", authored)))
    if aireg: errs.append(f'AI-register tell(s) banned, state the literal thing: {aireg}')
    ing = sorted(set(re.findall(r",\s*(?:highlighting|underscoring|emphasizing|showcasing|reflecting|symbolizing|fostering|ensuring)\s", authored)))
    glue = sorted(set(re.findall(r"(?i)\b(?:the (?:chain|gloss|grammar|answer|evidence) (?:carries|holds|bears|sits|stands)\b|carries its caveat|(?:entry|book|title|corpus|narration) carries|is graded|is attested|stands confirmed)\b", authored)))
    if glue: errs.append(f'abstract-subject glue verb(s) banned, make the actor the subject: {glue}')
    if ing: errs.append(f'tack-on -ing phrase(s) banned: {ing}')
    # double headings: article h3s under a numbered section h2 are banned
    # (home: "Titles, subtitles, and headings", user-directed 2026-09-07)
    if re.search(r'<main[^>]*data-category="(?:debate|exegesis)"', src):
        for sm in re.finditer(r'<section id="tab\d+"[^>]*>(.*?)</section>', src, re.S):
            h35 = re.search(r'<h[35][^>]*>([^<]*)</h[35]', sm.group(1))
            if h35:
                errs.append(f'secondary heading under a section heading is a double heading ("{h35.group(1)[:40]}"); the section h2 plus flowing prose carries the structure')
    for am in re.finditer(r'<article[^>]*>.*?</article>', src, re.S):
        art = am.group(0)
        h5s = re.findall(r'<h5 class="analysis-heading">', art)
        bqs = re.findall(r'<blockquote', art)
        if len(h5s) == 1 and len(bqs) <= 1 and '<h3' in art:
            h5 = re.search(r'<h5 class="analysis-heading">([^<]*)</h5>', art).group(1)[:40]
            errs.append(f'single-exhibit subsection carries a redundant subheading ("{h5}"); an h5 must partition distinct exhibits or add a claim the h3 lacks')
    # fact-card placement: a subsection carrying both a fact card and a quoted
    # callout must place the card immediately before its first callout, and a
    # subsection with a callout must carry a card at all (home: "Fact cards",
    # user-directed 2026-09-07).
    CARD = re.compile(r'<div class="premise-card space-y-1 mb-4">\s*<p class="text-sm">', re.S)
    is_narr = re.search(r'<main[^>]*data-category="narration"', src)
    scopes = [] if is_narr else (list(re.finditer(r'<article[^>]*>.*?</article>', src, re.S)) + list(re.finditer(r'<section id="comparison"[^>]*>.*?</section>', src, re.S)))
    for sm in scopes:
        sc = sm.group(0)
        bq = sc.find('<blockquote')
        if bq < 0:
            continue
        ends = [cm.end() for cm in re.finditer(r'<div class="premise-card space-y-1 mb-4">\s*<p class="text-sm">.*?</div>', sc, re.S)]
        for cm2 in re.finditer(r'<div class="premise-card space-y-1 mb-4">\s*<p class="text-sm">.*?</div>', sc, re.S):
            ctxt = cm2.group(0)
            mref = re.search(r'<strong>Verse:\s*</strong>[^<]*\bQur\'an \d+:\d+', ctxt) or re.search(r'<strong>Verse:\s*</strong>[^<]*\b(?:Genesis|Exodus|Numbers|Psalm|Psalms|Isaiah|Ephesians|Luke|John|Matthew) \d+:\d+', ctxt)
            if mref:
                after = sc[cm2.end():]
                bqm2 = re.search(r'<blockquote class="quran-callout"', after)
                if not (bqm2 and after[:bqm2.start()].strip() == ''):
                    errs.append('a card naming a scripture reference must sit directly above that verse quoted in a quran-callout')
                    break
        for bqm in re.finditer(r'<blockquote', sc):
            b = bqm.start()
            if not any(sc[e:b].strip() == '' for e in ends):
                errs.append('every quoted callout carries its own fact card immediately above it; a callout without an adjacent Source/Claim card fails (first offender at offset %d in its subsection)' % b)
                break
    pivot = sorted(set(re.findall(r"(?i)\b(?:it is not about|it['’]s not about|isn['’]t about|not merely|not simply)\b", authored)))
    if pivot: errs.append(f'AI-style contrast pivot(s) banned by style rules: {pivot}')
    litotes = sorted(set(re.findall(r'(?i)\b(?:not un\w+|no small|no minor|no ordinary|no little|no mere|hardly|scarcely|nothing if not|not for nothing|no stranger to|far from \w+ing|by no means|in no way|not exactly|is not the same thing as|are not the same thing as)\b', authored)))
    if litotes: errs.append(f'litotes found (banned); state the positive claim directly: {litotes}')
    irony = sorted(set(re.findall(r'(?i)\b(?:of course|naturally|predictably|needless to say|one might almost say|how convenient|amusingly|ironically|it goes without saying)\b', authored)))
    if irony: errs.append(f'irony/sarcasm marker(s) banned; rewrite as a plain statement: {irony}')

    # finished-sentence + contrast gate on the site's own prose.
    # Translations are stripped: quoted source statements keep their phrasing
    # (e.g. the Imam's "not one as opposed to two"), so the general "not X
    # but Y" catch runs only on prose the site itself wrote. Tables, glossary
    # <details>, and cite lines are data, not prose.
    prose2 = src[src.find('<main'):] if '<main' in src else src
    prose2 = re.sub(r'<script.*?</script>', ' ', prose2, flags=re.S)
    prose2 = re.sub(r'<table.*?</table>', ' ', prose2, flags=re.S)
    prose2 = re.sub(r'<details.*?</details>', ' ', prose2, flags=re.S)
    prose2 = re.sub(r'<p class="rtl[^"]*"[^>]*>.*?</p>', ' ', prose2, flags=re.S)
    prose2 = re.sub(r'<p class="[^"]*transliteration[^"]*"[^>]*>.*?</p>', ' ', prose2, flags=re.S)
    prose2 = re.sub(r'<p class="[^"]*translation[^"]*"[^>]*>.*?</p>', ' ', prose2, flags=re.S)
    prose2 = re.sub(r'<span class="honorific">[^<]*</span>', ' ', prose2)
    prose2 = re.sub(r'<cite[^>]*>.*?</cite>', ' ', prose2, flags=re.S)
    # section headings are labels, and a mandated heading title may carry a
    # plain comparative ("Why We Choose A Rather Than B"); strip h2-h6 like
    # tables and glossaries before the contrast and sentence scans
    prose2 = re.sub(r'<h[2-6][^>]*>.*?</h[2-6]>', ' ', prose2, flags=re.S)
    # block boundaries end a unit, so card lines and headings never merge into fake sentences
    prose2 = re.sub(r'</(?:p|div|li|h[1-6]|article|section|blockquote)>', '. ', prose2)
    prose2 = re.sub(r'<br\s*/?>', '. ', prose2)
    prose2 = re.sub(r'<[^>]+>', ' ', prose2)
    prose2 = re.sub(r'\s+', ' ', prose2)
    notbut = sorted({m.group(0) for m in re.finditer(r"(?i)\bnot\s+(?!only\b)[\w'’-]+(?:\s+[\w'’-]+){0,5}\s+but\b", prose2)})
    if notbut:
        errs.append(f'"not X but Y" contrast framing banned; state both sides as finished sentences ("The verse does not grant the right. It conditions it."): {notbut[:4]}')
    pivots2 = sorted(set(re.findall(r'(?i)\b(?:rather than|instead of|as opposed to)\b', prose2)))
    if pivots2:
        errs.append(f'contrast pivot(s) banned; rewrite as two direct statements: {pivots2}')
    # sentence backstop (home: "Reading level"): no site-prose sentence over 35 words
    LABEL = r'(?i)^(?:Premise \d+|Conclusion|Open question|Source|Speaker|Chain|Dating|Claim|Verse|Locus|Method|Reports|Place|Actor|Date)\s*:'
    longsents = []
    for s in re.split(r'[.!?]+', prose2):
        s = s.strip()
        if not s or len(re.findall(r', from | and from ', s)) >= 2 or re.match(LABEL, s):
            continue
        n = len(re.findall(r"[A-Za-z'’-]+", s))
        if n > 35:
            longsents.append((n, s[:70]))
    if not haddad and longsents:
        longsents.sort(key=lambda x: -x[0])
        errs.append(f'{len(longsents)} sentence(s) over 35 words (25 is the target; 35 the backstop); split them, longest is {longsents[0][0]} words: "{longsents[0][1]}..."')

    # catalogue register / page-internal narration (see "Titles, subtitles, and headings")
    for pat in (r'\(\d+ cards\)', r'\bthe card states\b', r'\bthe page preserves\b',
                r'\bNo card\b', r'\bcards below\b',
                r'attached to (?:the|each) (?:promise|movement|section)',
                r'as built and as placed'):
        if re.search(pat, src, re.I): errs.append(f'machine phrasing banned: {pat}')
    # landing pages are exempt: article titles mirrored into the index may
    # legitimately contain comma-spliced pairs.
    if not is_landing:
        for m in re.finditer(r'<h[1-4][^>]*>([^<]*, and the [^<]*)</h[1-4]>', src):
            errs.append(f'comma-spliced heading; rewrite as spoken English: {m.group(1).strip()[:60]}')
    if re.search(r'<title>[^<]*\bThe (?:Hadith|Report|Story) of [^<]* on ', src):
        errs.append('citation-shaped title; use a plain sentence or Why-question like the sibling pages')
    if re.search(r'<p class="text-md md:text-lg[^"]*">[^<]*\(d\.\d+ AH\), [^<]*, no\. \d+:', src):
        errs.append('provenance-first subtitle; write a sentence with a verb and file provenance at the end')

    # --- narration and translation standards (see ~/.agents/prose/translation.md) ---
    main_node = index.first('main')
    commentary_heading = next((n for text, n in index.headings() if text == 'Commentary'), None)
    if main_node and commentary_heading and main_node['start'] < commentary_heading['start']:
        narr = src[main_node['content_start']:commentary_heading['start']]
    else:
        narr = ''
    if narr:
        unnamed = [m for m in re.finditer(r'(?:>|\s)(?:He|he) said\s*[:,]', narr)]
        if unnamed: errs.append(f'{len(unnamed)} unnamed "He said" speaker tag(s); name every speaker')
        for pat in (r'"O [A-Z]', r'\bglad tidings\b', r'\bI adjure you\b', r'\bgive the lie\b',
                    r'\bby the right of\b', r'\bwhat occurs to you\b', r'\bspake\b|\bthee\b|\bthou\b'):
            if re.search(pat, narr): errs.append(f'archaic idiom in narration: {pat}')
        for pat in (r'\bThe (?:reply|method|pattern|terms|standard|test|oath) (?:that|used|was|left|fixed)\b',
                    r'\bTwo figures stood on offer\b', r'\bcarried its own refutation\b',
                    r'\bleft no middle ground\b', r'\bRead as\b', r'\bclosed in on\b',
                    r'\bno interpretation laid over\b', r'\bon his account\b',
                    r'\bthe whole weight of the claim\b', r'\bcompleted the demonstration\b'):
            if re.search(pat, narr): errs.append(f'empty framing sentence in narration: {pat}')
    for slug in ('sunni-tafsir', 'shia-tafsir', 'prophet-imams-biography', 'genealogy-biography',
                 'sunni-hadith-general', 'shia-hadith-general', 'quran-sciences', 'history-geography'):
        if slug in src: errs.append(f'corpus bucket label used as citation: {slug}')
    # aggregating sites never appear anywhere in the file (see "Citation rules"):
    # not as sources, not in meta keywords, not in footers, not in og tags.
    # The site's authors' pen names (Silas, Shamoun) credit the same site and are
    # banned by the same rule, but stay manual (Silas is also a New Testament figure).
    # NEVER exempt landing pages from this gate: the facts index mirrors article
    # content verbatim, and the 2026-08 leak lived partly there.
    _low = src.lower()
    for aggsite in ('answering-islam', 'answering islam', 'answering-christianity',
                    'bibleviz', 'philb61', 'evilbible', 'infidels.org', 'wikiislam'):
        if aggsite in _low:
            errs.append(f'aggregating-site reference "{aggsite}" banned everywhere on the page, including meta tags and footers; describe the attack generically ("the attack", "a circulating catalogue") and cite the primary holder')
    BOOKS = r"(?:Qur'an|Quran|Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song(?: of (?:Songs|Solomon))?|Canticles|Wisdom|Sirach|Tobit|Judith|Baruch|Maccabees|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation)"
    for m in re.finditer(r'\(([^)]*\d+:\d+[^)]*)\)', re.sub(r'<[^>]+>', ' ', src)):
        if not re.search(BOOKS, m.group(1)):
            errs.append(f'scripture reference without book name: ({m.group(1)})')
    comm = src[commentary_heading['start']:] if commentary_heading else ''
    if re.search(r'<p class="rtl font-amiri[^"]*"[^>]*>.*?</p>\s*<p class="italic transliteration">', comm, flags=re.S):
        errs.append('transliteration paragraph follows Arabic inside commentary; remove it')

    # Quote/callout structure. Keep this mechanical: it validates shape, not
    # whether a passage should have been quoted in the first place.
    callouts = []
    for node in index.nodes:
        if node['tag'] != 'blockquote':
            continue
        classes = set(node['attrs'].get('class', '').split())
        kind = next((k for k in ('quran-callout', 'hadith-callout') if k in classes), None)
        if kind:
            callouts.append((kind, node, index.inner(node)))

    for kind, node, body in callouts:
        body_index = HTMLIndex(body)
        body_index.feed(body)
        pnodes = [n for n in body_index.nodes if n['tag'] == 'p']
        translations = [n for n in pnodes if 'translation' in set(n['attrs'].get('class', '').split())]
        translits = [n for n in pnodes if 'transliteration' in set(n['attrs'].get('class', '').split())]
        arabic = [
            n for n in pnodes
            if {'rtl', 'font-amiri'} <= set(n['attrs'].get('class', '').split())
            and n['attrs'].get('lang') == 'ar'
        ]
        cites = [n for n in body_index.nodes if n['tag'] == 'cite']
        locus = node['attrs'].get('id') or f'offset {node["start"]}'
        if not translations:
            errs.append(f'{kind} at {locus} carries no translation paragraph')
        if len(cites) != 1:
            errs.append(f'{kind} at {locus} must carry exactly one <cite>; found {len(cites)}')
        # Bible originals may be Hebrew or Greek. A verified original and
        # complete translation do not require an optional romanization layer.
        biblical_original = any(n['attrs'].get('lang') in {'he','grc'} for n in pnodes)
        if kind == 'quran-callout' and not biblical_original:
            if not arabic:
                errs.append(f'quran-callout at {locus} carries no Arabic <p class="rtl ... font-amiri" lang="ar"> block')
            if not translits:
                errs.append(f'quran-callout at {locus} carries no transliteration paragraph')
        # Arabic in a callout must live inside a canonical Arabic paragraph.
        # Remove those nodes by span, then scan what remains.
        residue = body
        for child in sorted(arabic, key=lambda n: n['start'], reverse=True):
            residue = residue[:child['start']] + ' ' + residue[child['end']:]
        if re.search(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFC]', residue):
            errs.append(f'{kind} at {locus} contains Arabic outside a canonical rtl paragraph')

    # lexical grounding floor (home: "Lexical grounding"): a section whose
    # opening summary box flags contested words must cite at least one
    # lexicon inside that section; Qur'anic cross-usage and tafsir do not
    # substitute. Diacritics are stripped before matching so Lisān/Ṣiḥāḥ
    # match their plain spellings.
    def _nodiac(t):
        t = ''.join(c for c in unicodedata.normalize('NFD', t) if unicodedata.category(c) != 'Mn')
        return t.replace('\u02bf', '').replace('\u02be', '').lower()
    LEXMARK = ('lisan al-arab', 'qamus', 'sihah', 'tahdhib al-lughah',
               'maqayis', 'ibn faris', 'ibn manzur', 'al-jawhari',
               'fayruzabadi', 'al-azhari', 'al-khalil', 'brown-driver',
               'halot', 'gesenius', 'bdag', 'thayer', 'liddell',
               'lewis and short', 'oxford latin dictionary',
               'oxford english dictionary')
    cboxes = list(re.finditer(r'<strong>Contested(?:\s+words)?\.\s*</strong>(.*?)</p>', src, flags=re.S))
    for bx in cboxes:
        scope = index.enclosing(bx.start())
        if not scope:
            errs.append('Contested words box must live inside an <article> or <section> so lexical evidence cannot leak across the page')
            segment = bx.group(0)
        else:
            segment = index.outer(scope)
        boxtxt = _plain_text(bx.group(1)).lower()
        if re.search(r'<strong>Method\.', bx.group(0)):
            errs.append('contested-words box carries a Method label; method order is scaffolding, not reader content')
        if not re.search(r'\b(reads?|means?|says?|fix(?:es|ed)?|defines?|charge|turns?|bless(?:es)?|pray?s?|names?|shows?)\b', boxtxt):
            errs.append(f'contested-words box is an inventory without a dispute; state who reads the word how, not a word list ({boxtxt[:60]}...)')
        seg = _nodiac(segment)
        if not any(k in seg for k in LEXMARK):
            flagged = _plain_text(bx.group(1))[:70]
            errs.append(f'section flags contested words ({flagged}...) but cites no lexicon; per "Lexical grounding" the dictionaries come before Qur\'anic usage and tafsir')

    # honorific system: ligatures in English prose must be wrapped in
    # span.honorific; legacy (s)/(a) abbreviations are banned on new pages
    # NOTE: RTL blocks are NOT stripped here. Ligatures inside Arabic paragraphs
    # must ALSO be wrapped in span.honorific, because Amiri lacks the glyphs.
    unwrapped = re.sub(r'<span\s+class=["\']honorific["\'][^>]*>.*?</span>', ' ', src, flags=re.S | re.I)
    m = re.search(r'[ﷺ﵇﵍﵈﵊﵁﵀ﷻ﷿]', unwrapped)
    if m:
        errs.append(f'honorific ligature U+{ord(m.group()):04X} not wrapped in <span class="honorific">')
    abbr = sorted(set(re.findall(r'\w \((?:s|a|as|saws|sws|pbuh)\)', src, re.I)))
    if abbr: errs.append(f'legacy honorific abbreviation(s) {abbr} found; use the Unicode ligature + span.honorific system')

    # HARD RULE: no honorifics on the enemies of the Ahl al-Bayt (see Honorifics).
    # Any honorific ligature attached to an enemy name in non-Arabic text fails.
    # Landing pages are exempt: rows mirrored from legacy articles carry their
    # own bytes, and the fix belongs in the article, not the index.
    ENEMIES = r'(?:Umar|Abu\s+Bakr|Abubakr|Uthman|Mu[\'’]?awiya|Yazid|Khalid(?:\s+ibn\s+al-Walid)?|Ibn\s+Abbas|Abd\s+Allah\s+ibn\s+Abbas)'
    noarabic = re.sub(r'<p class="rtl[^"]*"[^>]*>.*?</p>', ' ', src, flags=re.S)
    if not is_landing:
        if re.search(r'\b(?:' + ENEMIES + r')\s*(?:<span class="honorific">\s*[ﷺ﵇﵍﵈﵊﵁﵀ﷻ﷿]\s*</span>|[ﷺ﵇﵍﵈﵊﵁﵀ﷻ﷿])', noarabic):
            errs.append('honorific attached to an enemy of the Ahl al-Bayt (banned by hard rule); name enemies bare in English prose and translations')
        if re.search(r'\b(?:' + ENEMIES + r')\s*[-–,]?\s*(?:may\s+God\s+(?:be\s+pleased\swith|have\s+mercy\s+on)\s+(?:him|her|them)|God\s+be\s+pleased\s+with\s+(?:him|her|them))', noarabic, re.I):
            errs.append('spelled-out honorific attached to an enemy of the Ahl al-Bayt (banned by hard rule)')

    # single design standard
    for bad in ('#A43820', 'text-red-', 'bg-red-', 'bg-amber-', 'border-l-4',
                'quote-original', 'quote-translit', 'quote-translation', 'font-arabic'):
        if bad in src: errs.append(f'banned token present (single design standard): {bad}')
    # RTL rendering: a page that quotes Arabic in class="rtl" paragraphs must
    # carry the direction rule (lang="ar" alone does not set direction; without
    # it the Arabic renders left-justified in an LTR block)
    if 'class="rtl' in src and 'direction: rtl' not in src:
        errs.append('page carries class="rtl" Arabic paragraphs but no "direction: rtl" rule; Arabic renders left-justified (add the .rtl rule from the reference pages)')
    if re.findall(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B50]', src):
        errs.append('emoji found (banned)')
    # flow-chart diagram boxes may center their labels (chart-node) and arrow
    # glyphs (chart-arrow); every other use of text-center before the footer
    # keeps failing (home: Step 2e, single design standard)
    last_footer = src.rfind('<footer')
    for m in re.finditer(r'<(\w+)([^>]*\btext-center\b[^>]*)>', src):
        if m.start() < last_footer and not re.search(r'\bchart-(?:node|arrow)\b', m.group(2)):
            errs.append('text-center outside the site footer (page chrome is left-aligned; only chart-node/chart-arrow diagram boxes may center)')
            break

    # category system (see ~/.agents/prose/article-structure.md)
    # scope: article pages only. index.html and facts.html are exempt (no data-category).
    if is_landing:
        cat = 'index'  # exempt from category anatomy; structural checks still run
    else:
        mcat = re.search(r'<main[^>]*data-category="(debate|exegesis|narration|commentary)"', src)
        cat = mcat.group(1) if mcat else None
    if not cat:
        errs.append('missing <main data-category="debate|exegesis|narration|commentary"> declaration')
    else:
        heading_texts = {text for text, _ in index.headings()}
        has_verdict = 'Final Verdict' in heading_texts
        has_conclusion_closer = any(t.startswith('Conclusion:') for t in heading_texts)
        has_reading = 'The Reading' in heading_texts
        if cat == 'debate' and not (has_verdict or has_conclusion_closer):
            errs.append('debate page missing Final Verdict block (or a "Conclusion: ..." closer heading)')
        if cat != 'debate' and has_verdict:
            errs.append(f'{cat} page carries "Final Verdict"; only debate pages do (exegesis closes with "The Reading", narration with its own heading)')
        if cat == 'exegesis' and not has_reading:
            errs.append('exegesis page missing "The Reading" closing section')

    if cat == 'debate':
        main_html = index.inner(main_node) if main_node else src
        if 'premise-card' not in main_html:
            # 2026-09-06: a debate intro may open with the human prose opening
            # instead of the premise grid; require a substantial prose intro
            first_sec = re.search(r'<section[^>]*>.*?</section>', main_html, flags=re.S)
            prose_words = len(re.findall(r"[A-Za-z'’-]+", re.sub(r'<[^>]+>', ' ', first_sec.group(0)))) if first_sec else 0
            if prose_words < 150:
                errs.append('debate page missing premise-card argument in the intro (or a prose introduction of at least 150 words)')
        if 'conclusion-card' not in main_html:
            errs.append('debate page missing conclusion-card derived from the intro premises')

    # opponent declaration + mandatory comparative section
    # (home: "The Christian refutation sequence"). The trigger is the
    # opponent, not the charge's shape: moral and historical charges from
    # Christian polemic (sword verse, marriage ages, killed critics)
    # count. The comparison gate is structural; depth is the council's.
    if cat == 'debate':
        mopp = re.search(r'<main[^>]*data-opponent="([^"]+)"', src)
        if not mopp:
            errs.append('debate page missing data-opponent="christian|sunni|orientalist|secular" declaration (decided in the Stage 1 plan)')
        elif mopp.group(1) not in ('christian', 'sunni', 'orientalist', 'secular'):
            errs.append(f'data-opponent="{mopp.group(1)}" is not one of christian|sunni|orientalist|secular')
        elif mopp.group(1) == 'christian':
            cmp_node = index.by_id('comparison')
            if not cmp_node or cmp_node['tag'] != 'section':
                errs.append('christian-opponent debate page missing the comparative section (<section id="comparison">) before the Final Verdict; per "The Christian refutation sequence" the page states the Christian beliefs on the topic and argues the four criteria')
            else:
                cbody = index.inner(cmp_node)
                if not re.search(r'<h[23][^>]*>', cbody):
                    errs.append('comparative section carries no heading')
                if '<cite' not in cbody:
                    errs.append('comparative section cites no primary Christian holder (no <cite> in the section); beliefs are traced to fathers, councils, creeds, or scripture per step 3')
                verdict_node = next((n for text, n in index.headings() if text == 'Final Verdict' or text.startswith('Conclusion:')), None)
                if verdict_node and cmp_node['start'] > verdict_node['start']:
                    errs.append('comparative section must appear before the Final Verdict')

    # The Facts block (debate/exegesis): presence, rows, anchors, qualifiers, drift
    QUALIFIERS = ('stated', 'reported', 'attributed', 'likely', 'disputed')
    if cat in ('debate', 'exegesis'):
        facts_node = index.by_id('facts')
        if not facts_node or facts_node['tag'] != 'section':
            errs.append(f'{cat} page missing The Facts block (<section id="facts">) after the intro card')
        else:
            ftxt = index.outer(facts_node)
            tables = re.findall(r'<table.*?</table>', ftxt, flags=re.S)
            if not tables:
                errs.append('The Facts block carries no <table>')
            rows = 0
            for t in tables:
                rows += len(re.findall(r'<tr', t))
            if rows < 4:  # header row + at least 3 fact rows
                errs.append(f'The Facts block has {rows - 0} table rows total; need at least 3 fact rows')
            # qualifier taxonomy on every row body
            body_rows = re.findall(r'<tbody>(.*?)</tbody>', ftxt, flags=re.S) or [ftxt]
            flat_rows = []
            for chunk in body_rows:
                for r in re.findall(r'<tr.*?</tr>', chunk, flags=re.S):
                    flat_rows.append(r)
            qcol = [c for c in re.findall(r'<th[^>]*>\s*(?:Qualifier|Status)\s*</th>', ftxt)]
            if flat_rows and not qcol:
                errs.append('Facts tables missing the Qualifier column (mandatory on every table)')
            for r in flat_rows:
                cells = [re.sub(r'<[^>]+>', '', c).strip()
                         for c in re.findall(r'<td[^>]*>(.*?)</td>', r, flags=re.S)]
                if cells and not any(q in cells for q in QUALIFIERS):
                    errs.append(f'Facts row without a Qualifier cell from the taxonomy {QUALIFIERS}: "{cells[0][:40]}..."')
            # anchors resolve + hash-open script present when rows carry anchors
            row_links = re.findall(r'href="#([^"]+)"', ftxt)
            if flat_rows and not row_links:
                errs.append('Facts rows carry no detail anchors (href="#..."); no anchor, no row')
            idset2 = set(re.findall(r'id="([^"]+)"', src))
            for a in row_links:
                if a not in idset2:
                    errs.append(f'Facts anchor #{a} resolves to nothing on the page')
            if row_links and 'hashchange' not in src:
                errs.append('page with anchored Facts rows needs the hash-handling script (scroll-to-target on #hash; open <details> on narration pages)')
            # hedge parity: prose hedge words near an anchored target must survive in the row
            HEDGES = ('quite likely', 'most likely', 'reportedly', 'probably', 'perhaps', 'it is likely', 'possibly')
            seen_anchors = set()
            for a in row_links:
                if a in seen_anchors:
                    continue
                seen_anchors.add(a)
                target_node = index.by_id(a)
                if not target_node:
                    continue
                target = _plain_text(index.inner(target_node))
                hedge = next((h for h in HEDGES if h in target.lower()), None)
                row = next((r for r in flat_rows if f'href="#{a}"' in r), None)
                if hedge and row:
                    rowtxt = re.sub(r'<[^>]+>', ' ', row).lower()
                    if 'likely' not in rowtxt and 'reported' not in rowtxt and 'attributed' not in rowtxt and 'disputed' not in rowtxt:
                        errs.append(f'Facts row for #{a} flattens a hedge: target prose says "{hedge}" but the row carries no qualifier')

    # new architecture: sticky nav present, no JS-toggled hiding outside details
    if cat in ('debate', 'exegesis'):
        if 'position: sticky' not in src and 'sticky top-0' not in src:
            errs.append('debate/exegesis pages need the sticky section nav (position: sticky)')
        if not re.search(r'<nav[^>]*aria-label', src):
            errs.append('sticky nav missing its <nav aria-label> landmark')
        if re.search(r'<div class="accordion-item', src):
            errs.append('accordion-item found on a new page; body content must be open <article> sections')
        if 'aria-current' not in src:
            errs.append('scroll-spy aria-current missing on the sticky nav')
    if cat == 'narration' or commentary_heading:
        if re.search(r'<div class="accordion-item', src):
            errs.append('narration Commentary must be a native <details>, not a JS accordion')
        if cat == 'narration':
            if not commentary_heading:
                errs.append('narration page missing Commentary heading')
            main_html = index.inner(main_node) if main_node else src
            detail_count = len(re.findall(r'<details\b', main_html, flags=re.I))
            if detail_count != 1:
                errs.append(f'narration page must carry exactly one Commentary <details> block; found {detail_count}')

    # fixed four-beat rhythm ban (content-named subheadings instead)
    item_bodies = re.findall(r'<article[^>]*>(.*?)</article>', src, flags=re.S) or re.findall(r'accordion-content[^>]*>(.*?)(?=accordion-item|</main>|<h2)', src, flags=re.S)
    for body in item_bodies:
        heads = [re.sub(r'<[^>]+>', '', h).strip()
                 for h in re.findall(r'analysis-heading[^>]*>([^<]*)<', body)]
        heads = [h for h in heads if h]
        for beat in (('Introduction', 'Example', 'Implication', 'Conclusion'),
                     ('Introduction', 'Example', 'Application', 'Conclusion')):
            n = min(len(heads), 4)
            if n == 4 and tuple(heads[:4]) == beat:
                errs.append(f'fixed four-beat rhythm {beat} banned; name subheadings after their content')
                break

    # grade 9 gate on the site's own prose (FK + reading ease; quote internals
    # and name chains excluded). Landing pages are exempt (mirrored rows).
    def _syl(w):
        w = re.sub(r'[^a-z]', '', w.lower())
        if not w: return 0
        n = len(re.findall(r'[aeiouy]+', w))
        return max(1, n - (1 if w.endswith('e') and n > 1 else 0))
    def _stats(text):
        sents = [s for s in re.split(r'[.!?]+', text) if s.strip()]
        sents = [s for s in sents if len(re.findall(r', from | and from ', s)) < 2]
        words = re.findall(r"[A-Za-z'’-]+", ' '.join(sents))
        if len(sents) < 3 or len(words) < 60: return None
        return len(words)/len(sents), sum(_syl(w) for w in words)/len(words)
    prose = src[src.find('<main'):] if '<main' in src else src
    prose = re.sub(r'<script.*?</script>', ' ', prose, flags=re.S)
    prose = re.sub(r'<table[^>]*>.*?</table>', ' ', prose, flags=re.S)  # tables are data, not prose (same exclusion as the sentence cap)
    prose = re.sub(r'<p class="rtl[^"]*"[^>]*>.*?</p>', ' ', prose, flags=re.S)
    prose = re.sub(r'<p class="[^"]*transliteration[^"]*"[^>]*>.*?</p>', ' ', prose, flags=re.S)
    prose = re.sub(r'<p class="[^"]*translation[^"]*"[^>]*>.*?</p>', ' ', prose, flags=re.S)
    prose = re.sub(r'<span class="honorific">[^<]*</span>', ' ', prose)
    prose = re.sub(r'<cite[^>]*>.*?</cite>', ' ', prose, flags=re.S)
    prose = re.sub(r'<[^>]+>', ' ', prose)
    st = _stats(prose)
    if st is not None and not is_landing and not haddad:
        wps, spw = st
        g = 0.39 * wps + 11.8 * spw - 15.59
        e = 206.835 - 1.015 * wps - 84.6 * spw
        if g > 10.5:
            errs.append(f'page prose measures Flesch-Kincaid grade {g:.1f} (ceiling 10.5); shorten sentences and prefer everyday words')
        if e < 55:
            errs.append(f'page prose measures Flesch Reading Ease {e:.1f} (floor 55, target 60); shorten sentences and prefer everyday words')

    if 'Faith &amp; Reason in Islam' not in src: errs.append('missing/stale site footer')

    return errs


# ---------------------------------------------------------------------------
# Self-test: every gate must fire on its fixture, and every documented
# exception must stay clean. Substring assertions isolate one gate per
# fixture, so unrelated failures on minimal pages do not mask results.
# ---------------------------------------------------------------------------

ADVISORY_PREFIXES = (
    'AI-style contrast', 'litotes', 'irony/', 'source-text-as-subject',
    'abstract-subject glue', 'AI-register tell', 'preamble opener',
    'not-X-but-Y', 'contrast pivot', 'unfinished',
)

def is_advisory(message):
    return message.startswith(ADVISORY_PREFIXES) or 'Flesch' in message or 'sentence(s) over 35' in message

def check(src, register='standard'):
    """Hard structural failures. Semantic cues and readability need review."""
    return [message for message in _check(src, register=register) if not is_advisory(message)]

def diagnostics(src, register='standard'):
    return [message for message in _check(src, register=register) if is_advisory(message)]


def _mini(body, main='<main data-category="debate">'):
    return ('<!DOCTYPE html><html><head><title>t</title></head><body>'
            + main + body + '</main>'
            + '<footer>Faith &amp; Reason in Islam</footer></body></html>')

_LONG_OK = ' '.join(['The man went home and ate bread with his sons.'] * 14)
_LONG_BAD = ' '.join([
    'Consequently, the ecclesiastical authorities promulgated increasingly sophisticated doctrinal formulations, systematically delineating appropriate soteriological categories.',
    'Notwithstanding considerable historiographical disagreement, contemporary scholarship predominantly characterizes these developments as unprecedented theological consolidation.',
    'Furthermore, the institutional manifestations subsequently acquired independent ecclesiastical significance, transcending their originally contingent liturgical functionality.',
]) * 2

FIXTURES = [
    # (name, src, must_appear, must_not_appear)
    ('not-but fires',            _mini('<p>The verse does not grant the right but conditions it on a treaty.</p>'), '"not X but Y"', None),
    ('not-only exception clean', _mini('<p>The verse not only names the act but also fixes the penalty.</p>'), None, '"not X but Y"'),
    ('translation exception clean', _mini('<p class="translation">The Imam said, my God is one God, not one as opposed to two.</p>'), None, 'contrast pivot'),
    ('heading comparative clean', _mini('<h2>10. What Finally Explains Why We Choose A Rather Than B?</h2><p>Plain prose here.</p>'), None, 'contrast pivot'),
    ('rather-than fires',        _mini('<p>The school reads the verse as a command rather than a permission.</p>'), 'contrast pivot', None),
    ('instead-of fires',         _mini('<p>The judge rules by the text instead of by his own opinion.</p>'), 'contrast pivot', None),
    ('litotes far-from fires',   _mini('<p>The chain is far from settling the question.</p>'), 'litotes', None),
    ('far from Mecca clean',     _mini('<p>He died in Gaza, far from Mecca, before the child was born.</p>'), None, 'litotes'),
    ("Ja'far from clean",        _mini("<p>The chain runs from Ja'far from al-Baqir.</p>"), None, 'litotes'),
    ('by no means fires',        _mini('<p>This reading is by no means forced.</p>'), 'litotes', None),
    ('long sentence fires',      _mini('<p>The ' + 'very ' * 20 + 'long sentence runs far past the hard limit of thirty-five words for absolutely no good reason at all here.</p>'), 'over 35 words', None),
    ('short sentences clean',    _mini('<p>The man went home. He ate bread. His sons sat with him.</p>'), None, 'over 35 words'),
    ('aggregator fires',         _mini('<p>Plain prose here.</p>').replace('<title>t</title>', '<title>t</title><meta name="keywords" content="x, answering-islam">'), 'aggregating-site', None),
    ('aggregator clean',         _mini('<p>Plain prose here.</p>'), None, 'aggregating-site'),
    ('em dash fires',            _mini('<p>A claim — a strong one.</p>'), 'em/en dash', None),
    ('chart-node centered clean', _mini('<div class="chart-node border rounded p-2 text-center">Allah gives being</div>'), None, 'text-center outside'),
    ('text-center on prose fires', _mini('<p class="text-center">Centered prose.</p>'), 'text-center outside', None),
    ('colon fires',              _mini('<p>The charge: it fails.</p>'), 'colon in prose', None),
    ('heading colon clean',      _mini('<h2>1. The Problem: If God Is Sovereign</h2><p>Plain prose here.</p>'), None, 'colon in prose'),
    ('conclusion closer clean',  _mini('<p>Text.</p>', main='<main data-category="debate"><h2>Conclusion: Why It Holds</h2>'), None, 'missing Final Verdict'),
    ('debate no closer fires',   _mini('<p>Text.</p>'), 'missing Final Verdict', None),
    ('preamble opener fires', _mini('<p>The page speaks to two readers at once. Then the verse arrives.</p>'), 'preamble opener', None),
    ('preamble layer feed fires', _mini('<p>The answer moves in layers, and each layer feeds the next. Ibn Sida defines mercy.</p>'), 'preamble opener', None),
    ('preamble content clean', _mini('<p>The dictionaries print the mercy sense inside their entries for this root.</p>'), None, 'preamble'),
    ('verse card without verse fires', _mini('<article id="x"><h3>T</h3><div class="premise-card space-y-1 mb-4"><p class="text-sm"><strong>Verse:</strong> Qur\'an 33:56</p></div><p>Prose only.</p><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote></article>'), 'naming a scripture reference', None),
    ('built-and-placed fires', _mini('<h3>The Word as Built and as Placed</h3><p>Ibn Sida defines it.</p>'), 'machine phrasing', None),
    ('apparatus voice fires', _mini('<p>The chain is disputed, and the report is cited here with that status.</p>'), 'apparatus voice', None),
    ('apparatus kept-as-printed fires', _mini('<p>The final clause is copied, and it is kept as printed.</p>'), 'apparatus voice', None),
    ('apparatus clean', _mini('<p>Sahl ibn Ziyad is a disputed transmitter. The report says what it says.</p>'), None, 'apparatus'),
    ('below nav fires', _mini('<p>The dictionaries below show what the construction carried.</p>'), 'below', None),
    ('below nav clean', _mini('<p>The dictionaries show what the construction carried inside the entries.</p>'), None, 'below navigation'),
    ('h5 under section fires', _mini('<main data-category="debate"><section id="tab1"><h2>1. S</h2><article id="a"><h5 class="analysis-heading">Sub</h5><p>T.</p></article></section></main>'), 'double heading', None),
    ('glue verb fires', _mini('<p>The chain carries its caveat. The grammar stays Godward.</p>'), 'glue verb', None),
    ('ai register fires', _mini('<p>The gallery serves as a testament to art. At its core, the deeper issue remains.</p>'), 'AI-register', None),
    ('tack-on ing fires', _mini('<p>The temple uses blue colors, reflecting the natural beauty of the region.</p>'), 'tack-on', None),
    ('ai register clean', _mini('<p>The gallery is a space for contemporary art. The question is whether teams adapt.</p>'), None, 'AI-register'),
    ('hadith transliteration fires', _mini('<blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p><p class="italic transliteration">y</p></blockquote>'), 'transliterations are scripture-only', None),
    ('hadith no transliteration clean', _mini('<blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p><p class="translation">y</p></blockquote>'), None, 'transliterations are scripture-only'),
    ('article h3 under section fires', _mini('<main data-category="debate"><section id="tab1"><h2>1. Section</h2><article id="a"><h3>Sub</h3><p>Text.</p></article></section></main>'), 'double heading', None),
    ('no h3 clean', _mini('<main data-category="debate"><section id="tab1"><h2>1. Section</h2><article id="a"><p>Text.</p><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote></article></section></main>'), None, 'double heading'),
    ('double title fires', _mini('<article id="x"><h3>The Verse Itself</h3><div class="analysis-section"><h5 class="analysis-heading">The Verse</h5><p>Ibn Sida defines it.</p><blockquote class="quran-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote></div></article>'), 'redundant subheading', None),
    ('double title clean with two exhibits', _mini('<article id="x"><h3>Lexicons</h3><div class="analysis-section"><h5 class="analysis-heading">Ibn Sida</h5><p>One.</p><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote><h5 class="analysis-heading">al-Jawhari</h5><p>Two.</p><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">y</p></blockquote></div></article>'), None, 'redundant subheading'),
    ('card placement fires', _mini('<article id="x"><h3>T</h3><div class="premise-card space-y-1 mb-4"><p class="text-sm"><strong>Source:</strong> K</p></div><div class="analysis-section"><p>Intro prose sits between.</p><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote></div></article>'), 'every quoted callout', None),
    ('card placement clean', _mini('<article id="x"><h3>T</h3><div class="analysis-section"><p>Intro prose.</p><div class="premise-card space-y-1 mb-4"><p class="text-sm"><strong>Source:</strong> K</p></div><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote></div></article>'), None, 'every quoted callout'),
    ('second quote cardless fires', _mini('<article id="x"><h3>T</h3><div class="analysis-section"><p>Intro.</p><div class="premise-card space-y-1 mb-4"><p class="text-sm"><strong>Source:</strong> K</p></div><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">y</p></blockquote></div></article>'), 'every quoted callout', None),
    ('every quote carded clean', _mini('<article id="x"><h3>T</h3><div class="analysis-section"><p>Intro.</p><div class="premise-card space-y-1 mb-4"><p class="text-sm"><strong>Source:</strong> K</p></div><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote><div class="premise-card space-y-1 mb-4"><p class="text-sm"><strong>Source:</strong> K2</p></div><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">y</p></blockquote></div></article>'), None, 'every quoted callout'),
    ('card missing fires', _mini('<article id="x"><h3>T</h3><div class="analysis-section"><p>Intro.</p><blockquote class="hadith-callout"><p class="rtl font-amiri" lang="ar">x</p></blockquote></div></article>'), 'every quoted callout', None),
    ('method label in box fires', _mini('<section><p><strong>Contested words.</strong> <em>yusalluna</em>, the verb under dispute. <strong>Method.</strong> Construction first.</p><p>Ibn Manzur, Lisan al-Arab, defines it.</p></section>'), 'Method label', None),
    ('inventory box fires', _mini('<section><p><strong>Contested words.</strong> <em>yusalluna alā</em>, second stem. <em>salāt</em>, <em>duā</em>, <em>bāraka</em>.</p><p>Ibn Manzur, Lisan al-Arab, defines it.</p></section>'), 'inventory without a dispute', None),
    ('dispute box clean', _mini('<section><p><strong>Contested words.</strong> The charge reads <em>yusalluna alā</em> as prayer directed at the Prophet. Ibn Manzur, Lisan al-Arab, defines it.</p></section>'), None, 'inventory without a dispute'),
    ('meta statement fires',     _mini('<p>This article examines the claim in full.</p>'), 'meta statement', None),
    ('navigation meta fires',    _mini('<p>The sections that follow develop this line in full.</p>'), 'meta statement', None),
    ('premise pointer fires',    _mini('<p>Sections 2 through 4 carry this premise.</p>'), 'meta statement', None),
    ('previous section fires',   _mini('<p>The previous section ended with a dominion.</p>'), 'meta statement', None),
    ('same-thing litotes fires', _mini('<p>Dependence is not the same thing as compulsion.</p>'), 'litotes', None),
    ('narrmeta fires',           _mini('<p>The narration records the event.</p>'), 'source-text-as-subject', None),
    ('scripture ref fires',      _mini('<p>See (16:43) for this point.</p>'), 'without book name', None),
    ('duplicate id fires',       _mini('<p id="a">x</p><p id="a">y</p>'), 'DUPLICATE ids', None),
    ('enemy honorific fires',    _mini('<p>Umar <span class="honorific">\uFD41</span> spoke.</p>'), 'enemy of the Ahl al-Bayt', None),
    ('unwrapped ligature fires', _mini('<p>The Imam \uFD47 answered.</p>'), 'not wrapped', None),
    ('emoji fires',              _mini('<p>He smiled \U0001F600 at them.</p>'), 'emoji found', None),
    ('rtl without direction fires', _mini('<blockquote class="hadith-callout"><p class="rtl font-amiri text-xl" lang="ar">كلام</p><p class="translation">"Words."</p><cite class="text-sm text-gray-500">- Book, p. 1</cite></blockquote>'), 'direction: rtl', None),
    ('rtl with direction clean', _mini('<style>.rtl{direction: rtl;text-align: right;}</style><blockquote class="hadith-callout"><p class="rtl font-amiri text-xl" lang="ar">كلام</p><p class="translation">"Words."</p><cite class="text-sm text-gray-500">- Book, p. 1</cite></blockquote>'), None, 'direction: rtl'),
    ('four-beat fires',          _mini('<article><h4 class="analysis-heading">Introduction</h4><h4 class="analysis-heading">Example</h4><h4 class="analysis-heading">Implication</h4><h4 class="analysis-heading">Conclusion</h4></article>'), 'four-beat', None),
    ('commentary category accepted', _mini('<h2>Sources and their limits</h2><p>The report attributes this view to its narrator.</p>', main='<main data-category="commentary">'), None, 'missing <main data-category'),
    ('commentary needs no narration apparatus', _mini('<h2>Sources and their limits</h2><p>The report attributes this view to its narrator.</p>', main='<main data-category="commentary">'), None, 'Commentary'),
    ('commentary has no forced verdict', _mini('<h2>Sources and their limits</h2><p>The report attributes this view to its narrator.</p>', main='<main data-category="commentary">'), None, 'missing Final Verdict'),
    ('missing category fires',   _mini('<p>Text.</p>', main='<main>'), 'missing <main data-category', None),
    ('debate needs facts fires', _mini('<p>Text.</p>'), 'missing The Facts block', None),
    ('opponent missing fires',   _mini('<p>Text.</p>'), 'data-opponent', None),
    ('opponent invalid fires',   _mini('<p>Text.</p>', main='<main data-category="debate" data-opponent="jews">'), 'not one of christian|sunni', None),
    ('christian needs comparison fires', _mini('<p>Text.</p>', main='<main data-category="debate" data-opponent="christian">'), 'comparative section', None),
    ('comparison without cite fires', _mini('<section id="comparison"><h2>What Christians Believe</h2><p>Words about beliefs.</p></section>', main='<main data-category="debate" data-opponent="christian">'), 'no primary Christian holder', None),
    ('comparison clean',         _mini('<section id="comparison"><h2>What Christians Believe</h2><p>Words about beliefs.</p><blockquote class="hadith-callout"><p class="translation">"A quote."</p><cite class="text-sm text-gray-500">- Augustine, City of God, book III, ch. 5</cite></blockquote></section>', main='<main data-category="debate" data-opponent="christian">'), None, 'comparative section'),
    ('lexical floor fires',      _mini('<div><p><strong>Contested words.</strong> makr, law</p><p>Body of the section.</p></div>'), 'cites no lexicon', None),
    ('lexical floor clean',      _mini('<section><p><strong>Contested words.</strong> makr, law</p><p>Ibn Manzur, Lisan al-Arab, defines it.</p></section>'), None, 'cites no lexicon'),
    ('FK/FRE pass clean',        _mini(f'<p>{_LONG_OK}</p>'), None, 'Flesch'),
    ('FK/FRE dense fires',       _mini(f'<p>{_LONG_BAD}</p>'), 'Flesch', None),
    ('FK/FRE table excluded',    _mini(f'<p>{_LONG_OK}</p><table><tr><td>al-Muraysi, against Banu al-Mustaliq, Dhu al-Qa\'da, no battle</td><td>al-Hudaybiyya Umrat al-Qadiyya Dumat al-Jandal Tabuk Rajab Shawwal Muharram Jumada al-Khandaq Qurayza Khaybar Hunayn al-Ta\'if</td></tr></table>'), None, 'Flesch'),
    ('landing exempts mirrored title', _mini('<h3>Denying Sonship: A View, and the Rest</h3><p>Umar <span class="honorific">\uFD41</span> row.</p>', main='<main data-category="facts-index">'), None, 'comma-spliced'),
    ('landing keeps aggregator gate', _mini('<h3>Index</h3><meta name="keywords" content="x, answering-islam">', main='<main data-category="facts-index">'), 'aggregating-site', None),
    # Haddad register waiver: the grade-9 prose gates (dash, colon, sentence
    # cap) are waived in that register, but structural gates still fire.
    # 5th tuple element = register under which to run the fixture.
    ('haddad waives dash/colon/length', _mini('<p>The charge: al-Dhahabi declared it weak — a decisive grading of the chain, whose narrator Isa b. Maymunah al-Thaqafi al-Basri al-Kufi Abu al-Mughira transmitted it with a broken isnad that the hadith masters graded fatally weak.</p>'), None, 'em/en dash', 'haddad'),
    ('haddad keeps dash gate off in standard', _mini('<p>The charge: al-Dhahabi declared it weak — a decisive grading.</p>'), 'em/en dash', None),
    ('haddad keeps aggregator gate', _mini('<p>Plain prose, and a link: see answering-islam.</p>'), 'aggregating-site', None, 'haddad'),
    ('bold prose colon fires', _mini('<p><strong>The charge: it fails.</strong></p>'), 'colon in prose', None),
    ('label colon stays clean', _mini('<p><strong>Source:</strong> Book name</p>'), None, 'colon in prose'),
    ('narration unnamed comma fires', _mini('<p>He said, words.</p><h2>Commentary</h2><details><summary>Notes</summary><p>Text.</p></details>', main='<main data-category="narration">'), 'unnamed "He said"', None),
    ('narration one details required', _mini('<h2>Commentary</h2>', main='<main data-category="narration">'), 'exactly one Commentary <details>', None),
    ('lexicon cannot leak from next section', _mini('<section><p><strong>Contested words.</strong> law</p><p>Body.</p></section><section><p>Ibn Manzur, Lisan al-Arab, defines another term.</p></section>'), 'cites no lexicon', None),
    ('wrapped then bare honorific fires', _mini('<p><span class="honorific">\uFD47</span> text \uFD47</p>'), 'not wrapped', None),
    ('Hebrews scripture ref clean', _mini('<p>See (Hebrews 1:3).</p>'), None, 'without book name'),
    ('category attribute order still gates nav', _mini('<p>Text.</p>', main='<main class="page" data-category="debate" data-opponent="sunni">'), 'sticky section nav', None),
    ('broken internal anchor fires', _mini('<p><a href="#missing">go</a></p>'), 'internal anchor', None),
    ('bible original without romanization clean', _mini('<blockquote class="quran-callout"><p lang="grc">λογος</p><p class="translation">Word.</p><cite>John 1:1, Textus Receptus</cite></blockquote>'), None, 'carries no transliteration'),
    ('quran callout missing Arabic fires', _mini('<blockquote class="quran-callout"><p class="italic transliteration">text</p><p class="translation">Words.</p><cite>Quran 1:1</cite></blockquote>'), 'carries no Arabic', None),
    ('quran callout missing transliteration fires', _mini('<style>.rtl{direction: rtl;}</style><blockquote class="quran-callout"><p class="rtl font-amiri" lang="ar">\u0643\u0644\u0627\u0645</p><p class="translation">Words.</p><cite>Quran 1:1</cite></blockquote>'), 'carries no transliteration', None),
    ('callout missing cite fires', _mini('<blockquote class="hadith-callout"><p class="translation">Words.</p></blockquote>'), 'exactly one <cite>', None),
    ('debate premise card required', _mini('<div class="conclusion-card">Conclusion.</div>'), 'missing premise-card', None),
    ('debate prose intro clean', _mini('<section id="argument"><p>' + 'The problem stated plainly enough for a first reader to follow. ' * 20 + '</p></section><blockquote class="conclusion-card"><p>Formula.</p></blockquote>'), None, 'premise-card'),
    ('debate thin prose intro fires', _mini('<section id="argument"><p>Short intro.</p></section><blockquote class="conclusion-card"><p>Formula.</p></blockquote>'), 'missing premise-card', None),
    ('debate conclusion card required', _mini('<div class="premise-card">Premise.</div>'), 'missing conclusion-card', None),
    ('quran callout class order clean', _mini('<style>.rtl{direction: rtl;}</style><blockquote class="quran-callout"><p lang="ar" class="font-amiri text-xl rtl">\u0643\u0644\u0627\u0645</p><p class="transliteration italic">kalam</p><p class="translation">Words.</p><cite>Quran 1:1</cite></blockquote>'), None, 'carries no Arabic'),
    ('contested box requires section scope', _mini('<p><strong>Contested words.</strong> law</p><p>Ibn Manzur, Lisan al-Arab.</p>'), 'must live inside an <article> or <section>', None),
]

# fixtures may carry a 5th element: the register to run them under


def selftest():
    failed = 0
    for fixture in FIXTURES:
        name, src, must, mustnot = fixture[:4]
        register = fixture[4] if len(fixture) > 4 else 'standard'
        errs = _check(src, register=register)
        text = '\n'.join(errs)
        problems = []
        if must and not any(must in e for e in errs):
            problems.append(f'expected a failure containing "{must}"')
        if mustnot and any(mustnot in e for e in errs):
            problems.append(f'expected no failure containing "{mustnot}"')
        if problems:
            failed += 1
            print(f'SELFTEST FAIL: {name} [register={register}]: ' + '; '.join(problems))
        else:
            print(f'selftest ok: {name}' + (f' [register={register}]' if register != 'standard' else ''))
    print(f'\n{len(FIXTURES) - failed}/{len(FIXTURES)} fixtures pass')
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('file', nargs='?', help='HTML article to validate')
    parser.add_argument('--register', choices=('standard', 'haddad'), default='standard')
    parser.add_argument('--selftest', action='store_true', help='run validator fixtures')
    parser.add_argument('--format', choices=('text', 'json'), default='text', dest='output_format')
    ns = parser.parse_args(argv)

    if ns.selftest:
        if ns.file:
            parser.error('--selftest does not take a file')
        return selftest()
    if not ns.file:
        parser.error('file is required unless --selftest is used')

    path = Path(ns.file)
    try:
        src = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        print(f'FAILED to read {path}: {exc}', file=sys.stderr)
        return 2

    errs = check(src, register=ns.register)
    warnings = diagnostics(src, register=ns.register)
    if ns.output_format == 'json':
        import json
        print(json.dumps({'ok': not errs, 'errors': errs, 'count': len(errs), 'review_warnings': warnings, 'editorial_approval': 'separate review required'}, ensure_ascii=False, indent=2))
    else:
        for warning in warnings:
            print('REVIEW:', warning)
        for e in errs:
            print('FAIL:', e)
        print('OK' if not errs else f'{len(errs)} problem(s)')
    return 1 if errs else 0


if __name__ == '__main__':
    sys.exit(main())