---
name: faith-reason-note
description: Publish a researched Islamic note as a Faith & Reason article, preserving its canonical Markdown content and resolving substantive research gaps before release.
---

# Publish a Faith & Reason article

A request to fix/update and republish an existing URL includes applying the
current shared article format, even when that URL was published earlier in this
session. Reload the current build instructions and check the retained build's
status before declaring completion. Live bytes matching an old approved build
do not establish compliance with the current renderer. A format update needs no
separate user request; proceed through the supported revision and publication.


Accept a researched note, topic, or existing article to repair. Default to
website publication. An explicit audit-only, draft-only, preview, or no-publish
instruction overrides that default. Reuse an approved, unchanged master;
research and repair substantive gaps before rendering when necessary.

Read and follow [the shared article workflow](../../prose/article-workflow.md).
It owns routing, research, the canonical master, source verification, review,
and the checked publishing handoff. Follow its reference-loading table for
content standards and destination mechanics. Website create and repair use its article_build.py manifest, maintained
renderer and rendering preflight before review. Do not start a second writing
pipeline or ask the user to invoke its internal stages separately.

The shared workflow applies in Kimi, Claude, Codex, and other skill clients.
Existing `validate.py`, `translate.py`, and `translate-style.md` paths remain
supported. Translation uses a native subagent inheriting the active parent model. The shared
helper prepares requests and validates responses; it does not launch OpenCode.
Follow the translation procedure linked from the shared workflow.

For corrections after review, use the shared article_build.py revision lifecycle:
revise, preflight, evidence, reviews, then actual affected review and prepare/
verify/stage. Use checked contextual reuse; do not write JSON port scripts.
Complete scripture alignment before council review. Diagnose CI with the exact
run/commit through publication_status.py; regression fixtures and article release
results are separate. These commands are agent responsibilities within this
invocation, not extra tasks for the user.

All council and release reviewers also inherit the running model through native
subagents. No Copilot, OpenCode, alternate endpoint or paid-usage change without
explicit authorization. Use release-request/release-accept before final verify
and stage. GitHub runs mechanical checks only; publication needs no Copilot quota.

When resuming after a process update, reload article-build.md and run the existing
manifest's status first. A stale policy requires a fresh supported revision and
actual affected review. A legacy handoff without a usable manifest uses `adopt`.
Never copy fixture approvals, patch receipt hashes, or edit generated HTML. Keep
project work on Titan; use the versioned bundle's tests for maintenance separately
from the article run. Reading these instructions does not migrate an old receipt.

Bind the supplied article URL to its run with `article_build.py scope` when
resuming an older manifest. One worktree serves one requested article. A failure
on another page does not authorize repairing it. Use `advance` for mechanical
prerequisites and native `review-request`/`review-accept` for actual master,
scripture and visual judgments. HTML conversion reuses verified master content;
do not write duplicate per-cell observations, receipt-fill scripts, or modified
source archives to obtain a pass. Read article-build.md for these commands.

For routine repairs, use the existing article, registered source evidence and
prose instructions. Run review-plan before delegation, then give reviewers the
generated prompt and response form. Do not investigate baseline schemas or
validator internals to complete a normal review. Additional research addresses
specific evidence gaps. Keep reviewer tasks scoped to their supplied inputs;
do not forward the entire session history. Use session-qualified native IDs,
never dummy agents to avoid collisions. See article-build.md for the supported
readiness, response and legacy-provenance commands.

Website creation and repair both use the shared reader-v1 format through
article_build.py. Follow the website reference for layout, typography, retained
Faith & Reason colors and Back navigation. Never reuse an old HTML shell.
