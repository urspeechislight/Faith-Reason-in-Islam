"""Synthetic fixtures only; these tests grant no article or language approval."""
import copy,contextlib,io,json,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
import article_build as B
import article_revision as R
import scripture_alignment as A
import release_runner as L
import review
from test_article_build import ManifestTests,note
from test_scripture import note as scripture_note
from test_pipeline import ReviewTests


def alignment(text):
    result=A.prepare(text);result.update(status='approved',reviewer='synthetic test fixture')
    for row in result['quotes']:
        assert len(row['source_tokens'])==len(row['roman_tokens'])
        row.update(status='passed',evidence='Synthetic identity mapping only; this fixture verifies no historical translation.',units=[{'source_index':i,'source':token,'roman_start':i,'roman_end':i+1,'romanization':row['roman_tokens'][i]} for i,token in enumerate(row['source_tokens'])])
    return result


class AlignmentTests(unittest.TestCase):
    def test_complete_and_partial_layers(self):
        source=scripture_note('alpha beta gamma','alpha beta gamma','three words')
        record=alignment(source);self.assertEqual(A.errors(source,record),[])
        for changed in [source.replace('*alpha beta gamma*','*alpha beta*'),source.replace('three words','four words'),source.replace('Latin','Greek')]:
            self.assertTrue(A.errors(changed,record))
        incomplete=scripture_note('alpha beta gamma','alpha beta','three words')
        pending=A.prepare(incomplete);self.assertTrue(A.errors(incomplete,pending))
    def test_omission_overlap_and_reordered_mappings(self):
        source=scripture_note('alpha beta','alpha beta','two words');record=alignment(source)
        for edit in ('omission','overlap','reorder','blank-reviewer','pending'):
            changed=copy.deepcopy(record)
            if edit=='omission':changed['quotes'][0]['units'].pop()
            if edit=='overlap':changed['quotes'][0]['units'][1]['roman_start']=0
            if edit=='reorder':changed['quotes'][0]['units'].reverse()
            if edit=='blank-reviewer':changed['reviewer']=''
            if edit=='pending':changed['status']='pending'
            self.assertTrue(A.errors(source,changed),edit)
    def test_multitoken_romanization_and_unicode(self):
        source=scripture_note('alpha beta','al pha beta','two words');record=A.prepare(source);record.update(status='approved',reviewer='fixture')
        q=record['quotes'][0];q.update(status='passed',evidence='Synthetic split tokens preserve every source item exactly once here.',units=[dict(source_index=0,source='alpha',roman_start=0,roman_end=2,romanization='al pha'),dict(source_index=1,source='beta',roman_start=2,roman_end=3,romanization='beta')])
        self.assertEqual(A.errors(source,record),[])
        self.assertEqual(A.words('ʿalayhi samāʾ ʾanā'),['ʿalayhi','samāʾ','ʾanā'])
        self.assertEqual(A.words('1. ἀ  אשה  كلام al-pha'),['ἀ','אשה','كلام','al-pha'])
    def test_plain_prose_needs_no_scripture_record(self):self.assertEqual(A.errors('He went home.',None),[])


