---
name: islamic-note
description: Research a topic or source note against the Titan corpus, write and verify a canonical Markdown note, and publish new or repaired articles through the shared checked workflow.
---

# Research, write, and save an Islamic note

Accept a topic, question, raw sources, existing note, or article to repair.
A note-only request saves a reviewed canonical Markdown note on Titan. A request
to create an article or fix/update a supplied published article includes
publication in this invocation. Explicit draft, preview, audit or no-publish
instructions override that default. Deliver to the Mac Obsidian vault when
requested. Workflow maintenance does not authorize article edits or publication.

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
