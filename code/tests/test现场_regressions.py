"""Regression cases motivated by real CPU preparation failures."""
import pathlib,sys,unittest
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import prepare_official,run_identity
import preflight_data

class TestFieldRegressions(unittest.TestCase):
    def test_registered_model_must_use_actual_remote_https_storage(self):
        base='https://clearml.example/files'
        self.assertEqual(run_identity.clearml_storage_uri(base+'/'),base)
        run_identity.validate_registered_model_uri(base+'/project/model.zip',base)
        for bad in ['/work/model.zip','file:///work/model.zip','http://clearml.example/files/model.zip',
                    'https://other.example/files/model.zip','https://clearml.example/files-other/model.zip']:
            with self.assertRaises(RuntimeError):run_identity.validate_registered_model_uri(bad,base)
        for bad in ['','http://clearml.example/files','https://user:secret@clearml.example/files']:
            with self.assertRaises(RuntimeError):run_identity.clearml_storage_uri(bad)

    def test_nonboolean_authorization_values_fail_closed(self):
        import copy
        good={'identity_verified':True,'gpu_window_approved':True,'experiment_approved':True,
              'sources_approved':{k:True for k in ['swift/Qwen3-SFT-Mixin','swift/self-cognition:qwen3']},
              'decision_ref':'SYNTHETIC-TEST-ONLY','source_snapshot_ref':'SYNTHETIC-TEST-ONLY'}
        run_identity.validate_authorization(good)
        for bad in ['false','true',1,[],None,False]:
            for key in ['identity_verified','gpu_window_approved','experiment_approved']:
                obj=copy.deepcopy(good);obj[key]=bad
                with self.assertRaises(RuntimeError):run_identity.validate_authorization(obj)
            for key in good['sources_approved']:
                obj=copy.deepcopy(good);obj['sources_approved'][key]=bad
                with self.assertRaises(RuntimeError):run_identity.validate_authorization(obj)

    def test_mixin_jinja_kept_but_identity_case_variants_rejected(self):
        code={'messages':[{'role':'assistant','content':'<h1>{{ message }}</h1> {{name}}'}]}
        self.assertEqual(prepare_official.unresolved_placeholders([code],1),[])
        for token in ['{{NAME}}','{{AUTHOR}}','{{AUTHOER}}','{{name}}','{{ author }}']:
            identity={'messages':[{'role':'assistant','content':token}]}
            self.assertTrue(prepare_official.unresolved_placeholders([code,identity],1))

    def test_outer_help_uses_real_sft_parser_fallback(self):
        good='--model --save_strategy --data_seed --tuner_type --eval_strategy'
        with patch.object(run_identity.subprocess,'run',side_effect=[
            SimpleNamespace(stdout='--tuner_backend'),SimpleNamespace(stdout=good)]) as call:
            self.assertEqual(run_identity.swift_cli_help(),good)
            self.assertEqual(call.call_args_list[1].args[0][-1],
                'from swift.pipelines import sft_main; sft_main(["--help"])')

    def test_incomplete_real_parser_fails_closed(self):
        with patch.object(run_identity.subprocess,'run',return_value=SimpleNamespace(stdout='--tuner_backend')):
            with self.assertRaisesRegex(RuntimeError,'incomplete'):run_identity.swift_cli_help()

    def test_transformers_batchencoding_counts_tokens_not_mapping_keys(self):
        import tempfile,json,hashlib
        from collections import UserDict
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as tmp:
            root=pathlib.Path(tmp);data=root/'data';data.mkdir();model=root/'model';model.mkdir()
            (model/'config.json').write_text('{}');(model/'model.safetensors').write_bytes(b'FAKE-TEST')
            (data/'train.jsonl').write_text(json.dumps({'messages':[{'role':'user','content':'hello'}]})+'\n')
            (data/'manifest.json').write_text(json.dumps({'rows':1,'files_sha256':{'train.jsonl':run_identity.sha(data/'train.jsonl')}}))
            tokenizer=SimpleNamespace(apply_chat_template=lambda *a,**k:UserDict({'input_ids':list(range(2050)),'attention_mask':[1]*2050}))
            fake=SimpleNamespace(AutoTokenizer=SimpleNamespace(from_pretrained=lambda *a,**k:tokenizer))
            with patch.dict(sys.modules,{'transformers':fake}):
                report=preflight_data.scan(data,model)
            self.assertEqual(report['max_tokens'],2050)
            self.assertEqual(report['overlength_rows'],1)
