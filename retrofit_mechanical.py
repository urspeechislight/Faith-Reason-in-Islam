#!/usr/bin/env python3
"""Batch-mechanical retrofit for legacy Faith & Reason pages.

Adds, append-only and idempotently:
  1. <main data-category="...">
  2. the hash-handling script (opens tab panes / accordions on #hash)

Prose, ids, and Arabic blocks are untouched (Arabic hashes verified before
and after). Facts blocks and content-named heading renames are NOT done
here; those need per-page judgment and are applied separately.

Usage: python3 retrofit_mechanical.py [page.html ...]   (no args = all known)
"""
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path.home() / "code" / "Faith-Reason-in-Islam"

CATS = json.loads((Path(__file__).parent / "retrofit_inventory.json").read_text())

SCRIPT = '''
    <script>
    (function () {
        function openHash() {
            var id = decodeURIComponent(location.hash.slice(1));
            if (!id) return;
            var el = document.getElementById(id);
            if (!el) return;
            var pane = el.closest('.tab-pane') || el.closest('.accordion-item');
            if (pane && pane.classList.contains('tab-pane')) {
                var btn = document.querySelector('[data-target="' + pane.id + '"]');
                if (btn) btn.click();
            }
            setTimeout(function () { el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 250);
        }
        window.addEventListener('hashchange', openHash);
        window.addEventListener('DOMContentLoaded', function () { setTimeout(openHash, 100); });
    })();
    </script>
</body>'''


def rtl_hashes(src):
    return [hashlib.sha256(m.group(0).encode()).hexdigest()
            for m in re.finditer(r'<p class="rtl[^"]*"[^>]*>.*?</p>', src, flags=re.S)]


def retrofit(path: Path) -> str:
    src = path.read_text()
    before = rtl_hashes(src)
    changed = []

    if "data-category=" not in src:
        cat = CATS[path.name]["cat"]
        if src.count("<main>") == 1:
            src = src.replace("<main>", f'<main data-category="{cat}">', 1)
            changed.append("data-category")
        elif "<main" in src:
            src = re.sub(r"<main(?![^>]*data-category)", f'<main data-category="{cat}"', src, count=1)
            changed.append("data-category")
        else:
            return "SKIP: no <main> tag"

    if "hashchange" not in src:
        assert src.count("</body>") == 1
        src = src.replace("</body>", SCRIPT, 1)
        changed.append("hash-script")

    after = rtl_hashes(src)
    assert before == after, f"{path.name}: ARABIC BLOCKS CHANGED, aborting"
    if changed:
        path.write_text(src)
    return f"OK: {', '.join(changed) if changed else 'already done'}"


def main():
    pages = sys.argv[1:] or list(CATS)
    for name in pages:
        p = REPO / name
        if not p.exists():
            print(f"{name}: MISSING")
            continue
        try:
            print(f"{name}: {retrofit(p)}")
        except AssertionError as e:
            print(f"{name}: ABORTED ({e})")


if __name__ == "__main__":
    main()
