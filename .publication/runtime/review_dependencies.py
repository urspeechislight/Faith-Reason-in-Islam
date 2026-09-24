"""Explicit review dependency groups and audited legacy policy compatibility."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
GROUPS={
 'editorial':('callout_structure.py','contract.md','drafting.md','editorial.md','council-article.md','paragraphs.md','review.py','review_identity.py','review_dependencies.py','quote_layout.py','scripture.py'),
 'render':('callout_structure.py','conversion_review.py','quote_layout.py','scripture.py','review_dependencies.py'),
}


def dependencies(kind):
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in GROUPS[kind]}


def digest(kind):
    return hashlib.sha256(json.dumps(dependencies(kind),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def matches(value,kind):
    expected=digest(kind)
    if value==expected:return True
    path=ROOT/'review-policy-compat.json'
    return path.is_file() and json.loads(path.read_text()).get(value,{}).get(kind)==expected


def runtime_matches(previous,current):
    """Allow only an exact audited old/new runtime pair, never arbitrary hash rebinding."""
    def names(values):
        result={Path(k).name:v for k,v in values.items()}
        return result if len(result)==len(values) else None
    old,new=names(previous),names(current)
    if old is None or new is None:return False
    if old==new:return True
    path=ROOT/'review-policy-compat.json'
    if not path.is_file():return False
    return any(old==row['before'] and new==row['after'] for row in json.loads(path.read_text()).get('runtime_transitions',[]))
