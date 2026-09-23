#!/usr/bin/env python3
"""Export verified corpus context for independent review; check archive consistency.

Export runs against Titan's read-only corpus. Offline verification proves archive
consistency, not corpus provenance or the truth of an interpretation.
"""
import argparse
import hashlib
import json
from pathlib import Path
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
            content = re.sub(r'^> ?', '', line)
            if AR.search(content): buf.append(content)
            elif content.strip(): flush()
        else: flush()
    flush()
    return blocks


def verify(bundle, note):
    errors = []
    if bundle.get('schema') != 1 or bundle.get('artifact_sha256') != sha(note):
        errors.append('source archive is missing or belongs to a different master')
    sources = bundle.get('sources', [])
    if not sources: errors.append('source archive is empty')
    ids = [s.get('id') for s in sources]
    if len(ids) != len(set(ids)): errors.append('duplicate source IDs')
    quotes = []
    for source in sources:
        key = str(source.get('id'))
        raw = source.get('raw', '')
        if not raw or source.get('raw_sha256') != sha(raw): errors.append(key+': full source text hash mismatch')
        if not source.get('citation'): errors.append(key+': source identity/locus missing')
        if source.get('kind') == 'corpus':
            entry = source['passage']
            if source['citation'] != entry.get('source'):errors.append(key+': displayed citation contradicts corpus metadata')
            if entry['source_sha256'] != sha(raw) or entry['quote_sha256'] != sha(entry['quote']):
                errors.append(key+': ledger hash mismatch')
            if raw[entry['start']:entry['end']] != entry['quote']:
                errors.append(key+': quotation differs from source slice')
            quotes.append(entry['quote'])
        elif source.get('kind') != 'external' or not source.get('url') or not source.get('accessed'):
            errors.append(key+': external source URL/access date missing')
    for i, block in enumerate(arabic_blocks(note), 1):
        if flat(block) not in [flat(q) for q in quotes]: errors.append(f'Arabic block {i}: missing exact ledger slice')
    for claim in bundle.get('claims', []):
        if not claim.get('claim') or not claim.get('source_ids') or not set(claim['source_ids']) <= set(ids):
            errors.append('claim map has missing or unknown evidence')
    return errors


def export(db, note, ledger, external=None, claims=None):
    if ledger.get('schema') != 1: raise ValueError('unknown ledger schema')
    sources = []
    with sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro', uri=True) as connection:
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
    errors = verify(bundle, note)
    if errors: raise ValueError('; '.join(errors))
    return bundle


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('note',type=Path);p.add_argument('ledger',type=Path);p.add_argument('output',type=Path)
    p.add_argument('--db',type=Path,default=Path('/home/fahmy/code/islamic/index/corpus.db'))
    p.add_argument('--external',type=Path,help='JSON array of external sources: id, kind=external, citation, url, accessed, raw, raw_sha256')
    p.add_argument('--claims',type=Path,help='JSON array: claim, source_ids, inference, limits')
    a=p.parse_args()
    try:
        if a.output.exists():raise ValueError('output exists; preserve evidence and use a new path')
        bundle=export(a.db,a.note.read_text(),json.loads(a.ledger.read_text()),json.loads(a.external.read_text()) if a.external else None,json.loads(a.claims.read_text()) if a.claims else None)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n')
        print('Full source archive exported after live corpus verification; independent fidelity review still required.')
        return 0
    except (OSError,ValueError,KeyError,TypeError,sqlite3.Error) as e:print('BLOCKED:',e);return 1
if __name__=='__main__':raise SystemExit(main())
