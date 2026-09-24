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
been inspected. Each run has a separate manifest and an exclusive command lock. `stage` refuses draft/note deliveries; `status` revalidates any recorded ready bundle and returns nonzero for stale evidence.

## Resume after a workflow change

Read this file again when the process changes during an active session. Run
`article_build.py status RUN/build.json` first. A blocked/stale record is a
located failure, not an invitation to rebind policy hashes. Use `revise` with
the current candidate to create a fresh run under the installed toolchain;
retain all historical responses and perform genuine current affected review.
The maintained commands regenerate rendering, mappings and hashes. No article
run may author a receipt-porting/rebinding script or edit generated HTML.

If an older run has a handoff but no usable manifest, import its retained source:

```bash
python3 ~/.agents/prose/article_build.py adopt NEW_RUN/build.json \
  --handoff SITE/.prose-reviews/SLUG.handoff.json --site-root SITE --slug SLUG
```

For a preview, pass `--delivery draft`; for note-only recovery use `--delivery note`.
Add `--source EDITED.md` to retain an already corrected candidate. The command
copies the original handoff, source and historical review unchanged, creates
pending new paths, and grants no approval. Then use preflight, the actual
scripture/source review, evidence, reviews and prepare/release/verify/stage.
`adopt` and `revise` never manufacture advisor responses or migrate pass labels.

## Keep the requested article isolated

Every new run claims one article slug in its site worktree. A second slug in
that worktree is rejected. For an existing manifest created before this rule,
bind the user-supplied URL before continuing:

```bash
python3 ~/.agents/prose/article_build.py scope RUN/build.json --url REQUESTED_URL
```

Use `init --url REQUESTED_URL` for new repair runs. Scope records live in the
worktree's Git metadata. Use a fresh worktree for another authorized article;
never delete or change a scope record to broaden a task. If a whole-site gate
names a different article, diagnose its preservation/deployment state separately.
Do not start repairing it, borrow its reviews, or change the runtime from an
article session. A runtime defect is workflow maintenance with regression tests,
not an invitation to relax the article's checks. These local boundaries detect
mistakes in maintained commands; they cannot police arbitrary shell edits.

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
lists/quotes stop with a diagnostic. Literal source numbering is preserved as quotation text. Extend the
maintained renderer and preservation contract with a fixture when needed; never
silently remove source content or make a per-article generator.

## One mechanical advance, then actual review

After init/adopt/revise, use the maintained prerequisite command:

```bash
python3 ~/.agents/prose/article_build.py advance RUN/build.json \
  --ledger CITATIONS.json --external EXTERNAL-SOURCES.json --claims CLAIMS.json
```

Omit inapplicable flags. The manifest saves the exact input paths; subsequent
`advance` calls and revisions inherit them. This runs rendering preflight,
live source export into an immutable archive, and pending review creation in
order. It stops on the first failed stage with its evidence intact. Repeating
it reuses exact successful artifacts; it never replaces completed judgments.
A scripture alignment failure requires actual fidelity review below, then
another `advance`. Do not rename/copy evidence1/2/3 files to guessed paths.
`paths` prints the authoritative registered paths.

Complete the actual council under council-article.md and retain its responses,
identities and original candidate hashes in the pending master record. The
writer coordinates the work but cannot generate clean observations or invent
reviewer identities. Then request the editorial judgment and visual inspection:

```bash
python3 ~/.agents/prose/article_build.py review-request RUN/build.json \
  --kind master --parent-model ACTIVE_MODEL --output RUN/master-request
python3 ~/.agents/prose/article_build.py review-request RUN/build.json \
  --kind render --parent-model ACTIVE_MODEL --output RUN/render-request
```

Delegate each prompt.txt to a native subagent inheriting the running model.
The request contains the exact candidate, current schema and relevant evidence.
The master reviewer completes actual prose, source, cue and council judgments.
The render reviewer inspects the page and screenshots and returns visual
findings. HTML uses a verified-conversion record: exact handoff preservation
plus actual visual review. It does not need another observation on every table
cell, list item or source caption. Master review and source verification still
apply to all content. Unmapped/changed text fails conversion and returns to the
Markdown stage. Generated HTML is never edited independently.

Ingest each unedited response with the same maintained command:

```bash
python3 ~/.agents/prose/article_build.py review-accept RUN/build.json \
  --request RUN/master-request/request.json --response ACTUAL_RESPONSE.json \
  --agent-id ACTUAL_CHILD_ID --model ACTIVE_MODEL
```

Use the render request for its response. Blocked, malformed or stale replies are
retained and grant no approval. Ask the responding reviewer to correct a malformed
response once; never fill its judgments yourself. A substantive finding returns
to its source stage and a supported revision. Accepted records are immutable and
the manifest registers them. No JSON completion, hash-rebinding or port scripts.

After both reviews pass, run `prepare`, `release-request`/`release-accept` from
publication.md, and `verify`. The final reviewer independently reads the complete
candidate and retained findings. No external model is called by these commands.
`stage` copies only the five verified artifacts into the registered worktree.
The transaction preserves replaced files, resumes interruptions and rejects
outside changes. Regenerate indexes and follow the protected branch/PR procedure.
Never disable branch protection or bypass a failed gate. Report publication only
after the main deployment succeeds and live bytes match the checked output.

## Scripture before expensive review

The first preflight creates `reviews/scripture-alignment.json` when scripture
is present. A pending or incomplete record blocks the preflight. The fidelity
reviewer checks the actual original, complete Romanization and direct English
against the cited source before approving it. Review every quote now, including
ones the previous council did not flag. Use the native scripture reviewer before the council:

```bash
python3 ~/.agents/prose/article_build.py review-request RUN/build.json \
  --kind scripture --source-context RETAINED-SOURCE-DOSSIER.json \
  --parent-model ACTIVE_MODEL --output RUN/scripture-request
```

Supply the actual original source dossier, including all relevant corpus captures
and external editions. It may be retained evidence from an older candidate; it
is source context, never approval of the current text. The request includes the
current original, Roman and English layers and a pending positional alignment
schema. Delegate its prompt through a native inherited-model child, then use
`review-accept` with its unedited response. Run `advance` again. Neither equal
token counts nor a successful alignment checker establishes linguistic fidelity.
One source word can map to several Roman tokens; preserve phonemic apostrophes,
ʿ and ʾ. The final reviewer independently checks the complete layers again.

## Revise without rebuilding records by hand

Keep the edited Markdown in a separate file, then run:

```bash
python3 ~/.agents/prose/article_build.py revise RUN/build.json \
  --source EDITED.md --output NEXT_RUN/build.json --reason "Concrete correction"
python3 ~/.agents/prose/article_build.py advance NEXT_RUN/build.json
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
then ingest actual responses using review-request/review-accept and run prepare,
release-request/release-accept, verify and stage normally.

`article_build.py status RUN/build.json` reports the recorded stage and next
command. It does not report publication; inspect the exact GitHub run using
publication.md. A successful local verification never proves that deployment completed.
