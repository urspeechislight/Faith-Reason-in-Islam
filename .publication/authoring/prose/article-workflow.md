# One article, one master

The user can ask either existing skill to research a topic, save the note, and
publish it. The agent coordinates the stages; the user does not manage scripts,
review files, category selection, or a second skill invocation. A note-only
islamic-note request saves a note. Asking either skill to create an article or
update/fix a supplied published article includes publication in the same run.
An explicit draft, preview, audit or no-publish request overrides that default.
A plain faith-reason-note request publishes the supplied note, researching
substantive gaps first when needed. Workflow maintenance authorizes changes to
the process, not edits or publication of articles quoted as examples.

## Model authorization

Use native subagents inheriting the current agent's model for every delegated
model task: translation, all council roles, follow-ups and final review. Do not
choose a different model, launch Copilot/OpenCode/GitHub Models, call another
provider, or enable paid usage without explicit user authorization. CI performs
mechanical checks only. The user does not need a Copilot allowance to publish.
Follow publication.md for the artifact-bound native final-review handoff.

## Load the applicable references

Both skill names are entry points into this workflow. Follow these references
inside the same invocation; loading a publication reference is not a second
research/writing run. A skill file is agent guidance, not an executable job
scheduler. The explicit commands and final-artifact gates below provide the
mechanical checks; no client is assumed to run Claude-specific hooks.

| When | Authoritative instruction file |
|---|---|
| Plan or draft a master | [article-structure.md](article-structure.md), [article-sources.md](article-sources.md) |
| New research or substantive repair | [faith-reason-research](../skills/faith-reason-research/SKILL.md) and its relevant research references |
| Draft or revise authored prose | [contract.md](contract.md), [drafting.md](drafting.md), [paragraphs.md](paragraphs.md) |
| Translate new or corrected source text | [translation.md](translation.md), [translate-style.md](translate-style.md) |
| Build/validate a master, optional vault copy | [Markdown format](../skills/islamic-note/references/markdown.md) |
| Review before release | [editorial.md](editorial.md), [council-article.md](council-article.md) |
| Hosted publication and deployment | [publication.md](publication.md) |
| Render/preflight any website create or repair | [Repeatable builds](article-build.md) |
| Website publication or HTML preview requested | [Website format](../skills/faith-reason-note/references/website.md) |

Read only the conditional resources needed for the task. For an approved,
unchanged master, reuse its evidence after checking provenance and current
review validity. Do not ask the user to launch research, polishing, or publishing
skills separately. State the plan and proceed when scope is clear. Explicit
no-publish, preview, draft-only and audit-only instructions override defaults.

For scripture, read article-sources.md before selecting the language layers or
translating. It requires the actual source language, scripture-only transliteration,
direct English, and at most two aligned significant terms. Workflow maintenance
is tested with unpublished fixtures and does not authorize article edits or release.

Each rule has one owner in this table. Destination references own syntax,
layout and delivery only. Shared research and prose tools keep their existing
paths; do not fork them by client. When changing mechanical enforcement, update
the owning rule, implementation and a meaningful regression fixture together.
Examples and historical backups are not additional instructions. Source
fidelity and the user's request outrank a style target or template convention.

## Choose create, repair, or publish

- **Create** from a topic or sources: define the question, research it, write
  one cited master, preflight its rendering before review, then publish for an
  article request; save only for a note-only request.
- **Repair** a note or URL: preserve the existing note, HTML and deployment
  version in a new run directory. Read the complete article. List concrete
  defects with locations and distinguish research/attribution/inference,
  translation, prose, and rendering defects. Trace each defect to its earliest
  affected stage, repair that stage, and carry the corrected master forward.
  Reassess evidence coverage across the whole article, including omitted
  primary sources, variants, alternative readings and counterevidence. Reuse
  verified material, but do not restrict collection to already identified defects
  or the previous council's backlog. Record coverage by the article's questions
  and claims and run additional collection where gaps or uncertainties remain.
  Inspect every callout, not just authored exposition. Missing research provenance
  requires a new scoped survey, not an invented retrospective approval.
- **Publish** an approved note: verify its sources and approval references,
  then convert and check it without re-authoring. If substantive defects are
  found, switch internally to repair and explain the needed correction.

For repairs, record each changed claim, its original wording, corrected wording,
source IDs and reason. A request to correct an article authorizes correcting
its unsupported claims; a narrow polish request preserves the argument and
reports substantive defects separately. Keep source/translation corrections
separate from the prose-only pass. Preserve Arabic by recapturing corpus bytes.
For full repair, preserve a coverage assessment and a defect list with locations,
changes, evidence and validation. The final report distinguishes source corrections,
prose/quotation-layout corrections, rendered inspection and deployed-content
verification. Do not call an article repaired solely because receipts pass.
After repairs, reread the whole article for coherence and run the
applicable gates. Do not limit the final read to changed sentences.

