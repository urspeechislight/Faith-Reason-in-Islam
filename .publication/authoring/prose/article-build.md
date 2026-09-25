# Repeatable article builds

Use `python3 ~/.agents/prose/article_build.py` for every website create or repair.
It renders canonical Markdown through the maintained reader templates, reader.css and reader.js.
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

Reload this file for every new repair invocation and after a process change.
“Fix and republish URL” includes the current shared format. Earlier completion,
a green deployment and live bytes equal to an old approved page are historical
publication evidence; they do not establish current format compliance.

Run `article_build.py status RUN/build.json`. `needs-revision` and
`format_current: false` mean the retained build no longer matches current inputs.
Continue with a supported revision and actual affected review without asking
for a separate re-render request. `format_current: true` alone is not approval:
source, review, release and deployment checks still apply. An unchanged current
build can reuse its verified work; do not create changes merely to republish.

```bash
python3 ~/.agents/prose/article_build.py revise RUN/build.json \
  --source CANDIDATE.md --output NEXT_RUN/build.json --reason 'Apply current article format'
```

Scope compares local changes against the shared upstream ancestor when it can
prove that ancestor descends from the original task baseline. Merged updates
therefore do not become unrelated local edits. The original scope record stays
unchanged. Unmerged, staged, unstaged and untracked unrelated work still blocks.

If the recorded worktree is busy or on an unsuitable branch, preserve it. Fetch
origin and create a fresh isolated worktree at origin/main using the usual Git
procedure, then select it through the supported flag:

```bash
python3 ~/.agents/prose/article_build.py revise RUN/build.json \
  --source CANDIDATE.md --site-root CLEAN_SITE_WORKTREE \
  --output NEXT_RUN/build.json --reason 'Continue repair with current workflow'
```

This requires a clean same-repository worktree at fetched origin/main, the same
article identity and unchanged destination article/receipt bytes relative to the
parent's recorded or staged versions. It preserves the parent manifest, source,
reviews and worktree, records the destination transition, and starts a new
unapproved build. If the destination article changed, inspect that current
version and use its retained handoff with `adopt`; do not overwrite it with an
old candidate. Never edit scope bases, manifests, receipt hashes or generated
HTML to get past these checks. No receipt-porting scripts or verifier archaeology.

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
include both templates, reader CSS/JS, source policies and verification code.
Keep Mac-owned global files and Titan runtime synchronized; do not edit policy
or approval hashes inside records to conceal version differences.

## Rendering options

Pass a JSON file with `init --config FILE` only when needed. Supported keys are
`section_ids`, `note_map`, `languages`, `source_paragraphs`, `source_roles`,
`template` and `register`.
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

For a report with a source heading, chain and narration, declare semantic roles
in this same configuration before preflight:

```json
{"source_roles": {"Exact report caption": ["heading", "isnad", "matn"]}}
```

The list follows every paragraph in the callout, including original and English
layers. Allowed roles are `heading`, `context`, `isnad`, `matn`; each nested `> >`
paragraph must be `matn` and each outer `>` paragraph must have another role.
A chapter heading is `heading`, never `isnad`. Mark chains from the actual source;
position before a narration does not establish a chain. Without a role map,
outer paragraphs remain neutral source context and nested paragraphs remain matn.
Do not invent labels or explain isnad/matn inside the callout. Typography and the
chain separator distinguish the units. The full narration, including unquoted
narrative sentences, remains in its explicit matn group.

For an existing run, pass the complete replacement rendering configuration to
`revise --config FILE` together with the usual source, output and reason flags.
Include retained language and section mappings. This preserves the parent run,
regenerates presentation and requires actual affected review; never edit an old
manifest or HTML to apply these roles. This is rendering preparation within the
normal workflow, not a separate research or receipt-writing stage.

Supported blocks are H1–H3 subject to category rules, soft-wrapped paragraphs,
source/abstract/summary callouts, flat lists, fact cards and tables, ordinary
blockquotes and inline links/emphasis/code. Unsupported images, raw HTML, nested
lists/quotes stop with a diagnostic. Literal source numbering is preserved as quotation text. Extend the
maintained renderer and preservation contract with a fixture when needed; never
silently remove source content or make a per-article generator.

## Use the prepared review, not validator exploration

For an ordinary article repair, read the existing article, its registered corpus
captures and the installed prose instructions. Correct concrete defects and reuse
valid evidence. Research again only for a missing source, a changed claim or a
specific fidelity concern. The presence of corpus text does not itself prove that
the article's interpretation is correct.

