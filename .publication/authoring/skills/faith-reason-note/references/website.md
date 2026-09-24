# Website rendering and publication

Read only when the requested deliverable includes website output or preview.
Research, writing, source checks and editorial/council approval occur once in
`~/.agents/prose/article-workflow.md`. This file owns destination mechanics.
Read applicable website repository instructions on Titan before operations.

## Repository and templates

Authoritative repository: `/home/fahmy/code/Faith-Reason-in-Islam`, normally
main/origin, GitHub Pages at https://urspeechislight.github.io/Faith-Reason-in-Islam/.
From the Mac use `titan-project -C /Users/me/code/Faith-Reason-in-Islam -- ...`.
Inspect actual branch/remotes/status and catalogue before changes. Preserve
existing slugs and URLs; do not rename an article to create a second version.

Use `../template-tabs.html` for open sectioned pages (the filename is historical,
not permission to create tabs) or `../template-flowing.html` for a single thread
and narration. These paths are relative to this reference. Templates provide
layout only. Preserve all approved master text and paragraph boundaries through
handoff.py version 4, with mapped block IDs and source-note-sha256 metadata.
Do not add template prose, extra headings, duplicate cards, or silently remove
quotations. If a template or validator conflicts with the master, resolve the
format issue or revise/review the master first. Never rewrite only the HTML.

Map category to `<main data-category="debate|exegesis|narration|commentary">`
using the actual category. Map the master's opponent for applicable debates.
The shared structure file governs content and heading order. Existing reference
pages illustrate design, not authority to copy their prose or old rules.

Use [the repeatable build procedure](../../../prose/article-build.md) and
article_build.py for conversion. Run-local generators and old-page shell copying
are unsupported. Fix shared layout once in the maintained template/CSS/renderer,
then regenerate and preflight before review.

## Rendering specification

- **Fonts** (loaded in `<head>`, never substitute): Inter for body,
  `font-serif` = Playfair Display for headings, `font-amiri` = Amiri for
  Arabic, and 'Scheherazade New' for honorific ligatures per article-sources.md and the font rules below. (If a note ever contains Hebrew, class
  `font-hebrew` with 'SBL Hebrew'; Greek stays Inter.) Arabic paragraphs
  carry class `rtl` with `lang="ar"`, and the page CSS must include the
  `.rtl { direction: rtl; text-align: right; }` rule: `lang="ar"` alone
  does not set direction, and without the rule the Arabic renders
  left-justified (the validator fails the build on it).
- **Palette**: background `#FDFBF7`, body text `#3D4451`. The site has ONE
  accent system, hardcoded in the templates: `#B99C6B` for decoration only
  (borders, active-tab underline, the verdict rule) and `#8A6D3B` for
  anything read as text (headings, active-tab label, kicker). No other
  accent exists. Terracotta (`#A43820`), red text (`text-red-*`), and red or
  amber backgrounds (`bg-red-*`, `bg-amber-*`) are banned everywhere.
- **Callouts are tint boxes, never side stripes.** `quran-callout` (bg
  `#F3F5F7`, full 1px border `#DFE4EA`) for Qur'an quotes; `hadith-callout`
  (bg `#F8F1E2`, full 1px border `#E9DCC3`) for hadith, tafsir, and
  scholarly narrations. No `border-l-4` accent stripes anywhere on the
  page. Premise cards in the intro section use class `premise-card`
  (neutral tint `#F7F4EC`, border `#E7E0D1`); the conclusion premise card
  uses `conclusion-card` (warm tint, border in `#B99C6B`). Hairline
  borders everywhere are `#E7E0D1`, not Tailwind's `border-gray-200`.
- **Consolidate parallel exhibits.** When two or more quotations answer the
  same question in the same way (two lexicons on one word, two poems on one
  construction, two dictionary entries making the same point), place them
  side by side under ONE card in ONE visual unit, or present them in a
  comparison table with columns per source. Never stack three sequential
  card-plus-quote pairs that could be one side-by-side unit. The reader
  sees the convergence at a glance, and the page shrinks.
