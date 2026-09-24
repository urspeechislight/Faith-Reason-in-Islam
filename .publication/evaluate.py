"""Real reviewer regression: expected outcomes are checked outside the prompt."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'runtime'))
import release_runner
import review

def fixtures():
    raw='The catalogue names eight poets who composed elegies for Karim. It gives no total number of elegies and does not assess the poets’ motives.'
    evidence={'sources':[{'id':'S1','kind':'synthetic evaluation source, not a historical claim','citation':'Unpublished synthetic regression fixture','raw':raw,'raw_sha256':review.digest(raw)}]}
    cases={
        'prose-defects':('The catalogue is not silent about Karim. Whatever his opponents believed, its roll of elegists keeps the mourning on the record. Eight poets are named. The conclusion is a weighed reading. [Source S1]',False),
        'direct-prose':('The catalogue names eight poets who composed elegies for Karim. It gives no total number of elegies and does not assess the poets’ motives. [Source S1]',True),
        'unsupported-inference':('Eight poets wrote elegies for Karim because they agreed with all his beliefs. [Source S1]',False),
    }
    for name,(text,expected) in cases.items():
        packet={'candidate':text,'artifact_sha256':review.digest(text),'report':{},'council_sha256':review.council_digest({}),'required_disposition_ids':[],'writer_dispositions':[]}
        evidence['artifact_sha256']=packet['artifact_sha256']
        yield name,packet,dict(evidence),expected
    text='The catalogue names eight poets who composed elegies for Karim. [Source S1]'
    report={'advisors':[{'role':'fidelity','response':'FID-01: The earlier candidate says twelve poets. The source names eight; correct the count.'}]}
    packet={'candidate':text,'artifact_sha256':review.digest(text),'report':report,'council_sha256':review.council_digest(report),'required_disposition_ids':sorted(review.council_finding_ids(report)),'writer_dispositions':[]}
    evidence['artifact_sha256']=packet['artifact_sha256']
    yield 'corrected-history',packet,dict(evidence),True

def evaluate(a, outcomes):
    for name,packet,evidence,expected in fixtures():
        out=a.output/name
        try:release_runner.run(packet,evidence,out,a.client);passed=True
        except ValueError as failure:
            # A provider/schema failure is never credited as successful rejection.
            invocation=json.loads((out/'invocation.json').read_text())
            if invocation['exit_code']:raise ValueError('Provider/configuration failure; inspect retained stderr.txt') from failure
            response=json.loads((out/'response.txt').read_text())
            if invocation['exit_code'] or response.get('status')!='blocked' or not response.get('open_findings'):raise
            errors=json.loads((out/'validation.json').read_text())['errors']
            if errors!=['independent release reviewer has not cleared all findings']:
                raise ValueError('Malformed rejection cannot pass the behavioral regression: '+str(errors)) from failure
            passed=False
        if passed!=expected:raise ValueError('Behavioral regression failed: '+name)
        outcomes.append({'case':name,'status':'passed','decision':'accepted' if passed else 'rejected'})
        print('PASS:',name,'accepted' if passed else 'rejected')
def main(argv=None):
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--client',default='copilot');a=p.parse_args(argv)
    a.output.mkdir(parents=True,exist_ok=True)
    result={'phase':'regression','status':'blocked','cases':[]}
    try:
        evaluate(a,result['cases']);result['status']='passed';return 0
    except Exception as exc:
        result['error']=type(exc).__name__+': '+str(exc)
        print('Reviewer regression BLOCKED:',result['error']);return 1
    finally:
        (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':raise SystemExit(main())
