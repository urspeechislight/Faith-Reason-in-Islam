#!/usr/bin/env python3
"""Bind website text to a canonical Markdown master. Does not assess its truth or quality."""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path

import importlib.util as _ilu
_sp = _ilu.spec_from_file_location('article_scripture', Path(__file__).resolve().parent/'scripture.py')
scripture = _ilu.module_from_spec(_sp); _sp.loader.exec_module(scripture)
import re
VERSION=4

def sha(s):return hashlib.sha256(s.encode()).hexdigest()
def clean(s):return re.sub(r'\s+',' ',html.unescape(s)).strip()
def link_tokens(s):
    """Return source spans, visible labels and destinations; balance URL parentheses."""
    out=[];i=0
    while i<len(s):
        if s.startswith('[[',i):
            end=s.find(']]',i+2)
            if end<0:raise ValueError('unclosed wikilink')
            content=s[i+2:end];target,sep,label=content.partition('|')
            out.append((i,end+2,label if sep else target,target if target.startswith('#') else 'wiki:'+target));i=end+2;continue
        if s[i]=='[':
            close=s.find('](',i+1)
            if close!=-1 and '[' not in s[i+1:close] and '\n' not in s[i:close]:
                if i and s[i-1]=='!':raise ValueError('images require explicit converter support')
                j=close+2;start=j;depth=1
                while j<len(s) and depth:
                    if s[j]=='\\':j+=2;continue
                    if s[j]=='(':depth+=1
                    elif s[j]==')':depth-=1
                    j+=1
                if depth:raise ValueError('unclosed link destination')
                target=s[start:j-1]
                if not target or re.search(r'\s',target):raise ValueError('link titles/whitespace destinations need explicit converter support')
                out.append((i,j,s[i+1:close],target));i=j;continue
        i+=1
    return out

def inline(s):
    s=scripture.unmark(s)
    if re.search(r'<[A-Za-z/!]',s):raise ValueError('raw HTML in Markdown requires explicit conversion support')
    for a,b,label,target in reversed(link_tokens(s)):s=s[:a]+label+s[b:]
    s=re.sub(r'\*\*(.+?)\*\*',r'\1',s)
    s=re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)',r'\1',s)
    s=re.sub(r'`([^`]+)`',r'\1',s)
    return clean(s)

def source_links(source):
    return [{'label':inline(label),'target':target} for _,_,label,target in link_tokens(source)]

def blocks(source):
    m=re.match(r'^---\n(.*?)\n---\n',source,re.S)
    body=source[m.end():] if m else source
    if re.search(r'^\s*(```|~~~)|^!\[|^\[\^',body,re.M):raise ValueError('fences/images/footnote definitions need an explicit converter extension')
    out=[];buf=[];buf_links=[]
    def flush():
        if not buf:return
        text=inline('\n'.join(buf));buf.clear()
        if text:out.append({'id':f'n{len(out)+1:04d}','text':text,'links':list(buf_links)})
        buf_links.clear()
    for line in body.splitlines():
        if not line.strip():flush();continue
        if re.fullmatch(r'\s*---+\s*',line):flush();continue
        if line.startswith('#'):
            flush();buf_links.extend(source_links(line));buf.append(re.sub(r'^#{1,6}\s+','',line));flush();continue
        buf_links.extend(source_links(line))
        if line.startswith('>'):
            line=re.sub(r'^(?:>\s?)+','',line)
            line=re.sub(r'^\[!\w+\][-+]?\s*','',line)
        line=re.sub(r'^\s*(?:[-*+] |\d+\. )','',line)
        if line.lstrip().startswith('|'):
            if re.fullmatch(r'[|:\-\s]+',line):continue
            line=inline(line).replace(r'\|','\x00')
            line=' '.join(x.strip() for x in line.strip().strip('|').split('|')).replace('\x00','|')
        buf.append(line)
    flush()
    if not out:raise ValueError('empty source')
    cat=re.search(r'^category:\s*([a-z-]+)\s*$',m[1],re.M) if m else None
    return out,cat[1] if cat else None

def paragraph_layout(source, records):
    """Keep paragraph boundaries inside source callouts, including quoted blank lines."""
    lines=source.splitlines();layout={};used=set();i=0
    while i<len(lines):
        match=re.match(r'^> ?\[!(info|note|tip|warning|quote)\][-+]?\s*(.*)$',lines[i])
        if not match:i+=1;continue
        caption=inline(match[2]);i+=1;paragraphs=[];buf=[]
        def flush():
            if buf:paragraphs.append(inline(' '.join(buf)));buf.clear()
        while i<len(lines) and lines[i].startswith('>'):
            if re.match(r'^> ?\[!\w+\]',lines[i]):
                raise ValueError('Separate source callouts with a blank line')
            content=re.sub(r'^>\s?','',lines[i])
            content=re.sub(r'^\s*(?:[-*+] |\d+\. )','',content)
            if content.strip():buf.append(content)
            else:flush()
            i+=1
        flush()
        expected=clean(' '.join([caption]+paragraphs))
        candidates=[b for b in records if b['id'] not in used and b['text']==expected]
        if not candidates:
            raise ValueError('Separate source callouts from surrounding prose with blank lines')
        if not paragraphs:raise ValueError('Source callout has no paragraphs')
        identifier=candidates[0]['id'];used.add(identifier)
        layout[identifier]={'caption':caption,'paragraphs':paragraphs}
    return layout

