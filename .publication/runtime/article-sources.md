# Source and citation conventions

Read before capturing sources and building a master. `article-workflow.md`
owns collection and exact-slice verification; the research framework owns
reasoning and source priority. This file owns citation presentation and the
shared honorific convention. None of these rules permits altering corpus text.

## Quotations and citations

Use the actual work title, author, volume and printed page, plus chapter,
report or verse number when provided. Corpus categories are never titles.
Verify attribution against the page actually quoted. A later author's quotation
is a transmitted witness, not automatically independent corroboration or an
endorsement. Distinguish a primary report from a modern scholar describing it;
quote the primary evidence where available and label any secondary dependence.

Put substantive source quotations in separate callouts, including scripture,
hadith, tafsir, scholarly verdicts, lexicons, poetry and historical reports.
Keep one continuous source passage per callout, with meaningful internal
paragraphs. Do not merge distinct reports or scatter one passage into many
boxes. For multi-page passages preserve separate ledger entries and continuous
source identity; no invented joins or silent elision of limiting clauses.
A quotation needs its complete translation and visible citation. Sources with
no Arabic do not acquire fabricated Arabic to satisfy a presentation check.

Separate article introduction, quoted evidence, and interpretation. Follow
`paragraphs.md` for narrator/direct-speech separation and actual blank lines.
Transliteration is a separate layer only for scripture; a lexicon lemma can be
transliterated inline in its translation. Poetry and reports have no separate
transliteration paragraph. The approved master determines all rendered layers.

Name the book in every scripture reference, e.g. Qur'an 16:43 rather than
16:43 alone. When a historical speaker quotes scripture, identify that passage
first and its preserving hadith/tafsir source next. Do not falsely identify a
transmitted paraphrase with a canonical verse or silently replace its wording.

## Scripture and sources outside the corpus

For scripture exhibits use the verified source-language text, its transliteration,
and a complete direct English translation. Do not insert an Arabic Bible layer
or translate Greek/Hebrew/Aramaic/Latin through Arabic. Identify the actual work,
passage, language and edition. Latin is the source for a quoted Latin work or
Vulgate witness, not the original language of a Hebrew/Greek biblical book.
Treat later translations and paraphrases as distinct witnesses, not originals.

Fetch the source edition and retain its raw response and metadata. A named
English edition may be used only after checking its translation basis against
the quoted source; otherwise produce and review a direct translation using
translation.md. Label an original translation as a translation, never as a named
published edition. Do not force an edition choice from a past article. Verify
source text against the archived edition, allowing documented NFC normalization
where needed, never silently replacing a different word or edition.

Scripture alone receives a separate transliteration layer: Qur'an, Bible,
Torah and other actual scripture. Reports, commentary, lexicons and poetry do
not. Transliterate the displayed source wording using one identified convention;
keep inflections and diacritics. Latin already uses Latin letters; its romanized
layer may reproduce that text, not an invented pronunciation. Preserve complete
original and English passages with meaningful paragraphs.

## Significant words across scripture layers

Mark zero, one or two significant lexical terms per quoted passage. Two is a
maximum, never a quota. Each selected term has one matching mark in the original,
one in transliteration, and one in English. Use the smallest faithful rendering;
an English phrase may be necessary for one source word. Do not mark whole clauses,
incidental words, or repeat marks throughout a long passage. Explain the word's
relevance in substantive nearby analysis; highlighting alone proves no lexical
claim. A term that can mean woman or wife must be interpreted in its grammar and
context, not treated as evidence of alteration merely because translations differ.

Use `<mark data-term="1">word</mark>` (and `2` only when warranted) inside
existing quotation paragraphs, including the italic Markdown transliteration.
IDs are scoped to that passage and remain identical across its three layers,
even if word order changes. The HTML converter preserves IDs, words and positions.
Do not add attributes, nested markup, decorative labels or generated tooltip text.
The first term uses a single underline and the second a double underline, with
unchanged readable text color. The mark is presentation: retain unmarked source
bytes in the ledger and strip only this strictly checked markup for comparison.
Do not modify original spelling, punctuation, vocalization or translation to
force alignment. A source or translation correction requires its own review.


For Arabic quotations the corpus exact-slice ledger remains the automated
coverage gate. An external edition with different orthography needs a supported
external-source verification route, not an approximate corpus match. If the
current checker cannot represent a legitimate source, diagnose that capability
gap and add a tested verification path before release; never invent Arabic,
change editions silently, or waive the gate. Retain external file/URL, edition,
page/section and retrieval date with verified source text in the dossier.
Greek/Hebrew and other non-Arabic sources need checks against their originals.

