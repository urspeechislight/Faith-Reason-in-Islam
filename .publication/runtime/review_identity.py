"""Session-qualified host provenance; this does not authenticate model providers."""
import json
from pathlib import Path


def identity(session_id, agent_id):
    if not all(isinstance(x,str) and x.strip() and len(x)<=256 for x in (session_id,agent_id)):
        raise ValueError('retain actual native session and child agent IDs')
    return {'session_id':session_id,'agent_id':agent_id}


def actor(row):
    name=str(row.get('reviewer','')).strip()
    origin=row.get('reviewer_identity')
    if origin is None:return (None,name)
    value=identity(origin.get('session_id'),origin.get('agent_id'))
    if name!=value['agent_id']:raise ValueError('reviewer identity disagrees with retained native agent ID')
    return (value['session_id'],name)


def same(left,right):
    a,b=actor(left),actor(right)
    return a[1]==b[1] and (a[0]==b[0] or a[0] is None or b[0] is None)


def distinct(primary, actors):
    errors=[]
    for index,row in enumerate(actors):
        try:
            actor(row)
            if same(primary,row) or any(same(row,prior) for prior in actors[:index]):
                errors.append('reviewer identity collision or ambiguous legacy scope: '+str(row.get('reviewer'))+'; retain actual session provenance; never burn agent IDs')
        except (ValueError,AttributeError) as exc:errors.append(str(exc))
    return errors


def origins(report, path):
    """Attach historical scope only with matching retained response and invocation evidence."""
    import copy,hashlib
    result=copy.deepcopy(report)
    rows=json.loads(Path(path).read_text())
    if not isinstance(rows,list):raise ValueError('council origins must be a list')
    seen=set()
    for row in rows:
        group,index=row['group'],row['index']
        if group not in ('advisors','peer_reviews','followup_reviews') or type(index) is not int or (group,index) in seen:
            raise ValueError('invalid or duplicate council origin selector')
        seen.add((group,index))
        target=result[group][index]
        origin=identity(row['session_id'],row['agent_id'])
        if origin['agent_id']!=target['reviewer']:raise ValueError('origin cannot rename a historical reviewer')
        transcript=Path(row['transcript']).resolve();raw=transcript.read_text()
        evidence=json.loads(raw)
        if (evidence.get('session_id')!=origin['session_id'] or evidence.get('agent_id')!=origin['agent_id']
            or evidence.get('response')!=target['response']):
            raise ValueError('origin requires the retained host invocation record with matching session, agent and verbatim response')
        if target.get('reviewer_identity') not in (None,origin):raise ValueError('historical identity is already bound differently')
        target['reviewer_identity']=origin
        target['identity_evidence']={'path':str(transcript),'sha256':hashlib.sha256(raw.encode()).hexdigest()}
    return result
