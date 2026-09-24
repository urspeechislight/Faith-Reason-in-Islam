#!/usr/bin/env python3
"""Lossless review-context helpers. External model execution is disabled.

The legacy run() entry point fails closed. Use native inherited-model subagents
and article_build.py release-request/release-accept. This module launches none.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from html.parser import HTMLParser
import review

ROOT = Path(__file__).resolve().parent


class SourceText(HTMLParser):
    """Remove document markup, retaining every visible source text node."""
    def __init__(self):
        super().__init__(convert_charrefs=True); self.hidden=0; self.parts=[]
    def handle_starttag(self, tag, attrs):
        if tag in {'script','style'}: self.hidden += 1
        elif tag in {'p','div','br','li','h1','h2','h3','tr'}: self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in {'script','style'}: self.hidden=max(0,self.hidden-1)
        elif tag in {'p','div','li','h1','h2','h3','tr'}: self.parts.append('\n')
    def handle_data(self, value):
        if not self.hidden: self.parts.append(value)


def review_evidence(bundle):
    """Deduplicate full contexts and decode transport escaping, never summarize."""
    contexts={};sources=[]
    for source in bundle['sources']:
        key=source['raw_sha256']
        if key not in contexts:
            raw=source['raw'];form='original text'
            try:
                context=json.loads(raw);form='decoded original JSON'
            except (ValueError,TypeError):
                if '<html' in raw[:2000].lower():
                    parser=SourceText();parser.feed(raw);context=''.join(parser.parts);form='complete HTML text, scripts/styles omitted'
                else:context=raw
            contexts[key]={'representation':form,'content':context}
        entry={k:v for k,v in source.items() if k not in {'raw','passage'}}
        entry['context']=key
        if 'passage' in source:
            entry['excerpt_offsets']={k:source['passage'][k] for k in ['start','end']}
        sources.append(entry)
    return {'artifact_sha256':bundle['artifact_sha256'],'sources':sources,'contexts':contexts,
            'claims':bundle.get('claims',[]),
            'scripture_alignment':bundle.get('scripture_alignment'),
            'citation_ledger_schema':bundle.get('citation_ledger_schema',1),
            'citation_dispositions':bundle.get('citation_dispositions',{}),
            'provenance':'Original archive is retained unchanged. Context keys hash original raw bytes. JSON escaping and HTML markup are presentation transformations; no source sentences are summarized or selected.'}


def review_packet(packet):
    """Decode review JSON and reference exact duplicate candidate quotations.

    All reviewer judgments and any wording absent from the candidate remain.
    The original report/hash remains authoritative and is retained in the job.
    """
    candidate=packet['candidate']
    def deduplicate(value):
        if isinstance(value,list): return [deduplicate(v) for v in value]
        if not isinstance(value,dict): return value
        result={}
        for key,item in value.items():
            if key=='text' and isinstance(item,str) and len(item)>40 and item in candidate:
                result['exact_text_in_candidate_sha256']=review.digest(item)
            else: result[key]=deduplicate(item)
        return result
    result=json.loads(json.dumps(packet))
    for group in ['advisors','peer_reviews','followup_reviews']:
        for response in result['report'].get(group,[]):
            try: decoded=json.loads(response.get('response',''))
            except (ValueError,TypeError): continue
            response['response']=deduplicate(decoded)
            response['representation']='Original JSON decoded; exact duplicated candidate text replaced by its hash. All judgments and differing historical wording retained.'
    return result


def run(*args,**kwargs):
    raise ValueError('External model execution is disabled. Use article_build.py release-request and a native subagent inheriting the active model; then release-accept.')

if __name__=='__main__':
    raise SystemExit('External model execution is disabled; use the native article review workflow.')
