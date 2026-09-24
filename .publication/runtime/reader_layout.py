"""Validate reader furniture and project disclosure cells back to canonical table order.

Only enumerated interface labels are removed. Every visible facts cell remains
in its original column and row; extra or missing content is an error.
"""
import html,json,re
from html.parser import HTMLParser

class Node:
    def __init__(self,tag='',attrs=None,start=0,parent=None):
        self.tag=tag;self.attrs=attrs or {};self.start=start;self.end=start;self.open_end=start;self.close_start=start;self.parent=parent;self.children=[];self.data=[]
    def text(self):return ''.join(self.data)
    def within(self,other):return self.start>=other.open_end and self.end<=other.close_start

class Tree(HTMLParser):
    VOID={'meta','link','br','hr','img','input','wbr','source','area','base','embed','param','track','col'}
    def __init__(self,source):
        super().__init__(convert_charrefs=True);self.source=source;self.offsets=[0]+[m.end() for m in re.finditer('\n',source)];self.nodes=[];self.stack=[];self.texts=[];self.feed(source)
    def pos(self):
        line,col=self.getpos();return self.offsets[line-1]+col
    def handle_starttag(self,tag,attrs):
        n=Node(tag,dict(attrs),self.pos(),self.stack[-1] if self.stack else None);n.open_end=n.start+len(self.get_starttag_text());n.end=n.open_end;n.close_start=n.open_end
        self.nodes.append(n)
        if n.parent:n.parent.children.append(n)
        if tag not in self.VOID:self.stack.append(n)
    def handle_endtag(self,tag):
        if tag in self.VOID:return
        if not self.stack or self.stack[-1].tag!=tag:raise ValueError('reader HTML nesting is malformed')
        n=self.stack.pop();n.close_start=self.pos();n.end=self.source.index('>',n.close_start)+1
    def handle_data(self,data):
        if self.stack:self.texts.append((data,self.stack[-1]))
        for n in self.stack:n.data.append(data)
    def inner(self,n):return self.source[n.open_end:n.close_start]

def plain(text):return re.sub(r'\s+',' ',html.unescape(text)).strip()
def ancestor(node,key):
    while node:
        if key in node.attrs:return node
        node=node.parent