For Christian doctrines consult the indexed Christian collection and relevant
primary fathers, councils, creeds and confessions. Existing reference-search
helpers and indexes are finding aids only; inspect their supported interface
before use. Verify beliefs against their actual holders, not an aggregator.

The site's existing publication convention excludes aggregating/attack-site
names and URLs from the article, metadata, and source footer (answering-islam,
answering-christianity, BibViz, EvilBible, infidels.org, WikiIslam). Preserve such
intake provenance in the dossier. Name the charge generically in reader-facing
prose and cite the primary holder of each substantive claim. Pen-name aliases
require manual checking because names can also belong to legitimate sources.
Apply this before approving the master; the renderer must not delete citations.

## Honorifics

This is the publication's existing editorial convention, not a finding about
any person's historical standing. Apply it to the master before approval.
Keep corpus Arabic unchanged, including its original formulas and punctuation.

| Figure or source formula | Character |
|---|---|
| Prophet Muhammad | ﷺ U+FDFA |
| Male singular, including Imams and Jesus | ﵇ U+FD47 |
| Female singular, including Fatimah and Maryam | ﵍ U+FD4D |
| Plural, the Imams or Ahl al-Bayt | ﵈ U+FD48 |
| alayhi al-salatu wa-l-salam | ﵊ U+FD4A |
| Companion's pleasure formula when source marks it | ﵁ U+FD41 |
| Deceased scholar's mercy formula when source marks it | ﵀ U+FD40 |
| jalla jalaluhu | ﷻ U+FDFB |
| azza wa jall | ﷿ U+FDFF |

Use source-established honorifics consistently on corresponding English mentions;
do not invent them. Legacy (s), (a), (as), and (pbuh) abbreviations are excluded.
Transliteration spells the formula out. The shared translator returns plain
names; the builder applies this convention during assembly and fidelity review.
Markdown uses bare ligatures; HTML wraps them for font rendering without
changing the text, as specified in the website format reference.

The existing site convention omits honorifics from its own English mentions
of Abu Bakr, Umar, Uthman, Mu'awiya, Yazid, Khalid ibn al-Walid and Ibn Abbas,
and figures treated similarly in its Imami editorial convention. Keep their
names bare in headings, cards, tables, prose and decorative translated formulas.
Verbatim Arabic still retains every source byte. Do not omit a prayer or curse
that is substantive evidence rather than a decorative formula. If applying
this convention would change the quoted proposition, retain the evidence and
resolve the presentation/validator conflict explicitly before release.

## Research archives and existing articles

A captured source need not become a displayed quotation. Keep the immutable
research ledger, including Arabic Bible witnesses, in the research dossier.
For a candidate that displays only some captured passages, use citation ledger
schema 2 with an explicit `dispositions` map keyed by every passage ID. For example, the `dispositions` value is:

```json
{
  "greek-corpus-1":{"use":"quotation"},
  "arabic-witness-1":{"use":"research-only","reason":"Retained for comparison; the exhibit uses the independently archived Greek edition."}
}
```

Keep the actual captured objects in `passages`, unchanged.
Every research-only entry needs a substantive reason reviewed with the evidence.
Both uses retain full corpus metadata, page-hash and exact-slice checks. Only
`quotation` entries are required to appear in the note. Schema 1 keeps its old
quote-required behavior and cannot silently accept research-only exemptions.
Do not overwrite old ledgers, automatically demote missing quotations, put
Arabic into hidden HTML, or discard evidence to pass a check. Build a new
candidate ledger and preserve the earlier one.

Archive the displayed Greek/Hebrew/etc. edition separately with actual source
text, identity, locus, URL and retrieval date. The evidence exporter checks the
unmarked displayed scripture original against archived text; an Arabic witness
cannot satisfy that check. Translation and transliteration still need linguistic
review. The exported dossier retains schema-2 dispositions for hosted review.

These are new candidate rules, not authorization to migrate or republish old
notes. A historical note may pass its original corpus check and fail today's
presentation check. Report those distinct results. During an in-progress run,
record the policy change and stop at a draft boundary if it requires source or
translation changes; preserve the existing artifact and receipts. Resume with
a separately verified candidate only within the user's article-editing scope.

External archives retain the source response unchanged. JSON verse-list and
simple Tanach XML decoding and NFC comparison are presentation operations over
retained raw bytes. Do not strip joiners, change vowel points, insert missing
letters or combine editions to make a displayed quotation match. A corrected
or composite transcription is editorial material, not an untouched external
witness. Preserve it separately with its differences; recapture and cite an
actual source supporting the displayed original, or report the mismatch. A URL
and a recomputed hash alone cannot authenticate an edited archive.
