#!/usr/bin/env python3
"""Extract prose, preserve source blocks, and verify hash-bound editorial review.

prepare ORIGINAL --snapshot baseline.json
inspect DRAFT --snapshot baseline.json --output review.json
verify DRAFT --snapshot baseline.json --review review.json

Inspect produces a PENDING review. A reviewer must read every prose block and
complete concrete observations. This tool checks evidence of review, not whether
an LLM's editorial judgment is correct. No command publishes anything.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

VERSION = '2026-09-23.3'
ROOT = Path(__file__).resolve().parent
# Validators may load this module by path from another skill directory.
import importlib.util
_layout_spec = importlib.util.spec_from_file_location('article_quote_layout', ROOT/'quote_layout.py')
quote_layout = importlib.util.module_from_spec(_layout_spec)
_layout_spec.loader.exec_module(quote_layout)
AR = re.compile(r'[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]')
CUES = {
    'opaque-verdict': r'\b(?:one (?:word|command|line|look|sign|tear|answer|name|blow) (?:won|held|answered|changed|decided|ended|broke|silenced) (?:it|everything|them|him|her|all)|(?:that|this) (?:was|is) the (?:answer|story|test|point|turn)|it (?:was|is) enough|that (?:decided|settled|answered) (?:it|everything|him))\b',
    'argumentative-metaphor': r'\b(?:clos\w* the door|open\w* the road|hinge of (?:this|the) history|strips? the .{1,45} of its disguise|refuted .{0,25} by its own silence)\b',
    'litotes': r'\b(?:not (?:un\w+|insignificant|without|unknown|impossible)|no (?:small|minor|ordinary|mere|little)\b|hardly|scarcely|nothing if not|not for nothing)\b',
    'decorative-contrast': r'\b(?:not\b[^.!?]{1,140}\bbut\b|rather than|instead of|as opposed to|whatever the\b[^.!?,]{0,80}|even (?:his|her|their|its) own)\b',
    'irony': r'\b(?:of course|naturally|predictably|needless to say|one might almost say|how convenient|graciously concedes?)\b',
    'empty-framing': r'\b(?:(?:the|this) (?:reasoning|point|answer|verdict|record|picture) is (?:stated plainly|clear|simple|plain|obvious)|the documented facts are these|both (?:things|sides) are in the sources|the same entry preserves the sequel)\b',
    'source-performance': r'\b(?:keeps?\b[^.!?]{0,90}\bon the record|(?:the |his own )?(?:record|portrait|entry|obituary|tradition) (?:turns|is double.edged|tells a fuller story|stands as|carries its qualifications)|(?:the|a)\b[^.!?]{0,40}\b(?:held the darker view|fairest surviving assessment))\b',
    'process-leakage': r'\b(?:every quotation below|quoted here as|cited here with|kept as printed|our research strategy|we (?:selected|chose) (?:these|the) sources|school.s own (?:sources|biographical dictionary)|(?:record|sources) of his own school)\b',
    'source-narration': r"\b(?:preserves? the shape of (?:the|a) scene|(?:report|source|account).s own detail|(?:reading|argument) stands on [^.!?]{1,65} page|(?:the |one )?(?:report|relay|entry) (?:still )?does its work)\b",
    'rhetorical-flourish': r"\b(?:before anyone thought to doubt it|no one in (?:the|this) [^.!?]{1,45} stops to ask|(?:reaches?|reach) the same ground by another road|if [^,;.!?]{1,45} falls, the (?:idiom|argument|case|reading) stands|one speaker, two addresses, two peoples)\b",
    'document-navigation': r'\b(?:the next (?:(?:two|three|four|\d+) )?(?:parts?|sections?)|the previous section|this (?:article|section) (?:shows|examines|will)|where the story runs next)\b',
}
QUANTIFIERS = re.compile(r'\b(?:all|every|always|never|none|no|not|most|some|only|may|might|likely|possibly|reportedly|attributed|proves?|suggests?)\b', re.I)

def digest(data: bytes | str) -> str:
    return hashlib.sha256(data.encode() if isinstance(data, str) else data).hexdigest()


SEMANTIC_CHECKS = (
    'meta-and-process', 'litotes', 'decorative-contrast', 'irony-and-theater',
    'openings-and-repetition', 'first-read-clarity', 'fidelity-and-attribution',
)
FUNCTIONS = {'claim','evidence','explanation','inference','qualification','locator','heading','data'}
COUNCIL_ROLES = {'prose','economy','reader','fidelity','reasoning'}

def policy_digest() -> str:
    # Bind the actual review policy and implementation, not just the prose contract.
    names = ('contract.md','drafting.md','editorial.md','council-article.md','paragraphs.md','quote_layout.py','review.py','handoff.py','pre_push.py')
    return digest(''.join(name + ':' + digest((ROOT/name).read_bytes()) + '\n' for name in names))

def cue_items(blocks: list[dict]) -> list[dict]:
    items=[]
    for block in blocks:
        for name,pattern in CUES.items():
            for match in re.finditer(pattern,block['text'],re.I):
                items.append({'id':f"{block['id']}:{name}:{match.start()}",
                              'block_id':block['id'],'kind':name,'text':match.group(),
                              'status':'pending','reason':''})
    return items

def save(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)

def read(path: Path) -> dict:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f'{path}: expected JSON object')
    return data

class ProseHTML(HTMLParser):
    """Gather authored text while hashing immutable source/layout regions."""
    BLOCK = {'p','h1','h2','h3','h4','h5','h6','li','summary','title','div','section','article','main','br','blockquote','table','tr','td','th'}
    PROTECT = {'pre','code','cite','script','style'}
    VOID = {'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.offsets = [0] + [m.end() for m in re.finditer('\n', source)]
        self.stack = []
        self.text = []
        self.blocks = []
        self.protected = []
        self.links = []
        self.protect_start = None
        self.kind = 'prose'
        self.feed(source)
        self.close()
        self.flush()
        if self.stack:
            raise ValueError('unclosed HTML elements: ' + ', '.join(x['tag'] for x in self.stack[-5:]))
    def pos(self):
        row, col = self.getpos()
        return self.offsets[row-1] + col
    def hidden(self):
        return any(x['hidden'] for x in self.stack)
    def flush(self):
        text = re.sub(r'\s+', ' ', ''.join(self.text)).strip()
        if text:
            self.blocks.append({'kind':self.kind,'text':text})
            if any(x['tag'] in {'td','th'} for x in self.stack):
                self.protected.extend('table-number:'+n for n in re.findall(r'\d+(?:[.,]\d+)*', text))
        self.text = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.BLOCK:
            self.flush()
            self.kind = tag
        for key in ('href','src','id'):
            if key in a:
                self.links.append((key,a[key]))
        if tag == 'meta' and a.get('name') in ('description',):
            self.blocks.append({'kind':'description','text':a.get('content','')})
        classes = a.get('class','').split()
        # Layout and language classes never exempt authored text. Only explicit
        # source containers protect quotations; their evidence is checked separately.
        protect = tag in self.PROTECT or (tag in {'blockquote','table'} and a.get('data-content-role') == 'source')
        hidden = protect or tag in {'nav','footer'}
        if protect and self.protect_start is None:
            self.flush()
            self.protect_start = self.pos()
        if tag not in self.VOID:
            self.stack.append({'tag':tag,'protected':protect,'hidden':hidden})
        elif protect and self.protect_start is not None:
            self.protected.append(self.source[self.protect_start:self.pos()+len(self.get_starttag_text())])
            self.protect_start = None
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)
    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if tag in self.BLOCK:
            self.flush()
        if not self.stack or self.stack[-1]['tag'] != tag:
            raise ValueError(f'malformed HTML nesting at </{tag}>')
        self.stack.pop()
        if self.protect_start is not None and not any(x['protected'] for x in self.stack):
            end = self.source.find('>', self.pos())+1
            self.protected.append(self.source[self.protect_start:end])
            self.protect_start = None
    def handle_data(self, data):
        if not self.hidden():
            self.text.append(data)
    def handle_entityref(self, name):
        self.handle_data(html.unescape('&'+name+';'))
    def handle_charref(self, name):
        self.handle_data(html.unescape('&#'+name+';'))

def markdown(source: str) -> tuple[list[dict],list[str],list]:
    protected, blocks, links = [], [], []
    lines = source.splitlines(keepends=True)
    i = 0
    if lines and lines[0].strip() == '---':
        end = next((j for j in range(1,len(lines)) if lines[j].strip() == '---'),None)
        if end is None:
            raise ValueError('unclosed frontmatter')
        metadata = []
        for line in lines[1:end]:
            m = re.match(r'(title|summary):\s*(.*)',line)
            if m:
                blocks.append({'kind':m[1],'text':m[2].strip()})
            else:
                metadata.append(line)
        protected.append(''.join(metadata));i=end+1
    buf = []
    def flush():
        if buf:
            text = re.sub(r'\s+',' ',''.join(buf)).strip()
            if text: blocks.append({'kind':'prose','text':text})
            buf.clear()
    while i < len(lines):
        line=lines[i]
        if re.match(r'^\s*(`{3,}|~{3,})',line):
            flush();start=i;fence=re.match(r'^\s*(`{3,}|~{3,})',line)[1];i+=1
            while i<len(lines) and not re.match(r'^\s*'+re.escape(fence[0])+r'{'+str(len(fence))+r',}\s*$',lines[i]):i+=1
            if i==len(lines):raise ValueError('unclosed code fence')
            protected.append(''.join(lines[start:i+1]));i+=1;continue
        if line.startswith('>'):
            flush();start=i
            while i<len(lines) and lines[i].startswith('>'):i+=1
            quote=''.join(lines[start:i])
            if re.match(r'^>\s*\[!(abstract|summary)\]',quote,re.I):
                for content in quote.splitlines()[1:]:
                    if content.lstrip('> ').strip():blocks.append({'kind':'argument','text':content.lstrip('> ').strip()})
            elif re.match(r'^>\s*\[!(info|note|tip|warning|quote)\]',quote,re.I):
                protected.append(quote)
            else:
                text=re.sub(r'(?m)^>\s?', '', quote)
                blocks.append({'kind':'quoted-prose','text':re.sub(r'\s+',' ',text).strip()})
            continue
        if line.lstrip().startswith('|'):
            flush();start=i
            while i<len(lines) and lines[i].lstrip().startswith('|'):i+=1
            for row in lines[start:i]:
                if re.fullmatch(r'[|:\-\s]+',row):continue
                blocks.append({'kind':'table-row','text':row.strip()})
                protected.extend('table-number:'+n for n in re.findall(r'\d+(?:[.,]\d+)*',row))
                links.extend(re.findall(r'\]\(([^)]+)\)|\[\[([^\]|]+)(?:\|[^\]]+)?\]\]',row))
            continue
        protected.extend(re.findall(r'`[^`\n]+`',line))
        links.extend(re.findall(r'\]\(([^)]+)\)|\[\[([^\]|]+)(?:\|[^\]]+)?\]\]',line))
        if not line.strip():flush()
        elif re.match(r'^#{1,6}\s|^\s*[-*]\s',line):
            flush();blocks.append({'kind':'heading' if line.startswith('#') else 'item','text':line.strip()})
        else:buf.append(line)
        i+=1
    flush()
    return blocks,protected,links

def extract(source: str, fmt: str) -> dict:
    if fmt in ('html','htm'):
        p=ProseHTML(source);blocks,protected,links=p.blocks,p.protected,p.links
    elif fmt=='md':
        blocks,protected,links=markdown(source)
    else:
        raise ValueError('supported formats: .md, .html, .htm')
    for i,b in enumerate(blocks):
        b['id']=f'b{i+1:04d}'
    return {'blocks':blocks,'quotes':quote_layout.extract(source,fmt),'protected_sha256':digest(json.dumps(protected,ensure_ascii=False)),
            'links_sha256':digest(json.dumps(links,ensure_ascii=False))}

def inspect_file(path: Path) -> dict:
    data=path.read_bytes()
    result=extract(data.decode(),path.suffix.lstrip('.').lower())
    result.update({'schema':VERSION,'artifact_sha256':digest(data),'format':path.suffix.lstrip('.').lower()})
    return result

def cues(text: str) -> list[str]:
    return [name for name,pat in CUES.items() if re.search(pat,text,re.I)]

def template(draft: dict, snapshot: dict) -> dict:
    return {
        'schema':VERSION,'status':'pending','reviewer':'',
        'artifact_sha256':draft['artifact_sha256'],
        'baseline_sha256':snapshot['artifact_sha256'],
        'contract_sha256':digest((ROOT/'contract.md').read_bytes()),
        'policy_sha256':policy_digest(),
        'blocks':[dict(b, cues=cues(b['text']),decision='pending',function='',observation='') for b in draft['blocks']],
        'claim_preservation':{'status':'pending','negation_quantifiers_attribution':'','source_alignment':''},
        'source_verification':{'status':'pending','evidence':''},
        'translation_fidelity':{'status':'pending','evidence':''},
        'structural_validation':{'status':'pending','evidence':''},
        'council':{'status':'pending','evidence':'','reviewed_artifact_sha256':'',
                   'profile_sha256':'','report':{}},
        'cue_resolutions':cue_items(draft['blocks']),
        'semantic_review':{name:{'status':'pending','blocks':[],'evidence':''} for name in SEMANTIC_CHECKS},
        'quote_layout_review':quote_layout.pending(draft['quotes']),
        'rendered_layout':None,
        'findings':[],
        'scope_cues_before':[(b['id'],QUANTIFIERS.findall(b['text'])) for b in snapshot['blocks'] if QUANTIFIERS.search(b['text'])],
        'scope_cues_after':[(b['id'],QUANTIFIERS.findall(b['text'])) for b in draft['blocks'] if QUANTIFIERS.search(b['text'])],
    }

def observation_anchored(text: str, observation: str) -> bool:
    """Require a short current-text excerpt, not semantic certification.

    Four consecutive words survive punctuation/case changes. Very short blocks
    require their full text. This detects stale/generic observations; it cannot
    establish that the judgment attached to an excerpt is correct.
    """
    words = lambda value: re.findall(r"\w+(?:['’]\w+)*", value.casefold())
    source, note = words(text), words(observation)
    size = min(4, len(source))
    if not size:
        return text.strip() in observation
    windows = {tuple(source[i:i+size]) for i in range(len(source)-size+1)}
    return any(tuple(note[i:i+size]) in windows for i in range(len(note)-size+1))


def council_digest(report: dict) -> str:
    """Bind the independent release response to the complete council it read."""
    return digest(json.dumps({k:v for k,v in report.items() if k != 'release'},
                             ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def council_responses(report: dict) -> list[tuple[str, dict]]:
    responses = []
    for key in ('advisors', 'peer_reviews'):
        items = report.get(key, [])
        if not isinstance(items, list):
            continue
        for index, item in enumerate(items, 1):
            if isinstance(item, dict):
                namespace = str(item.get('role', 'unknown')) if key == 'advisors' else f'peer-{index}'
                responses.append((namespace, item))
    return responses


def council_finding_ids(report: dict) -> set[str]:
    """Inventory both panels, including responses with unnumbered findings.

    :response requires an assessment of each complete response, so an unfamiliar
    finding-ID format cannot silently remove a reviewer from the closure check.
    """
    ids = set()
    for namespace, item in council_responses(report):
        ids.add(namespace+':response')
        ids.update(namespace+':'+identifier for identifier in re.findall(
            r'\b(?:[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-\d{1,3}|[A-Z]{1,8}\d{1,3})\b',
            str(item.get('response', ''))))
    return ids


def release_errors(report: dict, artifact_sha256: str) -> list[str]:
    """Read the reviewer's actual JSON response, not the writer's pass label.

    This validates provenance and explicit disposition, not reviewer identity
    or the truth of editorial judgment. Retain the original tool transcript.
    """
    release = report.get('release', {})
    if not isinstance(release, dict) or not str(release.get('reviewer', '')).strip():
        return ['independent council release response missing; chairman approval cannot close reviewer findings']
    try:
        raw = release.get('response')
        if not isinstance(raw, str):
            raise ValueError('response must be the verbatim reviewer JSON string')
        response = json.loads(raw)
        if not isinstance(response, dict):
            raise ValueError('response must be a JSON object')
    except (ValueError, TypeError) as exc:
        return ['invalid independent release response: '+str(exc)]
    errors = []
    if response.get('status') != 'passed' or response.get('open_findings') != []:
        errors.append('independent release reviewer has not cleared all findings')
    if response.get('artifact_sha256') != artifact_sha256:
        errors.append('independent release reviewer read a different candidate')
    if response.get('council_sha256') != council_digest(report):
        errors.append('independent release response is stale for these council findings/dispositions')
    if len(str(response.get('assessment', '')).split()) < 12:
        errors.append('independent release response needs a substantive final-text assessment')
    dispositions = response.get('dispositions')
    if not isinstance(dispositions, list) or any(
        not isinstance(item, dict) or not str(item.get('id', '')).strip()
        or item.get('status') not in ('resolved', 'not-a-defect')
        or len(str(item.get('evidence', '')).split()) < 8
        for item in dispositions
    ):
        errors.append('independent release dispositions missing or unresolved')
    supplied = {item.get('id') for item in dispositions if isinstance(item, dict) and isinstance(item.get('id'), str)} if isinstance(dispositions, list) else set()
    missing = council_finding_ids(report) - supplied
    if missing:
        errors.append('independent release omitted advisor finding IDs: '+', '.join(sorted(missing)))
    # Empty dispositions cannot close a report that explicitly still blocks.
    # Inspect verdict lines, not quoted article wording or historical prose.
    blocking = []
    for namespace, item in council_responses(report):
        opening = str(item.get('response', '')).splitlines()[:8]
        if any(re.match(r'\s*(?:[#* _]|\d+[.)])*\s*(?:follow[ -]up verdict\s*:\s*)?blocking findings\b', line, re.I) for line in opening):
            blocking.append(namespace)
    if blocking and (not isinstance(dispositions, list) or not dispositions):
        errors.append('blocking council responses require independent finding dispositions: '+', '.join(blocking))
    return errors


def verify_handoff(page: str, receipt: dict) -> list[str]:
    """A faithful conversion can reuse only an actually verified master review."""
    import handoff
    if receipt.get('schema') != 3:
        return ['publication requires a version-3 handoff with explicit source roles']
    errors = handoff.verify(page, receipt)
    if errors:
        return errors
    baseline, record = receipt.get('source_baseline'), receipt.get('source_review')
    if not isinstance(baseline, dict) or not isinstance(record, dict):
        return ['handoff has no verified master approval; preservation is not editorial acceptance']
    source = receipt['source_markdown']
    draft = dict(extract(source, 'md'), schema=VERSION, format='md', artifact_sha256=digest(source))
    return ['master review: '+e for e in verify(draft, baseline, record)]


def verify(draft: dict, baseline: dict, review: dict, council_source_sha256: str | None = None) -> list[str]:
    errors=[]
    for label,data in [('baseline',baseline),('review',review)]:
        if data.get('schema')!=VERSION:errors.append(label+' schema mismatch')
    if draft['protected_sha256']!=baseline.get('protected_sha256'):errors.append('protected quotations, translations, metadata, tables, or code changed; perform a separate source-verified revision and start a new editorial baseline')
    if draft['links_sha256']!=baseline.get('links_sha256'):errors.append('link targets or anchors changed')
    for key,expected in [('artifact_sha256',draft['artifact_sha256']),('baseline_sha256',baseline.get('artifact_sha256')),('contract_sha256',digest((ROOT/'contract.md').read_bytes())),('policy_sha256',policy_digest())]:
        if review.get(key)!=expected:errors.append(key+' mismatch; review is stale')
    if review.get('status')!='approved' or not str(review.get('reviewer','')).strip():errors.append('review must be approved by a named reviewer/model')
    rows=review.get('blocks',[])
    if not isinstance(rows,list) or len(rows)!=len(draft['blocks']):errors.append('review does not cover every prose block')
    else:
        observations = {}
        for expected,row in zip(draft['blocks'],rows):
            if not isinstance(row,dict):errors.append('invalid block review');continue
            if any(row.get(k)!=expected[k] for k in ('id','kind','text')):errors.append(expected['id']+' reviewed text differs')
            if row.get('decision') not in ('keep','revised','source-review-needed'):errors.append(expected['id']+' lacks a decision')
            if row.get('decision')=='source-review-needed':errors.append(expected['id']+' has unresolved source review')
            if row.get('function') not in FUNCTIONS:errors.append(expected['id']+' lacks a substantive prose function')
            if len(str(row.get('observation','')).split())<5:errors.append(expected['id']+' needs a specific editorial observation')
            observation = str(row.get('observation',''))
            if not observation_anchored(expected['text'], observation):
                errors.append(expected['id']+' observation must quote current block text (four consecutive words, or the whole shorter block)')
            normalized = re.sub(r'\s+', ' ', observation).strip().casefold()
            previous = observations.get(normalized)
            if previous and previous['text'] != expected['text']:
                errors.append(expected['id']+' reuses '+previous['id']+' observation for different text; reread this block')
            observations[normalized] = expected
            if row.get('function') == 'heading' and expected['kind'] not in {'heading','title','h1','h2','h3','h4','h5','h6','summary'}:
                errors.append(expected['id']+' labels body prose as a heading')
    expected_cues=cue_items(draft['blocks'])
    resolutions=review.get('cue_resolutions')
    if not isinstance(resolutions,list) or len(resolutions)!=len(expected_cues):
        errors.append('cue resolutions missing; every current match needs contextual review')
    else:
        for expected,row in zip(expected_cues,resolutions):
            if not isinstance(row,dict) or any(row.get(k)!=expected[k] for k in ('id','block_id','kind','text')):
                errors.append('cue resolution does not match the actual artifact');continue
            if row.get('status')!='legitimate' or len(str(row.get('reason','')).split())<8:
                errors.append(expected['id']+' unresolved prose cue; delete/rewrite or explain its necessary meaning')
    semantic=review.get('semantic_review',{})
    ids={b['id'] for b in draft['blocks']}
    for name in SEMANTIC_CHECKS:
        item=semantic.get(name,{}) if isinstance(semantic,dict) else {}
        touched=item.get('blocks',[])
        if (item.get('status')!='passed' or len(str(item.get('evidence','')).split())<8
                or not isinstance(touched,list) or not touched or any(x not in ids for x in touched)):
            errors.append(name+' semantic review incomplete; cite actual inspected blocks and findings')
    council=review.get('council',{})
    if council.get('status')!='passed':
        errors.append('council must pass; an article review cannot be waived')
    if council.get('reviewed_artifact_sha256') not in {draft['artifact_sha256'],council_source_sha256} or not council.get('reviewed_artifact_sha256'):
        errors.append('council reviewed a different candidate; refresh review or verify the master handoff')
    if council.get('profile_sha256')!=digest((ROOT/'council-article.md').read_bytes()):
        errors.append('council article profile missing or stale')
    report=council.get('report',{})
    if not isinstance(report,dict):report={}
    advisors=report.get('advisors',[]);peers=report.get('peer_reviews',[])
    if (not isinstance(advisors,list) or len(advisors)!=5 or
        {a.get('role') for a in advisors if isinstance(a,dict)}!=COUNCIL_ROLES or
        any(not isinstance(a,dict) or not str(a.get('reviewer','')).strip() or len(str(a.get('response','')).split())<8
            or not re.fullmatch(r'[0-9a-f]{64}',str(a.get('reviewed_sha256',''))) for a in advisors)):
        errors.append('council requires the five actual article advisor responses')
    if (not isinstance(peers,list) or len(peers)!=5 or
        any(not isinstance(a,dict) or not str(a.get('reviewer','')).strip() or len(str(a.get('response','')).split())<8
            or not re.fullmatch(r'[0-9a-f]{64}',str(a.get('reviewed_sha256',''))) for a in peers)):
        errors.append('council peer review evidence incomplete')
    mapping=report.get('anonymization',{})
    if not isinstance(mapping,dict) or set(mapping)!=set('ABCDE') or set(mapping.values())!=COUNCIL_ROLES:
        errors.append('council anonymization mapping incomplete')
    if len(str(report.get('synthesis','')).split())<8:errors.append('council synthesis missing')
    errors.extend(release_errors(report, council.get('reviewed_artifact_sha256', '')))
    claim=review.get('claim_preservation',{})
    if claim.get('status')!='passed' or any(len(str(claim.get(k,'')).split())<5 for k in ('negation_quantifiers_attribution','source_alignment')):errors.append('claim-preservation review incomplete')
    for key in ('source_verification','translation_fidelity','structural_validation','council'):
        item=review.get(key,{})
        if item.get('status') not in ('passed','not-applicable') or len(str(item.get('evidence','')).split())<5:errors.append(key+' evidence incomplete')
    errors.extend(quote_layout.review_errors(draft['quotes'],review.get('quote_layout_review')))
    if draft.get('format') in ('html','htm'):
        errors.extend(quote_layout.render_errors(draft['quotes'],review.get('rendered_layout'),draft['artifact_sha256']))
    findings=review.get('findings',[])
    if not isinstance(findings,list):errors.append('findings must be a list')
    elif any(not isinstance(x,dict) or x.get('status') not in ('resolved','accepted-with-reason') or len(str(x.get('resolution','')).split())<5 for x in findings):errors.append('unresolved editorial findings')
    return errors

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['scan','prepare','inspect','verify','release-packet'])
    parser.add_argument('file',type=Path)
    parser.add_argument('--snapshot',type=Path)
    parser.add_argument('--handoff',type=Path,help='Verified HTML handoff allowing reuse of the master council')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--review',type=Path)
    parser.add_argument('--render',type=Path,help='Chromium capture JSON from quote_layout.py capture, embedded by inspect')
    args=parser.parse_args(argv)
    try:
        draft=inspect_file(args.file)
        if args.command=='release-packet':
            if not args.review or not args.output:parser.error('--review and --output required')
            if args.output.exists():raise ValueError('release packet exists; preserve it and use a new path')
            record=read(args.review);council=record.get('council',{});report=council.get('report',{})
            if council.get('reviewed_artifact_sha256')!=draft['artifact_sha256']:
                raise ValueError('build the release packet from the final master candidate actually under review')
            save(args.output,{'artifact_sha256':draft['artifact_sha256'],
                 'council_sha256':council_digest(report),'candidate':args.file.read_text(),
                 'report':{k:v for k,v in report.items() if k!='release'},
                 'writer_dispositions':record.get('findings',[]),
                 'required_disposition_ids':sorted(council_finding_ids(report)),
                 'instruction':'Independently read the complete candidate and all council findings. Writer dispositions are proposals, not approval. Return the release JSON specified in council-article.md. Preserve source fidelity and inspect prose sentence by sentence.'})
            print('Release packet saved; no approval generated.');return 0
        if args.command=='scan':
            result={'schema':VERSION,'artifact_sha256':draft['artifact_sha256'],
                    'policy_sha256':policy_digest(),'blocks':draft['blocks'],
                    'cues':cue_items(draft['blocks']),
                    'semantic_checks':list(SEMANTIC_CHECKS),'quote_layout_review':quote_layout.pending(draft['quotes']),'status':'unreviewed'}
            if args.output:save(args.output,result)
            else:print(json.dumps(result,ensure_ascii=False,indent=2))
            print(f"{len(result['cues'])} cues; contextual sentence review is still required.")
            return 0
        if not args.snapshot:parser.error('--snapshot required for prepare, inspect and verify')
        if args.command=='prepare':
            if args.snapshot.exists():raise ValueError('baseline already exists; use a new path to preserve audit history')
            save(args.snapshot,draft);print(f"Baseline saved; {len(draft['blocks'])} prose blocks. This is not source verification.");return 0
        baseline=read(args.snapshot)
        if args.command=='inspect':
            if not args.output:parser.error('--output required')
            if args.output.exists():raise ValueError('review output already exists; use a new path')
            record=template(draft,baseline)
            if args.render:
                record['rendered_layout']=read(args.render)
                failures=quote_layout.render_errors(draft['quotes'],record['rendered_layout'],draft['artifact_sha256'])
                if failures:raise ValueError('; '.join(failures))
            save(args.output,record);print('PENDING review saved; inspect authored prose AND protected quotation layout.');return 0
        if not args.review:parser.error('--review required')
        council_source=None
        if args.handoff:
            import handoff
            receipt=read(args.handoff)
            failures=verify_handoff(args.file.read_text(),receipt)
            if failures:raise ValueError('invalid handoff: '+'; '.join(failures))
            council_source=receipt['source_sha256']
        errors=verify(draft,baseline,read(args.review),council_source)
        for error in errors:print('FAIL:',error)
        print('Review record verified; editorial judgments remain the reviewer\'s responsibility.' if not errors else f'{len(errors)} review failure(s)')
        return bool(errors)
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print('ERROR:',exc);return 2

if __name__=='__main__':
    raise SystemExit(main())
