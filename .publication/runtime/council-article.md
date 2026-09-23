# Article council profile

Use for Islamic notes and Faith & Reason articles. This profile replaces the
general council's business personas, word caps, "do not hedge" instruction and
scores. It also replaces the generic chairman's authority to decide release.
Keep independent review and anonymous peer review; the writer coordinates fixes,
and an independent reviewer decides whether the final candidate clears them.
The writer must finish the drafting checks and editorial deletion pass first.

## Inputs and independence

Give each advisor the exact candidate, its SHA-256, category, contract.md,
drafting.md, this profile and the relevant source dossier. All read the whole
candidate. Supply source evidence to fidelity reviewers; do not claim that
reading the article alone verifies it. Do not provide the writer's self-score
or preferred verdict. Run advisors independently in batches within available
concurrency; one does not see another's answer until peer review.

Use these five roles:

1. `prose`: inspect every authored sentence for empty meta commentary, source-as-
   performance narration, internal process leakage, litotes, decorative contrast
   (including sentence pairs and "whatever/despite/even his own" concessions),
   irony, theatrical personification and vague abstractions. Include titles,
   summaries, headings, card text and closing paragraphs. Apply the deletion test.
2. `economy`: read whole sections and the whole article for unnecessary openings,
   preview/recap cycles, duplicated heading/card/body content, redundant quote
   introductions/paraphrases, mandatory-looking conclusions and forced transitions.
   Recommend deletions before replacement text. Preserve necessary explanations.
3. `reader`: identify exactly where a nonspecialist loses the subject, referent,
   term or inference. Request only the explanation needed at that point. No
   generic request for more context, roadmaps, transitions or conclusions.
4. `fidelity`: compare Arabic, translations, attribution, edition/locus, source
   boundaries, chronology, negation and quantifiers with the evidence. Check
   that a page/bundle limit was not described as a break in the original text.
   Identify missing evidence explicitly; a byte match proves only a text match.
5. `reasoning`: assess inference, scope, counterevidence and the strongest relevant
   objection. For a survey, distinguish allegations, independent corroboration,
   authorial positions and historical facts. Do not impose a polemical structure
   on narration, exegesis or commentary.

## Required response

Return located findings rather than a score. Each finding gives an ID, block or
section, exact sentence, defect class, what the sentence contributes, and a
concrete action (`delete`, `rewrite`, `source-review`). For a rewrite state the
meaning to preserve. A clean verdict identifies passages inspected and why they
are needed. Do not invent defects to meet a quota. Necessary source contrasts,
negations and qualifications are never style failures merely because they match
a pattern. Distinguish source translations from authored exposition.

The reader and fidelity reviewers must inspect every quotation and translation,
including long callouts, speaker changes, nested quotation marks and incomplete
beginnings/endings. Protecting source text from rewriting does not exempt it
from these reviews. Refer to callout/paragraph IDs from quote_layout_review.
The reader checks paragraph usability; the fidelity reviewer checks source
boundaries and preservation when a split or correction is needed. Review the
complete final article, not only the previous council's residual backlog.

The prose and economy reviewers must examine both scanner hits and unflagged
prose. Neither a readable sentence nor a low grade score proves that it earns
its place. A paragraph containing a fact may still contain several dispensable
sentences; review their contribution separately. Calling the paragraph a
"bridge", "documentary thesis", "load-bearing contrast", or "designed structure"
does not resolve a located prose defect. Identify the exact fact or inference
that deletion would lose and consider whether a direct sentence preserves it.
For a clean verdict, quote current text in each relevant defect class and
explain the judgment. Do not cite block numbers belonging to an earlier draft. The reader reviewer must not undo a justified deletion by requesting
a generic introduction or transition.

Peer reviewers receive anonymized findings and the candidate. Check proposed
cuts for lost meaning and proposed additions for bloat. Identify missed defect
classes. The chairman retains supported minority findings; majority approval or
a high score cannot cancel a concrete unresolved defect.