class RevisionTests(ManifestTests):
    # Inherits existing manifest boundary tests and exercises the new lifecycle.
    def ready(self):
        self.init();self.preflight();data=B.read(self.manifest)
        master=review.inspect_file(self.source);fixture=ReviewTests()
        B.write(data['paths']['baseline'],master);B.write(data['paths']['review'],fixture.approved(master))
        self.assertEqual(self.call('prepare',self.manifest),0)
        ready=B.read(self.manifest)['ready'];html=review.inspect_file(Path(ready['paths']['html']))
        B.write(data['paths']['html_baseline'],html);B.write(data['paths']['html_review'],fixture.approved(html))
        B.write(data['paths']['evidence'],{'schema':1,'artifact_sha256':review.digest(self.source.read_text()),'sources':[{'kind':'external','id':'fixture','citation':'Synthetic witness only','url':'https://example.invalid','accessed':'2026-09-23','raw':'He went home.','raw_sha256':review.digest('He went home.')}],'claims':[]})
        self.assertEqual(self.call('verify',self.manifest),0)
    def test_revision_preserves_parent_and_starts_pending(self):
        self.init();self.preflight();before=self.manifest.read_bytes();old=self.source.read_text()
        self.source.write_text(note(extra='A later witness arrived.'))
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--output',self.root/'bad/candidate.md','--reason','collision'),1)
        self.assertFalse((self.root/'bad').exists())
        child=self.root/'r2/build.json'
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--output',child,'--reason','synthetic correction'),0)
        self.assertEqual(self.manifest.read_bytes(),before);self.assertEqual((child.parent/'previous.md').read_text(),old)
        data=B.read(child);self.assertIsNone(data['ready']);self.assertEqual(data['builds'],[])
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--output',child,'--reason','repeat'),1)
        with patch.object(B.review,'extract',return_value={'quotes':[]}):self.assertEqual(self.call('preflight',child),0)
        self.assertEqual(self.call('reviews',child),0)
        self.assertEqual(B.read(B.read(child)['paths']['review'])['status'],'pending')
    def test_reuse_requires_real_prior_review_and_keeps_current_approval_pending(self):
        self.ready();self.source.write_text(note(extra='A later witness arrived.'))
        child=self.root/'r2/build.json'
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--output',child,'--reason','new detail'),0)
        with patch.object(B.review,'extract',return_value={'quotes':[]}):self.assertEqual(self.call('preflight',child),0)
        self.assertEqual(self.call('reviews',child),0)
        plan=B.read(child.parent/'revision.json');eligible=[r for r in plan['blocks'] if r['eligible_for_context_review']]
        self.assertTrue(eligible)
        confirmation=child.parent/'context.json';B.write(confirmation,{'artifact_sha256':plan['artifact_sha256'],'revision_sha256':B.digest(child.parent/'revision.json'),'reviewer':'synthetic context reviewer','blocks':[{'id':eligible[0]['current_id'],'reason':'The exact section and its source context remain identical in this fixture.'}]})
        self.assertEqual(self.call('reuse',child,'--confirmation',confirmation),0)
        current=B.read(B.read(child)['paths']['review']);self.assertEqual(current['status'],'pending')
        self.assertEqual(len([r for r in current['blocks'] if r.get('reuse')]),1)
        old=B.read(child.parent/'previous.review.json');old['schema']='old';B.write(child.parent/'previous.review.json',old)
        self.assertEqual(self.call('reuse',child,'--confirmation',confirmation),1)
    def test_evidence_exports_are_immutable_and_revision_inherits_recipe(self):
        import sqlite3
        self.init();self.preflight();db=self.root/'db.sqlite';sqlite3.connect(db).close()
        ledger=self.root/'ledger.json';external=self.root/'external.json'
        B.write(ledger,{'schema':1,'passages':[]})
        B.write(external,[{'kind':'external','id':'fixture','citation':'Synthetic source','url':'https://example.invalid','accessed':'2026-09-23','raw':'He went home.','raw_sha256':review.digest('He went home.')}])
        self.assertEqual(self.call('evidence',self.manifest,'--ledger',ledger,'--external',external,'--db',db),0)
        first=Path(B.read(self.manifest)['paths']['evidence']);before=first.read_bytes()
        self.assertEqual(self.call('evidence',self.manifest),0);self.assertEqual(Path(B.read(self.manifest)['paths']['evidence']),first)
        self.source.write_text(note(extra='A later witness arrived.'));child=self.root/'r2/build.json'
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--output',child,'--reason','new source context'),0)
        self.assertEqual(self.call('evidence',child),0);self.assertNotEqual(B.read(child)['paths']['evidence'],str(first));self.assertEqual(first.read_bytes(),before)
    def test_stage_accepts_own_changes_and_blocks_other_changes(self):
        self.ready();self.assertEqual(self.call('stage',self.manifest),0)
        self.assertEqual(self.call('verify',self.manifest),0);self.assertEqual(self.call('stage',self.manifest),0)
        target=self.site/'reading.html';target.write_text('another session')
        self.assertEqual(self.call('stage',self.manifest),1);self.assertEqual(target.read_text(),'another session')
    def test_stage_resume_keeps_unmodified_sources_and_protects_journal(self):
        self.ready();original=Path.replace;failed=[False]
        def interrupt(path,target):
            if '.article-build.' in path.name and not failed[0]:failed[0]=True;raise OSError('simulated interruption')
            return original(path,target)
        with patch.object(Path,'replace',interrupt):self.assertEqual(self.call('stage',self.manifest),1)
        data=B.read(self.manifest);self.assertIn('staging',data)
        self.assertEqual(self.call('revise',self.manifest,'--source',self.source,'--output',self.root/'r2/build.json','--reason','premature'),1)
        self.assertEqual(self.call('stage',self.manifest),0);self.assertNotIn('staging',B.read(self.manifest))
        data=B.read(self.manifest);journal=Path(data['staged']['path']);journal.write_text('{}')
        self.assertEqual(self.call('verify',self.manifest),1)
    def test_second_manifest_stage_cannot_enter_same_article_transaction(self):
        self.ready()
        # Stage holds a site/slug lock even when a different manifest is used.
        with patch.object(R,'stage_locked',side_effect=lambda b,a:R.stage(b,a)):
            self.assertEqual(self.call('stage',self.manifest),1)
    def test_mapping_context_changed_or_ambiguous_is_fresh(self):
        old='# One\n\nThe witness left.\n\n# Two\n\nThe king arrived.\n'
        new=old.replace('The king arrived.','The king returned.')
        proposals=R.mapping(old,new);self.assertTrue(any(x['eligible_for_context_review'] for x in proposals))
        self.assertFalse(all(x['eligible_for_context_review'] for x in proposals))
        self.assertFalse(any(x['eligible_for_context_review'] for x in R.mapping('A sentence.\n\nA sentence.','A sentence.\n\nA sentence.')))
    def test_alignment_retention_is_exact_and_bound_to_previous_preflight(self):
        old=scripture_note('alpha beta','alpha beta','two words');record=alignment(old)
        path=self.root/'alignment.json';B.write(path,record);preflight=self.root/'preflight.json';B.write(preflight,{'binding':{'scripture_review_sha256':B.digest(path)}})
        parent={'paths':{'scripture_review':str(path)},'latest_build':'one','builds':[{'id':'one','preflight':str(preflight)}]}
        kept=R.retained_alignment(B,parent,old,old+'\nA new paragraph.\n');self.assertEqual(kept['status'],'approved');self.assertEqual(A.errors(old,kept),[])
        changed=R.retained_alignment(B,parent,old,old.replace('*alpha beta*','*alpha*'));self.assertEqual(changed['status'],'pending')
        record['reviewer']='altered';B.write(path,record);self.assertIsNone(R.retained_alignment(B,parent,old,old))


