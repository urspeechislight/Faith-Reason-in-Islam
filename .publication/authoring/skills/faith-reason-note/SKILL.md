---
name: faith-reason-note
description: Publish a researched Islamic note as a Faith & Reason article, preserving its canonical Markdown content and resolving substantive research gaps before release.
---

# Publish a Faith & Reason article

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
