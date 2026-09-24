# Hosted publication gate

Faith & Reason publishes through `.github/workflows/publication.yml` in the site
repository. `Publication gate` must pass before `Deploy checked site` can run.
A local hook, writer-authored pass field, or HTTP 200 is not deployment approval.

Before expensive article review, inspect the selected base revision's latest full
publication/deployment result. A successful runtime-only check does not approve
its articles. If an earlier article failure left main undeployed, identify that
existing blocker immediately and keep it in the run record. Do not repair
unrelated articles outside the request, disable checks, or wait for propagation
of a skipped deployment. Research and preview can continue independently, but
publication still requires the full gate to clear the actual public tree.

Prepare and review the canonical candidate using the shared article workflow.
Keep actual advisor/peer responses and source findings. Correct prose during
writing; use independent review to catch missed defects. Do not invent or rewrite
a reviewer's response to make a receipt pass.

For this hosted destination, the final independent release review happens on
GitHub. Use article_build.py preflight before review and its prepare/verify commands
from article-build.md to bind the exact master and HTML reviews. The ordinary local verifier still requires a completed
release decision; the hosted gate explicitly defers only that decision, checks
the other records, and invokes the reviewer itself. It does not need another
local release-model call first. A pending handoff is never approval to publish.

Export the source dossier from the exact candidate on Titan:

```bash
python3 ~/.agents/prose/article_build.py evidence RUN/build.json --ledger CITATIONS.json --external EXTERNAL-SOURCES.json --claims CLAIMS.json
```

Omit either optional flag when inapplicable. The registered scripture alignment
must be complete. The manifest retains the source recipe; revisions automatically
use a new content-addressed archive after live verification. The exporter reads the live corpus
read-only and checks source metadata, complete page hashes, exact quote slices,
and Arabic coverage before saving the full source pages. External sources use
`id`, `kind: external`, `citation`, `url`, `accessed`, `raw`, and `raw_sha256`;
retain the actual source text and its edition/locus. Scripture originals must
match archived source text directly. Citation schema 2 preserves explicit
quotation/research-only dispositions; both retain corpus integrity checks. Claim entries use `claim`,
`source_ids`, `inference`, and `limits`. The independent reviewer must assess
missing evidence, translations and inferences; a hash cannot establish them.

Commit `<slug>.evidence.json` beside the handoff, baseline, and review in
`.prose-reviews/`. Render from the master with explicit source roles. Social
metadata, alt text, tooltips, and other authored attributes are reviewed too.
Regenerate the derived pages using `python3 .publication/build_indexes.py`.
This generator includes commentary and narration fact tables and takes new or
revised article blurbs from their reviewed metadata.

Use a fresh isolated Titan worktree and the urspeechislight GitHub identity.
Never change branch protection, bypass hooks, or patch review status/hash fields
to obtain a pass. Preserve concurrent work and inspect a rejection before any
retry; do not repeatedly stash/rebase/push a shared main checkout.

Push a publication branch, inspect the hosted review, and fix any concrete
failure in the master or evidence. Keep each prior result. Stop after three
unsuccessful substantive repair rounds and report the unresolved issue; never
waive the check. A provider outage or malformed response also blocks release.
Do not treat a queued job or uploaded branch as a completed publication.

After the branch check passes, merge within the user's publication authorization.
Inspect the main-branch Actions jobs. A failed gate means deployment was skipped;
read and fix the actual error rather than waiting for Pages propagation. Only
a queued/running job warrants a bounded wait. Once deployment succeeds, fetch the live page, and compare
its bytes with the checked commit. Retain the Actions run link and downloaded
review artifact alongside the research run. Save the approved candidate as the
canonical master and optional vault delivery only with that actual approval.