def prepare(source,path='',schema=VERSION):
    records,category=blocks(source)
    if category not in ('debate','exegesis','narration','commentary'):raise ValueError('valid category frontmatter required')
    if schema not in (2,3,4):raise ValueError('unsupported handoff schema')
    receipt={'schema':schema,'source_path':path,'source_sha256':sha(source),'source_markdown':source,'category':category,'blocks':records,'links':source_links(source),'anchor_map':{},'note_map':{}}
    if schema>=3:receipt['paragraph_layout']=paragraph_layout(source,records)
    if schema>=4:receipt['scripture_highlights']=scripture.highlights(source,'md')
    return receipt

class Rendered(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    SPACE={'p','div','section','article','li','br','tr','td','th','summary','blockquote','cite','h1','h2','h3','h4','h5','h6'}
    def __init__(self,source):
        super().__init__(convert_charrefs=True);self.stack=[];self.records=[];self.active=None;self.outside=[];self.source_hash=None;self.category=None;self.main_count=0;self.links=[];self.in_caption=False;self.link=None;self.layout={};self.paragraph=None;self.source_roles=[]
        self.feed(source);self.close()
        if self.stack:raise ValueError('unclosed HTML')
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if a.get('data-content-role')=='source':
            self.source_roles.append((tag,a.get('data-note-block')))
        if tag=='meta' and a.get('name')=='source-note-sha256':self.source_hash=a.get('content')
        if tag=='main':self.category=a.get('data-category');self.main_count+=1
        if 'data-note-block' in a:
            if self.active is not None:raise ValueError('nested note blocks')
            self.active={'id':a['data-note-block'],'parts':[],'caption':[],'links':[],'caption_links':[], 'tag':tag,'paragraphs':[]}
        if tag=='p' and self.active is not None:
            if self.paragraph is not None:raise ValueError('nested paragraph')
            self.paragraph=[]
        if tag=='cite' and 'data-note-citation' in a:
            if self.active is None:raise ValueError('citation outside mapped source block')
            self.in_caption=True
        if tag=='a' and 'href' in a and self.active is not None:
            if self.link is not None:raise ValueError('nested links')
            self.link={'target':a['href'],'parts':[]}
        if tag in self.SPACE and self.active is not None:self.active['parts'].append(' ')
        if tag not in self.VOID:self.stack.append((tag,'data-note-block' in a))
    def handle_endtag(self,tag):
        if tag in self.VOID:return
        if not self.stack or self.stack[-1][0]!=tag:raise ValueError('malformed HTML closing '+tag)
        _,ends=self.stack.pop()
        if tag=='p' and self.paragraph is not None:
            self.active['paragraphs'].append(clean(''.join(self.paragraph)));self.paragraph=None
        if tag=='cite':self.in_caption=False
        if tag=='a' and self.link is not None:
            self.active['caption_links' if self.in_caption else 'links'].append({'label':clean(''.join(self.link['parts'])),'target':self.link['target']});self.link=None
        if ends:
            self.layout[self.active['id']]={'tag':self.active['tag'],'paragraphs':self.active['paragraphs']}
            caption=clean(''.join(self.active['caption']))
            caption=re.sub(r'^[-–—]\s+','',caption)
            text=clean(caption+' '+''.join(self.active['parts']))
            self.records.append({'id':self.active['id'],'text':text,'links':self.active['caption_links']+self.active['links']});self.active=None
        elif tag in self.SPACE and self.active is not None:self.active['parts'].append(' ')
    def handle_data(self,data):
        if self.paragraph is not None:self.paragraph.append(data)
        if self.link is not None:self.link['parts'].append(data)
        if self.active is not None:self.active['caption' if self.in_caption else 'parts'].append(data)
        elif any(t=='main' for t,_ in self.stack) and data.strip():
            if not any(t in ('nav','script','style') for t,_ in self.stack):self.outside.append(data.strip())

def verify(source,receipt):
    expected=prepare(receipt['source_markdown'],receipt.get('source_path',''),schema=receipt.get('schema'));errors=[]
    for key in ('schema','source_sha256','category','blocks','links'):
        if receipt.get(key)!=expected[key]:errors.append('invalid handoff '+key)
    if expected['schema']>=4:errors.extend(scripture.errors(receipt['source_markdown'],'md'));errors.extend(scripture.errors(source,'html'))
    page=Rendered(source)
    if expected['schema']<4 and (scripture.highlights(source,'html') or scripture.highlights(receipt['source_markdown'],'md')):errors.append('scripture lexical marks require a version-4 handoff')
    if expected['schema']>=4:
        if receipt.get('scripture_highlights')!=expected['scripture_highlights']:errors.append('invalid scripture highlight receipt')
        if scripture.highlights(source,'html')!=expected['scripture_highlights']:errors.append('scripture highlight words, roles, IDs or offsets changed during conversion')
        errors.extend(scripture.errors(receipt['source_markdown'],'md'))
        errors.extend(scripture.errors(source,'html'))
    if expected['schema']>=3:
        if receipt.get('paragraph_layout')!=expected['paragraph_layout']:
            errors.append('invalid handoff paragraph_layout')
        for block in expected['blocks']:
            actual=page.layout.get(block['id'],{})
            if actual.get('tag') not in ('p','div','section','article','blockquote','li','ul','ol','table','tr','td','th','h1','h2','h3','h4','h5','h6','details','summary'):
                errors.append(block['id']+': mapped content needs a block element, not inline spans')
        for identifier,layout in expected['paragraph_layout'].items():
            actual=page.layout.get(identifier,{})
            if actual.get('tag')!='blockquote' or actual.get('paragraphs')!=layout['paragraphs']:
                errors.append(identifier+': source-callout paragraphs merged, split, reordered or not rendered as a blockquote')
        if page.source_roles != [('blockquote',identifier) for identifier in expected['paragraph_layout']]:
            errors.append('source content roles must match the master callouts exactly; authored content cannot be hidden as source')
    if page.main_count!=1:errors.append('expected exactly one main')
    if page.category!=expected['category']:errors.append('category changed during conversion')
    if page.source_hash!=expected['source_sha256']:errors.append('missing or stale source-note-sha256')
    expected_records=[]
    for block in expected['blocks']:
        transformed=[]
        for link in block['links']:
            target=link['target']
            if target.startswith('wiki:'):
                mapped=receipt.get('note_map',{}).get(target)
                if not mapped or not re.fullmatch(r'[A-Za-z0-9_./-]+\.html(?:#[A-Za-z0-9_.:-]+)?',mapped):
                    errors.append('internal note needs a catalogue-verified relative HTML target: '+target);mapped=target
            elif target.startswith('#'):
                mapped=receipt.get('anchor_map',{}).get(target,target)
                if not mapped.startswith('#'):errors.append('heading anchors must remain internal')
            else:mapped=target
            transformed.append({'label':link['label'],'target':mapped})
        expected_records.append(dict(block,links=transformed))
    if page.outside:errors.append('unmapped article text: '+' | '.join(page.outside[:3]))
    if page.records!=expected_records:
        want={b['id']:(b['text'],b['links']) for b in expected_records};got={b['id']:(b['text'],b['links']) for b in page.records}
        for key in want:
            if got.get(key)!=want[key]:errors.append(key+': omitted or rewritten source block')
        if list(want)!=[b['id'] for b in page.records]:errors.append('source blocks duplicated, added, or reordered')
    return errors

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    s=sub.add_parser('prepare');s.add_argument('note',type=Path);s.add_argument('receipt',type=Path)
    s.add_argument('--baseline',type=Path,help='Approved master baseline; required with --review')
    s.add_argument('--review',type=Path,help='Master review to verify and embed for publication')
    s.add_argument('--pending-release',action='store_true',help='Prepare for hosted final review; does not approve publication')
    s=sub.add_parser('verify');s.add_argument('page',type=Path);s.add_argument('receipt',type=Path)
    a=p.parse_args()
    try:
        if a.cmd=='prepare':
            if a.receipt.exists():raise ValueError('receipt exists; use a new path to retain history')
            data=prepare(a.note.read_text(),str(a.note.resolve()));a.receipt.parent.mkdir(parents=True,exist_ok=True)
            if bool(a.baseline) != bool(a.review):raise ValueError('provide both --baseline and --review')
            if a.review:
                import review
                baseline=json.loads(a.baseline.read_text());record=json.loads(a.review.read_text())
                errors=review.verify(review.inspect_file(a.note),baseline,record,require_release=not a.pending_release)
                if errors:raise ValueError('master approval failed: '+'; '.join(errors))
                data.update(source_baseline=baseline,source_review=record,release_pending=a.pending_release)
            a.receipt.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
            print(len(data['blocks']),'source blocks mapped; '+(('awaiting hosted release review' if a.pending_release else 'verified master approval embedded') if a.review else 'preview only: no editorial approval embedded'));return 0
        errors=verify(a.page.read_text(),json.loads(a.receipt.read_text()))
        for e in errors:print('FAIL:',e)
        print('Conversion text matches source.' if not errors else 'Conversion rejected.');return bool(errors)
    except (ValueError,KeyError,TypeError,OSError) as e:print('ERROR:',e);return 2
if __name__=='__main__':raise SystemExit(main())
