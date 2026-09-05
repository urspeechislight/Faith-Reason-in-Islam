# Council Round 2 — The Matter Between Two Matters (site page)

Date: 2026-09-05 · Seats: Executor, Contrarian, Outsider (fix verification + fresh scoring)

## Scores

| Seat | R | C | P | D | Verdict |
|---|---|---|---|---|---|
| Executor | 8 | 9 | 8 | 9 | FIXES_VERIFIED_MORE_NEEDED |
| Contrarian | 9 | 9 | 8 | 8.5 | FIXES_VERIFIED_MORE_NEEDED |
| Outsider | 6 | 8 | 7 | 7 | FIXES_VERIFIED_MORE_NEEDED |

Averages: R 7.7 / C 8.7 / P 7.7 / D 8.2.

## Round-1 fix verification

All six round-1 fixes verified present and substantive by every seat — with one critical placement bug found by all three: the AH/takfir/Ahl al-Bayt glossary entries had been inserted AFTER `</html>` (orphaned `<dt>/<dd>` markup rendering as stray text below the footer). This was the single largest driver of the Outsider's R6.

## Fixes applied (commit f69b41a)

1. Orphaned glossary markup removed; the four entries (AH, takfir/tashrik, Ahl al-Bayt, **Asharis** — new, flagged undefined by Outsider) re-inserted correctly inside the glossary `<ul>` in its native `<li><strong>` shape.
2. takfir/tashrik glossed in plain words at its first prose use.
3. 18:29 commentary scoped: the overclaim "leaves nothing to a decree reading" replaced with what the grammar proves against the flat decree reading, plus the compatibilist rejoinder named and priced (it must concede the Merv two-wills division, after which the imperative addresses the settling, never replaces it).
4. 91:7-8 exhibit replaced by the full **91:7-10** span (corpus bytes from the treatise p.133): the purify/bury pair now text-grounds the knowledge-not-choice gloss inside the exhibit itself.
5. "epistemic" rewritten in plain words (the boundary of knowing, not of force).
6. Duplicated footer line removed.

Post-fix gates: validator OK · rigor 38/38 · live HTTP 200.

## Residuals noted, not acted on

- Contrarian: the bestowal bridge answers the narrow selection question, leaves the broad withholding question (why God does not always prevent) to wisdom — half answer, half restatement. Deliberate: the page reports the school's answer, and the corpus's own framing (the son-of-Adam speech, the ʿIlm al-Yaqīn intervention report with its warning context) is already on the page.
- Outsider: dense sentences in the Merv-negation and Muhsini translation stretches. These are the source texts' own periodic constructions; the wall-of-text rule is satisfied at the element level and the register is the site's dense-scholarly canon.

## Round 3

Trajectory R 8.2→7.7 (placement bug, now fixed) · C 8.1→8.7 · D 8.4→8.2. Round 3 dispatched on the fixed page.