An audit-only request ends with findings and a repair plan. A draft-only request
ends with a Markdown candidate and, only if requested, an HTML preview in the
run directory, leaving
the current master and published page intact. It does not invoke publication.
The agent performs this routing from the user's request without making the
user coordinate multiple skills or internal commands.

## Authoritative files

From the Mac run project commands through titan-project with an explicit -C.
On Titan work directly. Canonical content is
`/home/fahmy/code/islamic/notes/<slug>.md`; retain working research under
`/home/fahmy/code/islamic/runs/<slug>/research/`. Website output belongs to
`/home/fahmy/code/Faith-Reason-in-Islam/<slug>.html`. These are different views
of one authored article, not independently maintained drafts.

Save a new master only after review. Work in a new run directory during
revision; preserve the previous master until the revision is ready. Never
silently replace unrelated work. If Obsidian delivery is requested, copy the
approved master to the Mac vault using its Title Case filename and verify the
same bytes. The Mac path is not a Titan path. A website-only request need not
wait for iCloud or a vault write.

Reuse the existing slug when updating an article. Check the catalogue and Git
history first; do not create competing `greatest-name`/`greatest-name-seals`
versions. If live HTML differs from the checkout, fetch it to an audit file
and inspect Git/deployment provenance before modifying or pushing. Do not
silently overwrite newer live work.

## Research before prose

Read the research skill linked above for new or substantive research. Begin with the reader's question, audience, scope,
and the conclusion the evidence would need to establish. A narration presents
one source story; a question assembled from several reports usually needs
commentary or debate. Choose by purpose, not the presence of hadith.

Use the maintained backend in `workflow/research.py`; read
`/home/fahmy/code/islamic/workflow/RESEARCH.md` for commands and query semantics.
The agent writes the query plan and runs the tools. The user supplies the topic,
not SQL or a sequence of tool invocations. Normal research uses this backend;
one-off SQL is reserved for diagnosing a missing backend capability, which
should then be added to the reusable tool.

For focused follow-ups, use the shared `workflow/query.py search-batch` and
`fetch-many` CLI (or MCP `search_batch` / `fetch_many`) documented in
`workflow/RESEARCH.md`. Inventory every exact-query match; a small response page
never means no evidence exists later. Follow result/source-inventory cursors and
record unresolved review. Use `collect` for durable article-wide inventories and
source dispositions. Reuse retrieved pages and batch independent operations.

Create a plan with facets, names/wording variants, primary-source targets and
counterevidence. `phrase` matches adjacent words. In `all` and `any`, each term
is still a phrase. Use `groups` for concepts that can occur separately: aliases
inside a group are OR; groups are AND. For example, `[["السبكي"],["ابن تيمية"]]`
finds both names anywhere on the same page; one term `"السبكي ابن تيمية"`
requires adjacency and misses most relevant pages. Add separate alias queries
and report continuations because co-occurrence cannot span page boundaries.

For a phrase query use `{"mode":"phrase","terms":["search words"]}`;
`{"phrase":"search words"}` is an accepted shorthand. Query objects also need
`id`, `facet` and `purpose`. Use `python3 workflow/research.py plan-example` for
a valid template or `validate-plan PLAN --json` for an offline check. Do not
inspect implementation source to rediscover the schema. Collection validates
all queries before database work, so a separate validation call is optional.
Write plans directly on Titan or pass JSON through `titan-project` to `collect -`
on stdin; avoid the local temporary-file/SCP round trip. Preserve a run's plan
and inspect command exit status and outputs; a launched PID is not completion.

On Titan, the normal first collection is:

```bash
python3 workflow/research.py collect runs/<slug>/plan.json runs/<slug>/research
```

The authoritative corpus is built from `/home/fahmy/code/sol/data/books` and
includes author/title indexes and a hashed source inventory in the main SQLite
database. This command uses those integrated indexes, enumerates ALL
matches for the declared queries, writes a source inventory and readable
`overview.md`, then retrieves an explicitly limited first batch with full pages
and same-work context. Read `batch-001/pages.txt`; JSON uses `records[]`.
The first batch is a starting sample, not completion. Inspect the entire source
inventory and retrieve relevant sources/queries with `bundle`; use `--offset`
for continuation. No retrieval command marks evidence as read or accepted.
Keep additional query rounds in new research directories and reuse existing
bundles rather than fetching the same pages again.

