#!/usr/bin/env python3
"""Deterministic Markdown-to-HTML rendering. No rewriting, approval, or publishing."""
import argparse
import copy
import datetime
import html
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import handoff as H
VERSION='2026-09-23.1'
TEMPLATES=ROOT.parent/'skills/faith-reason-note'
SOURCE_TYPES={'info','note','tip','warning','quote'}
CALL=re.compile(r'^> ?\[!(\w+)\][-+]?\s*(.*)$')
AR=re.compile(r'[\u0621-\u063a\u0641-\u064a\u066e-\u06d3]')
HONORIFIC=re.compile(r'[\uFD40-\uFD4F\uFDFA-\uFDFF]')


def esc(s):return html.escape(str(s),quote=True)
def slug(text):
    value=re.sub(r'[^\w\s-]','',H.inline(text).lower(),flags=re.UNICODE)
    value=re.sub(r'[\s_]+','-',value).strip('-')
    if not value:raise ValueError('heading needs an explicit section ID: '+text)
    return value


def metadata(source):
    m=re.match(r'^---\n(.*?)\n---\n',source,re.S)
    if not m:raise ValueError('frontmatter is required')
    values={}
    for line in m[1].splitlines():
        found=re.match(r'^([a-z][a-z_-]*):\s*(.*)$',line)
        if not found:continue
        key,value=found.groups()
        if key in values:raise ValueError('duplicate frontmatter key: '+key)
        if value[:1] in ('"',"'"):
            if value[0]=='"':value=json.loads(value)
            elif value.endswith("'"):value=value[1:-1].replace("''", "'")
        if key in ('title','summary','category','opponent') and value in ('|','>','|-','>-'):
            raise ValueError(key+': use a single-line frontmatter scalar')
        values[key]=value
    return values,source[m.end():]


def source_items(source):
    """Keep raw source alongside the authoritative handoff block inventory."""
    _,body=metadata(source);chunks=[];buf=[];start=1
    def flush():
        nonlocal buf
        if buf:chunks.append((start,list(buf)));buf=[]
    for number,line in enumerate(body.splitlines(),1):
        if not line.strip() or re.fullmatch(r'\s*---+\s*',line):flush();continue
        if line.startswith('#'):
            flush();chunks.append((number,[line]));continue
        if not buf:start=number
        buf.append(line)
    flush()
    expected,_=H.blocks(source);items=[]
    for line,raw in chunks:
        one,_=H.blocks('---\ncategory: commentary\n---\n'+'\n'.join(raw)+'\n')
        if len(one)!=1:raise ValueError(f'body line {line}: block needs explicit separation')
        item=dict(one[0],line=line,raw=raw,id=f'n{len(items)+1:04d}')
        items.append(item)
    if [{k:i[k] for k in ('id','text','links')} for i in items]!=expected:
        raise ValueError('source parser differs from handoff inventory; stop before rendering')
    return items


def text_html(text):return HONORIFIC.sub(lambda m:'<span class="honorific">'+m[0]+'</span>',html.escape(text,quote=False))


def inline(text,receipt):
    """Render the exact supported inline syntax without flattening links or marks."""
    H.scripture.unmark(text)
    links={a:(b,label,target) for a,b,label,target in H.link_tokens(text)}
    out=[];i=0
    while i<len(text):
        if i in links:
            end,label,target=links[i]
            if target.startswith('wiki:'):
                if target not in receipt.get('note_map',{}):raise ValueError('unresolved catalogue link: '+target)
                target=receipt['note_map'][target]
            elif target.startswith('#'):target=receipt.get('anchor_map',{}).get(target,target)
            elif re.match(r'^[a-z][a-z0-9+.-]*:',target,re.I) and not target.startswith(('https://','http://','mailto:')):
                raise ValueError('unsupported link scheme: '+target)
            out.append(f'<a href="{esc(target)}">{inline(label,receipt)}</a>');i=end;continue
        mark=H.scripture.MARK.match(text,i)
        if mark:
            out.append(f'<mark data-term="{mark[1]}">{esc(mark[2])}</mark>');i=mark.end();continue
        matched=False
        for token,tag in [('**','strong'),('`','code'),('*','em')]:
            if text.startswith(token,i):
                end=text.find(token,i+len(token))
                if end>i+len(token):
                    content=text[i+len(token):end]
                    out.append(f'<{tag}>'+ (text_html(content) if tag=='code' else inline(content,receipt))+f'</{tag}>')
                    i=end+len(token);matched=True;break
        if matched:continue
        if text[i]=='<' and re.match(r'</?[A-Za-z!]',text[i:]):raise ValueError('unsupported raw HTML in Markdown')
        out.append(text_html(text[i]));i+=1
    return ''.join(out)


