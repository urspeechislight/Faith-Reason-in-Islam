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

def main(argv=None):
    raise SystemExit('External provider evaluation is disabled. Use fixtures() with native inherited-model subagents; CI runs only mechanical tests.')
if __name__=='__main__':main()
