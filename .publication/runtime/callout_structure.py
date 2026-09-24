"""Explicit Markdown source and nested body paragraphs; never infer isnad boundaries."""
import re


def paragraphs(lines):
    result=[];buf=[];depth=None
    def flush():
        nonlocal depth
        if buf:result.append({'text':' '.join(buf),'depth':depth});buf.clear()
        depth=None
    for line in lines:
        match=re.match(r'^(?:>[ \t]?)+',line)
        if not match:raise ValueError('Separate the source callout from prose with a blank line')
        level=match[0].count('>')-1;text=line[match.end():]
        if level>1:raise ValueError('Use one compact nested quote level inside a source callout')
        if not text.strip():flush();continue
        if depth is not None and level!=depth:raise ValueError('Separate isnad and quoted body with a quoted blank line')
        depth=level;buf.append(text)
    flush()
    return result


def mixed_chain(text):
    """High-confidence long isnad joined to direct speech; short speech tags are not guessed."""
    quote=re.search(r'["“]',text)
    if not quote:return False
    prefix=text[:quote.start()]
    return len(prefix.split())>=18 and len(re.findall(r'\bfrom\b',prefix,re.I))>=3 and bool(re.search(r'\b(?:said|say|says)\b',prefix,re.I))


def matn_errors(parts):
    """Catch clearly identified English chains whose following body loses its inset."""
    errors=[];chain_seen=False
    for part in parts:
        text=part['text']
        chain=len(re.findall(r'\bfrom\b',text,re.I))>=3 and bool(re.search(r'\b(?:said|says|reported)\b',text,re.I))
        if chain:
            chain_seen=True
            if part['depth']:errors.append('Keep the isnad outside the matn inset')
            if mixed_chain(text):errors.append('Separate the long isnad from the complete matn')
        elif chain_seen and re.search('[A-Za-z]',text) and not part['depth']:
            errors.append('Indent every matn paragraph, including narration before and after speech')
    return errors