class ReviewerRetryTests(unittest.TestCase):
    def packet(self):
        report={'advisors':[{'response':'FID-01: Correct the count of witnesses.'}]}
        return {'candidate':'The source names eight witnesses.','artifact_sha256':review.digest('The source names eight witnesses.'),'report':report,'council_sha256':review.council_digest(report),'required_disposition_ids':sorted(review.council_finding_ids(report)),'writer_dispositions':[]}
    def response(self,p,**extra):
        return dict(status='passed',artifact_sha256=p['artifact_sha256'],council_sha256=p['council_sha256'],assessment='The current candidate gives the count in the source and preserves its limited scope.',open_findings=[],dispositions=[{'id':key,'status':'resolved','evidence':'The candidate now says eight witnesses and matches the exact count given in the supplied source.'} for key in p['required_disposition_ids']],**extra)
    def invoke(self,responses):
        packet=self.packet();evidence={'sources':[{'raw':'Eight witnesses.','raw_sha256':review.digest('Eight witnesses.')}],'artifact_sha256':packet['artifact_sha256']}
        calls=[]
        def run(*args,**kwargs):
            value=responses[min(len(calls),len(responses)-1)];calls.append(1)
            if isinstance(value,Exception):raise value
            kwargs['stdout'].write(value if isinstance(value,str) else json.dumps(value));kwargs['stdout'].flush()
            return subprocess.CompletedProcess([],0)
        with tempfile.TemporaryDirectory() as td,patch.object(L.shutil,'which',return_value='/fixture/client'),patch.object(L.subprocess,'run',side_effect=run):
            error=None
            try:L.run(packet,evidence,Path(td)/'review')
            except ValueError as exc:error=str(exc)
            receipts=list((Path(td)/'review').rglob('invocation.json'))
            return calls,error,[json.loads(p.read_text()) for p in receipts]
    def test_missing_dispositions_get_one_real_retry(self):
        passed=self.response(self.packet());empty=dict(passed,dispositions=[])
        calls,error,_=self.invoke([empty,passed]);self.assertEqual(len(calls),2);self.assertIsNone(error)
        calls,error,_=self.invoke([empty]);self.assertEqual(len(calls),2);self.assertIsNotNone(error)
    def test_substantive_hash_and_provider_failures_are_never_retried(self):
        passed=self.response(self.packet())
        for value in [dict(passed,status='blocked',open_findings=['FID-02']),dict(passed,artifact_sha256='wrong'),'not json',subprocess.TimeoutExpired(['fixture'],1)]:
            calls,error,receipts=self.invoke([value]);self.assertEqual(len(calls),1);self.assertIsNotNone(error);self.assertEqual(len(receipts),1)

if __name__=='__main__':unittest.main()
