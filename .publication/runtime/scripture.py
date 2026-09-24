"""Scripture layers and paired lexical emphasis. No translation or publication."""
import re
import unicodedata
from html.parser import HTMLParser

MARK = re.compile(r'<mark data-term="([12])">([^<>]+)</mark>')
ROLES = ('original', 'transliteration', 'translation')

def unmark(text):
    plain = MARK.sub(lambda m:m[2], text)
    if re.search(r'</?mark\b', plain, re.I):
        raise ValueError('Use only <mark data-term="1|2">literal word</mark>; no nested marks or extra attributes')
    return plain

def runs(text):
    unmark(text)
    result=[];end=0;offset=0
    for m in MARK.finditer(text):
        offset+=len(text[end:m.start()])
        result.append({'term':m[1],'text':m[2],'start':offset,'end':offset+len(m[2])})
        offset+=len(m[2]);end=m.end()
    return result

def normalized(text):
    return re.sub(r'\s+',' ',text).strip()

def markdown(source):
    lines=source.splitlines();result=[];i=0
    while i<len(lines):
        m=re.match(r'^>\s*\[!quote\][-+]?\s*(.*)',lines[i],re.I)
        if not m:i+=1;continue
        row={'caption':m[1],'paragraphs':[]};i+=1;buf=[];parts=[]
        while i<len(lines) and lines[i].startswith('>'):
            text=re.sub(r'^(?:>\s?)+','',lines[i])
            if text.strip():buf.append(text)
            elif buf:parts.append(normalized(' '.join(buf)));buf=[]
            i+=1
        if buf:parts.append(normalized(' '.join(buf)))
        role='original'
        for text in parts:
            if text.startswith('*') and text.endswith('*') and not text.startswith('**'):
                role='transliteration';text=text[1:-1]
            elif role=='transliteration':role='translation'
            row['paragraphs'].append({'role':role,'text':unmark(text),'marks':runs(text)})
        result.append(row)
    return result

class ScriptureHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True);self.rows=[];self.row=None;self.p=None;self.mark=None;self.depth=0;self.errors=[];self.citing=False
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if self.mark is not None:self.errors.append('Nested markup inside lexical marks is forbidden')
        if tag=='p' and 'transliteration' in a.get('class','').split() and self.row is None:self.errors.append('Transliteration paragraphs are scripture-only')
        if tag=='blockquote':
            if self.row:self.depth+=1
            elif 'quran-callout' in a.get('class','').split():
                self.row={'caption':'','paragraphs':[]};self.depth=1
        if tag=='cite' and self.row is not None:self.citing=True
        if tag=='p' and self.row is not None:
            classes=a.get('class','').split();role=next((r for r in ('transliteration','translation') if r in classes),'original')
            self.p={'role':role,'text':'','marks':[],'language':a.get('lang','')}
        if tag=='mark':
            if self.p is None or self.mark is not None or set(a)!={'data-term'} or a.get('data-term') not in {'1','2'}:
                self.errors.append('Lexical marks require a scripture paragraph and only data-term="1|2"')
            else:self.mark={'term':a['data-term'],'start':len(self.p['text']),'text':''}
    def handle_data(self,data):
        if self.citing and self.row is not None:self.row['caption']+=data
        if self.p is not None:self.p['text']+=data
        if self.mark is not None:self.mark['text']+=data
    def handle_endtag(self,tag):
        if tag=='cite':self.citing=False
        if tag=='mark' and self.mark is not None:
            self.mark['end']=len(self.p['text']);self.p['marks'].append(self.mark);self.mark=None
        if tag=='p' and self.p is not None:
            self.row['paragraphs'].append(self.p);self.p=None
        if tag=='blockquote' and self.row is not None:
            self.depth-=1
            if self.depth==0:self.rows.append(self.row);self.row=None

def html(source):
    parser=ScriptureHTML();parser.feed(source)
    if parser.mark is not None:parser.errors.append('Unclosed lexical mark')
    return parser.rows,parser.errors

