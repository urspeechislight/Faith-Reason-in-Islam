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

Both historical template names (`template-tabs.html`, `template-flowing.html`)
use the same maintained reader layout. Creation and repair always regenerate
from canonical Markdown with `article_build.py`; never copy a published page's
shell or construct a run-local generator. The reference is
https://sun-moon-twelve-stars.mr-famzy.chatgpt.site/ (version 6), with the
Faith & Reason palette and a Back link replacing Original article.
`reader.css`, `reader.js`, and `render_article.py` own this format.
Preserve approved master text, paragraph boundaries, mapped block IDs and
source-note-sha256. Layout supplies interface labels only; no invented prose.

Map category to `<main data-category="debate|exegesis|narration|commentary">`
using the actual category. Map the master's opponent for applicable debates.
The shared structure file governs content and heading order. Existing reference
pages illustrate design, not authority to copy their prose or old rules.

Use [the repeatable build procedure](../../../prose/article-build.md) and
article_build.py for conversion. Run-local generators and old-page shell copying
are unsupported. Fix shared layout once in the maintained template/CSS/renderer,
then regenerate and preflight before review.

## Rendering specification

- **Typography:** Inter body; Literata headings and English quotations; Amiri
  Arabic; Scheherazade New honorifics. Preserve actual language and direction.
  Body is 17px/1.85, English quotations 17px/1.9, Arabic 24px/2.1. Use the
  shared stylesheet, including its narrow-screen sizes, without local overrides.
- **Colors:** paper #FDFBF7, ink #3D4451, muted #6B7280, accent #8A6D3B,
  hairlines #E7E0D1. Reports retain #F8F1E2 with #E9DCC3 borders; scripture
  retains #F3F5F7 with #DFE4EA borders. Preserve original Faith & Reason colors.
- **Shell:** wide masthead and title area (1320px maximum); category eyebrow,
  canonical title and optional canonical summary. Reading grid has a 244px
  sidebar and article column up to 760px, with numbered chapter navigation.
  Sidebar sticks on desktop. Below 760px use collapsible mobile contents.
- **Navigation:** chapter labels and links come from actual master headings.
  Scroll-spy marks the current chapter. Deep links open containing details.
  Both Back links go to the distinct HTTP(S) referring page when available;
  direct visits fall back to index.html. They must work without JavaScript.
- **Premises and conclusion:** open two-column premise grid on wide screens,
  one column on narrow screens. Preserve authored claims and exact closing.
  A summary caption identical to its section heading shares that visible label;
  other captions remain visible. No fabricated premise titles or recaps.
- **Facts:** canonical Markdown tables become numbered native details rows.
  The claim is the summary; Actor, Date, Place, Source and Qualifier remain
  separately labeled expanded fields, with the original supporting-passage
  link. Every cell, its order and link are checked against the master. Other
  tables remain tables. The fact index reads this same canonical projection.
- **Quotations:** one source passage stays in one square tint callout, with
  source label, source-defined paragraphs, and citation separated by a rule.
  Desktop padding is 32px horizontally, mobile 20px. Explicit nested Markdown
  `> >` identifies the entire matn; `>` holds its isnad. Render chain and matn
  as separate labeled units with the chain rule and distinct typography from
  the reference. Preserve nested dialogue boundaries and all source text.
  Never infer Arabic boundaries, merge paragraphs or add transliteration to
  reports. Scripture remains original → transliteration → English.
- **Source roles:** only canonical source callouts carry data-content-role=source.
  Interface labels have enumerated data-reader-ui roles validated separately;
  they cannot hide authored text or grant a quotation exemption.
- **Open reading:** article sections remain open. Facts, glossary and narration
  commentary can use native details, which work without JavaScript. Print
  expands disclosure content. All IDs are unique. No tabs or invented sections.
- **Footer:** site brand, current year, rights notice and Back link. Chrome stays
  outside mapped article content. Source marks and lexical underlines are kept.

These are the `reader-v1` visual rules. Older quotation.css measurements remain
for verifying legacy pages only; do not layer them over reader.css. A format
upgrade requires a new render/preflight and visual review. Unchanged canonical
prose and source evidence retain their separate review lifecycle.

## Mapping details

- Convert a report callout to blockquote.hadith-callout and scripture to
  blockquote.quran-callout. A master callout's paragraphs become separate p
  elements within its mapped blockquote; its title becomes cite with
  data-note-citation. Do not flatten source and translated paragraphs.
- Wrap every honorific ligature in span.honorific, including within Arabic.
  The class uses Scheherazade New; markup changes no underlying source text.
- Map master fact lists into premise-card elements. Facts tables in section#facts
  use the checked disclosure mapping described above, with resolved detail links. Preserve qualifier wording exactly.
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
before review; its final verify checks master and HTML approval together. The native inherited-model reviewer supplies the final release decision; CI
verifies its bindings without calling an external provider. A separate
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

Both templates use reader.css and reader.js. Test real fonts at desktop and
narrow widths, expanded facts, chain/matn distinction, source layers, and linked
term underlines. Workflow maintenance does not authorize article publication.
