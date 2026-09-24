"""Synthetic native-response fixtures, never historical or article approvals."""
import copy,json,tempfile,unittest,contextlib,io
from pathlib import Path
from unittest.mock import patch
import native_release as N
import review
import article_build as B
from test_pipeline import ReviewTests

def response(value):
    return json.dumps({'status':'passed','artifact_sha256':value['artifact_sha256'],'council_sha256':value['council_sha256'],'request_sha256':N.packet_hash(value),
        'assessment':'Synthetic fixture only: the candidate preserves the supplied source without adding unsupported claims or empty framing.',
        'open_findings':[], 'dispositions':[{'id':key,'status':'resolved','evidence':'Synthetic fixture only: the retained finding is resolved in this exact current candidate and source context.'} for key in value['required_disposition_ids']]})

def finish_fixture(B,manifest):
    data,source,page,evidence_raw,report=N.current(B,manifest)
    value=N.packet(source,page,evidence_raw,report,'synthetic-parent-model')
    record=B.read(data['paths']['review']);record['council']['report']['release']=N.receipt(value,response(value),'synthetic-native-child','synthetic-parent-model')
    B.write(data['paths']['review'],record)
    return B.main(['prepare',str(manifest)])

class NativeTests(unittest.TestCase):
    def setUp(self):
        self.source='The source names eight witnesses.';self.page='<main><p>The source names eight witnesses.</p></main>'
        self.evidence=json.dumps({'sources':[{'raw':self.source}]})
        self.report={'advisors':[{'role':'fidelity','response':'FID-01: Correct the count of witnesses.'}]}
        self.packet=N.packet(self.source,self.page,self.evidence,self.report,'active-parent')
    def approved(self):return dict(self.report,release=N.receipt(self.packet,response(self.packet),'native-child','active-parent'))
    def test_exact_native_receipt_and_all_bindings(self):
        report=self.approved();self.assertEqual(N.errors(self.source,self.page,self.evidence,report),[])
        for args in [(self.source+' Changed.',self.page,self.evidence,report),(self.source,self.page+' changed',self.evidence,report),(self.source,self.page,self.evidence+' ',report),(self.source,self.page,self.evidence,dict(report,synthesis='new council evidence'))]:self.assertTrue(N.errors(*args))
        with patch.object(N,'contract_hash',return_value='new policy'):self.assertTrue(N.errors(self.source,self.page,self.evidence,report))
    def test_missing_blocked_incomplete_and_wrong_request_rejected(self):
        for edit in [{'status':'blocked','open_findings':['R-01']},{'dispositions':[]},{'request_sha256':'wrong'}]:
            raw=json.loads(response(self.packet));raw.update(edit)
            with self.assertRaises(ValueError):N.receipt(self.packet,json.dumps(raw),'child','active-parent')
        self.assertTrue(N.errors(self.source,self.page,self.evidence,self.report))
    def test_model_override_or_fake_native_label_rejected(self):
        with self.assertRaisesRegex(ValueError,'inherit'):N.receipt(self.packet,response(self.packet),'child','another-provider/model')
        for edit in [{'inherited':False},{'model':'other'},{'agent_id':''},{'request_sha256':'wrong'},{'response_sha256':'wrong'}]:
            report=self.approved();report['release']['native'].update(edit);self.assertTrue(N.errors(self.source,self.page,self.evidence,report))
    def test_malformed_native_metadata_is_a_controlled_rejection(self):
        for bad in [None,[],False]:
            report=self.approved();report['release']['native']=bad
            self.assertTrue(N.errors(self.source,self.page,self.evidence,report))
    def test_prompt_contains_complete_candidate_evidence_and_exact_metadata(self):
        text=N.prompt(self.packet);self.assertIn(self.source,text);self.assertIn(N.packet_hash(self.packet),text);self.assertIn('same model as your parent',text)
    def test_accept_retains_blocked_response_without_changing_master(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);request=root/'request.json';request.write_text(json.dumps(self.packet));raw=json.loads(response(self.packet));raw.update(status='blocked',open_findings=['R-01']);reply=root/'reply.json';reply.write_text(json.dumps(raw))
            args=type('Args',(),dict(manifest=root/'build.json',request=request,response=reply,agent_id='native-child',model='active-parent'))()
            current=({},self.source,self.page,self.evidence,self.report)
            with patch.object(B,'verify',return_value=0),patch.object(N,'current',return_value=current),patch.object(B,'write',side_effect=AssertionError('must not write master')):
                with self.assertRaisesRegex(ValueError,'not cleared'):N.accept(B,args)
            self.assertTrue(list((root/'responses').glob('*/response.txt')))

if __name__=='__main__':unittest.main()
