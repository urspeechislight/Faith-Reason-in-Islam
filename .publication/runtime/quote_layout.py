#!/usr/bin/env python3
"""Inventory protected quotations for review; measure rendered HTML with Chromium.

capture ARTICLE.html --output RENDER.json captures desktop/mobile evidence.
No command edits, approves, publishes, or translates article content.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import re
from html.parser import HTMLParser
from pathlib import Path

import importlib.util as _ilu
_sp = _ilu.spec_from_file_location('article_scripture', Path(__file__).resolve().parent/'scripture.py')
scripture = _ilu.module_from_spec(_sp); _sp.loader.exec_module(scripture)

VERSION = 3
HON = set('ﷺ﵇﵍﵈﵊﵁﵀ﷻ﷿﵌')
AR = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]')

def sha(text):
    return hashlib.sha256(text.encode() if isinstance(text,str) else text).hexdigest()

def flat(text):
    return re.sub(r'\s+',' ',text).strip()

def md_inline(text):
    # Markdown emphasis markers are layout, not content: normalize them the
    # same way the text-preservation receipt (handoff.inline) does, so md and
    # rendered shas agree for transliteration lines and literal-asterisk text.
    s=re.sub(r'\*\*(.+?)\*\*',r'\1',scripture.unmark(text))
    s=re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)',r'\1',s)
    s=re.sub(r'`([^`]+)`',r'\1',s)
    return flat(s)

class Quotes(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows=[];self.q=None;self.current=None;self.caption=False;self.mk=None
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=='blockquote' and attrs.get('data-content-role')=='source':
            if self.q is not None:raise ValueError('nested source blockquote needs explicit layout support')
            self.q={'caption':'','paragraphs':[],'raw':'','marks':[]}
        if self.q is not None:
            if tag=='p':self.current=''
            if tag=='mark':self.mk={'term':attrs.get('data-term'),'text':''}
            if tag=='cite':self.caption=True
            if tag=='br' and self.current is not None:self.current+=' '
    def handle_data(self,data):
        if self.q is None:return
        if self.mk is not None:self.mk['text']+=data
        if self.caption:self.q['caption']+=data
        elif self.current is not None:self.current+=data
        else:self.q['raw']+=data
    def handle_endtag(self,tag):
        if self.q is None:return
        if tag=='mark' and self.mk is not None:self.q['marks'].append(self.mk);self.mk=None
        if tag=='p' and self.current is not None:
            self.q['paragraphs'].append(flat(self.current));self.current=None
        if tag=='cite':self.caption=False
        if tag=='blockquote':
            if not self.q['paragraphs'] and flat(self.q['raw']):self.q['paragraphs']=[flat(self.q['raw'])]
            self.rows.append(self.q);self.q=None

def extract(source,fmt):
    if fmt in ('html','htm'):
        parser=Quotes();parser.feed(source);rows=parser.rows
    else:
        rows=[];lines=source.splitlines();i=0;fence=None
        while i<len(lines):
            line=lines[i]
            fm=re.match(r'^\s*(`{3,}|~{3,})',line)
            if fm:
                if fence is None:fence=fm[1][0]
                elif fm[1][0]==fence:fence=None
                i+=1;continue
            m=None if fence else re.match(r'^>\s*\[!(info|note|tip|warning|quote)\]-?\s*(.*)',line,re.I)
            if not m:i+=1;continue
            row={'caption':m[2],'paragraphs':[],'marks':[]};buf=[];i+=1
            while i<len(lines) and lines[i].startswith('>'):
                content=re.sub(r'^> ?', '',lines[i])
                row['marks'].extend({'term':m['term'],'text':m['text']} for m in scripture.runs(content))
                if content.strip():buf.append(content)
                elif buf:row['paragraphs'].append(md_inline(' '.join(buf)));buf=[]
                i+=1
            if buf:row['paragraphs'].append(md_inline(' '.join(buf)))
            rows.append(row)
    result=[]
    for n,row in enumerate(rows,1):
        paragraphs=[]
        for k,text in enumerate(row['paragraphs'],1):
            text=flat(text)
            lang='original' if any(c not in HON for c in AR.findall(text)) else 'translation-or-other'
            cues=[];words=len(text.split())
            if words>=100:cues.append('dense-paragraph')
            if lang!='original':
                if text.count('"')>=4:cues.append('ambiguous-double-quotation-nesting')
                if re.search(r'\b(?:with|then|and|because|of|the|a|an|that)\s*["”\']?$',text,re.I):cues.append('possible-unfinished-tail')
            paragraphs.append({'id':f'q{n:04d}:p{k}','text':text,'sha256':sha(text),'language':lang,'words':words,'cues':cues})
        english=[p['text'] for p in paragraphs if p['language']!='original']
        if english and english[0].startswith(('"','“')) and english[-1].endswith(('"','”')):
            next(p for p in paragraphs if p['language']!='original')['cues'].append('outer-quotation-wrapper')
        result.append({'id':f'q{n:04d}','caption':flat(row['caption']),'paragraphs':paragraphs,'lexical_marks':row.get('marks',[])})
    return result

def pending(quotes):
    return [dict(copy.deepcopy(q),status='pending',paragraph_boundaries='',speaker_and_quotation_boundaries='',source_completeness='',
                 cue_resolutions=[{'id':p['id']+':'+cue,'status':'pending','reason':''} for p in q['paragraphs'] for cue in p['cues']]) for q in quotes]

def review_errors(quotes,records):
    if not isinstance(records,list) or len(records)!=len(quotes):return ['quote_layout_review must cover every source callout, including protected translations']
    errors=[]
    for q,row in zip(quotes,records):
        if not isinstance(row,dict) or any(row.get(k)!=q[k] for k in ['id','caption','paragraphs']):
            errors.append(q['id']+' quotation layout review does not match current paragraphs');continue
        for field in ['paragraph_boundaries','speaker_and_quotation_boundaries','source_completeness']:
            if len(str(row.get(field,'')).split())<8:errors.append(q['id']+' needs a specific '+field+' review')
        if row.get('status')!='passed':errors.append(q['id']+' quote layout review pending')
        expected=[p['id']+':'+c for p in q['paragraphs'] for c in p['cues']]
        resolutions=row.get('cue_resolutions')
        if not isinstance(resolutions,list) or [x.get('id') if isinstance(x,dict) else None for x in resolutions]!=expected:
            errors.append(q['id']+' quote layout cues missing or changed');continue
        for cue in resolutions:
            if cue.get('status')!='legitimate' or len(str(cue.get('reason','')).split())<8:
                errors.append(cue['id']+' unresolved; fix the source-stage defect or justify from the actual passage')
    return errors

def finite(value):
    return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value)

def render_errors(quotes,record,artifact_sha256,require_render=False):
    if not quotes and not require_render:return []
    if not isinstance(record,dict):return ['rendered quotation measurements missing']
    errors=[]
    if record.get('schema')!=VERSION or record.get('artifact_sha256')!=artifact_sha256 or record.get('engine')!='chromium':errors.append('rendered quotation evidence missing or stale')
    views=record.get('viewports')
    if not isinstance(views,list) or len(views)!=2:return errors+['desktop and mobile rendered evidence required']
    for v,width in zip(views,[1280,390]):
        if not isinstance(v,dict) or v.get('width')!=width:
            errors.append('rendered viewport missing or wrong width');continue
        if not re.fullmatch('[0-9a-f]{64}',str(v.get('screenshot_sha256',''))):errors.append('rendered screenshot evidence missing')
        if not finite(v.get('overflow_px')) or v['overflow_px']>2:errors.append(f'{width}px viewport has horizontal page overflow or missing measurement')
        if v.get('authored_sha256') != record.get('authored_sha256') or not record.get('authored_sha256'):errors.append('rendered authored text differs from checked HTML')
        if v.get('hidden_blocks'):errors.append('mapped article text is not visibly rendered: '+', '.join(v['hidden_blocks']))
        if v.get('pseudo_text'):errors.append('CSS-generated article text is absent from the master')
        marks=v.get('lexical_marks',[])
        expected_marks=[m for q in quotes for m in q.get('lexical_marks',[])]
        if isinstance(marks,list) and [{'term':m.get('term'),'text':m.get('text')} for m in marks if isinstance(m,dict)]!=expected_marks:errors.append('rendered lexical marks missing or changed')
        if marks != [] and not isinstance(marks,list):errors.append('invalid rendered lexical marks')
        for mark in marks if isinstance(marks,list) else []:
            if mark.get('visible') is not True or mark.get('underline') is not True:errors.append('lexical emphasis is hidden or lacks a visible underline')
            if mark.get('style') != ('double' if mark.get('term')=='2' else 'solid'):errors.append('lexical emphasis does not distinguish its paired term')
        rows=v.get('callouts')
        if not isinstance(rows,list) or len(rows)!=len(quotes):errors.append('rendered evidence omits source callouts');continue
        for q,row in zip(quotes,rows):
            if not isinstance(row,dict) or row.get('id')!=q['id'] or not isinstance(row.get('paragraphs'),list) or len(row['paragraphs'])!=len(q['paragraphs']):
                errors.append(q['id']+' rendered paragraph coverage differs');continue
            for index,(p,item) in enumerate(zip(q['paragraphs'],row['paragraphs'])):
                if not isinstance(item,dict) or item.get('sha256')!=p['sha256']:
                    errors.append(p['id']+' rendered text differs');continue
                if item.get('visible') is not True or not finite(item.get('height')) or item['height']<=0:errors.append(p['id']+' not visibly rendered')
                if not finite(item.get('gap_before')) or (index>0 and item['gap_before']<8):errors.append(p['id']+f' lacks visible paragraph spacing at {width}px')
                if not finite(item.get('inset_px')) or item['inset_px']<10:errors.append(p['id']+' quotation lacks a visible directional inset')
                low,high=(1.8,2.1) if item.get('language')=='ar' else (1.7,2.0) if item.get('language') in ('he','arc','syr') else (1.5,1.7)
                if not finite(item.get('line_ratio')) or not low<=item['line_ratio']<=high:errors.append(p['id']+' quotation line spacing is outside its readable compact range')
    return errors

def capture(path,output):
    # Import only for explicit browser capture; scan and Git gates remain stdlib.
    from playwright.sync_api import sync_playwright
    if output.exists():raise ValueError('render output exists; preserve prior audit evidence')
    data=path.read_bytes();quotes=extract(data.decode(),'html')
    import review
    def authored(text):return sha(json.dumps(review.extract(text,'html')['blocks'],ensure_ascii=False))
    result={'schema':VERSION,'artifact_sha256':sha(data),'engine':'chromium','authored_sha256':authored(data.decode()),'viewports':[]}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
        try:
            page=browser.new_page()
            page.goto(path.resolve().as_uri(),wait_until='networkidle',timeout=45000)
            page.evaluate('document.fonts.ready')
            for width,height in [(1280,900),(390,844)]:
                page.set_viewport_size({'width':width,'height':height})
                # Expand native source/commentary containers before inspecting.
                page.locator('details').evaluate_all('(els)=>els.forEach(e=>e.open=true)')
                page.evaluate("""() => {window.articleVisible = e => {
                    const r=e.getBoundingClientRect();
                    if(r.height<=0 || r.width<=0 || r.right<=0 || r.left>=innerWidth) return false;
                    if(e.checkVisibility && !e.checkVisibility({checkOpacity:true,checkVisibilityCSS:true})) return false;
                    for(let n=e;n;n=n.parentElement){const s=getComputedStyle(n);
                        if(s.visibility==='hidden'||s.display==='none'||Number(s.opacity)===0||/opacity\\(0(?:%|\\.0+)?\\)/.test(s.filter))return false;}
                    return !/rgba\\([^)]*,\\s*0\\)/.test(getComputedStyle(e).color);
                }}""")
                rows=page.locator('blockquote[data-content-role="source"]').evaluate_all("""els=>els.map((q,i)=>({id:'q'+String(i+1).padStart(4,'0'),paragraphs:[...q.querySelectorAll('p')].map((p,j,ps)=>({text:p.textContent,language:p.lang||(getComputedStyle(p).direction==='rtl'?'ar':'en'),line_ratio:parseFloat(getComputedStyle(p).lineHeight)/parseFloat(getComputedStyle(p).fontSize),inset_px:getComputedStyle(p).direction==='rtl'?(q.getBoundingClientRect().right-parseFloat(getComputedStyle(q).paddingRight)-p.getBoundingClientRect().right):(p.getBoundingClientRect().left-q.getBoundingClientRect().left-parseFloat(getComputedStyle(q).paddingLeft)),visible:window.articleVisible(p),height:p.getBoundingClientRect().height,gap_before:j?p.getBoundingClientRect().top-ps[j-1].getBoundingClientRect().bottom:0}))}))""")
                hidden=page.locator('[data-note-block]').evaluate_all("els=>els.filter(e=>!window.articleVisible(e)).map(e=>e.dataset.noteBlock)")
                pseudo=page.locator('main *').evaluate_all("""els=>els.flatMap(e=>['::before','::after'].map(p=>getComputedStyle(e,p).content)).filter(t=>t&&!['none','normal','""'].includes(t)&&/[A-Za-z0-9\\u0600-\\u06ff]/.test(t))""")
                for row in rows:
                    for item in row['paragraphs']:item['sha256']=sha(flat(item.pop('text')))
                lexical_marks=page.locator('main mark[data-term]').evaluate_all("els=>els.map(e=>({term:e.dataset.term,text:e.textContent,visible:window.articleVisible(e),underline:getComputedStyle(e).textDecorationLine.includes('underline'),style:getComputedStyle(e).textDecorationStyle}))")
                expected_marks=[{'term':m['term'],'text':m['text']} for row in scripture.html(data.decode())[0] for para in row['paragraphs'] for m in para['marks']]
                if [{'term':m['term'],'text':m['text']} for m in lexical_marks]!=expected_marks:raise ValueError('rendered lexical emphasis differs from checked source')
                screenshot=output.with_name(output.stem+f'-{width}.png')
                page.screenshot(path=str(screenshot),full_page=True)
                result['viewports'].append({'width':width,'height':height,'callouts':rows,
                    'lexical_marks':lexical_marks,'authored_sha256':authored(page.content()),'hidden_blocks':hidden,'pseudo_text':pseudo,
                    'overflow_px':page.evaluate('Math.max(0,document.documentElement.scrollWidth-innerWidth)'),
                    'screenshot':str(screenshot),'screenshot_sha256':sha(screenshot.read_bytes())})
        finally:browser.close()
    if path.read_bytes()!=data:raise ValueError('article changed during browser capture')
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['scan','capture']);parser.add_argument('file',type=Path);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.command=='capture':
            if args.file.suffix.lower() not in ('.html','.htm'):raise ValueError('capture requires HTML')
            record=capture(args.file,args.output)
            errors=render_errors(extract(args.file.read_text(),'html'),record,sha(args.file.read_bytes()))
            for error in errors:print('FAIL:',error)
            return bool(errors)
        if args.output.exists():raise ValueError('output exists')
        args.output.write_text(json.dumps(pending(extract(args.file.read_text(),args.file.suffix[1:])),ensure_ascii=False,indent=2)+'\n')
        print('Pending quotation review saved; no source or layout approval granted.')
        return 0
    except (OSError,ValueError,ImportError) as exc:print('ERROR:',exc);return 2

if __name__=='__main__':raise SystemExit(main())
