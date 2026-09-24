#!/usr/bin/env python3
"""Explicit source-to-Romanization coverage, with separately named fidelity review.

A complete alignment proves token coverage, not linguistic accuracy. A reviewer
must judge each mapping against the actual source; these tools never translate.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import unicodedata
import scripture


def sha(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def words(text):
    # Keep intra-word apostrophes and hyphens; ignore verse numbers and punctuation.
    result=[];buf=[]
    for ch in scripture.unmark(text):
        if unicodedata.category(ch)[0] in 'LM':buf.append(ch)
        elif ch in "'’ʾʿ-־" :buf.append(ch)
        else:
            if buf:result.append(''.join(buf).strip("-־"));buf=[]
    if buf:result.append(''.join(buf).strip("-־"))
    return [x for x in result if any(unicodedata.category(ch)[0] in "LM" for ch in x)]


def inventory(source,fmt='md'):
    rows=scripture.html(source)[0] if fmt in ('html','htm') else scripture.markdown(source)
    result=[]
    for n,row in enumerate(rows,1):
        layers={role:' '.join(p['text'] for p in row['paragraphs'] if p['role']==role) for role in scripture.ROLES}
        layers={k:re.sub(r'\s+',' ',scripture.unmark(v)).strip() for k,v in layers.items()}
        result.append({'id':f's{n:04d}','caption':row['caption'],'layers':layers,
                       'source_tokens':words(layers['original']),'roman_tokens':words(layers['transliteration']),
                       'layers_sha256':sha(layers)})
    return result


def prepare(source,fmt='md'):
    return {'schema':1,'status':'pending','reviewer':'','quotes':[dict(q,status='pending',units=[],evidence='') for q in inventory(source,fmt)]}


def errors(source,record,fmt='md'):
    expected=inventory(source,fmt)
    if not expected:return []
    if not isinstance(record,dict) or record.get('schema')!=1:return ['scripture alignment missing; prepare and review every original-to-transliteration mapping']
    issues=[]
    if record.get('status')!='approved' or not str(record.get('reviewer','')).strip():issues.append('scripture alignment requires approval by a named fidelity reviewer')
    rows=record.get('quotes')
    if not isinstance(rows,list) or len(rows)!=len(expected):return issues+['scripture alignment must cover every current quotation']
    for want,row in zip(expected,rows):
        label=want['id']+': '
        if not isinstance(row,dict):issues.append(label+'invalid alignment');continue
        if any(row.get(k)!=want[k] for k in ['id','caption','layers_sha256','source_tokens','roman_tokens']):issues.append(label+'alignment belongs to different quotation layers');continue
        if row.get('status')!='passed' or len(str(row.get('evidence','')).split())<8:issues.append(label+'source-aligned fidelity assessment missing')
        units=row.get('units');src=want['source_tokens'];roman=want['roman_tokens']
        if not src or not roman or not isinstance(units,list) or len(units)!=len(src):issues.append(label+'map every source word exactly once');continue
        cursor=0
        for index,(token,unit) in enumerate(zip(src,units)):
            if not isinstance(unit,dict):issues.append(label+'invalid token mapping');continue
            start,end=unit.get('roman_start'),unit.get('roman_end')
            if unit.get('source_index')!=index or unit.get('source')!=token:issues.append(label+'source word omitted, changed or reordered')
            if type(start)!=int or type(end)!=int or start!=cursor or end<=start or end>len(roman):issues.append(label+'Romanization spans must cover the displayed words once, in order');continue
            if unit.get('romanization')!=' '.join(roman[start:end]):issues.append(label+'mapping differs from displayed Romanization')
            cursor=end
        if cursor!=len(roman):issues.append(label+'unmapped Romanization words remain')
    return issues


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['prepare','verify']);p.add_argument('source',type=Path);p.add_argument('--record',type=Path,required=True);a=p.parse_args(argv)
    try:
        text=a.source.read_text();fmt=a.source.suffix.lstrip('.')
        if a.command=='prepare':
            if a.record.exists():raise ValueError('alignment exists; preserve it and use a fresh revision path')
            a.record.parent.mkdir(parents=True,exist_ok=True);a.record.write_text(json.dumps(prepare(text,fmt),ensure_ascii=False,indent=2)+'\n');print('Pending alignment written; no transliteration or approval generated.');return 0
        findings=errors(text,json.loads(a.record.read_text()),fmt)
        for item in findings:print('BLOCKED:',item)
        return bool(findings)
    except (OSError,ValueError,KeyError,TypeError) as exc:print('BLOCKED:',exc);return 1
if __name__=='__main__':raise SystemExit(main())
