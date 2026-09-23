# Draft from evidence

Read with contract.md before the first sentence. Apply while building each
section; the final editorial pass catches failures that survive this stage.

## Before drafting

Read `~/.agents/prose/paragraphs.md`. Draft paragraph and quotation boundaries
in the Markdown master as each section is written; do not defer them to rendering.

Keep the research map, search strategy, source-selection instructions, reviewer
advice and publication status in the run dossier. Draft from a smaller map of
reader-facing claims, source passages, necessary inferences and qualifications.
A user's instruction to investigate criticism is a research task, not a fact or
a voice for the article. Test allegations and adverse evidence before accepting
them. Attribute borrowed arguments when they are used; never invent independent
discovery or hide a material source dependence.

Choose section headings that name the subject or finding. Give each section one
reason to exist. A quotation need not have its own introduction, paraphrase and
conclusion. Closely related quotations can share one explanation. Required fact
cards locate evidence; they do not require another prose description of the card.

## While drafting

Start with the event, claim or answer. Supply only the background needed to
understand it. Write the opening after the body, using the supported answer and
any indispensable limit; do not summarize every section or announce the method.
Keep a question only when the question itself defines a real uncertainty.

For every authored sentence ask what the reader would lose if it disappeared.
Keep a fact, explanation, inference, necessary qualification or useful locator.
Delete a sentence that merely announces evidence, certifies fairness, repeats a
finding, narrates the source's literary movements or praises the research.
When a sentence mixes substance and decoration, retain the substance in plain
words. Deletion is an available edit; do not replace every removed sentence.

Attribution is substantive when it tells the reader whose claim this is or how
well it is supported. "Ibn Hajar reports that eight poets elegized him" is useful.
"The entry keeps the mourning on the record" adds no historical information.
"The manuscript ends mid-sentence" is useful only after inspecting the manuscript
or adequate source evidence. A clipped search result is not a damaged manuscript.

Evaluate each sentence separately: one useful claim does not justify the
empty framing beside it. "One relay preserves the shape of the scene" adds
nothing before "The men cast their pens, and Zakariyya's lot came out."
Delete the first sentence. "The envoy's silence on the spot is the report's
own detail" repeats information if the paragraph already says he could not
answer. Delete it. "If Muqatil falls, the idiom stands" needs a precise account
of which independently sourced evidence supports which inference. Name that
evidence once without staging a victory over an imagined hostile reader.
These defects remain defects in a polemical or scholarly register.

Explain an inference once, beside the evidence. A necessary contrast or negation
may carry the claim. Do not add an unasked alternative to give a sentence force.
Do not split a decorative contrast into two sentences and call it repaired.
Do not add litotes, irony, sneering qualifications, personified evidence or
concessive drama such as "whatever the councils judged". Preserve those features
inside actual source quotations when fidelity requires them.

## Stop failures before the next section

Read the section with the quotations collapsed, then compare it with the sources.
Can the reader follow the facts and reasoning? Cut dispensable first/last
sentences and duplicate explanations across the heading, card and body. Check
that deletion preserved who said what, uncertainty, dates, negation and scope.
Run `python3 ~/.agents/prose/review.py scan DRAFT --output SCAN.json` for early
feedback. Cues are questions to resolve in context, not automatic rewrite rules.
A zero-cue result does not waive this sentence-by-sentence reading.

When revising, change the sentence's job, not just its wording. Replacing
"So yes" with "The answer to the opening question is yes" leaves the same
empty introduction. Start with the answer itself. Replace "One qualification
belongs here" and "The provenance has a limit that matters" with the actual
qualification or provenance. Delete "The reading is not a single stray voice"
when the next sentence already identifies its several sources. Explaining a
limit is useful; announcing that a limit will be explained is dispensable.
Do these edits before recording approval observations. A review observation
must assess the prose, not invent a defense for keeping the draft's cadence.

Finish when the last necessary point is made. Commentary need not have a separate
recap. A required category close should state the answer and its essential limit
once; do not repeat the article as findings, qualifications and a final verdict.

## Calibration

These are prose examples, not fresh historical verification.

- "Eight poets are named ... Whatever the councils judged, the school's own
  biographical dictionary records him mourned in verse."
  Keep the sourced count once: "Ibn Hajar names eight poets who elegized him
  and mentions many others." Delete the concession. If the preceding sentence
  already gives this fact, delete the entire restatement.
- "The same entry's roll of elegists keeps the mourning on the record."
  Delete when the mourning has already been established. Do not replace it with
  "The elegies attest to his reception" or another abstract summary.
- "The reasoning is stated plainly." Delete; begin with the reasoning.
- "His verdict is categorical ... his own verdict, not ... a finding."
  Identify the attribution and the actual evidentiary limit. Do not replace an
  unsupported finding with a stylistic euphemism.
- "The evidence does not establish an exact date." Keep if warranted: removing
  the negation would reverse the finding.