The gate verifies every changed/new article, including pages with removed or
altered category markers. It obtains the release response itself, runs Chromium
checks, and binds the staged public inventory to exact checked hashes. Public
output excludes research receipts, source dossiers, council reports and drafts.
Unchanged historical pages in `legacy.json` are grandfathered, not newly reviewed.
Reuse comes from a successful main run, or a successful push run on the exact
same commit in this repository. Current-policy reuse requires unchanged checking
policy, article, handoff, review and source evidence. An identical historical
article and all four review/evidence files may retain an explicitly labelled
`preserved-prior-policy-review`; this is not approval under the new policy.
Any article or evidence change requires current checks. Reuse also checks the
Actions job steps: the full publication step must have succeeded. A runtime-only
run cannot supply article approval. Local pass files cannot supply it.

Static asset or index-template changes require updating their checked manifests
and validating the affected rendering. Keep the Mac-owned shared runtime and
Titan copy synchronized; `.publication/sync_runtime.py` snapshots the installed
Titan runtime for CI. Re-run the publication tests and hosted checks after an
implementation or policy change. Do not edit the CI snapshot alone.

GitHub checks archive consistency and performs independent source/translation
review using the exported evidence. Corpus provenance is established by the
Titan export step, not cryptographically authenticated by GitHub. Screenshots
are retained for inspection; the text reviewer is not claimed to have inspected
those images. These controls reduce known failures, not guarantee perfect prose.
Repository administrators retain control over workflows and protections.

The scripture/layout runtime update also requires `scripture.py` in the hosted
runtime snapshot beside evidence.py, handoff.py, review.py and quote_layout.py.
Preparing local workflow changes does not deploy this snapshot. Update and test
`.publication/sync_runtime.py` with that dependency before an authorized workflow
rollout; never publish an article merely to install a runtime change.

## Deploying workflow code without publishing articles

For an authorized runtime rollout, use an isolated branch containing only the
runtime, its manifest/snapshot helper, gate/tests and publication workflow.
The workflow classifies the event diff and verifies the full public inventory
and `.prose-reviews/` bytes against its base. Runtime mode still runs mechanical
tests and actual reviewer regression fixtures, then skips staging and Pages
deployment. Its result has `mode: runtime-only` and an empty `article_approvals`
list. Verify the successful main run and skipped deployment before reporting
completion. Mixed article/runtime changes take the full publication route.

## Read the correct failure once

Use the actual run ID and full head commit from the pushed branch:

```bash
python3 ~/.agents/prose/publication_status.py --run RUN_ID --commit FULL_SHA \
  --output RUN/ci --wait-seconds 30
```

The command verifies the run’s head SHA, reports failed job steps, and downloads
only the named artifact for that run and attempt. `article-release-*` contains
article decisions; `reviewer-regression-*` contains synthetic reviewer tests.
Read the typed `result.json`, not a recursive response.txt glob. Exit 2 means
still running; return control between bounded waits. A failed or skipped job
needs diagnosis, not a long propagation sleep.

A passed reviewer response with missing or too-short finding dispositions gets
one schema correction attempt against the same complete input. Both invocations
are retained. Substantive blocks, incorrect hashes, invalid JSON and provider
failures never become passes through retry. Fix concrete article findings through
the supported revision commands and submit the corrected bytes for review.

Reviewer regression is mandatory when its exact runtime, policies, evaluator,
client configuration or workflow changes. Article-only runs may reuse a
successful main-ancestor regression step with the same fingerprint for at most
24 hours. Missing/expired proof or API errors cause a fresh regression run.
Manual dispatch always runs it. Failure blocks the job; continue-on-error is
forbidden. This reuse does not grant article approval.

The site now versions the authoring commands, templates, CSS, shared instructions
and tests in `.publication/authoring/`, with release checks in
`.publication/runtime/`. `sync_runtime.py --agents-root PATH` snapshots an
isolated tested toolchain. `install_toolchain.py --target PATH` validates both
manifests, retains replaced bytes, and installs the same bundle; `--check`
verifies an installation. For an existing active installation, use `--expected`
with a target-relative pre-change hash inventory so concurrent edits stop rollout.
Install only after testing the bundle in a separate target. Do not modify policy
mid-review and then edit old receipts to match; use a fresh revision and genuine
revalidation when policy changes invalidate historical review.
