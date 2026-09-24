# Markdown master and optional Obsidian delivery

Read when constructing or validating the canonical master for either destination.
`~/.agents/prose/article-structure.md` owns category anatomy;
`article-sources.md` owns citation and honorific rules. This file owns Markdown
syntax and optional vault delivery. Canonical masters live on Titan, not in the
vault. Do not run a separate note-writing cycle for website requests.

## Vault facts

- Vault root:
  `/Users/me/Library/Mobile Documents/iCloud~md~obsidian/Documents/ob-main/Obsidian Vault/personal/islamic/`
  (referred to below as `$VAULT`). Read/write with the normal tools.
- Folder taxonomy (exactly one per note, chosen during planning):
  - `01-method-and-apologetics`: method, epistemology, the affirmative case
  - `02-tawhid-and-theology`: divine unity, attributes, theology
  - `03-prophethood-and-revelation`: prophethood, finality, revelation
  - `04-quran-tafsir`: exegesis of specific verses, alleged-error rebuttals
  - `05-imamah`: the imamate, wilaya, the Ahl al-Bayt
  - `06-christianity`: Christianity, Trinity, gospels
  - `07-history-and-sira`: history, life of the Prophet, historical objections
  - `08-cosmology-unseen`: cosmology, the unseen, esoteric narrations
  - `eschatology`: death, barzakh, resurrection, the last day
  - `_attachments` (images), `_drafts` (working material), and `_reference`
    are not destination folders.
- Filename convention: the note's title in Title Case (the existing vault
  convention, e.g. `Why Imam Ali Did Not Fight for the Khilafa.md`). Never
  rename an existing note: backlinks, indexes, and memory of paths all break.
  `ls` the destination folder before creating; never duplicate an existing
  title.
- The corpus lives on titan (`ssh -i ~/.ssh/titan_key titan`, repo
  `~/code/islamic`). Citation resolution, commentary grounding, and every
  byte-verification run against it.
- **Vault verification is explicit.** Run the shared source checks and final review check
  regardless of the host application. Claude Code may additionally run
  `~/.claude/hooks/islamic_note_gate.py`; Kimi does not inherit Claude hooks.
  Hooks are supplementary and do not replace verification of the final file.
- Legacy notes are frozen: never restyle their prose as a side effect of
  filing a new note. The validator runs on new notes only.

## Note formatting (the vault's rendering of the site design system)

- **Quote blocks**: every quoted text follows this exact shape. The default
  (hadith, tafsir, scholarly, historical) is three parts, a collapsed
  callout whose title line is the citation:
  ```markdown
  > [!info]- Imam al-Sadiq ﵇, al-Kafi, vol.1, p.123
  > اللغةُ العربية
  >
  > The source narrator’s words in translation.
  ```
  Scripture quotes add an italic
  transliteration layer between the verified original language and English translation (four parts) and use
  the scripture callout type:
  ```markdown
  > [!quote]- Qur'an 16:43
  > فَاسْأَلُوا أَهْلَ الذِّكْرِ
  >
  > *fa-s'alū ahla al-dhikri*
  >
  > "So ask the people of the reminder."
  ```
  The trailing `-` keeps the callout collapsed so long notes stay compact;
  the reader expands what they need. The citation title is visible while
  collapsed, so every callout is self-describing.
- **Report callout color taxonomy.** The site renders every hadith, tafsir,
  scholarly, and historical quote in one warm callout; the vault's native
  callout system supports a finer semantic split, so the default (three
  part) callout is typed by the report's content, not its source work:

  | Callout type | Category | Use for |
  |---|---|---|
  | `[!info]-` | Imam hadith | Reports narrated **from an Imam** of the Ahl al-Bayt (the Imam's own words, rulings, or commentary). The title should name the Imam. |
  | `[!note]-` | Virtue / biography / history | Reports about a person's virtues, character, biography, genealogy, historical narrations, or any content not covered by the other types. The catch-all. |
  | `[!tip]-` | Scholarly verdict | A scholar's or theologian's analytical verdict, tafsir reading, theological argument, or bibliographic survey. |
  | `[!warning]-` | Minority / rejection | Minority positions, rejected opinions, or reports of faults and lapses. |

  Classify by the report's content, not by the source work: a hadith from
  Imam al-Sadiq inside al-Kafi is `[!info]-`; a biographical description in
  Bihar al-Anwar without an Imam as the direct speaker is `[!note]-`; a
  scholar's verdict in a tafsir work is `[!tip]-`. One report per callout;
  never bundle two reports into one block. The scripture callout
  (`[!quote]-`) is reserved for scripture, the class that carries transliteration; it is the vault's
  equivalent of the site's `quran-callout` and is never used for other
  content.
- **Structural callouts**: the debate intro's premises live in one open
  `> [!abstract]` block (numbered list of premises inside); the debate
  conclusion card is a `> [!summary]` block. These are the only structural
  callouts; section bodies use plain headings.
- **Structure mapping**: frontmatter then H1 title; use the category anatomy
  in article-structure.md. H2 sections and narration H3 commentary cards map to
  the same website headings. Fact cards are bullet lists of key-value lines;
  Facts blocks are real Markdown tables with detail anchors. Serial kickers
  and sibling/hub links follow the title. No raw HTML or emoji.
- **Images**: for optional vault delivery, use `_attachments/` and Obsidian
  embeds with license attribution when required. Website image layout is owned
  by its format reference; do not replace article text with an image.
- **In-note anchors**: commentary links and Facts `↗` links use
  `[[#<heading>|label]]`. Headings must be unique across the note (the
  validator checks).
- **Frontmatter** (every new note):
  ```yaml
  ---
  title: <Title>
  category: debate|exegesis|narration|commentary
  serial: <hub-or-part-designation>   # only when the serial flag is set
  folder: <destination folder>
  date: YYYY-MM-DD
  source: <book, author, volume, chapter>
  summary: <one-sentence summary, same rules as the subtitle>
  enforce: none
  ---
  ```

For website-bound debate, include `opponent` in frontmatter when applicable.
Frontmatter summary becomes the website subtitle; keep its wording unchanged.
A website-only master may omit vault-specific folder metadata. `enforce: none`
is legacy vault metadata, not permission to skip any shared verification gate.
For commentary the anatomy in article-structure.md applies; do not add the
Facts table, numbered argument sections or closing verdict from debate examples.

## Validation and delivery

Run on the completed candidate on Titan:

```bash
python3 ~/.agents/skills/islamic-note/validate.py runs/<slug>/candidate.md
```

The validator checks Markdown structure; corpus verification, translation
fidelity, editorial and council approval remain required by the shared workflow.
Do not waive a source or structure failure to file a note. If a valid source or
format exposes an unsupported validator case, repair it with a regression case.
Legacy notes remain untouched outside an explicit repair/normalization request.
An authorized regenerated master uses the current format and review gates.

After the final review.py check, save notes/<slug>.md on Titan. For requested
vault delivery, copy the exact approved bytes to the chosen Mac folder. Check
title collisions and preserve the old version on repairs. Verify destination
bytes and its final review using the same baseline/review records. Claude hooks
are supplementary; Kimi and other clients must execute the explicit checks.

Scripture follows `~/.agents/prose/article-sources.md`: original language,
transliteration, direct English. Bible quotations have no inserted Arabic layer.
Use its paired `<mark data-term="1|2">` notation for at most two significant
terms. The citation identifies the actual source language and edition. Preserve
blank quoted lines between paragraphs and language layers. Marks are presentation,
not source bytes; the checked handoff preserves their exact lexical alignment.