Use `sources --author ... --title ...` to search the integrated author/title index. Query filters
can select authors, titles, categories, or exact source paths. Use the maintained filters or column-qualified FTS `MATCH`, not
unindexed leading-wildcard `LIKE` scans. Author/title filters are normalized
metadata matches, not reliable school/sect labels.
A Sunni author's book quoting a charge is not automatically Sunni corroboration;
read the attribution, date, context and independence of the underlying report.

Resolve zero-hit and excessively broad queries before drafting their dependent
claims. Zero hits may mean wrong aliases, accidental phrase adjacency, page
boundaries or overly restrictive filters. Add narrower concept combinations
and source-targeted rounds; retain the original counts. An explicitly limited
`engage.py` discovery result or the first bundle cannot establish coverage.
For maintenance, rebuild and validate the whole versioned corpus using
`index/rebuild_corpus.py`; `catalog` only reports the integrated index on the
current schema. Read `index/CORPUS.md` before changing a corpus version. Existing
research inventories are tied to their corpus build and need refresh after
switching versions. All research corpus reads are read-only.

When researching the Ahl al-Bayt school's interpretation, prioritize its reports
and riwa'i tafsir. For other questions, source priority follows the requested
question and tradition; do not impose that priority on every topic.
Then check interpretation, provenance, and adverse evidence in early and later
commentaries and bibliographies. Source priority governs order, not exclusion.
Read the full relevant report, adjacent limiting clauses, and any materially
different version. Adjacent row IDs may be different works: verify relpath,
volume, page, and continuity before combining text. Distinguish independent
witnesses from later copies of one report.

In sources.json, record read/duplicate/out-of-scope/unavailable with a specific
reason and the matching row IDs actually read. Review the source inventory;
do not mass-fill relevance decisions. Retain additional searches separately.
Map every main claim to evidence, counterevidence, and an explicit inference.
If a relevant source is unavailable or the evidence does not settle a question,
state the limit and narrow the conclusion. Zero query hits never prove absence
from the tradition. Report coverage within the indexed corpus and chosen
queries; never promise that all relevant knowledge has been collected.

Test interpretations rather than assuming a term's everyday meaning. Check
unstated premises in numerical or historical arguments. Distinguish a surviving
witness's date from a text's origin and an unverified attribution from a proven
forgery. Claims about a whole school require evidence at that scope.

## Capture and verify citations

Use `workflow/citations.py` for corpus passages. Select the required contiguous
range from a full page read, retaining nearby qualifications and report context.
Capture it programmatically; never type or repair the Arabic from memory.

```bash
python3 workflow/citations.py capture ROWID runs/<slug>/source-01.json --id source-01 --start START --end END
python3 workflow/citations.py verify runs/<slug>/citations.json runs/<slug>/candidate.md
```

Combine the captured `passages` arrays into `citations.json` with `schema: 1`
when every Arabic capture is displayed. For mixed displayed and research-only
evidence, use schema 2 and explicit per-source dispositions as specified in
`article-sources.md`; retain the earlier ledger unchanged.
One ledger entry represents one contiguous excerpt from one corpus page. If a
report spans pages, keep their source identities and separate contiguous
callout paragraphs; never infer continuity from row ID proximity alone.
The verifier compares captured slices and source metadata with the live corpus
and checks that every Arabic callout block is accounted for in the note. Only
layout whitespace can differ in the note; letters and punctuation cannot.

Render each citation from the captured work, author, volume and page, checking
the English work title against the actual corpus metadata. Record report/verse
numbers where the source provides them. Every quotation and material factual
claim needs a reader-visible citation. A claim-evidence map records source IDs,
what each passage establishes, the author's inference and its limits. A
mechanical quotation match cannot grade a chain or prove the interpretation.

For evidence outside this Arabic corpus, retain its actual file/URL, edition,
page/section and access date; verify against that original. Never manufacture
Arabic to satisfy a callout convention. The translation fidelity pass must
account for the full quoted text, including qualifications and uncertainty.

Before saving any scripture-bearing master, including an internal-only note,
run `python3 ~/.agents/prose/evidence.py CANDIDATE.md CITATIONS.json EVIDENCE.json
--external EXTERNAL-SOURCES.json --claims CLAIMS.json --scripture-review ALIGNMENT.json`
as one command, omitting
inapplicable optional flags. Use a new evidence output path for each candidate.
Prepare and complete the named scripture alignment review described in
article-build.md first. Website runs use `article_build.py evidence` to register
the source recipe and choose immutable archive paths automatically.
This verifies the displayed original against its own archived source and keeps
research-only dispositions reviewable. The corpus-only citations check cannot
verify a Greek/Hebrew exhibit from an Arabic witness. Complete the independent
source/translation review as well; archive coverage proves textual presence,
not the source's authority or correctness of interpretation.

