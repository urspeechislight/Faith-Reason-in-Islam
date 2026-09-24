"""Visual review of a verified conversion; no second editorial approval is fabricated."""
import json
import re
import review
import quote_layout

KIND = 'verified-conversion-v1'
CHECKS = ('quotation_insets', 'direction_and_spacing', 'overflow_and_visibility', 'navigation_and_metadata')


def binding(page, source_sha256, render):
    return {'artifact_sha256': review.digest(page), 'source_sha256': source_sha256,
            'policy_sha256': review.policy_digest(),
            'render_sha256': review.digest(json.dumps(render, sort_keys=True, ensure_ascii=False))}


def pending(page, source_sha256, render):
    return {'kind': KIND, 'schema': 1, 'status': 'pending',
            **binding(page, source_sha256, render), 'rendered_layout': render}


def response_errors(value, response):
    errors = []
    if not isinstance(response, dict): return ['visual review must be a JSON object']
    if response.get('binding') != value: errors.append('visual review is stale for these source, HTML, rendering or policy bytes')
    if response.get('status') != 'passed' or response.get('open_findings') != []:
        errors.append('visual reviewer has unresolved findings')
    if len(str(response.get('assessment', '')).split()) < 12: errors.append('visual review needs a specific assessment')
    checks = response.get('checks', {})
    for name in CHECKS:
        row = checks.get(name, {}) if isinstance(checks, dict) else {}
        if not isinstance(row, dict) or row.get('status') != 'passed' or len(str(row.get('evidence', '')).split()) < 8:
            errors.append(name + ': actual rendered inspection is missing')
    return errors


def master_errors(source,master):
    required=['structural_validation','council']
    if re.search('[\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]',source):required+=['source_verification','translation_fidelity']
    return ['master '+name+' must pass for this article' for name in required if master.get(name,{}).get('status')!='passed']


def errors(page, baseline, record, receipt, require_release=True):
    errors = review.verify_handoff(page, receipt, require_release=require_release)
    errors.extend(master_errors(receipt.get('source_markdown',''),receipt.get('source_review',{})))
    draft = dict(review.extract(page, 'html'), schema=review.VERSION, format='html', artifact_sha256=review.digest(page))
    if baseline != draft: errors.append('conversion baseline differs from the exact rendered article')
    render = record.get('rendered_layout')
    expected = binding(page, receipt.get('source_sha256'), render)
    if record.get('schema') != 1 or record.get('kind') != KIND or record.get('status') != 'approved':
        errors.append('conversion visual review is pending or invalid')
    if any(record.get(k) != v for k, v in expected.items()): errors.append('conversion record binding mismatch')
    native = record.get('native', {})
    raw = record.get('response', '')
    if not isinstance(native, dict): return errors + ['visual native provenance missing']
    if (not native.get('agent_id') or native.get('model') != native.get('parent_model')
        or not native.get('model') or native.get('inherited') is not True
        or record.get('reviewer') != native.get('agent_id') or native.get('response_sha256') != review.digest(raw)):
        errors.append('visual review requires retained inherited-model response and actual child identity')
    try: response = json.loads(raw)
    except (ValueError, TypeError): return errors + ['invalid visual review response']
    if not isinstance(response,dict):return errors+['visual response must be a JSON object']
    if response.get('status')!='passed' or response.get('findings')!=[] or response.get('request_sha256')!=native.get('request_sha256'): errors.append('visual intake response is blocked or belongs to another request')
    errors.extend(response_errors(expected, response.get('record')))
    errors.extend(quote_layout.render_errors(draft['quotes'], render, draft['artifact_sha256'], require_render=bool(draft['quotes'])))
    return errors
