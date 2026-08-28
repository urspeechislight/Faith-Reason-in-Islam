# Council Transcript — Site Structure Framework

**Date:** 2026-08-14
**Subject:** One structural framework for the Faith & Reason in Islam essays site

## Original question

Design a consistent page-structure framework for the static HTML essays site. Current inconsistency survey: (A) Polemical refutation essays with inconsistent openings ("The Argument" / "The Argument Under Examination" / question-first / "The Christian Claim" / "What This Note Does NOT Claim"), most with thesis-box + premise/conclusion cards, four with tab bars currently mid-page after the intro; (B) Quranic linguistic analysis (verse callout first, thesis box, flowing sections, no tabs); (C) hadith commentary series (Arabic blockquote + Commentary, top series nav, no tabs); (D) reference/landing pages. Must answer: (1) opening convention — one pattern or per-type, exact element order; (2) tab bar placement — under header with intro folded into an "Overview" tab, or intro first then tabs, or jump-bar; (3) section conventions — tabs vs flowing vs cards, inner accordions; (4) missed consistency rules. Constraints: static HTML, no build step, hand-edited, must be simple to apply by hand.

## Anonymization mapping (revealed)

- Response A = The Executor
- Response B = The Contrarian
- Response C = The Outsider
- Response D = The First Principles Thinker
- Response E = The Expansionist

## Advisor responses (verbatim)

### The Contrarian (B)
The fatal flaw is the premise: designing a consistency framework for a system with no enforcement mechanism. Sixteen hand-edited HTML pages, no build step, no templating, Tailwind CDN. Whatever rules you decree today will drift within three pages, because nothing checks them — the survey itself is a catalog of drift. A rulebook doesn't fix hand-editing; hand-editing produces rulebook violations. The only durable fix is the excluded thing: a build step, or at minimum a shared header/nav include via a tiny script. If you refuse that, accept this is a one-time cleanup, not a "framework," and say so honestly. Second flaw: the tab-bar fix is probably wrong. Moving tabs above the intro and folding the argument into an "Overview" tab buries the thesis behind a click — on a static site, likely also hidden from search engines depending on how panes render. The first thing a reader of a refutation essay needs is the claim being refuted and the thesis. Tabs belong below the intro. The cure for mid-page tabs is moving them up to just under the intro, not swallowing the intro into tab one. Third: opening inconsistency is partly correct behavior. Question-first works for question-titled pages; sanction two openings (thesis-first for refutations, question-first for question-titled pages), not one. Missed rule: no canonical rule for what the conclusion card links to next — that's where readers leak out.

### The First Principles Thinker (D)
The wrong question is being asked. The survey treats pages as layouts and asks how to arrange furniture. First-principles: what is a page FOR? Every page does exactly one thing — advance one proposition and marshal evidence for it. Tabs, cards, callouts, tables are all "evidence blocks" under a thesis. Rebuild from that: (1) Opening: one pattern for all 16 pages — eyebrow (type label) → h1 → subtitle → thesis box stating the single claim. Question-headings are fine as h1s — a question is a thesis awaiting a verdict — but the thesis box must follow immediately. Per-type conventions are what produced the current mess. (2) Tabs: the premise "intro precedes tabs" is false once reframed — the intro IS the first evidence block, not a preamble. Tab bar directly under the thesis box, intro folded into tab 1 ("Overview"). Anything between the thesis and the navigation that delivers it is a broken promise. (3) Sections — rule of the count: one thread = flowing h2s; 2-3 parallel evidences = cards; 4+ siblings = tabs. Kill inner accordions — nesting collapsible structure inside a tab makes readers hunt for content they already navigated to. Accordions only for optional apparatus (full Arabic chains). (4) Missed rule: nav is chrome, not content — identical on all 16 pages.

### The Expansionist (E)
A latent product, not a normalization chore: a coherent corpus-grounded theological library — exactly the long-form primary-source content that survives the AI-content flood and gets rewarded by search and answer engines. (1) One opening pattern as an asset: question-first h1 mirroring the actual search query, subtitle as one-sentence thesis answer, then thesis box. Question-shaped h1s + immediate answers are what featured snippets and LLM citations extract. Types B/C get a sanctioned variant (verse/hadith callout first) but every page resolves to a stated thesis within the first screen. (2) Tabs directly under the header, intro folded into an "Overview" tab — and the missed upside: each tab is a standalone answer to a distinct sub-question; give each tab pane its own anchor URL and an h2 that reads like a query. Four essays become ~20 individually linkable, citable arguments. (3) Expand the type system upward: tabs = parallel independent cases; cards = sequential logic; flowing = sustained argument. Promote "Example/Implication" accordions into visible sub-headings or their own tabs. (4) Biggest missed asset: the index — grouped by type with each page's thesis as its description.