def callout_parts(item):
    match=CALL.match(item['raw'][0]);kind,caption=match.groups();parts=[];buf=[]
    for line in item['raw'][1:]:
        if not line.startswith('>'):raise ValueError(item['id']+': separate callout and prose with a blank line')
        value=re.sub(r'^>\s?','',line)
        if value.startswith('>'):raise ValueError(item['id']+': nested quote syntax needs an explicit renderer extension')
        if value.strip():buf.append(value)
        elif buf:parts.append(' '.join(buf));buf=[]
    if buf:parts.append(' '.join(buf))
    return kind,caption,parts


def original_language(caption,text,options):
    declared=options.get('languages',{}).get(caption)
    if declared:
        if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]+)*',declared):raise ValueError('invalid source language for '+caption)
        return declared
    # Arabic reports and explicitly named scripture editions have established labels.
    if AR.search(text):return 'ar'
    if re.search(r'[\u0370-\u03ff\u1f00-\u1fff]',text) and re.search(r'Greek|Textus Receptus|Septuagint|SBLGNT|Nestle',caption,re.I):return 'grc'
    if re.search(r'[\u0590-\u05ff]',text) and re.search(r'Hebrew|Leningrad|Masoretic|BHS|WLC',caption,re.I):return 'he'
    raise ValueError('declare the actual source language in render.languages for caption: '+caption)


def original_attrs(language):
    if language=='ar':return 'class="rtl font-amiri text-xl" lang="ar" dir="rtl"'
    if language in ('he','arc','syr'):return f'class="font-hebrew text-xl" lang="{language}" dir="rtl"'
    return f'class="text-xl" lang="{esc(language)}"'


def render_source(item,receipt,options):
    kind,caption,parts=callout_parts(item);identifier=item['id']
    layout=receipt['paragraph_layout'][identifier]
    if [H.inline(re.sub(r'^\s*(?:[-*+] |\d+\. )','',p)) for p in parts]!=layout['paragraphs']:
        raise ValueError(identifier+': source paragraph mapping differs')
    if any(re.match(r'^\s*(?:[-*+] |\d+\. )', re.sub(r'^>\s?', '', line)) for line in item['raw'][1:]):
        raise ValueError(identifier+': literal source numbering/bullets need a preserving handoff extension; never strip source text')
    rendered=[];role='original'
    original_count=options.get('source_paragraphs',{}).get(H.inline(caption))
    if original_count is not None and (type(original_count) is not int or not 0<original_count<len(parts)):
        raise ValueError(identifier+': source_paragraphs must leave at least one original and one English paragraph')
    for index,raw in enumerate(parts):
        # Match the supported master's paragraph role convention.
        if kind=='quote':
            if raw.startswith('*') and raw.endswith('*') and not raw.startswith('**'):
                role='transliteration';raw=raw[1:-1]
            elif role=='transliteration':role='translation'
        else:
            non_latin=re.search(r'[\u0370-\u03ff\u0590-\u05ff\u1f00-\u1fff]',H.scripture.unmark(raw))
            role='original' if (index<original_count if original_count is not None else AR.search(H.scripture.unmark(raw)) or non_latin) else 'translation'
            if original_count is None and options.get('languages',{}).get(H.inline(caption)) in ('la','en'):
                raise ValueError(identifier+': declare source_paragraphs for Latin-script report layers')
        if role=='original':attrs=original_attrs(original_language(H.inline(caption),H.inline(raw),options))
        elif role=='transliteration':attrs='class="italic transliteration"'
        else:attrs='class="translation" lang="en"'
        rendered.append(f'<p {attrs}>{inline(raw,receipt)}</p>')
    css='quran-callout' if kind=='quote' else 'hadith-callout'
    return f'<blockquote class="{css}" data-content-role="source" data-note-block="{identifier}">'+''.join(rendered)+f'<cite data-note-citation>{inline(caption,receipt)}</cite></blockquote>'