- **Quote blocks**: one continuous passage of one source is ONE callout; a second callout for the same passage is a defect. Every quoted text follows this exact shape. The default
  (hadith, tafsir, scholarly, historical) is three parts:
  ```html
  <blockquote class="hadith-callout" data-content-role="source" data-note-block="SOURCE_BLOCK_ID">
      <p class="rtl font-amiri text-xl" lang="ar">ARABIC</p>
      <p class="translation">The source narrator’s words in translation.</p>
      <cite data-note-citation class="text-sm text-gray-500">- Source, Vol. X, p. Y</cite>
  </blockquote>
  ```
  Every scripture callout renders the master's transliteration between
  original text and translation as shown below. For Bible exhibits preserve
  their approved language/edition layers from article-sources.md. Report
  callouts have no added transliteration layer:
  ```html
  <blockquote class="quran-callout" data-content-role="source" data-note-block="SOURCE_BLOCK_ID">
      <p class="rtl font-amiri text-xl" lang="ar">ARABIC</p>
      <p class="italic transliteration">Transliteration.</p>
      <p class="translation">"Translation."</p>
      <cite data-note-citation class="text-sm text-gray-500">- Source, Vol. X, p. Y</cite>
  </blockquote>
  ```
- **Content roles:** only mapped source callouts carry `data-content-role="source"`.
  Table prose, premise/conclusion cards, and ordinary authored blockquotes remain
  in the prose inventory. Language and translation CSS classes cannot exempt
  authored text. The handoff rejects source roles outside the master's callouts.
- **Long callouts preserve source-defined paragraphs.** Follow
  `~/.agents/prose/paragraphs.md`: separate narrator framing and direct speech
  at meaningful boundaries, keep one source passage in one callout, and map
  every original/translation paragraph to its own `<p>`. Include explicit
  margins between paragraphs. No mechanical two-sentence splitting or invented
  Arabic punctuation. Fix missing paragraph breaks in the master before making
  the handoff; conversion preserves them. One `<cite>` per callout.
- **Page chrome**: back-nav, left-aligned Playfair title and approved subtitle,
  compact margins and hairline rule. Use `max-w-4xl mx-auto`, not the full-width
  container. Keep the category's actual master sections and headings.
