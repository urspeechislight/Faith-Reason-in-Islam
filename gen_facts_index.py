#!/usr/bin/env python3
"""Generate the site-wide facts index (facts.html) from article Facts blocks.

Reads every article's <section id="facts"> tables and aggregates them into
one page grouped by category, then article, each row linking to
<article>.html#anchor. Regenerate whenever any article ships or its Facts
block changes; never hand-edit the output.
"""
import json
import re
from pathlib import Path

REPO = Path.home() / "code" / "Faith-Reason-in-Islam"
INV = json.loads((REPO / "retrofit_inventory.json").read_text())

ORDER = ["debate", "exegesis"]
CAT_LABEL = {"debate": "Debate Articles", "exegesis": "Exegesis Articles"}


def title_of(slug: str) -> str:
    src = (REPO / slug).read_text()
    m = re.search(r"<title>([^<]+)</title>", src)
    t = m.group(1).strip()
    t = re.sub(r"\s*[—–-]\s*Faith.*$", "", t).strip()
    return t


def extract_facts(slug: str):
    """Return [(subtable_title, [row_cells_with_first_anchor])] from a page."""
    src = (REPO / slug).read_text()
    m = re.search(r'<section id="facts".*?</section>', src, flags=re.S)
    if not m:
        return []
    ftxt = m.group(0)
    out = []
    for sec in re.findall(r'<div class="analysis-section">(.*?)(?=<div class="analysis-section">|$)', ftxt, flags=re.S):
        hm = re.search(r'analysis-heading[^>]*>([^<]+)<', sec)
        title = hm.group(1).strip() if hm else "Facts"
        rows = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", sec, flags=re.S):
            cells = [re.sub(r"<[^>]+>", "", c).strip()
                     for c in re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.S)]
            am = re.search(r'href="#([^"]+)"', r)
            if cells:
                rows.append((cells, am.group(1) if am else None))
        if rows:
            out.append((title, rows))
    return out


def main():
    parts = []
    for cat in ORDER:
        items = [(slug, meta) for slug, meta in INV.items() if meta["cat"] == cat]
        rows_any = False
        cat_html = [f'<section class="mt-10"> <h2 class="font-serif text-2xl font-bold mb-6 text-[#8A6D3B]">{CAT_LABEL[cat]}</h2>']
        for slug, _meta in items:
            facts = extract_facts(slug)
            if not facts:
                continue
            rows_any = True
            cat_html.append(
                f'<h3 class="font-serif text-xl font-bold mb-4 text-[#3D4451]">'
                f'<a class="hover:text-[#8A6D3B]" href="{slug}">{title_of(slug)}</a></h3>')
            for title, rows in facts:
                cat_html.append(f'<div class="analysis-section"><h4 class="text-sm font-semibold tracking-wide uppercase text-[#8A6D3B] mb-2">{title}</h4>')
                cat_html.append('<div class="premise-card overflow-x-auto mb-6"><table class="w-full text-sm">')
                # header from first row's arity
                first_cells = rows[0][0]
                if len(first_cells) == 7:
                    heads = ["Claim", "Actor", "Date", "Place &amp; control", "Source", "Qualifier", "Detail"]
                elif len(first_cells) == 4:
                    heads = ["Reading", "Basis", "Qualifier", "Detail"]
                else:
                    heads = [f"Col {i+1}" for i in range(len(first_cells))]
                cat_html.append('<thead><tr class="text-left">' + "".join(
                    f'<th class="py-2 pr-4 font-semibold">{h}</th>' for h in heads) + "</tr></thead><tbody>")
                for cells, anchor in rows:
                    tds = []
                    for i, c in enumerate(cells):
                        c = re.sub(r'(?<!class="honorific">)([\uFD3F-\uFDFA])', r'<span class="honorific">\1</span>', c)
                        if i == len(cells) - 1 and anchor:
                            tds.append(f'<td class="py-2"><a class="text-[#8A6D3B] underline" href="{slug}#{anchor}">&#8599;</a></td>')
                        else:
                            tds.append(f'<td class="py-2 pr-4">{c}</td>')
                    cat_html.append('<tr class="border-t border-[#E7E0D1]">' + "".join(tds) + "</tr>")
                cat_html.append("</tbody></table></div></div>")
        cat_html.append("</section>")
        if rows_any:
            parts.append("\n".join(cat_html))

    page = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Every key claim, actor, date, place, and source across the Faith and Reason in Islam articles, indexed for debate reference. Each row links into the article carrying the detail.">
    <title>The Fact Index · Faith &amp; Reason in Islam</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; background-color: #FDFBF7; color: #3D4451; }}
        main p {{ line-height: 1.7; }}
        .font-serif {{ font-family: 'Playfair Display', serif; }}
        .premise-card {{ background-color: #F7F4EC; border: 1px solid #E7E0D1; border-radius: 0.5rem; padding: 1rem 1.25rem; }}
        .analysis-section {{ margin-bottom: 1.5rem; }}
    </style>
</head>
<body class="antialiased">
    <div class="max-w-4xl mx-auto px-4 py-8 md:py-12">
        <nav class="mb-10">
            <a href="index.html" class="text-sm text-gray-500 hover:text-[#8A6D3B]">&larr; Faith &amp; Reason in Islam</a>
        </nav>
        <header class="mb-12">
            <p class="text-sm font-semibold tracking-widest uppercase text-[#8A6D3B] mb-3">Debate Reference</p>
            <h1 class="font-serif text-3xl md:text-5xl font-bold text-[#3D4451] mb-3">The Fact Index</h1>
            <p class="text-md md:text-lg text-gray-600 max-w-2xl">Every key claim, actor, date, place, and source across the articles, gathered in one place. Each row links into the article carrying the detail, and the Qualifier column preserves how firmly the sources state each claim.</p>
            <hr class="mt-10 border-[#E7E0D1]">
        </header>
        <main data-category="facts-index">
        {"".join(parts)}
        </main>
    </div>
    <footer class="text-center mt-16 pt-8 border-t border-[#E7E0D1] max-w-4xl mx-auto px-4">
        <p class="text-sm text-gray-500">&copy; 2025 Faith &amp; Reason in Islam · All Rights Reserved</p>
    </footer>
</body>
</html>
'''
    (REPO / "facts.html").write_text(page)
    n_rows = page.count('<tr class="border-t')
    print(f"facts.html written: {len(page)} bytes, {n_rows} fact rows")


if __name__ == "__main__":
    main()
