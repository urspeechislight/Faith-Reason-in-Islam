# Research framework

The full evidence order and method behind core sections 2 through 6.
This is the research layer. The shared `~/.agents/prose/article-workflow.md`
owns verification before either saving or publishing; destination references
own Markdown and HTML layout.

## 1. The research map

Before collecting evidence, write down:

1. the exact question (one sentence, question form);
2. the intended thesis (one sentence);
3. the strongest opposing thesis, when one exists, in its own terms;
4. the audience and the premises the argument may assume (an article
   addressed to readers who accept the Qur'an as Allah's word may cite
   it as evidence; an article addressed to a general audience may not);
5. the exact holder of each disputed claim: which school, author,
   denomination, council, century;
6. the conclusions that would overreach the evidence;
7. the terms, verses, reports, or historical claims that carry the
   dispute.

For debate mode, formalize the opponent's strongest case as numbered
premises plus a conclusion. The article answers that construction, not
the popular form of the charge, unless the two genuinely differ and the
difference is itself worth exposing.

## 2. The claim-evidence map

Matrix columns:

- **Claim**: one load-bearing assertion the article makes.
- **Type**: lexical, grammatical, Qur'anic, riwa'i, historical,
  theological, philosophical, or logical.
- **Evidence needed**: what would establish the claim.
- **Best source**: the strongest holder of that evidence, at its
  narrowest attribution.