- **Navigation**: sticky section nav (`position: sticky; top: 0`, background
  #FDFBF7, hairline bottom border, nav with aria-label), one horizontally
  scrollable row on mobile. Link only existing master sections. Use numbered
  labels where the sections are numbered, no emoji. With more than five links,
  use text-sm md:text-base. Targets have scroll offsets; scroll-spy sets
  aria-current="location". Use the template script, not custom content hiding.
- **Open content**: no JS-toggled tabs or accordion sections. Only Glossary and
  narration Commentary use native details. Print hides sticky nav and opens
  details. Find-in-page, reader mode and no-JS must expose article content.
- **Alignment**: left-aligned headers, sections and closings. No text-center
  before the footer except chart-node diagram boxes and chart-arrow rows.
- **Closing style**: retain the master's exact heading and content. Use the
  short accent rule, Playfair heading and max-w-3xl for the appropriate category
  closing. Conclusion prose uses font-semibold text-gray-800; accent color is
  for headings and labels, never conclusion paragraphs.
- **Quote classes**: use the current canonical classes above, not quote-original,
  quote-translit, quote-translation or font-arabic. Category anatomy and heading
  layers come from article-structure.md, not from an old model page.
- **Footer**: use the current year and `Faith & Reason in Islam · All Rights
  Reserved`. Keep site chrome outside mapped article content.
- IDs are unique across the page. A heading cannot be invented, renamed or
  duplicated during conversion to satisfy a layout pattern.

## Mapping details

- Convert a report callout to blockquote.hadith-callout and scripture to
  blockquote.quran-callout. A master callout's paragraphs become separate p
  elements within its mapped blockquote; its title becomes cite with
  data-note-citation. Do not flatten source and translated paragraphs.
- Wrap every honorific ligature in span.honorific, including within Arabic.
  The class uses Scheherazade New; markup changes no underlying source text.
- Map master fact lists into premise-card elements and real lists/tables without
  inventing or duplicating text. Facts tables live in section#facts, with tint
  styling and resolved detail links. Preserve qualifier wording exactly.
- Bible original Greek uses lang="grc";
  Hebrew uses font-hebrew and lang="he". Preserve the master's edition-cited
  layers. The source standard governs which layers exist, not a template.
- A Christian debate's existing comparison becomes section#comparison. A
  contested-words summary needs its lexical evidence in the same section.
- Narration Commentary uses one native details holding anchored commentary-card
  units; narrative links open the parent and scroll to the card on load and
  hashchange. Keep provenance together. Use tint boxes for speech; the old
  divine-speech side-stripe pattern is retired. Preserve the approved text.
- Facts anchors use sticky-nav scroll offsets and focus management. Serial
  links map through the handoff's note_map/anchor_map after checking targets.
  Keep images self-hosted under images/, with appropriate license attribution;
  do not hotlink. Images must not hide or replace mapped source content.

## Validate the conversion

Run `python3 ~/.agents/skills/faith-reason-note/validate.py --selftest` once per
session. article_build.py preflight validates the conversion and browser geometry
before review; its final verify checks master and HTML approval together. For the
hosted route it defers only the final release decision to GitHub. A separate
review.py pass without its required handoff cannot replace combined verification.
Inspect desktop/mobile rendering, paragraph spacing, expanded/collapsed content,
anchors, RTL, print and no-JS visibility. article-polish supplies the visual
review procedure. A passing text hash does not prove visual quality.

The HTML validator owns mechanical enforcement and its selftest fixtures.
Generated index pages have their existing structural/prose exemptions; source
and aggregator restrictions still apply. A requested repair must not use the
legacy-page exemption to release changed content without current review.

## Publish within the request

After final approval, write the checked HTML and commit its handoff, baseline,
and review under `.prose-reviews/<slug>.*.json` as specified by the shared
workflow. Add a new article to the appropriate DOMAIN_MAP and BLURB in
`gen_catalog.py`, with TITLE override only if necessary. Run gen_catalog.py;
never hand-edit the embedded catalogue in index.html. Battle/serial membership
may come from hub links; inspect the current generator and update the hub.
Regenerate facts.html from article Facts blocks when applicable, never hand-copy
rows. Preserve unrelated generated-index entries.

Inspect Git status and upstream before staging. Preserve unrelated changes;
use a fresh isolated Titan worktree from fetched origin/main for each publication. Do not stash, reset, or include someone
else's work merely to obtain a clean tree. Stage only this publication and its
required generated files/receipts. Synchronize without discarding work, commit,
and push a publication branch through the protected PR/check path within the
user's publication request. Use the urspeechislight identity. Never force-push
or disable branch protection to bypass a failure. On rejection,
inspect the remote state before a bounded rebase/retry; stop on a conflict
requiring a user decision. The pre-push gate must pass on the outgoing commit.

Verify the deployed revision with handoff.py against the committed receipt.
Inspect the Actions run: queued/running deployment is pending; a failed gate
and skipped deployment need correction, not repeated sleeps or propagation claims.
For a defective deployment, inspect the responsible commit before proposing or
performing an authorized targeted revert; never blindly revert HEAD.

## Scripture languages and lexical tracing

Apply article-sources.md to all new scripture exhibits: actual source language,
transliteration, then English; no automatically inserted Arabic Bible layer.
Each original paragraph has its real lang (grc, he, arc, la, ar, etc.). English
translation paragraphs use lang="en"; their transliteration counterpart is a
separate p.transliteration. Keep Hebrew/Aramaic RTL and Greek/Latin LTR. Preserve
`<mark data-term="1|2">` exactly from the master. Never infer terms during HTML
conversion. At most two IDs per passage, each present once in all three layers.
The handoff checks their text and offsets as well as all ordinary source text.

Both templates include shared quotation CSS: compact English line height,
roomier vocalized Arabic, paragraph gaps, directional insets within callouts,
and printable single/double underlines for linked terms. Keep citations at the
callout's normal edge. Test the actual font and narrow viewport; do not replace
visible emphasis with a hover interaction. These rules do not authorize editing
or publishing existing articles during workflow maintenance.
