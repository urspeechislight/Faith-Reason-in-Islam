# Council Transcript — hadith-authentication.html quality gate (2026-08-26)

Question: score the live debate page on readability, comprehensiveness, persuasiveness,
difficulty-to-escape, and connectedness; name broken links, weakest argument, biggest
gap, flipped negations. Three runs with fix cycles between them. Full report:
`council-report-1787785600.html`.

## Run 1 (after ship, commit 1aa8333)

- Contrarian: R7 C7 P7 D6 Cn6. Flipped quantifier on al-Khoei (¬∀ read as ∀¬, 3 sites);
  garbled sentence in a12; 'Ilal scope flip in commentary; Premise 3 promised not
  delivered; Khomeini/Uddat Facts rows missing.
- First Principles: R9 C7.5 P8 D7 Cn7. Both loads structurally carried; circularity
  (gates commanded by the corpus under test) unaddressed; quantifier flip.
- Expansionist: R9 C7 P8 D8 Cn7. Worked tarjih from Tahdhib named as the single
  highest-value addition; two exempted books unnamed.
- Outsider: R7 C7 P7 D6 Cn6. Front-loaded abstractions (companions of consensus,
  4,000 students) unexplained until section 6; Akhbari never explained; quantifier flip.
- Executor: R9 C7 P7 D6 Cn7. Three hatches tested: gates-fail-in-practice CLOSED
  (Kulayni/Khoei concessions), gate-circularity OPEN, departure-rule HALF-CLOSED;
  Ibn Asbat chain (contains al-Sayyari) fails the page's own test; quantifier flip.

Fix cycle 1 (164774a): quantifier fixed at 4 sites; garble repaired; 'Ilal scoped as
jurists' reading; Sistani direction unified; 5 bridges (Tusi->Mina, Kulayni->
Hanzala, Jahm->Asbat, Ashim->Uddat); Premise 3 delivered in a12 (wathaqa principle +
dismantling specifics); Akhbari + khabar glossary entries; 2 Facts rows added.

## Run 2

Scores R8.4 C7.6 P7.7 D6.9 Cn7.2. New catches: glossary duplicate sentence survived
pass 1's fix; Facts-row direction flip (khudh bi-ma khalafa = take what DIFFERS, row
said "rejects"); 'Ilal marked reported while mursal (should be attributed); section 3
intro promises reconciliation exhibit that does not exist; two books still unnamed;
Righteous Servant unglossed; 4 remaining links implicit; back-loaded bridges noted.

Fix cycle 2 (1de3f22): all of the above fixed; 3 more bridges moved to open sentences
where feasible; verdict softened ("the gates rest on the school's own transmitted
commands").

## Run 3

Scores R8.5 C7.9 P8.0 D6.9 Cn7.8. Zero flipped negations (each advisor polarity-checked
the Arabic). Remaining critiques repeat from runs 1-2 verbatim and are evidence-bound:
- gate-command transmission (ladder via Awali = attributed; 'Ilal = attributed)
- no worked tarjih example
- Akhbari counterposition held to a glossary line
- Ibn Asbat's own wording carries no limiter

Termination: run 3's gains came from prose; the residual findings are properties of
the evidence. Stopped per the no-improvement rule.

## Verification record

- Validator: OK every cycle; FK 9.26 -> 9.35 -> 9.43 -> 9.4x band (ceiling 10.5).
- Arabic: 12 blocks, all byte-verified verbatim on titan (Mustadrak 17/302-305;
  'Uyun 1/248-249; 'Ilal 2/221; Tahdhib 1/52-53; Kafi 1/56-57; Ta'adul 192-193;
  Mu'jam 1/110, 1/113).
- Translation: 12 units via translate.py, constraints clean, one litotes post-edited,
  speech-intro colons converted, ligatures wrapped.