- **Qualifier**: the hedge the source itself carries, verbatim.
- **Opponent reply**: the best countermove against this claim.
- **Status**: `grounded` (primary source verified), `partial`,
  `inference` (the article's own reasoning, explicitly marked), or
  `open` (unresolved; listed in the handoff).

Rules:

- Every major paragraph of the final article corresponds to a row.
- Every load-bearing claim is grounded or explicitly marked inference.
- Before drafting, connect each claim to evidence and its warranted inference.
  A source survey may have independent findings; do not force a next-question
  handoff between them.
- A claim with no evidence and no inference status is deleted, not
  kept because it sounded strong in draft.

### Scope audit

Run before and after drafting. The standing errors:

- evidence about Ash'ari kalam widened to "Islam";
- evidence about one Calvinist confession widened to "Christianity";
- one tafsir's gloss widened to "the school";
- one narrator's report widened to "Sunnism";
- one philosopher's system widened to "all scholars";
- a modern polemic's charge widened to the scholarly form it cites.

Match every conclusion's subject to the evidence's subject exactly.
Where the audience will hear the wider claim, state the narrow one
explicitly and say why the widening fails.

### Qualifier taxonomy

`stated` (the source asserts it), `reported` (a narration carries it),
`attributed` (a secondary source credits it), `likely` (the article
reasons to it), `disputed` (sources disagree). A hedged source sentence
never becomes a bare claim; the hedge is payload, because a flattened
claim is a gift to the opponent.

## 3. The evidence order (the Imami reading)

Default order unless the subject requires another:

1. **Qur'an.** The full local context plus relevant cross-passages.
   Establishes what the passage says, not yet what anyone reads into it.
2. **Riwa'i tafsir of the Ahl al-Bayt.** Tafsir al-Burhan, Tafsir
   al-Qummi, Tafsir al-Ayyashi, Majma' al-Bayan, Nur al-Thaqalayn:
   reports explaining the verse or concept from the Imams.
3. **Hadith and doctrinal reports.** Al-Kafi, al-Tawhid, Ma'ani
   al-Akhbar, Bihar al-Anwar, Wasa'il al-Shia: especially reports that
   define the theological distinction at issue.
4. **Early Imami scholars.** Al-Saduq, al-Mufid, al-Tusi, al-Tabrisi,
   al-Sharif al-Murtada as the subject requires.
5. **Later Imami scholarship and philosophy.** Al-Tabataba'i and after:
   clarify, systematize, or expose legitimate internal variation.

What each layer can and cannot do: the Qur'an fixes the wording and its
construction; riwa'i tafsir fixes how the school received it; hadith
carries the doctrinal boundary; scholars systematize; philosophy
organizes. No layer silently upgrades to another's authority.

Keep five distinctions visible in the draft at every step:

1. what the Qur'an explicitly says;
2. what a narration explicitly says;
3. how an exegete reads it;
4. how a theologian systematizes it;
5. what the article itself infers.

Do not flatten disagreement. When sources differ in explanation but
share a narrower boundary, state the convergence at that boundary and
name the variation above it.

Corpus discipline: pull every record verbatim from the corpus on titan
(search the FTS5 index, note title, volume, page). Real book titles
only, never corpus bucket labels. The shared workflow byte-verifies
every Arabic block before saving or publishing; the research layer supplies exact
records so that verification can pass.

## 4. Lexical grounding

The trigger is a contested word: someone's case depends on reading it
one way and an opponent reads it another, or a circulated rendering has
shifted, softened, or inverted the source language. Words merely quoted
in passing, technical terms, and undisputed vocabulary get no lexicon
treatment. A typical article carries one to three contested words.

### Construction first

The contested unit is the word as built and as placed, not the root.
Check before opening the lexicons:

- **Derivation and pattern.** The root's entry does not settle a
  derived form's sense; fa'il, maf'ul, if'al, tafa'ala narrow or shift
  it.
- **Attachment (`wa-`, `fa-`, or nothing).** A clause joined by wa- can
  share the previous clause's subject, condition, or qualification. An
  English rendering that starts the clause fresh has already taken a
  side.
- **The implied pronoun and its antecedent.** Arabic carries the
  reference in the verb; naming it wrongly is how a rendering smuggles
  a conclusion in.
- **Ellipsis.** The classical exegetes read an elided word back in; the
  elision is often where two camps diverge.
- **Restriction scope.** What the la- or illa- restricts, and what it
  leaves unrestricted, is a lexical question before a doctrinal one.

### Then the lexicons

Lisan al-Arab, al-Qamus al-Muhit, al-Sihah, Tahdhib al-Lughah,
Maqayis al-Lughah, al-Ayn. Two lexicons when the camps dispute the
sense; one when a rendering simply ignores an undisputed meaning. Pull
definitions verbatim from the corpus.

### Then usage witnesses

Classical poetry proves the definition lived in the language: Imru'
al-Qays, Zuhayr, al-Nabigha, al-A'sha, Labid, Hassan ibn Thabit,
al-Farazdaq, Jarir, Dhu al-Rumma. The witness must actually contain
the word in the disputed sense, and the article says so in plain
English. If no clean witness exists, say so and stand on the lexicons;
never bend a verse to fit.

### Then cross-usage, then context

Survey Qur'anic cross-usage without assuming one occurrence fixes every
other occurrence. State the semantic range first, then argue which
sense the local context selects.

The standing limits: lexicons establish the available language and the
burden of proof; context establishes the intended sense. Never claim a
dictionary makes figurative, technical, or theological usage
impossible.

### Other languages

The same discipline with that language's authorities, fetched
programmatically and cited by entry:

- **Hebrew**: BDB, HALOT, Gesenius; masoretic pointing and the
  Septuagint as early witnesses; Tanakh usage before the contested
  verse.
- **Greek**: BDAG, Thayer, LSJ; a New Testament usage survey plus a
  classical author's line; note the Septuagint's choice.
- **Latin**: Lewis and Short or the Oxford Latin Dictionary; classical
  usage as the witness.
- **English itself**: the OED entry with dated citations; the King
  James translators' own range is evidence, not authority.

Construction parallels apply (Hebrew waw-consecutive, Greek participle
chains and article presence, Latin accusative-with-infinitive). Quote
in the original script with translation and needed lemma transliteration inline, and cite
entry numbers precisely (BDB 210b, not "BDB says").

## 5. The thread of reasoning

Use `~/.agents/prose/contract.md` and `drafting.md`. Order evidence so the reader
can follow the reasoning. Explain each necessary inference once, beside the
source. A self-contained section can open with its evidence and finish when its
point is complete. Do not require emphatic closers, backward links or previews
around every exhibit. Cut redundant introductions and recaps before adding a
transition. A missing logical step needs an explanation of that step.

## 6. Source records

For each primary record preserve, when supplied and relevant: speaker;
narrator or chain; the complete passage needed for the argument; source
title; volume, page, chapter, or report number; grading or attribution
caveat; and the nearby clause that limits or explains the quoted line.

Never reduce a useful report to a rhetorically convenient fragment. The
Arabic script is copied verbatim from the source record; the research
layer never composes or edits Arabic. The translation accounts for the
full quoted extent (see `prose-translation.md`).
