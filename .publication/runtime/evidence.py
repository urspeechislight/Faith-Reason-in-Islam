#!/usr/bin/env python3
"""Export verified corpus context for independent review; check archive consistency.

Export runs against Titan's read-only corpus. Offline verification proves archive
consistency, not corpus provenance or the truth of an interpretation.
"""
import scripture_alignment
import argparse
import contextlib
import hashlib
import unicodedata
import json
from pathlib import Path

import importlib.util as _ilu
_sp = _ilu.spec_from_file_location('article_scripture', Path(__file__).resolve().parent/'scripture.py')
scripture = _ilu.module_from_spec(_sp); _sp.loader.exec_module(scripture)
import re
import sqlite3

FIELDS = ['rowid', 'relpath', 'author', 'title', 'vol', 'page', 'raw']
AR = re.compile(r'[\u0621-\u063a\u0641-\u064a\u066e-\u06d3\u0750-\u077f\u08a0-\u08c9]')
def sha(text): return hashlib.sha256(text.encode()).hexdigest()
def flat(text): return re.sub(r'\s+', ' ', text).strip()


def arabic_blocks(note):
    blocks, buf = [], []
    def flush():
        if buf: blocks.append('\n'.join(buf)); buf.clear()
    for line in note.splitlines():
        if re.match(r'^>\s*\[!', line): flush(); continue
        if line.startswith('>'):
            content = scripture.unmark(re.sub(r'^(?:>\s?)+', '', line))
            if AR.search(content): buf.append(content)
            elif content.strip(): flush()
        else: flush()
    flush()
    return blocks


def covered_slices(block, quotes):
    """Match whole captured slices in order, allowing only layout whitespace."""
    target = flat(block)
    normalized = [flat(q) for q in quotes]
    for start in range(len(normalized)):
        joined = ''
        for end in range(start, len(normalized)):
            joined = (joined + ' ' + normalized[end]).strip()
            if joined == target: return set(range(start, end + 1))
            if not target.startswith(joined): break
    return set()


def ledger_usage(ledger):
    """Schema 1 remains quote-required. Schema 2 records explicit research use."""
    schema = ledger.get('schema')
    if schema not in (1, 2): raise ValueError('unknown citation ledger schema')
    entries = ledger.get('passages', [])
    ids = [entry.get('id') for entry in entries]
    if any(not isinstance(key, str) or not key.strip() for key in ids): raise ValueError('source IDs must be nonempty strings')
    if len(ids) != len(set(ids)): raise ValueError('duplicate evidence IDs')
    if schema == 1:
        if 'dispositions' in ledger or any('usage' in e for e in entries):
            raise ValueError('research-only dispositions require citation ledger schema 2')
        return {key: {'use': 'quotation'} for key in ids}
    dispositions = ledger.get('dispositions')
    if not isinstance(dispositions, dict) or set(dispositions) != set(ids):
        raise ValueError('schema 2 requires a disposition for every source ID and no unknown IDs')
    for key, item in dispositions.items():
        if not isinstance(item, dict) or item.get('use') not in ('quotation', 'research-only'):
            raise ValueError(str(key)+': disposition must be quotation or research-only')
        if item['use'] == 'research-only' and (not isinstance(item.get('reason'), str) or not item['reason'].strip()):
            raise ValueError(str(key)+': research-only evidence needs a reason')
    return dispositions