def table_cells(line):
    line=line.strip().strip('|');links={a:b for a,b,_,_ in H.link_tokens(line)}
    cells=[];buf='';i=0
    while i<len(line):
        if i in links:end=links[i];buf+=line[i:end];i=end;continue
        if line.startswith('\\|',i):buf+='|';i+=2;continue
        if line[i]=='|':cells.append(buf.strip());buf=''
        else:buf+=line[i]
        i+=1
    cells.append(buf.strip());return cells


def render_list(raw,receipt):
    items=[];ordered=None;start=None
    for line in raw:
        m=re.match(r'^([-*+] |(\d+)\. )(.*)$',line)
        if m:
            current=bool(m[2])
            if ordered is not None and current!=ordered:raise ValueError('mixed list types need a blank line')
            if ordered is None:ordered=current;start=m[2]
            items.append(m[3])
        elif re.match(r'^\s+[-*+\d]',line):raise ValueError('nested lists need an explicit renderer extension')
        elif items:items[-1]+=' '+line.strip()
        else:raise ValueError('invalid list continuation')
    tag='ol' if ordered else 'ul';attr=f' start="{int(start)}"' if ordered else ''
    return f'<{tag}{attr}>'+''.join('<li>'+inline(t,receipt)+'</li>' for t in items)+f'</{tag}>'


def render_block(item,receipt,options):
    raw=item['raw'];first=raw[0];identifier=item['id'];mapped=f'data-note-block="{identifier}"'
    call=CALL.match(first)
    if call:
        kind,caption,parts=callout_parts(item)
        if kind in SOURCE_TYPES:return render_source(item,receipt,options)
        if kind not in ('abstract','summary'):raise ValueError(identifier+': unsupported callout '+kind)
        css='premise-card' if kind=='abstract' else 'conclusion-card'
        inner='<p>'+inline(caption,receipt)+'</p>' if caption else ''
        lines=[re.sub(r'^>\s?','',line) for line in raw[1:]]
        if lines and re.match(r'^(?:[-*+] |\d+\. )',lines[0]):inner+=render_list(lines,receipt)
        else:inner+=''.join('<p>'+inline(p,receipt)+'</p>' for p in parts)
        return f'<div class="{css}" {mapped}>{inner}</div>'
    if first.startswith('|'):
        rows=[table_cells(line) for line in raw if not re.fullmatch(r'[|:\-\s]+',line)]
        if any(len(row)!=len(rows[0]) for row in rows):raise ValueError(identifier+': inconsistent table columns')
        content=''
        for index,row in enumerate(rows):
            tag='th' if index==0 else 'td'
            content+='<tr>'+''.join(f'<{tag}>'+inline(cell,receipt)+f'</{tag}>' for cell in row)+'</tr>'
        return f'<div class="table-scroll" {mapped}><table>{content}</table></div>'
    if re.match(r'^(?:[-*+] |\d+\. )',first):
        fact=all(re.match(r'^[-*+] \*\*[^*]+:?\*\*',line) for line in raw)
        if fact:
            return f'<div class="premise-card space-y-1 mb-4" {mapped}>'+''.join('<p class="text-sm">'+inline(re.sub(r'^[-*+] ','',line),receipt)+'</p>' for line in raw)+'</div>'
        return f'<div {mapped}>'+render_list(raw,receipt)+'</div>'
    if first.startswith('>'):
        return f'<blockquote {mapped}><p>'+inline(' '.join(re.sub(r'^>\s?','',line) for line in raw),receipt)+'</p></blockquote>'
    if any(re.match(r'^(?:[-*+] |\d+\. |>|\|)',line) for line in raw[1:]):raise ValueError(identifier+': separate different block types with blank lines')
    return f'<p {mapped}>'+inline(' '.join(raw),receipt)+'</p>'


def validate_options(options):
    if not isinstance(options,dict):raise ValueError('render config must be an object')
    allowed={'slug','template','languages','source_paragraphs','section_ids','note_map','register'}
    if set(options)-allowed:raise ValueError('unknown render options: '+', '.join(sorted(set(options)-allowed)))
    for key in ('languages','source_paragraphs','section_ids','note_map'):
        if key in options and not isinstance(options[key],dict):raise ValueError(key+' must be an object')
    for key in ('languages','section_ids','note_map'):
        if any(not isinstance(k,str) or not isinstance(v,str) for k,v in options.get(key,{}).items()):raise ValueError(key+' must map strings to strings')
    if options.get('register','standard') not in ('standard','haddad'):raise ValueError('unknown prose register')


