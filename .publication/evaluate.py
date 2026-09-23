"""Real reviewer regression: expected outcomes are checked outside the prompt."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).parent/'runtime'))
import release_runner
import review

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--client',default='copilot');a=p.parse_args()
    evidence={'sources':[{'id':'S1','type':'synthetic evaluation source, not a historical claim','text':'The catalogue names eight poets who composed elegies for Karim. It gives no total number of elegies and does not assess the poets’ motives.'}]}
    cases={
        'prose-defects':('The catalogue is not silent about Karim. Whatever his opponents believed, its roll of elegists keeps the mourning on the record. Eight poets are named. The conclusion is a weighed reading. [Source S1]',False),
        'direct-prose':('The catalogue names eight poets who composed elegies for Karim. It gives neither a total count of the elegies nor an explanation of the poets’ motives. [Source S1]',True),
        'unsupported-inference':('Eight poets wrote elegies for Karim because they agreed with all his beliefs. [Source S1]',False),
    }
    for name,(text,expected) in cases.items():
        packet={'candidate':text,'artifact_sha256':review.digest(text),'report':{},'council_sha256':review.council_digest({}),'required_disposition_ids':[],'writer_dispositions':[]}
        out=a.output/name
        try:release_runner.run(packet,evidence,out,a.client);passed=True
        except ValueError:
            # A provider/schema failure is never credited as successful rejection.
            invocation=json.loads((out/'invocation.json').read_text())
            response=json.loads((out/'response.txt').read_text())
            if invocation['exit_code'] or response.get('status')!='blocked' or not response.get('open_findings'):raise
            passed=False
        if passed!=expected:raise ValueError('Behavioral regression failed: '+name)
        print('PASS:',name,'accepted' if passed else 'rejected')
if __name__=='__main__':main()
