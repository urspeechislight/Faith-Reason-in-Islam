# Council Transcript — ali-forbearance.html quality gate (2026-08-25)

Framed question: score the live debate page on readability, comprehensiveness, persuasiveness,
difficulty-to-escape, and connectedness; name every broken link, the weakest argument, the
biggest gap, and any flipped negation. Three runs with fix cycles between them; the full
council report with scores and fix lists is `council-report-1787679060.html`.

## Run 1 (after the full skill redo, commit 7d74b30)

- Contrarian: R7 C8 P6 D5 Cn6. Causal core all Sulaym; forty/four contradicts Mustadrak; ridda
  unexhibited; fitna-gloss flipped; duplicate al-Baqi quote.
- First Principles: R8 C8 P7 D6 Cn7. Command single-sourced; promise verse closes on assertion;
  "another account" flipped; 6+ missing bridges.
- Expansionist: R8 C8 P8 D7 Cn7. Ghadir unexhibited; ridda gap; Rounds by Night underused; two
  integrity slips ("the shura's men had opened with fire"; dangling Umm Kulthum reference).
- Outsider: R6 C8 P7 D6 Cn6. No cast list; qualifier column undefined; coerced-pledge special
  pleading; "twenty-five years of silence" flipped.
- Executor: R8 C8 P7 D6 Cn6. Premise 4 single-sourced; acceptance counter never faced; "his own
  silence" flipped; Tabuk objection (peer review found it already answered on page).

Peer review (5 seats): strongest responses A/C; Outsider response had the biggest blind spot
(presentation only); all seats caught the pledge-timeline contradiction and the
epistemic-contract inversion as council-wide misses.

Fix cycle 1 → commit 7aa2aaf: tab3-3 exhibit (Zurara via al-Tustari 4/420; al-Baqir via Ilal in
al-Muhsini 2/141; both corpus-verified) making the motive multi-chained; four flipped negations
fixed; two integrity slips fixed; forty/four made faithful to the Mustadrak text; pledge timeline
reconciled; honest audience line; nine bridges; Facts row added.

## Run 2

Scores R7.2 C8.2 P7.1 D6.4 Cn6.8. Regression found: a garbled sentence in the pledge-timeline
paragraph and a new flipped negation in the fitna gloss ("did not leave the wrong to grow").
Ridda premise still unexhibited; qualifier asymmetry (late sources unqualified); Ibn Abi al-Hadid
labeling inconsistent; nav labels truncated mid-word (markup-level, caught in run 3).

Fix cycle 2 → commit 1d497d1: tab6-1b ridda exhibit (Bukhari 8/140 Abu Hurayra/Umar; Aisha via
Ibn Ishaq in Ta'rikh al-Khamis 2/201; both corpus-verified) grounding the Arabia-in-crisis
premise in the Sunni canon; garbled sentence repaired; fitna flip fixed; weak-chain qualifiers on
Kashf al-Yaqin and al-Daylami; six bridges; ridda Facts row (stated).

## Run 3

Scores R7.4 C8.3 P7.6 D6.8 Cn7.2. Zero flipped negations (byte-checked against the Arabic).
Remaining named weaknesses are evidence-bound, not prose-bound: the conditional command is
Sulaym-only (no independent chain exists in the corpus); Ghadir/the right itself is out of scope
for this page; the Bukhari reconciliation reading remains contested ground. Convergence across
advisors on stopping: no dimension improved by a full point run-over-run.

Fix cycle 3 → commit e7d05eb: nav labels restored; timeline chronology inversion repaired; nine
bridges; forty-men threshold carries the "insight of the four" point; Verse of the Promise
labeled as the school's own reading; Miqdad source honesty; Usama attribution; Harun wording.

## Verification record

- Structural validator: OK on every cycle; FK 9.7 → 9.59 (ceiling 10.5).
- Arabic: 97 blocks at ship, byte-identical across all cycles; +2 blocks cycle 1 (Zurara, Baqir),
  +2 blocks cycle 2 (Bukhari ridda, Aisha), all verified verbatim against titan corpus loci
  (Mustadrak 11/76; Bihar 18/397-399; Bihar 29/213; al-Tustari 4/420; al-Muhsini 2/141;
  Bukhari 8/140; Ta'rikh al-Khamis 2/201). 101 blocks total at final state.