### The Outsider (C)
Types A/B/C/D don't exist for a first-time reader; I just click links from the index. One recognizable opening, same order every time: eyebrow, h1, one-line subtitle saying what claim this page addresses, then a 3-5 sentence plain-English summary. No thesis boxes, no premise cards before I've read a single word. Mid-page tabs are invisible — scrolled past twice. But folding the intro into an "Overview" tab hides the single most important paragraph behind a click; most readers never open tab 2. Intro FIRST, in full, then the tab bar, then the panes. If you want tabs "at the top," put a slim jump-bar of anchor links under the header that scrolls to the tab bar. Never put content people must read inside a hidden tab. Kill the tabs entirely if you can: on a phone five tabs are an overflow mess; flowing h2 sections with a sticky top anchor-nav are printable, searchable, and work when JS hiccups. Every tab bar is a liability you'll hand-maintain forever. Missed: Arabic callouts have no visible translation hint above the fold on some pages — for non-Arabic readers the page is decoration. And "isiah_9_6" as a filename is unspellable.

### The Executor (A)
Monday morning, in order. (1) Opening: one pattern, no exceptions — thesis-first because 8 of 16 pages already do it. Exact order: back-to-index nav; eyebrow (REFUTATION · 6 PARTS / QURANIC ANALYSIS / HADITH COMMENTARY · PART 3 OF 7); h1; one-line subtitle (the question being answered — absorbs question-type headings); thesis box. Type B already does this minus eyebrow; Type C moves the thesis box after the Arabic blockquote — one cut-paste. 16 hand edits, done by lunch. (2) Tabs: directly under the header, intro folded into tab 1 renamed "Overview" — verdict, not options. Mid-page tabs mean readers never discover tabs 2-6 exist; top tabs advertise full contents before any scroll. The intro doesn't deserve special placement; it's just content. Cut the argument section, paste into first tab pane, move tab bar markup after the thesis box. 4 pages, ~10 minutes each. (3) Section rules: 3+ parallel evidences of similar weight → tabs; one sequential argument → flowing h2s; premise/conclusion cards only inside Overview tab or flowing sections; kill inner accordions (Introduction/Example/Implication/Conclusion), flatten to bolded lead-ins — nested disclosure widgets inside tabs is two navigation systems stacked. (4) Missed rule: rename all intro sections to "Overview" — one word, everywhere.

## Peer reviews (summary)

- **Reviewer 1:** Strongest A — respects the constraint, concrete edit list. Biggest blind spot B — critique of the premise is not a deliverable. All missed: migration cost asymmetry and inbound/anchor breakage; no exit rule.
- **Reviewer 2:** Strongest A — engineer with a budget. Blind spot D — "intro is the first evidence block" produces the worst reader outcome (buried content); never engages reading-behavior evidence. All missed: verification mechanics ("definition of done"), tab markup choice (pure-CSS vs JS, no-JS behavior).
- **Reviewer 3:** Strongest D — reframes rather than rearranges; the count rule is the only mechanical decision procedure. Blind spot E — speculative SEO, per-type variants are drift-generating pluralism. All missed: verification and rollback for hand-editing; mobile behavior; migration order (reference page first).
- **Reviewer 4:** Strongest D — derives every ruling from one axiom. Blind spot E — answers a question nobody asked; hand-waves JS/fragment complexity. All missed: the actual artifact — a paste-able HTML skeleton template; rules without a template is how the current drift happened.
- **Reviewer 5:** Strongest D — generative principle; mechanical count rule. Blind spot E — technically shaky on hidden tab content vs extractors. All missed: enforcement within constraints (skeleton + checklist + 10-line lint script); conclusion/next-step rule.

## Chairman's synthesis

**Agreements:** one opening pattern (nav → eyebrow → h1 → subtitle → thesis box); mid-page tabs are a real failure; flatten nested accordions; the rule of the count for section choice.

**Clash:** the intro's fate when tabs move up — fold into "Overview" tab (Executor, First Principles, Expansionist) vs. never hide the intro (Contrarian, Outsider). Reviewers split 2 (Executor) / 3 (First Principles) on strongest.

**Blind spots caught:** no enforcement mechanism (mitigate with skeleton template + checklist); uncosted migration; no exit/next-reading rule; tab mechanics unexamined; Outsider's translation-visibility and filename points.

**Recommendation (chairman, resolving the clash):** separate the thesis from the intro. The thesis box stays above the tab bar on every page — the must-read paragraph is never hidden. The longer intro (background, premise cards, conclusion card) becomes the first tab, "Overview." Tab bar directly under the thesis box. This honors the First Principles axiom, the Executor's element order, and the Outsider's behavioral evidence.

Framework rules:
1. Universal skeleton: top nav (chrome) → eyebrow (type label) → h1 → one-line subtitle → thesis box → content area.
2. Content area by count: 1 thread → flowing h2 sections; 2–3 parallel evidences → cards; 4+ siblings → tabs (bar under thesis box; first tab "Overview").
3. All opening labels retire to "Overview". Question-form h1s allowed; subtitle carries the one-line answer.
4. Inner accordions flatten to bold sub-headings; accordions only for optional apparatus.
5. Exit rule: conclusion + next-reading link at the end of every page.
6. Enforcement: canonical skeleton template + per-page checklist in the repo.

**One thing to do first:** Convert the four tabbed refutation pages (umm-kulthum-marriage, ali-forbearance, hasan-mitlaq, quran-preservation), starting with umm-kulthum-marriage as the reference implementation.
