# Repeatable article builds

Use `python3 ~/.agents/prose/article_build.py` for every website create or repair.
It renders canonical Markdown through the maintained templates and quotation.css.
It never reads old article HTML as a template, rewrites prose, grants approval,
changes Git state, or publishes. The agent completes research, review and the
protected publication procedure in the same skill invocation.

Run project commands on Titan. From the Mac, use `titan-project -C` and pass
multiline Python/shell through a quoted stdin heredoc, for example:

```bash
/Users/me/.local/bin/titan-project -C /Users/me/code/islamic -- python3 - <<'PY'
from pathlib import Path
# A script's stdin reaches Titan unchanged; paths here are Titan paths.
PY
```

Do not nest scripts inside quoted SSH commands. Check command exit status
without piping it through tail/head/echo. Preserve failed artifacts. Do not
retry a mutating command after a connection failure until its remote state has
been inspected. Each run has a separate manifest and an exclusive command lock.

## Start once, before review

Use a new run directory and a working candidate; preserve the current master.
For publication use a fresh isolated Titan site worktree from fetched origin/main.
Read its repository instructions. Existing URLs keep their slug. Record the
actual existing baseline/review paths with the flags below when reusing a valid
unchanged review. Never guess versioned filenames or select the newest JSON.

```bash
python3 ~/.agents/prose/article_build.py init RUN/build.json \
  --source RUN/candidate.md --site-root SITE_WORKTREE \
  --slug ARTICLE-SLUG --operation repair --delivery publish \
  --baseline RUN/reviews/master.baseline.json --review RUN/reviews/master.review.json
python3 ~/.agents/prose/article_build.py preflight RUN/build.json
python3 ~/.agents/prose/article_build.py paths RUN/build.json
```

Use `--operation create` for a new article. Create rejects an occupied slug;
repair requires its existing HTML. Each later command checks the article and all four destination receipts against
their recorded starting hashes or this run’s own verified staging transaction;
concurrent changes require inspection and a fresh run against the current revision. Use `--delivery draft` for an unpublished
HTML preview. Note-only requests do not need a website manifest. An explicitly
requested preview can stop after preflight without obtaining publication review.

Preflight renders the exact candidate, verifies its handoff, runs the HTML
validator, and captures desktop/mobile quotation geometry in Chromium. It blocks
on missing languages, unsupported syntax, structural defects, overflowing or
hidden content, insufficient insets, spacing failures and changed quote text.
It produces no approval. Inspect its screenshots and print/no-JS presentation.
Fix a shared layout defect in the maintained renderer/template/CSS, with a
regression test. Fix content defects in the candidate. Never patch generated HTML
or an old published page to supply a shell. Rerun preflight before editorial or
council review; a changed master, render option, dependency or runtime invalidates
previous results. Failed/interrupted attempts remain and can be retried.

The manifest records absolute paths, source/runtime hashes, build history and
final checked artifact hashes. `paths` prints the registered paths, including
HTML and render evidence after preflight. Successful identical preflights reuse
their checked artifacts. Missing or edited artifacts block reuse. Runtime hashes
include both templates, quotation CSS, source policies and verification code.
Keep Mac-owned global files and Titan runtime synchronized; do not edit policy
or approval hashes inside records to conceal version differences.

## Rendering options

Pass a JSON file with `init --config FILE` only when needed. Supported keys are
`section_ids`, `note_map`, `languages`, `source_paragraphs`, `template` and `register`.
The manifest supplies `slug`. Unknown keys and obsolete caption/heading mappings
are rejected. For example:

```json
{
  "section_ids": {"A Christian reading": "comparison"},
  "note_map": {"wiki:Part One": "part-one.html"},
  "languages": {"John 2:4, Greek edition": "grc"},
  "template": "tabs"
}
```

Mappings must use headings and callout captions that actually occur in the
candidate. Choose the actual comparison section; do not relabel a section merely
to pass a check. The renderer resolves ordinary heading links automatically.
Sibling links must exist inside the selected site tree and are hashed for reuse.
Source languages come from explicit mappings or unambiguous script plus edition
labels; unknown editions stop the build. Latin-script report callouts need
`source_paragraphs: {"Exact caption": 1}` to distinguish their original paragraphs
from English. Scripture layers and significant-term marks come from the master.
The converter never chooses translations, transliterations or highlighted words.

Supported blocks are H1–H3 subject to category rules, soft-wrapped paragraphs,
source/abstract/summary callouts, flat lists, fact cards and tables, ordinary
blockquotes and inline links/emphasis/code. Unsupported images, raw HTML, nested
lists/quotes and literal source numbering stop with a diagnostic. Extend the
maintained renderer and preservation contract with a fixture when needed; never
silently remove source content or make a per-article generator.

## Bind actual reviews and check the complete result

Read the existing editorial/council instructions. After preflight run
`article_build.py reviews RUN/build.json` to create the registered master and
HTML baselines and pending reviews. This command also binds the HTML render
capture. Pending templates are not approval. Existing approved reviews can be reused only if their actual verifier
passes. Do not fill status/hash fields to migrate a stale review.

After source verification and actual master review:

```bash
python3 ~/.agents/prose/article_build.py prepare RUN/build.json
python3 ~/.agents/prose/article_build.py paths RUN/build.json
```

