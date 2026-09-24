"""Prepare native review inputs and ingest actual responses without receipt editing."""
import copy
import json
from pathlib import Path
import conversion_review as C
import review
import scripture_alignment as A
import release_runner
import review_dispatch
import review_identity
import review_dependencies

ROOT = Path(__file__).resolve().parent


def sha(value):
    return review.digest(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')))


def packet(B, manifest, kind, parent_model, source_context=None, session_id=None, council_origins=None):
    if not parent_model.strip(): raise ValueError('record the active inherited parent model')
    data = B.load(manifest)
    source, _ = B.inputs(data)
    result = {'schema': 1, 'kind': kind, 'slug': data['slug'], 'parent_model': parent_model,
              'candidate': source, 'artifact_sha256': review.digest(source), 'runtime': B.runtime()}
    if session_id:result['session_id']=session_id
    if kind == 'scripture':
        if not source_context: raise ValueError('scripture review requires --source-context with the retained original source dossier; it need not approve the current candidate')
        path=Path(source_context).resolve()
        result['source_context_path']=str(path)
        result['source_context']=path.read_text()
        result['template'] = A.prepare(source)
        result['instructions'] = 'Independently verify complete original, Romanization and direct English against the actual cited sources. Fill exact positional spans; a source word may map to several Roman tokens. Do not infer alignment from equal token counts. Return the completed record, or blocked findings. Do not edit the article or source archive.'
        result['response_contract']={'record_status':'approved','quote_status':'passed','reviewer':'native-child (host binds the actual child ID on intake)','quote_evidence_minimum_words':8,'units':'One object per source token: source_index (zero-based), source (exact), roman_start, roman_end (exclusive), romanization (exact joined token span). Cover all tokens in order, without overlap.'}
        result['policy'] = (ROOT / 'article-sources.md').read_text()
        return result
    source, directory, _ = B.current_build(data)
    if kind == 'master':
        evidence_path = Path(data['paths']['evidence'])
        if not evidence_path.is_file(): raise ValueError('register source evidence with article_build.py evidence before requesting master review')
        bundle = B.read(evidence_path)
        failures = B.evidence.verify(bundle, source)
        if failures: raise ValueError('; '.join(failures))
        result['source_evidence'] = release_runner.review_evidence(bundle)
        result['evidence_sha256'] = sha(bundle)
        result['baseline'] = B.read(data['paths']['baseline'])
        result['template'] = B.read(data['paths']['review'])
        if council_origins:
            result['council_origins_path']=str(Path(council_origins).resolve())
            result['template']['council']['report']=review_identity.origins(result['template']['council'].get('report',{}),council_origins)
        result['instructions'] = 'Review the complete current article and source evidence. Complete actual editorial judgments in the pending record. Retain real council responses and original input hashes. Do not manufacture advisor identities, generic observations, cue dispositions or approvals. If the council has not actually run, return blocked. Use reviewer native-child; the host records the actual responding child ID. No HTML prose duplication is required.'
        result['response_contract']={'record_status':'approved','reviewer':'native-child (host binds the actual child ID on intake)','decisions':['keep','revised','source-review-needed'],'functions':sorted(review.FUNCTIONS),'observation':'At least five words, including four consecutive words of current text (or the whole shorter block); explain the actual contribution. No generic completions.','cue_resolutions':'Every current cue: status legitimate and at least eight words of contextual reason, or return blocked.','semantic_review':'Every dimension: status passed, current block IDs and at least eight words of actual evidence.','source_fields':'Structural validation and council must be passed (not not-applicable); Arabic quotations also require passed source verification and translation fidelity. Claim-preservation and source/fidelity/structural/council fields must contain actual judgments, never placeholders. Council has real five advisor and five peer responses.','machine_fields':'Keep supplied schema/hash/text fields unchanged or omit top-level bindings. Host fills only missing machine bindings and the actual responding ID; it never supplies judgments.'}
        result['policies'] = {name: (ROOT / name).read_text() for name in ('contract.md', 'editorial.md', 'council-article.md')}
    elif kind == 'render':
        page = (directory / 'article.html').read_text()
        render = B.read(directory / 'render.json') if (directory / 'render.json').is_file() else None
        result.update(html_path=str(directory / 'article.html'), page=page, render=render,
                      binding=C.binding(page, review.digest(source), render))
        result['screenshots'] = {str(directory / name): value for name, value in B.read(directory / 'preflight.json')['artifacts'].items() if name.endswith('.png')}
        result['response_contract']={'status':'passed','open_findings':[],'assessment_minimum_words':12,'checks':{name:{'status':'passed','evidence_minimum_words':8} for name in C.CHECKS}}
        result['template'] = {'binding': result['binding'], 'status': 'pending', 'assessment': '', 'open_findings': [], 'checks': {name: {'status': 'pending', 'evidence': ''} for name in C.CHECKS}}
        result['instructions'] = 'Inspect the rendered page and both viewport screenshots. Check quotation insets, direction, spacing, long-quote readability, overflow, visibility, metadata and navigation. Review print/no-JS where applicable. The handoff checks exact source preservation; do not author another per-cell prose review. Return a passed visual record only for actual visual inspection; otherwise return blocked with located findings.'
    else: raise ValueError('unknown review kind')
    return result


def decorate(value):
    if value['kind']=='master':value['template']['council'].update(reviewed_artifact_sha256=value['artifact_sha256'],profile_sha256=review.digest((ROOT/'council-article.md').read_bytes()))
    value['runtime']=review_dependencies.dependencies('render' if value['kind']=='render' else 'editorial')


def request(B, a):
    if a.kind!='scripture':
        readiness=review_dispatch.plan(B,a.manifest)
        if readiness['errors']:raise ValueError('review prerequisites: '+'; '.join(readiness['errors']))
    value = packet(B, a.manifest, a.kind, a.parent_model, a.source_context, getattr(a,'session_id',None),getattr(a,'council_origins',None))
    if a.kind=='master':
        report=value['template'].get('council',{}).get('report',{})
        if any(len(report.get(group,[]))!=5 for group in ('advisors','peer_reviews')):
            raise ValueError('retain the actual five council and peer responses before master review; no reviewer can create missing council evidence')
    value['delivery']='referenced-v1'
    decorate(value)
    raw = json.dumps(value, ensure_ascii=False)
    directory = a.output.resolve()
    if directory.exists():
        if B.read(directory / 'request.json') != value: raise ValueError('request directory belongs to different inputs; use a new path')
    else:
        directory.mkdir(parents=True)
        B.write(directory / 'request.json', value)
    review_dispatch.materialize(value,directory,sha(value))
    print('Native ' + a.kind + ' review request:', directory / 'prompt.txt')
    print('Coordinator prompt bytes:', (directory/'prompt.txt').stat().st_size, '; machine archive bytes:', len(raw.encode()), '; source:', value['artifact_sha256'])
    return 0


def accept(B, a):
    value = B.read(a.request)
    raw = a.response.read_text()
    directory = a.request.resolve().parent / 'responses' / review.digest(raw)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'response.txt').write_text(raw)
    if not a.agent_id.strip() or a.model != value['parent_model']: raise ValueError('use the actual native child ID and inherited parent model')
    current = packet(B, a.manifest, value['kind'], value['parent_model'], value.get('source_context_path'),value.get('session_id'),value.get('council_origins_path'))
    if value.get('delivery')=='referenced-v1':
        current['delivery']='referenced-v1'
        decorate(current)
        review_dispatch.materialize(value,a.request.resolve().parent,sha(value),check=True)
    legacy_runtime=not value.get('delivery') and review_dependencies.runtime_matches(value.get('runtime',{}),current['runtime'])
    if legacy_runtime:
        current['runtime']=value['runtime']
        if value['kind']=='render' and review.policy_matches(value.get('binding',{}).get('policy_sha256'),'render'):
            current['binding']['policy_sha256']=value['binding']['policy_sha256']
            current['template']['binding']['policy_sha256']=value['binding']['policy_sha256']
    session_id=getattr(a,'session_id',None)
    if value.get('session_id') and session_id!=value['session_id']:raise ValueError('responding native session differs from request; use its actual --session-id')
    response = json.loads(raw)
    if not isinstance(response,dict):raise ValueError('native reviewer response must be an object')
    if response.get('request_sha256') != sha(value): raise ValueError('reviewer responded to a different request')
    if response.get('status') != 'passed' or response.get('findings') != []: raise ValueError('reviewer blocked this candidate; read the retained response')
    record = response.get('record')
    if not isinstance(record, dict): raise ValueError('review response record missing')
    data = B.load(a.manifest)
    kind = value['kind']
    if kind == 'render':
        failures = C.response_errors(value['binding'], record)
        record_raw = raw
        record = dict(kind=C.KIND, schema=1, status='approved', **value['binding'], rendered_layout=value['render'], reviewer=a.agent_id, response=record_raw,
                      native={'agent_id': a.agent_id, 'model': a.model, 'parent_model': value['parent_model'], 'inherited': True, 'request_sha256': sha(value), 'response_sha256': review.digest(record_raw)})
        key = 'html_review'
    else:
        template=value['template']
        if kind=='master' and legacy_runtime and not template.get('council',{}).get('report'):
            report=record.get('council',{}).get('report',{})
            actors=[r for group in ('advisors','peer_reviews','followup_reviews') for r in report.get(group,[])]+[report.get('release',{})]
            if any(isinstance(r,dict) and r.get('reviewer_identity') is not None for r in actors):
                raise ValueError('legacy council response cannot introduce scoped identities; retain origin evidence in a new request')
            template=copy.deepcopy(template);template['council']['report']=copy.deepcopy(report)
        record=review_dispatch.expand(template,record) if kind=='master' else copy.deepcopy(record)
        record['reviewer']=a.agent_id
        if session_id:record['reviewer_identity']=review_identity.identity(session_id,a.agent_id)
        elif record.get('reviewer_identity'):raise ValueError('supply --session-id to bind reviewer identity')
        for key in ('schema','artifact_sha256','baseline_sha256','contract_sha256','policy_sha256'):
            if key in value['template']:
                if key in record and record[key]!=value['template'][key]:raise ValueError('review response changed machine binding: '+key)
                record[key]=value['template'][key]
        failures = (A.errors(value['candidate'], record) if kind == 'scripture' else review.verify(review.inspect_file(Path(data['paths']['source'])), value['baseline'], record, require_release=False))
        if kind=='master':failures+=C.master_errors(value['candidate'],record)
        key = 'scripture_review' if kind == 'scripture' else 'review'
    if failures: raise ValueError('; '.join(failures))
    record = copy.deepcopy(record)
    if session_id:record['reviewer_identity']=review_identity.identity(session_id,a.agent_id)
    record['intake'] = {'request_sha256': sha(value), 'response_sha256': review.digest(raw), 'agent_id': a.agent_id, 'parent_model': value['parent_model'], 'model': a.model}
    target = directory / (kind + '.review.json')
    if target.exists() and B.read(target) != record: raise ValueError('immutable accepted response differs')
    already_accepted=Path(data['paths'][key]).resolve()==target and target.is_file()
    if kind=='master' and target.is_file():
        previous=copy.deepcopy(record);present=B.read(data['paths'][key])
        for item in (previous,present):item.get('council',{}).get('report',{}).pop('release',None)
        already_accepted=already_accepted or present==previous
    if already_accepted and kind=='master':current['template']=value['template']
    if current != value:raise ValueError('review request is stale; preserve the response and request current inputs')
    if already_accepted:
        print('Identical accepted response retained; current build readiness is unchanged.')
        return 0
    B.write(target, record)
    data['paths'][key] = str(target)
    data['ready'] = None
    B.write(a.manifest, data)
    print('Actual native response accepted:', target, '; run prepare after all reviews pass.')
    return 0