def errors(source,fmt):
    try:
        rows,issues=(html(source) if fmt in ('html','htm') else (markdown(source),[]))
    except ValueError as exc:return [str(exc)]
    if fmt not in ('html','htm'):
        try:unmark(source)
        except ValueError as exc:issues.append(str(exc))
        if len(MARK.findall(source))!=sum(len(p['marks']) for row in rows for p in row['paragraphs']):issues.append('Lexical marks are allowed only inside scripture quotation layers')
    for i,row in enumerate(rows,1):
        prefix=f'scripture {i}: '
        order=[ROLES.index(p['role']) for p in row['paragraphs']]
        if order!=sorted(order):issues.append(prefix+'layers must be original, transliteration, then English')
        found={p['role'] for p in row['paragraphs'] if p['text'].strip()}
        for role in ROLES:
            if role not in found:issues.append(prefix+'missing '+role+' layer')
        for para in row['paragraphs']:
            if para['role']=='transliteration' and any(unicodedata.category(ch).startswith('L') and 'LATIN' not in unicodedata.name(ch,'') and 'MODIFIER LETTER' not in unicodedata.name(ch,'') for ch in para['text']):
                issues.append(prefix+'transliteration must use Roman letters, not copied source script')
        for para in row['paragraphs']:
            if para['role']=='translation':
                letters=[ch for ch in para['text'] if unicodedata.category(ch).startswith('L')]
                latin=sum('LATIN' in unicodedata.name(ch,'') for ch in letters)
                if letters and latin<=len(letters)-latin:issues.append(prefix+'translation must contain English, not a copied source-language paragraph')
        slots={r:{} for r in ROLES}
        for p in row['paragraphs']:
            for mark in p['marks']:slots[p['role']].setdefault(mark['term'],[]).append(mark)
        ids=set().union(*(set(v) for v in slots.values()))
        if len(ids)>2 or not ids<={'1','2'}:issues.append(prefix+'at most two linked terms are allowed')
        for term in ids:
            for role in ROLES:
                marks=slots[role].get(term,[])
                if len(marks)!=1:issues.append(prefix+f'term {term} needs exactly one mark in {role}')
                elif not marks[0]['text'].strip():issues.append(prefix+'empty lexical mark')
                elif role!='translation' and len(marks[0]['text'].split())!=1:issues.append(prefix+'mark one source lexeme and its romanization, not an entire phrase')
                elif role=='translation' and re.search(r'[.!?;]|\b(?:because|although|whereas|therefore)\b',marks[0]['text'],re.I):issues.append(prefix+'highlight the English rendering of one lexeme, not a sentence or clause')
        originals=[p for p in row['paragraphs'] if p['role']=='original']
        # Arabic must not be inserted as an intermediary beside another source script.
        scripts=set()
        for p in originals:
            if re.search(r'[\u0621-\u064a]',p['text']):scripts.add('ar')
            if re.search(r'[\u0370-\u03ff\u1f00-\u1fff]',p['text']):scripts.add('grc')
            if re.search(r'[\u0590-\u05ff]',p['text']):scripts.add('he')
        bible=re.search(r'\b(?:Bible|Torah|Tanakh|Genesis|Exodus|Leviticus|Numbers|Deuteronomy|Joshua|Judges|Ruth|Samuel|Kings|Chronicles|Ezra|Nehemiah|Esther|Job|Psalms?|Proverbs|Ecclesiastes|Song(?: of (?:Songs|Solomon))?|Canticles|Wisdom|Sirach|Tobit|Judith|Baruch|Maccabees|Isaiah|Jeremiah|Lamentations|Ezekiel|Daniel|Hosea|Joel|Amos|Obadiah|Jonah|Micah|Nahum|Habakkuk|Zephaniah|Haggai|Zechariah|Malachi|Matthew|Mark|Luke|John|Acts|Romans|Corinthians|Galatians|Ephesians|Philippians|Colossians|Thessalonians|Timothy|Titus|Philemon|Hebrews|James|Peter|Jude|Revelation)\b',row['caption'],re.I)
        if bible and any(re.search(r'[\u0621-\u064a]',p['text']) for p in row['paragraphs']):issues.append(prefix+'Arabic intermediary is forbidden in every Bible layer')
        if 'ar' in scripts and (len(scripts)>1 or bible):issues.append(prefix+'Arabic intermediary is forbidden; quote the identified source language directly')
        if fmt in ('html','htm'):
            langs={p['language'] for p in originals}
            if '' in langs or len(langs)!=1:issues.append(prefix+'identify one actual source language with lang on every original paragraph')
            if 'ar' in langs and langs!={'ar'}:issues.append(prefix+'Arabic intermediary is forbidden')
            if any(p['language'] not in ('','en') for p in row['paragraphs'] if p['role']=='translation'):issues.append(prefix+'translation must be English')
    return issues

def highlights(source,fmt):
    rows=html(source)[0] if fmt in ('html','htm') else markdown(source)
    return [[{'role':p['role'],'text':p['text'],'marks':p['marks']} for p in row['paragraphs']] for row in rows if any(p['marks'] for p in row['paragraphs'])]
