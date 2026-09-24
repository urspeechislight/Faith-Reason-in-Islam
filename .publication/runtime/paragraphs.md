# Paragraphs and quotation boundaries

Apply while drafting the Markdown master and while translating source units.
Paragraph structure belongs to the source artifact, before the prose baseline;
the website preserves it. Do not defer paragraph decisions to HTML conversion.

## Write in meaning units

Give each paragraph one main thought. Start another for a new claim, example,
objection, inference, qualification that needs its own development, or change
of speaker. Two to four sentences often work for exposition; a short paragraph
may contain one. Review a dense paragraph around 100 words for a useful break,
but do not split mechanically at a count or put every sentence on its own line.
Use normal sentence punctuation and spaces within a paragraph. Use a blank
line between Markdown paragraphs; a single newline usually renders as a space.

Keep the article author's introduction, source quotation and explanation in
separate blocks. A quotation may contain its own narrator and direct speech:
paragraph those separately at natural boundaries within the same source callout.
Do not move the source narrator into the article author's voice. A necessary
short speech tag may stay with its speech. A new speaker starts a new paragraph.
Use quotation marks to distinguish direct speech from the surrounding translated
narration; do not wrap all narration in another pair of quotation marks merely
because it is a translation. Preserve quotation marks in a verbatim edition.
Never add a speaker, speech, punctuation inside the Arabic, or an explanatory
bridge just to make the layout work.

## Author callouts with paragraphs already present

Inside a Markdown callout, separate paragraphs with a line containing only `>`.
Keep a real blank line before and after the whole callout. Keep citation title,
original-language paragraphs, any required transliteration, and translated
paragraphs distinct. Preserve the complete original and complete translation.
Translations use `\n\n` paragraph separators in the translator's JSON strings.
Map them to `>` separators; do not join all lines into one string when assembling.

The following is a structural English-only illustration, not a historical quote:

```markdown
The author identifies a disagreement about the report.

> [!note]- Source title, edition and page
> [Verified original-language paragraphs are inserted here.]
>
> The witness described the meeting.
>
> > The judge said, “Read the document aloud.”
>
> The witness read it and then answered the question.

The report establishes that the document was read. It leaves its date uncertain.
```

Use `> >` for direct speech inside the source callout, with a quoted blank line
before and after it. Keep the isnad and narration at `>` depth; keep a short
speech tag with its speech when that reads naturally. Consecutive speech
paragraphs may share one nested quote. Use one extra level, even when speech
contains another quotation: retain its quotation marks without making a staircase
of progressively narrower text. Preserve every source word and its order.
The renderer does not infer speakers or repair mixed narration and speech.
A long transmission chain joined to direct speech must be separated in the master
before review. Translators must mark these boundaries while translating, not
leave them for the publication agent to discover.

A long source passage remains one callout with several paragraphs. Split where
meaning or the speaker changes, keeping original-language slices contiguous and
unchanged apart from permitted layout whitespace. Never split at every period:
abbreviations, reference numbers and a quotation's syntax need review. Keep
transmission chains and their attribution clear without dropping names.

## Preserve the structure in HTML

Map each source/translation paragraph to its own `<p>` inside the callout;
use `<cite>` for the citation and `<blockquote>` for the source container.
Nested `> >` paragraphs map to a `blockquote.source-speech` with
`data-quote-role="speech"`; its inner paragraphs remain inside the outer source.
The handoff preserves this hierarchy as well as the paragraph text.
Do not replace paragraphs with repeated `<br>` tags, inline spans or one large
`<p>`. Keep narrative framing and direct speech in their source-defined order.
Do not invent new paragraph boundaries during conversion: fix the Markdown
first, then regenerate its review/handoff when necessary.

Include explicit paragraph margins; line-height alone spaces lines, not
paragraphs. The publication template should supply these rules after resets:

Use the shared `quotation.css` embedded in both publication templates. Its
language-specific values and insets are described below; do not duplicate
competing defaults here.

These are template defaults, not a reason to restyle existing articles during
an unrelated task. Preserve existing typography and do not put implementation
instructions in the article itself. Check the rendered draft at mobile and
desktop widths; literal blank lines in HTML do not create visible margins.

## Check before proceeding

