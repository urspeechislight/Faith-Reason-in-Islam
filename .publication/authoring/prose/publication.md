# Checked publication with the active agent model

All model work uses native subagents inheriting the running agent's model and
provider configuration. This includes translations, council roles, follow-ups,
fidelity review and final release review. Do not invoke Copilot, GitHub Models,
OpenCode or another model/provider, even for regression tests, without explicit
user authorization. Never suggest paid allowance as the normal publication path.
Native subagents use the user's existing agent access; do not claim that their
use is free or independent of that access plan. If inheritance is unavailable,
report the limitation instead of selecting a provider.

The agent performs independent review before pushing. GitHub runs only mechanical
verification in `.github/workflows/native-publication.yml`; it makes no model
calls and has no Copilot permission. `Publication gate` remains required before
`Deploy checked site`. The retired `publication.yml` workflow stays disabled.
Never disable protection or waive a failed check to publish.

## Prepare the reviewed bundle

Use the shared workflow and article_build.py preflight, evidence, reviews and
prepare commands. Complete actual source, editorial, council and HTML review;
retain their real responses. Complete scripture alignment before council review.
The independent final reviewer must be a separate native subagent inheriting the
parent's active model. Fresh context preserves independence without changing
providers. Give it the whole current candidate, sources, all council findings,
and rendered authored text. The writer cannot approve its own changes.

```bash
python3 ~/.agents/prose/article_build.py release-request RUN/build.json \
  --parent-model "$ACTIVE_MODEL" --output RUN/native-release-1
```

Read the parent's model identifier from the host's runtime metadata. This flag
records it; it does not choose a model. Delegate the generated prompt.txt through
the host's native agent tool with model inheritance and no override. Retain the
actual child ID and exact final response. No Python command launches a model.

```bash
python3 ~/.agents/prose/article_build.py release-accept RUN/build.json \
  --request RUN/native-release-1/request.json --response RAW_RESPONSE.json \
  --agent-id NATIVE_CHILD_ID --model "$ACTIVE_MODEL"
python3 ~/.agents/prose/article_build.py verify RUN/build.json
python3 ~/.agents/prose/article_build.py stage RUN/build.json
```

Accept retains blocked and malformed replies without approving them. A complete
pass must resolve every required finding and bind the source, rendered HTML,
source archive, council and current policy. It writes a new review record,
preserves the original, and creates a verified immutable handoff. The manifest
points to the result only after successful preparation and verification.

If the reply omits required dispositions, return the exact schema diagnostic to
the same native reviewer once for a complete response; preserve both replies.
Do not invent missing decisions or silently treat malformed output as approval.
A substantive finding returns to the supported revise/preflight/evidence/reviews
cycle and actual affected review. Keep all earlier attempts. Stop after three
unsuccessful substantive rounds and report the unresolved issue.

Model identity and independence are recorded from the actual native invocation.
The receipt is not cryptographic proof of which model produced it. GitHub checks
artifact bindings, original response content and required findings; it does not
claim to run or authenticate the reviewer. Honest native tool transcripts and
source review remain necessary. Never manufacture a receipt from a pass label.

## Source evidence and staging

`article_build.py evidence` reads the corpus read-only and checks metadata, page
hashes, exact slices and coverage. Retain external originals with their actual
URL/file, edition, locus and access date. Scripture needs its own source-language
archive, complete transliteration and direct English, plus named alignment review.
Claim maps retain source IDs, inferences and limits. A byte match does not prove
an interpretation. The final native reviewer receives the complete source dossier.

Use a fresh isolated Titan site worktree and the urspeechislight GitHub identity.
`stage` copies the exact checked HTML and four `.prose-reviews/` files, including
the handoff with the native release response. Regenerate derived pages with
`python3 .publication/build_indexes.py`, inspect the diff, and push a branch/PR.
Do not stash/rebase/push a shared main checkout or copy another session's work.

Before expensive review, inspect the base's latest full publication result.
A runtime-only pass is not article approval. Existing article failures can still
block the public tree; identify them early and preserve their actual findings.
Workflow maintenance does not authorize repairing unrelated articles.

After protected checks pass, merge within the user's publication authorization.
Verify the main deployment and compare live bytes with the checked commit.
Only then report publication and save the approved canonical master. A pushed
branch, HTTP 200, matching title or skipped deployment is not publication.

## Diagnose one exact run

```bash
python3 ~/.agents/prose/publication_status.py --run RUN_ID --commit FULL_SHA \
  --output RUN/ci --wait-seconds 30
```

The command validates the head SHA, reports failed steps and downloads the exact
run/attempt artifact. Read its typed result.json and retained native review. Old
`reviewer-regression-*` artifacts contain historical synthetic provider tests;
they are not article decisions. Exit 2 means running. Return control between
bounded waits. Failed/skipped jobs need diagnosis, not propagation sleeps.

Current-policy reuse requires a successful same-repository main ancestor or
identical push commit, a successful full publication step, and unchanged policy,
article and four receipts. Identical historical files may retain explicitly
labelled older-policy approval. Any article/evidence change requires current
checks, including native review. Legacy pages remain grandfathered, not newly
approved. Runtime-only jobs cannot supply article approval.

## Install workflow changes without publishing articles

The versioned runtime and authoring bundle contain commands, policies, templates,
CSS and tests. `sync_runtime.py --agents-root PATH` snapshots an isolated tested
bundle. `install_toolchain.py --target PATH` verifies its manifests, preserves
replaced bytes and installs shared translation aliases. `--check` verifies an
installation; `--expected` takes pre-change hashes to protect concurrent edits.
Test a clean target before installing on Mac and Titan. Policy changes require
genuine revalidation, never patched approval hashes.

A runtime-only PR contains no article, receipt, catalogue or public-asset edits.
CI runs mechanical tests and checks exact preservation of public/review bytes;
it skips Pages and records no article approvals. It calls no model, including
for regression tests. Model behavior fixtures, when needed, run through native
inherited-model subagents in the agent session, with actual retained responses.
Confirm main checks and skipped deployment before claiming hosted rollout.