def normalize(source):
    if 'data-article-format="reader-v1"' not in source:return source
    tree=Tree(source);edits=[];uis=[]
    for n in tree.nodes:
        kind=n.attrs.get('data-reader-ui')
        if not kind:continue
        text=plain(n.text());allowed=False
        if n.parent is None:raise ValueError('reader label has no parent')
        if kind=='contents':allowed=text=='In this article' and n.parent is not None and n.parent.tag in ('nav','summary')
        elif kind=='chapter':allowed=bool(re.fullmatch(r'Chapter \d{2,}',text)) and n.parent is not None and n.parent.tag=='section'
        elif kind=='source':allowed=text in ('Scripture','Transmitted report') and n.parent is not None and n.parent.attrs.get('data-content-role')=='source'
        elif kind=='isnad':allowed=text in ('Isnad · Chain of transmission','الإسناد · Isnad') and 'isnad-segment' in n.parent.attrs.get('class','').split()
        elif kind=='matn':allowed=text in ('Matn · Report text','المتن · Matn') and bool(set(n.parent.attrs.get('class','').split()) & {'source-matn','source-speech'})
        elif kind in ('number','toggle','support','fact-label'):
            table=ancestor(n,'data-reader-table')
            if table:
                headers=json.loads(table.attrs['data-reader-table'])
                row=ancestor(n,'data-reader-row');cell=ancestor(n,'data-reader-cell')
                if kind=='number':allowed=row is not None and n.parent.tag=='summary' and row.attrs['data-reader-row'].isdigit() and text==f"{int(row.attrs['data-reader-row'])+1:02d}"
                elif kind=='toggle':allowed=row is not None and n.parent.tag=='summary' and text=='+'
                elif kind=='support':allowed=cell is not None and cell.attrs['data-reader-cell']==str(len(headers)-1) and headers[-1]=='↗' and n.parent.tag=='a' and text=='Read the supporting passage'
                else:allowed=n.tag=='dt' and n.attrs.get('data-column','').isdigit() and 0<int(n.attrs['data-column'])<len(headers) and text==headers[int(n.attrs['data-column'])]
        if not allowed or n.children:raise ValueError('invalid generated reader label: '+kind)
        uis.append(n);edits.append((n.start,n.end,''))
    for table in [n for n in tree.nodes if 'data-reader-table' in n.attrs]:
        if table.tag!='div' or not re.fullmatch('n[0-9]+',table.attrs.get('data-note-block','')):raise ValueError('facts disclosure lacks its canonical block')
        headers=json.loads(table.attrs['data-reader-table'])
        if not isinstance(headers,list) or len(headers)<2 or not all(isinstance(h,str) and h for h in headers):raise ValueError('invalid facts headers')
        rows=[n for n in tree.nodes if 'data-reader-row' in n.attrs and n.within(table)]
        if not rows:raise ValueError('empty facts disclosure')
        rendered=['<table><tr>'+''.join('<th>'+html.escape(h)+'</th>' for h in headers)+'</tr>']
        consumed=[]
        for index,row in enumerate(rows):
            if row.tag!='details' or row.attrs['data-reader-row']!=str(index):raise ValueError('facts rows missing or reordered')
            cells=[n for n in tree.nodes if 'data-reader-cell' in n.attrs and n.within(row)]
            if [c.attrs['data-reader-cell'] for c in cells]!=[str(k) for k in range(len(headers))]:raise ValueError('facts cells missing or reordered')
            consumed.extend(cells)
            parts=[]
            for cell in cells:
                content=tree.inner(cell)
                for ui in sorted((u for u in uis if u.within(cell)),key=lambda n:n.start,reverse=True):content=content[:ui.start-cell.open_end]+content[ui.end-cell.open_end:]
                parts.append('<td>'+content+'</td>')
            rendered.append('<tr>'+''.join(parts)+'</tr>')
        all_cells=[n for n in tree.nodes if 'data-reader-cell' in n.attrs and n.within(table)]
        if consumed!=all_cells:raise ValueError('orphaned or duplicated facts cells')
        for n in tree.nodes:
            if n.within(table) and not ancestor(n,'data-reader-cell') and n.tag not in {'div','details','summary','span','dl','dt','dd'}:raise ValueError('unsupported facts disclosure element')
        for text,n in tree.texts:
            if n.within(table) and text.strip() and not ancestor(n,'data-reader-cell') and not ancestor(n,'data-reader-ui'):raise ValueError('unmapped facts disclosure content')
        mapped=html.escape(table.attrs['data-note-block'],quote=True)
        replacement='<div data-note-block="'+mapped+'">'+''.join(rendered)+'</table></div>'
        edits=[e for e in edits if not table.start<=e[0]<table.end];edits.append((table.start,table.end,replacement))
    for n in tree.nodes:
        if 'data-reader-caption' not in n.attrs:continue
        caption=n.attrs['data-reader-caption'];target=n.attrs.get('aria-labelledby')
        heading=next((h for h in tree.nodes if h.tag=='h2' and h.attrs.get('id')==target),None)
        section=n.parent
        while section and section.tag!='section':section=section.parent
        if heading is None:
            heading=next((h for h in tree.nodes if h.tag=='h2' and h.parent and h.parent.attrs.get('id')==target),None)
        if not caption or heading is None or section is None or not heading.within(section) or plain(heading.text())!=caption or 'conclusion-card' not in n.attrs.get('class','').split():raise ValueError('conclusion caption must refer to its visible identical heading')
        opening=re.sub(r'\sdata-reader-caption="[^"]*"','',source[n.start:n.open_end])
        edits.append((n.start,n.open_end,opening+'<p>'+html.escape(caption)+'</p>'))
    for start,end,replacement in sorted(edits,reverse=True):source=source[:start]+replacement+source[end:]
    return source


def facts(source):
    """Visible facts content and its stable cell coordinates for browser measurement."""
    if 'data-article-format="reader-v1"' not in source:return []
    normalize(source)
    tree=Tree(source);rows=[]
    for cell in tree.nodes:
        if 'data-reader-cell' not in cell.attrs:continue
        table=ancestor(cell,'data-reader-table');row=ancestor(cell,'data-reader-row')
        if table is None or row is None:raise ValueError('facts cell outside its disclosure row')
        content=tree.inner(cell)
        ui=[n for n in tree.nodes if 'data-reader-ui' in n.attrs and n.within(cell)]
        for n in sorted(ui,key=lambda n:n.start,reverse=True):content=content[:n.start-cell.open_end]+content[n.end-cell.open_end:]
        text=plain(Tree('<div>'+content+'</div>').nodes[0].text())
        rows.append({'id':table.attrs['data-note-block']+':'+row.attrs['data-reader-row']+':'+cell.attrs['data-reader-cell'],'text':text})
    return rows


def render_errors(source,record):
    expected=facts(source)
    if not expected:return []
    errors=[]
    for view in (record or {}).get('viewports',[]):
        cells=view.get('fact_cells',[])
        if [{k:c.get(k) for k in ('id','text')} for c in cells]!=expected:errors.append('rendered facts cells missing, reordered or changed')
        if any(c.get('visible') is not True for c in cells):errors.append('facts cells must be visible when expanded')
    if len((record or {}).get('viewports',[]))!=2:errors.append('facts need desktop and mobile measurements')
    return errors