After each section, inspect prose with callouts collapsed and one long callout
expanded. The reader should see paragraph breaks, where quotation begins and
ends, speaker changes, and where the author's analysis resumes. Check long
paragraphs by meaning; do not shorten evidence to satisfy a length target.

Version-3 and version-4 handoffs record callout paragraph boundaries and reject merging,
splitting or reordering them, even if the flattened words are unchanged. They
also reject mapped prose blocks rendered as inline elements. Version-2 receipts
remain valid for existing artifacts; a repair should create a fresh version-4
handoff. This check preserves authored structure; it does not judge whether the
initial paragraph divisions or CSS are good. Source fidelity and rendered
inspection remain necessary.

## Required quotation review and rendered evidence

Protected text is protected from casual rewriting, not exempt from inspection.
Review every source callout for meaningful paragraph boundaries, identified
speaker changes, quotation nesting and complete opening/ending clauses. Original
Arabic paragraphs may be laid out with whitespace only after source verification;
translations may be reparagraphed without shortening their content. Correcting
translation punctuation or a clipped passage is a source-stage revision before
a fresh editorial baseline, not a waiver of the protected-text check.

`quote_layout.py` inventories all callouts, including their protected paragraphs.
Its density, quotation-wrapper, nesting and unfinished-tail cues require a
located decision. They are review triggers, not automatic edits or word limits.
In particular, a 311-word narrative containing a creed, witnesses, a release,
and a subsequent complaint needs inspection of those actual transitions; a
claim that its words match the receipt does not answer the layout question.

The final review record must include every `quote_layout_review` row generated
by review.py inspect. Describe paragraph boundaries, speaker/quotation boundaries
and source completeness for the actual callout. Remove defects and regenerate
the record; a cue that remains needs a passage-specific legitimate reason.
Do not mark a clipped translation legitimate merely because the captured slice
also ends there. Inspect adjacent source pages before deciding the source is
itself incomplete. Preserve genuine incomplete source text with an explanation.

For HTML with source callouts, capture browser evidence for the exact candidate:

```bash
python3 ~/.agents/prose/quote_layout.py capture ARTICLE.html --output RENDER.json
```

This requires Playwright and Chromium, measures every callout at desktop and
mobile widths, expands native details, and saves screenshots. It verifies
visible paragraphs, at least 8px between ordinary callout paragraphs, compact
4–12px gaps around same-language nested speech, and no
page-wide horizontal overflow. Use the screenshots for the human layout review;
positive margins cannot prove that a single paragraph is well organized.
Then pass `--render RENDER.json` to review.py inspect. Its final verification
and the outgoing-commit gate reject missing, stale or incomplete measurements.
A passing handoff cannot replace quotation review or browser evidence.

## Quotation inset and compact rhythm

All displayed quotations need an inset from surrounding prose, including inside
callouts. Keep the source citation at the callout's normal inner edge; inset
original, transliteration and English paragraphs by 12–16px. Outside callouts,
use a 20–24px inset. Retain quotation marks for direct speech inside a source and
use meaningful speaker paragraphs. Never add whitespace to the stored source
merely to simulate indentation. Insets are CSS, applied in the text direction:
Arabic/Hebrew from the right, English/Greek/Latin from the left.

Use line-height 1.55–1.6 for English quotations, 1.7 for main prose, and 1.85–2.0
for Arabic (check the actual vocalized font). Keep quotation text at normal
reading size. Use paragraph gaps around .7em and a larger 1em gap between original,
transliteration and translation. Avoid full justification. On narrow screens
reduce the inset to 12px without shrinking text. Inspect long quotations and
multiple speakers on desktop/mobile, in print and without JavaScript.

Source paragraph visibility and spacing checks are supplemented by actual inset
and line-height measurements. No generated labels, color legend, hover-only
explanation or reader-facing typography commentary is needed. See
article-sources.md for lexical marks, which stay visible in print.

Inside a callout, nested speech adds only 12px of padding and a subtle 1px
rule on its reading edge. Use 6px gaps around speech and between its paragraphs,
with English line-height 1.55. Keep the existing larger gap between language
layers. No empty spacer paragraphs, large quote margins, or additional quote
cards. Browser checks require an extra speech inset of 8–20px and reject gaps
above 12px between same-language narration and speech. Inspect the boundaries,
not just the outer callout's padding.
