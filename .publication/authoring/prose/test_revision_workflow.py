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
    def test_zwj_and_hebrew_section_markers_are_not_words(self):
        joined=scripture_note('אֱ\u200dלֹהִים דֶּבֶר פ','ʾElohim diber','God spoke')
        record=alignment(joined);self.assertEqual(A.errors(joined,record),[])
        counted=A.inventory(joined)[0]
        self.assertEqual(counted['source_tokens'],['אֱלֹהִים','דֶּבֶר'])
        self.assertEqual(counted['roman_tokens'],['ʾElohim','diber'])
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
        from test_native_release import finish_fixture
        self.assertEqual(self.call('verify',self.manifest),1)
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(finish_fixture(B,self.manifest),0)
        self.assertEqual(self.call('verify',self.manifest),0)
    def test_draft_and_note_stage_refuse_site_writes(self):
        self.init();data=B.read(self.manifest)
        before={str(p):p.read_bytes() for p in self.site.rglob('*') if p.is_file()} if hasattr(self,'site') else None
        for delivery in ['draft','note']:
            data['delivery']=delivery;B.write(self.manifest,data)
            self.assertEqual(self.call('stage',self.manifest),1)
        self.assertNotIn('staged',B.read(self.manifest))

    def test_status_revalidates_records_without_mutating_manifest(self):
        self.ready();before=self.manifest.read_bytes()
        self.assertEqual(self.call('status',self.manifest),0)
        self.assertEqual(self.manifest.read_bytes(),before)
        B.write(B.read(self.manifest)['paths']['html_review'],{})
        self.assertEqual(self.call('status',self.manifest),1)
        self.assertEqual(self.manifest.read_bytes(),before)

    def test_adopt_keeps_old_source_and_review_unapproved(self):
        self.ready();self.assertEqual(self.call('stage',self.manifest),0)
        data=B.read(self.manifest);receipt=Path(data['ready']['paths']['handoff']);raw=receipt.read_bytes()
        output=self.root/'adopted'/'build.json'
        self.assertEqual(self.call('adopt',output,'--handoff',receipt,'--site-root',data['paths']['site_root'],'--slug',data['slug']),0)
        adopted=B.read(output)
        self.assertIsNone(adopted['ready']);self.assertEqual(adopted['builds'],[])
        self.assertEqual(self.call('status',output),0)
        self.assertEqual((output.parent/'previous.handoff.json').read_bytes(),raw)
        self.assertEqual(Path(adopted['paths']['source']).read_text(),B.read(receipt)['source_markdown'])
        self.assertFalse(Path(adopted['paths']['review']).exists())
        self.assertEqual(self.call('adopt',output,'--handoff',receipt,'--site-root',data['paths']['site_root'],'--slug',data['slug']),1)

    def test_native_request_accept_preserves_prior_record_and_stages(self):
        from test_native_release import response
        self.ready();old=Path(B.read(self.manifest)['paths']['review']);before=old.read_bytes();request=self.root/'native-request'
        self.assertEqual(self.call('release-request',self.manifest,'--parent-model','active-model','--output',request),0)
        reply=self.root/'native-response.json';reply.write_text(response(B.read(request/'request.json')))
        self.assertEqual(self.call('release-accept',self.manifest,'--request',request/'request.json','--response',reply,'--agent-id','synthetic-native-child','--model','active-model'),0)
        self.assertEqual(old.read_bytes(),before);self.assertNotEqual(B.read(self.manifest)['paths']['review'],str(old))
        self.assertEqual(self.call('stage',self.manifest),0)
    def test_native_accept_failure_restores_manifest_and_preserves_response(self):
        from test_native_release import response
        self.ready();request=self.root/'native-request'
        self.assertEqual(self.call('release-request',self.manifest,'--parent-model','active-model','--output',request),0)
        reply=self.root/'native-response.json';reply.write_text(response(B.read(request/'request.json')))
        before=B.read(self.manifest);original=B.verify;calls=[]
        def verify(args):
            calls.append(1)
            if len(calls)==2:raise ValueError('simulated post-prepare verification failure')
            return original(args)
        with patch.object(B,'verify',side_effect=verify):self.assertEqual(self.call('release-accept',self.manifest,'--request',request/'request.json','--response',reply,'--agent-id','child','--model','active-model'),1)
        self.assertEqual(B.read(self.manifest),before);self.assertTrue(list((request/'responses').glob('*/response.txt')))
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


if __name__=='__main__':unittest.main()