def render(source,receipt,options=None,site_root=None):
    options={} if options is None else options;receipt=copy.deepcopy(receipt)
    validate_options(options)
    if H.sha(source)!=receipt.get('source_sha256'):raise ValueError('master bytes differ from handoff')
    meta,_=metadata(source);items=source_items(source)
    if not items or not items[0]['raw'][0].startswith('# '):raise ValueError('master must start with one H1 title')
    captions={H.inline(CALL.match(i['raw'][0])[2]) for i in items if CALL.match(i['raw'][0])}
    for key in ('languages','source_paragraphs'):
        if set(options.get(key,{}))-captions:raise ValueError(key+': configured caption is absent from the master')
    headings=[i for i in items if i['raw'][0].startswith('#')];ids={};heading_by_text={}
    special={'The Facts':'facts','Final Verdict':'verdict','The Reading':'reading','Commentary':'commentary','Glossary':'glossary'}
    for item in headings:
        m=re.match(r'^(#{1,3})\s+(.+)$',item['raw'][0])
        if not m:raise ValueError(item['id']+': headings deeper than H3 need an explicit extension')
        level=len(m[1]);label=H.inline(m[2])
        if label in heading_by_text:raise ValueError('duplicate heading: '+label)
        target=options.get('section_ids',{}).get(label,special.get(label,slug(label)))
        if not re.fullmatch(r'[\w-]+',target,re.UNICODE) or target in ids.values():raise ValueError('invalid/duplicate section ID: '+target)
        ids[item['id']]=target;heading_by_text[label]=target;item.update(level=level,label=label,heading=m[2])
    if set(options.get('section_ids',{}))-set(heading_by_text):raise ValueError('section_ids: configured heading is absent from the master')
    if sum(i['level']==1 for i in headings)!=1:raise ValueError('master needs exactly one H1')
    for link in receipt['links']:
        target=link['target']
        if target.startswith('#'):
            mapped=heading_by_text.get(target[1:],target[1:] if target[1:] in ids.values() else None)
            if not mapped:raise ValueError('unresolved master heading link: '+target)
            receipt['anchor_map'][target]='#'+mapped
    receipt['note_map']=dict(options.get('note_map',receipt.get('note_map',{})))
    for target in receipt['note_map'].values():
        if not re.fullmatch(r'[A-Za-z0-9_./-]+\.html(?:#[A-Za-z0-9_.:-]+)?',target):raise ValueError('invalid internal note target: '+target)
        if site_root:
            path=(Path(site_root)/target.split('#')[0]).resolve()
            if not path.is_relative_to(Path(site_root).resolve()) or not path.is_file():raise ValueError('internal note missing from site: '+target)
    title=headings[0]['label'];category=receipt['category'];template_name=options.get('template','flowing' if category=='narration' else 'tabs')
    if template_name not in ('tabs','flowing'):raise ValueError('template must be tabs or flowing')
    template=(TEMPLATES/f'template-{template_name}.html').read_text()
    head=template.split('</head>',1)[0]
    replacements={'SOURCE_NOTE_SHA256':receipt['source_sha256'],'PAGE_TITLE':title,'META_DESCRIPTION':meta.get('summary',''),'META_KEYWORDS':meta.get('keywords',''),'FILENAME':options.get('slug',slug(title))+'.html'}
    for key,value in replacements.items():head=head.replace('{{'+key+'}}',esc(value))
    if '{{' in head:raise ValueError('template head has unknown placeholders')
    css=(ROOT/'quotation.css').read_text()
    head+='\n<style>\n'+css+'''
body {margin:0} .article-shell{max-width:56rem;margin:auto;padding:1.25rem}
main p{margin-block-end:1em} main h2{margin-block:2rem 1rem} main h3{margin-block:1.5rem .75rem}
main .premise-card,main .conclusion-card{margin-block:1rem;padding:1.25rem;border-radius:.5rem}
main ul,main ol{padding-inline-start:1.5rem} main ul{list-style:disc} main ol{list-style:decimal}
main li+li{margin-block-start:.5em} main a{text-decoration:underline;color:#8A6D3B}
.table-scroll{overflow-x:auto;margin-block:1rem} table{width:100%;border-collapse:collapse}
th,td{padding:.65rem;border:1px solid #E7E0D1;text-align:start;vertical-align:top}
.font-hebrew{font-family:'SBL Hebrew',serif} .nav-row{display:flex;gap:1rem;overflow-x:auto;white-space:nowrap}
.commentary-card{padding-block:1rem} summary{cursor:pointer} section,article,h2,h3{scroll-margin-top:5rem}
@media print{nav.section-nav{display:none} details{display:block}}
</style></head>'''
    title_html=f'<h1 id="{esc(ids[items[0]["id"]])}" class="font-serif text-4xl" data-note-block="{items[0]["id"]}">'+inline(items[0]['heading'],receipt)+'</h1>'
    header='<header class="article-shell"><a href="index.html">Faith &amp; Reason in Islam</a>'+title_html
    if meta.get('summary'):header+='<p>'+text_html(meta['summary'])+'</p>'
    header+='</header>'
    nav='<nav class="section-nav" aria-label="Article sections"><div class="article-shell nav-row">'+''.join(f'<a class="navlink" href="#{esc(ids[i["id"]])}">{text_html(i["label"])}</a>' for i in headings if i['level']==2)+'</div></nav>'
    opponent=''
    if meta.get('opponent'):
        if meta['opponent'] not in ('christian','sunni','orientalist','secular'):raise ValueError('invalid opponent metadata')
        opponent=' data-opponent="'+meta['opponent']+'"'
    body=[f'<main class="article-shell" data-category="{category}"{opponent}>'];section=False;details=False;article=False
    for item in items[1:]:
        if 'level' in item:
            level=item['level'];label=item['label'];sid=ids[item['id']]
            if level==2:
                if article:body.append('</article>');article=False
                if details:body.append('</details>');details=False
                if section:body.append('</section>')
                body.append(f'<section id="{esc(sid)}" class="content-section">');section=True
                if (category=='narration' and label=='Commentary') or label in ('Glossary','Glossary of Key Terms'):
                    body.append('<details open><summary>');details=True
                    body.append(f'<h2 class="font-serif text-3xl" data-note-block="{item["id"]}">'+inline(item['heading'],receipt)+'</h2></summary>')
                else:body.append(f'<h2 class="font-serif text-3xl" data-note-block="{item["id"]}">'+inline(item['heading'],receipt)+'</h2>')
            else:
                if category in ('debate','exegesis'):raise ValueError(item['id']+': this category requires H2 sections, not H3 subdivisions')
                if article:body.append('</article>')
                body.append(f'<article id="{esc(sid)}" class="commentary-card">');article=True
                body.append(f'<h3 class="font-serif text-2xl" data-note-block="{item["id"]}">'+inline(item['heading'],receipt)+'</h3>')
        else:body.append(render_block(item,receipt,options))
    if article:body.append('</article>')
    if details:body.append('</details>')
    if section:body.append('</section>')
    body.append('</main>')
    scripts='\n'.join(re.findall(r'<script\b[^>]*>.*?</script>',template.split('</head>',1)[1],re.S))
    footer=f'<footer class="article-shell"><p>© {datetime.date.today().year} Faith &amp; Reason in Islam · All Rights Reserved</p></footer>'
    page=head+'<body>'+header+nav+'\n'.join(body)+scripts+footer+'</body></html>\n'
    errors=H.verify(page,receipt)
    if errors:raise ValueError('conversion rejected: '+'; '.join(errors))
    return page,receipt


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('receipt',type=Path);p.add_argument('output',type=Path);p.add_argument('--config',type=Path);p.add_argument('--mapped-receipt',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.output.exists() or a.mapped_receipt.exists():raise ValueError('outputs exist; preserve previous builds')
        data=json.loads(a.receipt.read_text());options=json.loads(a.config.read_text()) if a.config else {}
        page,receipt=render(data['source_markdown'],data,options)
        a.output.parent.mkdir(parents=True,exist_ok=True);a.mapped_receipt.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(page);a.mapped_receipt.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
        print('Rendered and handoff-verified',len(receipt['blocks']),'blocks. No approval or publication performed.');return 0
    except (OSError,ValueError,KeyError,TypeError) as exc:print('BLOCKED:',exc);return 1
if __name__=='__main__':raise SystemExit(main())