If the exact review files already exist elsewhere, provide both `--baseline`
and `--review` to prepare; successful validation registers those paths. Prepare
embeds the actual verified master records into an immutable handoff and pins the
HTML, source, runtime and review bytes. Hosted publication defers only the final
independent release decision to GitHub. All other review requirements still apply.

Use the printed HTML/render paths to create the HTML review at the manifest's
`html_baseline` and `html_review` paths. Reuse the verified master council through
the handoff as the editorial instructions allow; inspect all rendered content,
metadata and quotation layout. Run `article_build.py evidence RUN/build.json --ledger CITATIONS.json`
with applicable `--external`, `--claims` and `--db` flags. The manifest records
these exact inputs; later revisions inherit them. Each export rechecks the live
corpus and writes an immutable, content-addressed archive. An existing archive
from an earlier candidate cannot cause an output-path collision. Then run:

```bash
python3 ~/.agents/prose/article_build.py verify RUN/build.json
```

This combines the master approval, handoff preservation, HTML review, render
measurements and source archive checks. It cannot pass on separate successful
checks while the embedded master fails. Exact alternative paths can be supplied
with `--html-baseline`, `--html-review` and `--evidence`; successful verification
pins them. For hosted publication, success means prepared for hosted review,
not published. Any later edit invalidates the pinned artifacts.

Run `article_build.py stage RUN/build.json` to copy the five verified artifacts
to the registered worktree. The transaction preserves replaced files and can
resume after interruption. A site/slug lock prevents overlapping stage commands.
Other destination changes block staging; inspect them before proceeding. Regenerate indexes, review the diff,
and use the protected publication branch/PR procedure in publication.md. The
outgoing-commit and hosted checks validate those exact copied bytes again.
Never disable branch protection or bypass a failed gate. A failed job requires
its actual error log; waiting for Pages cannot repair it. Claim publication only
after the main deployment succeeds and live bytes match the checked commit.

## Scripture before expensive review

The first preflight creates `reviews/scripture-alignment.json` when scripture
is present. A pending or incomplete record blocks the preflight. The fidelity
reviewer checks the actual original, complete Romanization and direct English
against the cited source before approving it. Review every quote now, including
ones the previous council did not flag. Required fields are demonstrated by
`scripture_alignment.py prepare SOURCE --record NEW_PATH`; it creates no
transliteration or approval.

Each quote contains exact source and Roman tokens. Its `units` list has one
entry per source token, with zero-based `source_index`, exact `source`,
`roman_start`, exclusive `roman_end`, and exact `romanization`. Consecutive spans
must cover every displayed Roman token once. One source word can map to several
Roman tokens. Preserve phonemic apostrophes, ʿ and ʾ. The named reviewer records a
specific fidelity assessment in `evidence` and marks reviewed quotations
`passed`; only a completely reviewed record is `approved`. The mechanical check
establishes complete alignment, not correct pronunciation or interpretation.
The hosted reviewer receives the full layers, source and alignment for its own
assessment. Never invent token assignments merely to satisfy coverage.

## Revise without rebuilding records by hand

Keep the edited Markdown in a separate file, then run:

```bash
python3 ~/.agents/prose/article_build.py revise RUN/build.json \
  --source EDITED.md --output NEXT_RUN/build.json --reason "Concrete correction"
python3 ~/.agents/prose/article_build.py preflight NEXT_RUN/build.json
python3 ~/.agents/prose/article_build.py evidence NEXT_RUN/build.json
python3 ~/.agents/prose/article_build.py reviews NEXT_RUN/build.json
```

Use a new directory and the filename `build.json`. The retained preflight
supplies the previous source even if the working candidate was edited. The
parent, its evidence and review records remain intact. An interrupted stage
must be resumed before revision. A child records the current destination hashes,
fresh artifact paths and a `revision.json` mapping. No approval is carried over.

Valid scripture alignments survive only for unique quotations with exactly the
same citation and all three language layers, bound to the prior preflight.
Changed or ambiguous quotations remain pending. Unchanged historical council
responses remain available in the pending master review for genuine follow-up
review; they are not represented as a new council approval.

`revision.json` identifies uniquely matching prose blocks whose complete section
and protected evidence are unchanged. A reviewer may explicitly confirm those
blocks after inspecting their current context. Pass a JSON containing the current
`artifact_sha256`, the `revision_sha256`, the named `reviewer`, and `blocks` with
`id` and a substantive contextual `reason` to:

```bash
python3 ~/.agents/prose/article_build.py reuse NEXT_RUN/build.json --confirmation CONTEXT_REVIEW.json
```

Reuse verifies the previous approval under current policy. It copies only the
confirmed blocks’ judgments and records provenance. It never copies global
approval, changed-block judgments, semantic checks or cue dispositions. Duplicate
text, changed sections, changed protected quotations/links and stale prior
reviews require fresh review. No prefix matching or hand-written JSON port
scripts. Finish the actual affected reviews and full-article coherence check,
then run prepare, verify and stage normally.

`article_build.py status RUN/build.json` reports the recorded stage and next
command. It does not report publication; inspect the exact GitHub run using
publication.md. A successful local verification never closes hosted findings.
