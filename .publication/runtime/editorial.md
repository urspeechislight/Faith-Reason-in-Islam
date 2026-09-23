# Editorial review before filing or publication

The agent performs these steps inside the existing note/publication workflow.
Do not require the user to invoke another skill or manage review files.

Read contract.md and drafting.md before drafting or reviewing. The destination references own layout; article-workflow.md and
article-sources.md own sourcing. This procedure owns the final prose and meaning checks. It replaces
mandatory emphatic closers and backward/forward links. Readability measures and
phrase scans are cues for review, not proof of good prose.

1. Complete source verification and translation fidelity review on the working
   draft. Fix quotation boundaries, source metadata, and translations first.
   Inspect every source callout using paragraphs.md, including quotations and
   translations protected from the prose edit. Fix paragraph/speaker boundaries,
   quotation nesting and clipped passages before the baseline.
   Run the destination's structural validator. Record the exact commands and
   results; a cache check is not a fidelity check.
2. Save a baseline before the prose edit:
   `python3 ~/.agents/prose/review.py prepare DRAFT --snapshot BASELINE.json`
   The baseline hashes quotations, paired translations, tables, code, source
   metadata, and link targets. It is not evidence that those sources are correct.
3. Perform a full natural-prose-editor pass. Use the deletion test on every
   authored sentence, including headings, openings, card text and closings.
   Delete dispensable framing before rewriting mixed sentences. Read adjacent
   sections for repeated findings and forced transitions. Run
   `python3 ~/.agents/prose/review.py scan DRAFT --output SCAN.json` early and
   after the prose edit. This scan is advisory; zero cues is not prose approval. For site pages, article-polish also
   checks visual organization. Read each paragraph for what it claims and why
   the evidence supports it. Rewrite defective sentences or paragraphs from
   meaning. Inspect legitimate contrasts, negations, and qualifications before
   removing a phrase. Avoid mechanical replacements and word-count splitting.
4. Read the edited prose against the baseline and source evidence. Check names,
   dates, quantifiers, attribution, certainty, conditions, negation, and inference
   boundaries. Most/some/all/none changes need particular scrutiny. Flag an
   unsupported argument separately during prose-only editing. For an authorized
   substantive repair, correct it in the research stage and record the changed
   claim and supporting evidence before taking the editorial baseline.
5. Create the review record for the final candidate:
   `python3 ~/.agents/prose/review.py inspect DRAFT --snapshot BASELINE.json --output REVIEW.json`
   For HTML with source callouts, first run quote_layout.py capture as described
   in paragraphs.md; include `--render RENDER.json` in this inspect command.
   The generated record is pending. Read every listed block. Give each a keep
   or revised decision, a `function` from claim/evidence/explanation/inference/
   qualification/locator/heading/data, and a specific observation naming the
   content that would be lost by deletion. A generic "clear and accurate" is
   insufficient. Quote at least four consecutive words of the current block
   inside the observation (the whole text for shorter blocks), then explain
   its contribution or the edit. Different passages require different
   observations. Do not assign `heading` to a body paragraph.
   Block numbers are positional and change after insertion/deletion. Never
   copy observations by index, refresh their text/hash around old judgments,
   or fill remaining rows with generic comments. Reuse an observation only
   after matching unchanged content and checking its new context.
   Resolve every finding. `cue_resolutions` lists each current matched span.
   Remove/rewrite a defective span and regenerate the pending record; if a cue
   remains because it carries necessary meaning, mark it `legitimate` and give
   the contextual reason. Never waive a decorative phrase because it sounds
   scholarly. Recomputed cues prevent silently dropping flags from the record.
   Complete every `quote_layout_review` callout and its cue resolutions.
   Protected translations remain subject to paragraph, speaker, quote-nesting
   and completeness review. Source changes return to step 1 and a new baseline.
   Inspect the captured desktop/mobile screenshots; handoff preservation alone
   is not visual acceptance. Keep the browser output and screenshots in the run.
   Complete each `semantic_review` dimension with inspected block IDs and concrete
   observations, including unflagged prose. Pattern scans cannot detect every
   empty sentence, redundant introduction, irony or internal-process leak. Record evidence for source verification, translation
   fidelity, structural validation, and council review; use not-applicable only
   with a concrete reason, never for an unperformed required check. For existing
   source-aligned translations an earlier verified artifact may be cited if its
   exact protected bytes match. Otherwise review them against the source.
6. Run the article council in `council-article.md` on the substantive candidate
   before filing or publication. Embed its actual five advisor responses, peer
   reviews, anonymization mapping and synthesis in `council.report`; bind it to
   the candidate and profile hashes. A council status or score without these
   responses cannot pass. Do not fabricate or auto-fill evidence.
   Complete the profile's independent release check on the final master. The
   writer's synthesis cannot dismiss an unresolved prose defect as preference
   or required structure. Store the reviewer's actual JSON response; `passed`
   is read from that response, not inferred from the writer's approval field.
   For a verified unchanged Markdown-to-HTML handoff, cite the approved master’s
   council evidence instead of commissioning the same content review twice.
   The handoff must embed the master's baseline and review for re-verification.
   "Copied unchanged" is a preservation result, never a reason a prose cue is
   legitimate. Reuse the actual source judgment or review the cue in context.
   Scores are diagnostic; unresolved factual, fidelity, or editorial defects
   block release regardless of scores. Exegesis and narration have no
   difficulty-to-escape target. Coherence means an understandable relationship
   between ideas, not compulsory navigation or repeated conclusions.
7. Mark the record approved only after all required checks. Name the reviewing
   model/person and put concrete evidence in the preservation fields. Verify:
   `python3 ~/.agents/prose/review.py verify DRAFT --snapshot BASELINE.json --review REVIEW.json`
   Every prose block must be covered. Any byte change to the draft or shared
   review policy/implementation invalidates approval. Old receipts must be
   reviewed under the current schema; do not migrate them by filling defaults.
   For HTML reusing its unchanged master council, pass `--handoff HANDOFF.json`;
   the verifier checks conversion before accepting the master's council hash. Source changes require renewed source review
   and a new baseline with the prior audit trail retained.
8. File or publish the exact checked artifact. Recheck the destination copy.
   Shell, Python, SSH, Write, and Edit all use this same final-artifact check.
   Tool hooks are early feedback only; they do not certify the finished text.

For website Git publication, store records in
`.prose-reviews/<page-stem>.baseline.json` and
`.prose-reviews/<page-stem>.review.json`, committed with the article. The Titan
pre-push hook checks the article and records from the outgoing commit, not the
working tree. Unchanged historical articles need no retroactive receipt. For
vault notes retain the records next to the working draft, verify before copying,
and check the filed copy with the same records.

These records make omissions and stale approval detectable. They cannot prove
a reviewer's judgment is correct. Do not auto-fill observations, approvals, or
source results. Test quality with real rejected/accepted examples and an
independent reader; do not rely on model self-scores alone.