def archived_text(raw):
    """Decode archived transport without changing its retained bytes or hash."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        data = None
    if data is not None:
        def strings(value):
            if isinstance(value, str): return [value]
            if isinstance(value, list): return [s for item in value for s in strings(item)]
            if isinstance(value, dict): return [s for item in value.values() for s in strings(item)]
            return []
        parts = strings(data)
        def chapters(value):
            joined=[]
            if isinstance(value,list):
                if value and all(isinstance(v,dict) and isinstance(v.get('text'),str) and type(v.get('verse')) is int for v in value):
                    run=[];previous=None
                    for verse in value:
                        if previous is not None and verse['verse']!=previous+1:
                            joined.append(' '.join(run));run=[]
                        run.append(verse['text']);previous=verse['verse']
                    joined.append(' '.join(run))
                else:
                    for item in value:joined.extend(chapters(item))
            elif isinstance(value,dict):
                for item in value.values():joined.extend(chapters(item))
            return joined
        return parts + chapters(data)
    if raw.lstrip().startswith('<?xml') or re.match(r'\s*<Tanach[ >]',raw):
        import xml.etree.ElementTree as ET
        try:root=ET.fromstring(raw)
        except ET.ParseError:return [raw]
        if root.tag.rsplit('}',1)[-1]=='Tanach':
            verses=[]
            for verse in root.iter():
                if verse.tag.rsplit('}',1)[-1]!='v':continue
                children=list(verse)
                if not children or any(w.tag.rsplit('}',1)[-1]!='w' or list(w) for w in children):
                    return [raw]
                verses.append(' '.join((w.text or '') for w in children))
            if verses:return verses+[' '.join(verses)]
        return [raw]
    if re.search(r'<(?:html|body|p|div|span)\b', raw, re.I):
        from html.parser import HTMLParser
        class SourceText(HTMLParser):
            def __init__(self): super().__init__(convert_charrefs=True); self.parts=[]; self.skip=0
            def handle_starttag(self, tag, attrs):
                if tag in ('script', 'style'): self.skip+=1
                if tag in ('p', 'div', 'br', 'li'): self.parts.append(' ')
            def handle_endtag(self, tag):
                if tag in ('script', 'style'): self.skip=max(0,self.skip-1)
                if tag in ('p', 'div', 'li'): self.parts.append(' ')
            def handle_data(self, text):
                if not self.skip: self.parts.append(text)
        parser=SourceText();parser.feed(raw)
        return [''.join(parser.parts)]
    return [raw]


def scripture_coverage(note, quotes):
    """Match scripture after NFC comparison only; retain raw archives and corpus slices unchanged.

    Do not strip joiners, repair letters/points, harmonize editions, or alter the
    archive. A noncanonical mismatch requires a correctly identified source.
    """
    errors = []
    for index, row in enumerate(scripture.markdown(note), 1):
        original = unicodedata.normalize('NFC', flat(' '.join(p['text'] for p in row['paragraphs'] if p['role'] == 'original')))
        if not original or not any(original in unicodedata.normalize('NFC', flat(q)) for q in quotes):
            errors.append(f'scripture {index}: displayed original is absent from archived source text')
    return errors


def verify(bundle, note):
    errors = []
    if bundle.get('schema') != 1 or bundle.get('artifact_sha256') != sha(note):
        errors.append('source archive is missing or belongs to a different master')
    sources = bundle.get('sources', [])
    if not sources: errors.append('source archive is empty')
    ids = [s.get('id') for s in sources]
    if len(ids) != len(set(ids)): errors.append('duplicate source IDs')
    quotes = []
    corpus_entries = [s['passage'] for s in sources if s.get('kind') == 'corpus']
    ledger = {'schema': bundle.get('citation_ledger_schema', 1), 'passages': corpus_entries}
    if 'citation_dispositions' in bundle: ledger['dispositions'] = bundle['citation_dispositions']
    try: usage = ledger_usage(ledger)
    except ValueError as exc: errors.append(str(exc)); usage = {}
    for source in sources:
        key = str(source.get('id'))
        raw = source.get('raw', '')
        if not raw or source.get('raw_sha256') != sha(raw): errors.append(key+': full source text hash mismatch')
        if not source.get('citation'): errors.append(key+': source identity/locus missing')
        if source.get('kind') == 'corpus':
            entry = source['passage']
            if source.get('id') != entry.get('id'): errors.append(key+': source ID differs from ledger')
            if source['citation'] != entry.get('source'):errors.append(key+': displayed citation contradicts corpus metadata')
            if entry['source_sha256'] != sha(raw) or entry['quote_sha256'] != sha(entry['quote']):
                errors.append(key+': ledger hash mismatch')
            if raw[entry['start']:entry['end']] != entry['quote']:
                errors.append(key+': quotation differs from source slice')
            quotes.append(entry['quote'])
        elif source.get('kind') == 'external':
            if not source.get('url') or not source.get('accessed'):
                errors.append(key+': external source URL/access date missing')
            quotes.extend(archived_text(source['raw']))
        elif source.get('kind') != 'external':
            errors.append(key+': unknown source kind')
    for i, block in enumerate(arabic_blocks(note), 1):
        if not covered_slices(block, quotes): errors.append(f'Arabic block {i}: missing exact ledger slice')
    errors.extend(scripture_coverage(note, quotes))
    errors.extend(scripture_alignment.errors(note, bundle.get("scripture_alignment")))
    for entry in corpus_entries:
        if usage.get(entry['id'], {}).get('use') == 'quotation' and AR.search(entry['quote']):
            if not any(flat(entry['quote']) in flat(block) for block in arabic_blocks(note)):
                errors.append(entry['id']+': captured quotation missing from note')
    for claim in bundle.get('claims', []):
        if not claim.get('claim') or not claim.get('source_ids') or not set(claim['source_ids']) <= set(ids):
            errors.append('claim map has missing or unknown evidence')
    return errors


def export(db, note, ledger, external=None, claims=None, alignment=None):
    ledger_usage(ledger)
    sources = []
    connection_context=(sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro', uri=True) if ledger['passages'] else contextlib.nullcontext(None))
    with connection_context as connection:
        for entry in ledger['passages']:
            row = connection.execute('SELECT '+','.join(FIELDS)+' FROM pages WHERE rowid=?', (entry['source']['rowid'],)).fetchone()
            if row is None: raise ValueError('corpus row missing')
            data = dict(zip(FIELDS, row))
            if entry['source'] != {k:v for k,v in data.items() if k != 'raw'}:
                raise ValueError(entry['id']+': source identity differs from live corpus')
            sources.append({'id':entry['id'], 'kind':'corpus', 'citation':entry['source'],
                            'raw':data['raw'], 'raw_sha256':sha(data['raw']), 'passage':entry})
    sources.extend(external or [])
    bundle = {'schema':1, 'artifact_sha256':sha(note), 'sources':sources, 'claims':claims or []}
    if alignment is not None: bundle['scripture_alignment'] = alignment
    bundle['citation_ledger_schema'] = ledger['schema']
    if ledger['schema'] == 2: bundle['citation_dispositions'] = ledger['dispositions']
    errors = verify(bundle, note)
    if errors: raise ValueError('; '.join(errors))
    return bundle


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('note',type=Path);p.add_argument('ledger',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--db',type=Path,default=Path('/home/fahmy/code/islamic/index/corpus.db'))
    p.add_argument('--external',type=Path,help='JSON array of external sources: id, kind=external, citation, url, accessed, raw, raw_sha256')
    p.add_argument('--claims',type=Path,help='JSON array: claim, source_ids, inference, limits')
    p.add_argument('--scripture-review',type=Path,help='Approved original-to-Romanization alignment for every scripture quotation')
    a=p.parse_args()
    try:
        if a.output.exists():raise ValueError('output exists; preserve evidence and use a new path')
        bundle=export(a.db,a.note.read_text(),json.loads(a.ledger.read_text()),json.loads(a.external.read_text()) if a.external else None,json.loads(a.claims.read_text()) if a.claims else None, json.loads(a.scripture_review.read_text()) if a.scripture_review else None)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n')
        print('Full source archive exported after live corpus verification; independent fidelity review still required.')
        return 0
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as e:print('BLOCKED:',e);return 1
if __name__=='__main__':raise SystemExit(main())
