"""Local CPU-only tests using synthetic data; no live source, GPU, SDK or network."""
import copy, hashlib, json, os, pathlib, sys, tempfile, unittest
from unittest.mock import patch
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import derive_snapshot, eval_identity, preflight_data, prepare_official, register_evaluation, run_identity


def save(path, obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


class TestGate(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=pathlib.Path(self.tmp.name)
        self.orig=self.root/'orig';self.orig.mkdir()
        self.model=self.root/'base';self.model.mkdir()
        (self.model/'config.json').write_text('{}')
        (self.model/'model.safetensors').write_bytes(b'FAKE-ONLY')
        self.basefiles=run_identity.base_fingerprint(self.model)
        self.basesha=hashlib.sha256(json.dumps(self.basefiles,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
        lines=[]
        for i in range(2600):lines.append(json.dumps({'messages':[{'role':'user','content':str(i)},
             {'role':'assistant','content':'response'}]},ensure_ascii=False)+'\n')
        (self.orig/'train.jsonl').write_text(''.join(lines),encoding='utf-8')
        (self.orig/'identity_spec.json').write_text('{"name_zh":"test"}\n')
        self.manifest={'schema':'identity-official-snapshot-v1.2','snapshot_kind':'official_original',
            'rows':2600,'original_rows':2600,'requested_mixin':2000,'requested_identity':600,
            'source_specs':list(prepare_official.SOURCES),
            'files_sha256':{p:run_identity.sha(self.orig/p) for p in ('train.jsonl','identity_spec.json')}}
        save(self.orig/'manifest.json',self.manifest)
        self.approval=self.approved(self.orig)

    def approved(self, loc):
        m=json.loads((loc/'manifest.json').read_text())
        return {'approved_rows':m['rows'],'approved_data_sha256':run_identity.sha(loc/'train.jsonl'),
                'approved_snapshot_manifest_sha256':run_identity.sha(loc/'manifest.json')}

    def test_original_good(self):
        m,_=run_identity.validate_training_dataset(self.orig,self.approval)
        self.assertEqual(m['rows'],2600)

    def test_hardcode_replaced_not_open_gate(self):
        app=dict(self.approval,approved_rows=2599)
        with self.assertRaisesRegex(RuntimeError,'approved rows'):
            run_identity.validate_training_dataset(self.orig,app)

    def test_row_modified_same_count_blocks(self):
        p=self.orig/'train.jsonl'; p.write_bytes(p.read_bytes().replace(b'"2599"',b'"ABC"'))
        with self.assertRaisesRegex(RuntimeError,'integrity'):
            run_identity.validate_training_dataset(self.orig,self.approval)

    def derivative(self):
        decisions=self.root/'exclude.json';save(decisions,[{'index':10,'reason':'identity statement conflicts with approval'}])
        d=self.root/'derived';derive_snapshot.make_derivative(self.orig,decisions,d)
        a=self.approved(d)
        a.update(data_change_ref='review-123',data_change_approved=True,parent_snapshot_dir=str(self.orig))
        return d,a

    def test_approved_one_row_exclusion(self):
        d,a=self.derivative()
        m,_=run_identity.validate_training_dataset(d,a)
        self.assertEqual(m['rows'],2599)

    def test_derivative_needs_independent_change_authorization(self):
        d,a=self.derivative();a.pop('data_change_ref')
        with self.assertRaisesRegex(RuntimeError,'independent approval'):
            run_identity.validate_training_dataset(d,a)

    def test_derivative_not_forgeable_by_digest_and_count_only(self):
        d,a=self.derivative()
        p=d/'train.jsonl'
        p.write_bytes(p.read_bytes().replace(b'"2599"',b'"XYZ"'))
        m=json.loads((d/'manifest.json').read_text())
        m['files_sha256']['train.jsonl']=run_identity.sha(p);save(d/'manifest.json',m)
        a.update(approved_data_sha256=run_identity.sha(p),
                 approved_snapshot_manifest_sha256=run_identity.sha(d/'manifest.json'))
        with self.assertRaisesRegex(RuntimeError,'preserve approved original'):
            run_identity.validate_training_dataset(d,a)

    def test_preflight_missing_rejected(self):
        with self.assertRaisesRegex(RuntimeError,'Missing CPU'):
            run_identity.validate_length_preflight(self.orig,self.orig/'manifest.json',self.approval)

    def test_preflight_tokenizer_only_still_blocked(self):
        report={'schema':'identity-token-preflight-v1.2','dataset_sha256':run_identity.sha(self.orig/'train.jsonl'),
                'manifest_sha256':run_identity.sha(self.orig/'manifest.json'),
                'model_files_sha256':self.basesha,'rows_checked':2600,'max_length':2048,
                'overlength_rows':0,'template_tokenization_completed':True,
                'ms_swift_template_verified':False}
        save(self.orig/'preflight_report.json',report)
        a=dict(self.approval,preflight_model_files_sha256=self.basesha,
               preflight_report_sha256=run_identity.sha(self.orig/'preflight_report.json'))
        with self.assertRaisesRegex(RuntimeError,'unverified'):
            run_identity.validate_length_preflight(self.orig,self.orig/'manifest.json',a)
        report['ms_swift_template_verified']=True;save(self.orig/'preflight_report.json',report)
        a['preflight_report_sha256']=run_identity.sha(self.orig/'preflight_report.json')
        run_identity.validate_length_preflight(self.orig,self.orig/'manifest.json',a)

    def test_fake_chat_template_scans_length(self):
        class FakeToken:
            def apply_chat_template(self,msgs,**kw):return list(range(2200 if msgs[0]['content']=='10' else 20))
        import types
        fake=types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a,**kw:FakeToken()))
        with patch.dict(sys.modules,{'transformers':fake}):
            result=preflight_data.scan(self.orig,self.model)
        self.assertEqual(result['overlength_rows'],1)
        self.assertEqual(result['overlength_index_counts'][0]['index'],10)
        self.assertFalse(result['ms_swift_template_verified'])

    def test_base_tamper_block(self):
        eval_identity.verify_base_model(self.model,{'base_files':self.basefiles})
        (self.model/'model.safetensors').write_bytes(b'CHANGED')
        with self.assertRaisesRegex(RuntimeError,'do not match'):
            eval_identity.verify_base_model(self.model,{'base_files':self.basefiles})

    def test_unexpected_think_invalidates_nonthinking(self):
        answer, closed, bad=eval_identity.classify_answer('<think>secret','',[])
        self.assertEqual(answer,'')
        self.assertTrue(bad)
        answer,closed,bad=eval_identity.classify_answer('<think>x</think> safe',False,[])
        self.assertEqual(answer,'safe')
        self.assertTrue(bad)
        answer,closed,bad=eval_identity.classify_answer('<think>x</think> safe',True,[])
        self.assertEqual(answer,'safe');self.assertFalse(bad)

    def evidence(self, adapter, prompt=None, **kw):
        d={'schema':'identity-eval-v1.2','inference_engine':'transformers+peft',
            'cases_sha256':'c','mode':'nonthinking','seed':42,'max_new_tokens':1024,
            'temperature':0.7,'top_p':0.8,'top_k':20,'base_manifest_files_sha256':'base',
            'adapter_used':adapter,'system_sha256':prompt}
        d.update(kw)
        return d

    def test_abcd_prompt_exact_match(self):
        e=[self.evidence(False,None),self.evidence(False,'prompt1'),
           self.evidence(True,None),self.evidence(True,'prompt1')]
        self.assertEqual(len(register_evaluation.validate_comparisons(e)),1)
        e[-1]['system_sha256']='prompt2'
        with self.assertRaisesRegex(RuntimeError,'EXACTLY'):
            register_evaluation.validate_comparisons(e)

    def test_abcd_settings_mismatch_blocks(self):
        e=[self.evidence(False,None),self.evidence(False,'prompt'),
           self.evidence(True,None),self.evidence(True,'prompt',seed=10)]
        with self.assertRaisesRegex(RuntimeError,'Incomplete'):
            register_evaluation.validate_comparisons(e)

    def test_abcd_duplicate_condition_blocks(self):
        e=[self.evidence(False,None)]*2
        with self.assertRaisesRegex(RuntimeError,'Duplicate'):
            register_evaluation.validate_comparisons(e)

    def test_preflight_evidence_binds_exact_data_and_model(self):
        import types
        class FakeToken:
            def apply_chat_template(self,msgs,**kw):return [1]*50
        fake=types.SimpleNamespace(AutoTokenizer=types.SimpleNamespace(from_pretrained=lambda *a,**kw:FakeToken()))
        ev={'verified':True,'evidence_ref':'ms-swift pinned image log 001',
            'dataset_sha256':run_identity.sha(self.orig/'train.jsonl'),
            'model_files_sha256':self.basesha,'rows_checked':2600,
            'max_length':2048,'overlength_rows':0}
        src=self.root/'swift-evidence.json';save(src,ev)
        with patch.dict(sys.modules,{'transformers':fake}):
            report=preflight_data.scan(self.orig,self.model,src)
        self.assertTrue(report['ms_swift_template_verified'])
        ev['model_files_sha256']='bogus';save(src,ev)
        with patch.dict(sys.modules,{'transformers':fake}):
            with self.assertRaisesRegex(RuntimeError,'evidence absent'):
                preflight_data.scan(self.orig,self.model,src)

    def test_prepare_rejects_misspelled_template_placeholder(self):
        import types
        module=types.ModuleType('swift')
        sub=types.ModuleType('swift.dataset')
        def bad_loader(*a,**k):
            row={'messages':[{'role':'user','content':'Who? {{AUTHOER}}'},
                             {'role':'assistant','content':'I am a model'}]}
            return [row]*2600,None
        sub.load_dataset=bad_loader
        spec=self.root/'spec.json';save(spec,{'name_zh':'样例','name_en':'Example',
            'author_zh':'样例公司','author_en':'Example Co','note':'NOT TRAINING'})
        with patch.dict(sys.modules,{'swift':module,'swift.dataset':sub}):
            with patch.object(sys,'argv',['prepare_official.py','--spec',str(spec),'--out',str(self.root/'out')]):
                with self.assertRaisesRegex(RuntimeError,'placeholder'):
                    prepare_official.main()
        self.assertFalse((self.root/'out').exists())

    def test_identity_example_no_ineffective_note(self):
        d=json.loads((ROOT/'identity-spec.example.json').read_text())
        self.assertNotIn('note',d)
        self.assertEqual(d['name_en'],'Octacarbon LLM')

if __name__=='__main__': unittest.main()