Before translation, read the complete report and check both ends of every chosen
excerpt. Extend across pages when a sentence, name or qualification continues.
A page limit, extraction offset or bundle limit is not a source lacuna. Record
boundary decisions in the source ledger; do not ship clipped names or sentences.
If a real source is defective, establish that from the source evidence and name
the limitation accurately. Translation must not invent the missing ending.

## Routine repair execution

Use the existing article, registered corpus evidence and current prose rules.
Correct the identified defects, investigate specific source gaps, and use the
maintained commands. Before delegation, review-plan checks compatibility across
review stages. Delegate the generated prompt and response form with the minimum
relevant task context. The coordinator does not reverse-engineer validators or
read a second copy of every reviewer input. Follow the packet; return located
findings when blocked. Implementation exploration belongs to a reproducible tool
failure and workflow maintenance. See article-build.md for the complete interface.

## Write and review once

Read `drafting.md` and `paragraphs.md` before prose. Keep research strategy separate from reader-facing
claims. Build one readable Markdown master from the evidence map. Each section answers
a real question, gives the pertinent source, explains what follows, and names
any qualification that affects the answer. Keep unrelated material out of the
main line even when it was found during research. Retain useful excluded
material in the dossier rather than forcing every search result into the article.

Copy Arabic from the corpus, follow translation.md to delegate new translation
units to a native subagent inheriting the active model, and
verify quotations and complete translations. Apply the shared prose contract.
Keep commentary beside the evidence in research articles; do not repeat an
entire second argument under a narration's closing Commentary section.

For new masters, follow the website's existing scripture-only transliteration
convention in both formats. Poetry and lexicon quotes use report callouts;
lexicon lemma transliteration may sit inline in the translation. A legacy
note with extra presentation layers needs a documented format migration before
the final baseline: retain its original and auxiliary material in the dossier,
keep quotations and translations complete, and record the presentation changes.
Do not silently drop material during HTML conversion.

Run the note validator in the Markdown format reference and source checks. For
website output, initialize the run manifest and pass article_build.py preflight
as specified in article-build.md before expensive review. Then run editorial
review and the article council
profile in `council-article.md` on this
master before publication. Review concrete inferences, attribution, and
counterevidence; self-scores and unchanged source bytes are insufficient.
Unresolved material defects return to research. Save the approved master and
its baseline/review, then bind them to the passing website build.

## Render, review and publish the same build

Follow [article-build.md](article-build.md) for the maintained rendering command,
run manifest, early browser preflight and combined final verification. Both
create and repair use this route. The renderer reads the maintained templates
with reader.css and reader.js directly; published HTML is never its input shell. Do not
create run-local generators, search old runs for converters, or patch generated
HTML. Extend the maintained converter with a test for unsupported syntax.

The version-4 handoff preserves ordered text, links, source roles, paragraphs,
language layers and lexical marks. It embeds actual verified master review.
An unchanged master can reuse current valid source/council evidence; obsolete
schemas or policies require genuine revalidation, not approval-field changes.
Any content change returns to the Markdown/source stage and affected review.
Use `article_build.py revise`, then its preflight/evidence/reviews commands.
Use `advance` to run the mechanical prerequisites and register the evidence
recipe. Use native `review-request`/`review-accept` for actual judgments and the
verified-conversion visual record; no second per-cell HTML prose review.
Bind older runs to the requested URL with `scope`; a different article requires
its own authorization and worktree. Use its checked reuse operation for eligible context-inspected judgments; never
write one-off port scripts or rewrite approval hashes. Complete scripture
coverage and fidelity before expensive council review.
The final article_build.py verify combines master, HTML, handoff, rendered and
source-archive verification. Individual passes never excuse a combined failure.

For publication follow [publication.md](publication.md). Use a fresh isolated
Titan worktree and the urspeechislight GitHub identity. Stage only this run's
pinned output, receipts and required derived pages. Preserve other sessions'
work. Push a branch through protected checks; never disable protection or skip
review to make a push succeed. On a failure inspect the actual job before any
bounded retry. Only a successful main deployment plus exact live-byte comparison
permits a published claim. HTTP 200, a matching title or a queued job is insufficient.
Keep the Actions result and deployed-byte check in the run record.