The user's prose requirements are acceptance criteria. The writer cannot reject
a located meta statement, theatrical flourish, litotes, or unnecessary recap
as an "unverifiable stylistic preference", "thesis summary", or "required anatomy".
Preserve the required section and its substantive claims while fixing its prose.
If a proposed cut would lose necessary meaning, offer a direct alternative or
document the source conflict for independent adjudication. Do not strengthen a
qualified claim merely to avoid a negative construction.

## Evidence and resolution

Retain the actual advisor responses, anonymization mapping, peer responses and
synthesis. Embed the verbatim responses, not the writer's summary of how many
findings were applied. Keep the original candidate hashes with their responses
and distinguish later follow-up reviews; do not replace them with the final hash. Record each finding's disposition with the changed passage or the
source-based reason for keeping it. Do not auto-generate clean responses.

The final review JSON embeds `council.report` with `advisors` (five objects with
`role`, `reviewer`, `reviewed_sha256`, `response`), `peer_reviews` (five objects
with `reviewer`, `reviewed_sha256`, `response`), `anonymization` (A-E mapped to
the five role IDs), `synthesis`, and the independent `release` response below.
Retain the actual input hash on each advisor/peer response, including older rounds.
Set `council.reviewed_artifact_sha256` to the final candidate checked for release and
`council.profile_sha256` to this file's hash. Keep report and transcript files
beside the run too. The receipt makes missing/stale review detectable; it cannot
prove the reviewers judged well.

Resolve simple prose defects locally, then have an existing independent reviewer
check the fixes and reread the final article for repetitions introduced by edits.
Source or argument changes return to that stage and the affected reviewers.
Do not rerun all five for an unchanged argument or a verified HTML conversion.
Refresh the report to identify the exact final candidate and actual follow-up
reviews. Never relabel an old report as a review of new text. Stop after three
unsuccessful fix cycles and report the remaining issue without releasing it.

## Independent release decision

For the hosted Faith & Reason destination, [publication.md](publication.md)
runs this final check in GitHub Actions and captures the actual response. Do not
run a second local release check merely to populate an approval field.
For other destinations, use an existing council reviewer for this final check; do not add another full
council round. The writer cannot perform or fabricate this review. Generate its
input from the final Markdown candidate and completed council record:

```bash
python3 ~/.agents/prose/review.py release-packet DRAFT.md --review REVIEW.json --output RELEASE-PACKET.json
```

Give the reviewer this packet, the user's prose constraints, this profile and
the source evidence needed for unresolved source issues. It must read the entire
final candidate, all advisor/peer responses, and the writer's proposed dispositions.
Those dispositions are arguments to assess, not decisions to ratify. In
particular, reread passages whose cuts the writer rejected. Inspect each sentence
inside a useful paragraph; a useful fact cannot justify adjacent empty framing.

The reviewer returns a JSON object, without Markdown fences:

```json
{
  "status": "blocked",
  "artifact_sha256": "exact candidate hash from the packet",
  "council_sha256": "exact council hash from the packet",
  "assessment": "Located assessment of the final text and any remaining defects.",
  "open_findings": ["prose:P-02"],
  "dispositions": []
}
```

For a pass, `open_findings` is empty. `dispositions` must cover every ID in the
packet's `required_disposition_ids`, using the original reviewer namespace,
for example `prose:P-02` or `peer-1:PX-01`. The packet also includes a `:response`
entry for every advisor and peer; assess its entire response, including unnumbered
findings and ranges of IDs. Each item contains `id`, `status` (`resolved` or
`not-a-defect`), and `evidence` explaining the actual corrected text or the
source-based reason the finding was mistaken. Give new or unnumbered findings
IDs too. Keep unresolved IDs in `open_findings` and return `blocked`.

Retain this exact tool response and transcript. Embed its unedited JSON string
as `council.report.release.response`, with the actual reviewer/session identity
in `council.report.release.reviewer`. Do not compose a passing response yourself,
update its hashes, or remove its open findings. The verifier reads the reviewer's
decision and binds it to the candidate and complete council record. A blocked
result returns to editing. A chairman's summary cannot override it. Changed
content or council dispositions require the independent reviewer to refresh the
decision; unchanged HTML conversion reuses the verified master decision.

These checks detect missing, contradictory, or stale records. They do not
authenticate a model's identity or guarantee editorial judgment. Honest retention
of the actual responses remains required.
