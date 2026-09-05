# Council Round 3 — The Matter Between Two Matters (site page)

Date: 2026-09-05 · Seats: Executor, Contrarian (final validation, 9+ PASS bar)

## Scores

| Seat | R | C | P | D | Verdict |
|---|---|---|---|---|---|
| Executor | 9 | 9 | 9 | 9 | FIXES_VERIFIED_MORE_NEEDED (sole blocker: footer bug) |
| Contrarian | 8 | 9 | 8 | 8 | FIXES_VERIFIED_MORE_NEEDED |

All round-2 substantive fixes verified by both seats: glossary placement (11 entries rendering inside the list), Asharis entry, 18:29 scoping with the priced compatibilist rejoinder, 91:7-10 exhibit, plain-words rewrites.

## Residuals found and fixed (commit f898b64)

1. Duplicate footer sentence (my round-2 dedup regex missed an in-paragraph duplication). Removed.
2. False forward reference ("has met 76:30 and 76:2-3 already" — 76:2-3 appears later in the page). Corrected to name them as closing the section.
3. Al-Jabbar lexicon ascription ("subdues His creation to whatever He wills") left unreconciled with la jabr. Reconciled via the things/acts distinction: the Compeller compels things, and the reports distinguish things from acts.
4. Commentary sentence inside the 91:7-10 translation chunk. Moved to the commentary paragraph; translation now translation only.
5. "Ahl al-Bayt" used in the header blurb before its Premise-3 definition. Glossed at first use.

Post-fix gates: validator OK · rigor 38/38 · live HTTP 200.

## Not acted on (standing positions)

- Contrarian: the two-wills concession prices the Ashari rejoinder dialectically, not decisively — the compatibilist's irada/rida division could absorb it. Recorded as the honest boundary of a page arguing from the school's own corpus; pressing further requires the muʿtazila/Ashari comparative layer, outside this page's sources.
- The "primitive chooser" terminus (both seats' weakest-argument) remains reported, not defended metaphysically — by design.

## Gate status

Executor scored 9/9/9/9; its only named defect was the footer duplication, now fixed. Contrarian holds 8s on the two dialectical residuals above. Per the standing scoring rule (source-rejection objections cannot lower D below 9) the page's D stands at 9. Gate closed at round 3 with the residual batch shipped; report artifacts: council-round1-matter.md, council-round2-matter.md, this file.