Run `article_build.py review-plan RUN/build.json` before dispatching reviewers.
It reports stale master/render records before either review consumes model time.
Resolve the reported stage through advance or revise; retain completed records.
Do not inspect validator code to learn how to fill a review. The generated
prompt, response contract, locations and response form are the review interface.

Give the reviewer the prompt.txt path on Titan, its native session ID and the
active model, with the instruction to read the listed assets and complete the
form. Use a bounded task context; do not pass the full repair-session history.
Read the complete candidate and the source evidence needed for its claims.
The large request.json and baseline are machine archives, not extra reading
assignments. The coordinator reads the readiness result and final findings;
it does not separately reconstruct the reviewer schema or reread its packet.

The form omits redundant machine fields. Intake restores exact omitted bindings,
source text and retained council responses from the immutable request, never
observations, approvals, cue resolutions or other judgments. Each source callout
requires passed status, paragraph-boundary, speaker-boundary and completeness
assessments (at least eight words each), plus its listed cue resolutions.
A blocked response returns located findings. A malformed response gets one
bounded correction using the tool's error. Repeated tool failures stop that stage
with the exact command/error and retained files; they do not authorize JSON
surgery, dummy agents, policy changes, or reverse-engineering the pipeline during
an article task. Implementation inspection belongs to a reproducible tool defect
and a separate workflow maintenance change.

Reviewer identity is the native session ID plus native child ID. Supply
`--session-id NATIVE_SESSION_ID` on review-request, review-accept and release-accept.
Before substantive reading, the coordinator can check the spawned reviewer's
identity with `article_build.py review-identity RUN/build.json --request
RUN/master-request/request.json --session-id NATIVE_SESSION_ID --agent-id
ACTUAL_CHILD_ID`. Resolve an ambiguous legacy origin before consuming review time.
New council invocation records retain reviewer_identity with session_id and
agent_id while preserving reviewer as the actual child ID. A different session's
agent-2 is a different actor. An unknown legacy scope is never guessed.
For a legacy collision, review-request accepts `--council-origins ORIGINS.json`:
a list of group (advisors/peer_reviews/followup_reviews), index, session_id,
agent_id, and transcript path. Each retained host invocation JSON must contain
matching session_id, agent_id and the verbatim response. The command attaches
provenance without renaming reviewers or changing judgments. If evidence is
unavailable, obtain an actual affected review; never create agents to burn IDs.
Host records establish recorded provenance, not cryptographic provider identity.

Editorial and rendered review policies have separate dependency groups. Reviewed
compatibility entries accept only a specific old digest under an exact tested new
digest; all current validators still run. Unknown policy changes fail closed.
A changed orchestration helper does not by itself invalidate a render. Rendering,
source evidence and final release retain their own checks. Do not edit policy or
install a different toolchain midway through an article task.

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
  --kind master --parent-model ACTIVE_MODEL --session-id NATIVE_SESSION_ID --output RUN/master-request
python3 ~/.agents/prose/article_build.py review-request RUN/build.json \
  --kind render --parent-model ACTIVE_MODEL --session-id NATIVE_SESSION_ID --output RUN/render-request
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
  --agent-id ACTUAL_CHILD_ID --session-id NATIVE_SESSION_ID --model ACTIVE_MODEL
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

## Shared reader format

All new and repaired website articles use reader-v1, defined in the website
reference, render_article.py, reader.css and reader.js. The historical `tabs`
and `flowing` render options select the same layout. Colors remain Faith &
Reason's; the approved reference supplies typography and layout. Back links
use the referring page or index.html. No per-article CSS patches or generators.

For a run begun under an older format, use the supported `revise` lifecycle;
retain the old run and actual reviews, regenerate the new presentation and
review its desktop/mobile output. Old render approvals cannot approve new HTML.
Do not patch hashes or recreate review observations just to change the template.

Before accepting a rendering change, run `test_reader_layout`: its synthetic
heading/chain/matn fixture and fixed reference measurements cover desktop and
mobile typography, reading width, callout padding and paragraph spacing. Inspect
both viewport previews as well. Compare equivalent components and content; a
longer title or an article without an authored abstract naturally has a different
page silhouette. Never manufacture an abstract or source headings to match a
screenshot. Preserve the Faith & Reason palette and working Back navigation.
