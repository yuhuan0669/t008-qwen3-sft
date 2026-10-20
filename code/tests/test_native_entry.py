import importlib
import json
import os
import pathlib
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import native_recipe as n
import run_identity as r

HELP='--tuner_type --eval_strategy --save_strategy --save_steps --data_seed --model_name --model_author --external_plugins'
SPEC=n.spec_read(pathlib.Path(n.__file__).with_name('identity-spec.example.json'))

class NativeTests(unittest.TestCase):
    def command(self,mode='full',help_text=HELP):
        return n.build_command(mode,'/base','/out',SPEC,help_text)
    def test_formal_native_recipe(self):
        c=self.command(); i=c.index('--dataset')
        self.assertEqual(c[i+1:i+3],n.SOURCES)
        for key,value in [('--save_strategy','steps'),('--save_steps','50'),('--eval_strategy','no'),
                          ('--max_length','2048'),('--data_seed','42')]:
            self.assertEqual(c[c.index(key)+1],value)
        self.assertNotIn('--truncation_strategy',c) # actual default must resolve to delete
        self.assertIn(SPEC['author_en'],c)
        self.assertFalse(any(x.endswith('train.jsonl') for x in c))
    def test_aliases_and_missing_required_fail(self):
        c=self.command(help_text=HELP.replace('--tuner_type','--train_type').replace('--eval_strategy','--evaluation_strategy'))
        self.assertIn('--train_type',c);self.assertIn('--evaluation_strategy',c)
        with self.assertRaises(RuntimeError):self.command(help_text=HELP.replace('--model_author',''))
    def test_command_drift_and_smoke_bounded(self):
        c=self.command();n.validate_formal_command(self.command('smoke'),c,'smoke')
        bad=list(c);bad[bad.index('--max_length')+1]='2560'
        with self.assertRaises(RuntimeError):n.validate_formal_command(bad,c,'full')
    def test_cpu_branch_precedes_authorization_and_gpu(self):
        report={'verified':True}
        flags=['run_identity.py','cpu-check','--model','/base','--identity-spec','s',
               '--evidence-dir','o','--reference-snapshot','r','--base-files','b']
        with patch.object(sys,'argv',flags),patch.dict(os.environ,{},clear=True),\
             patch.object(n,'cpu_check',return_value=report) as check,\
             patch.object(r,'swift_cli_help',return_value=HELP),\
             patch.object(r,'require_env',side_effect=AssertionError('authorization in CPU branch')),\
             patch.object(r.subprocess,'Popen',side_effect=AssertionError('training started')):
            r.main();check.assert_called_once()
    def test_unauthorized_training_never_starts(self):
        with patch.object(sys,'argv',['run_identity.py','full']),patch.dict(os.environ,{},clear=True),\
             patch.object(r.subprocess,'Popen',side_effect=AssertionError('training started')):
            with self.assertRaises(RuntimeError):r.main()
    def test_native_config_bypass_fails(self):
        values=dict(dataset=n.SOURCES,split_dataset_ratio=0,max_length=2048,truncation_strategy='delete',
                    seed=42,data_seed=42,dataset_shuffle=True,use_hf=False)
        n.validate_native_args(types.SimpleNamespace(**values))
        for k,v in [('packing',True),('lazy_tokenize',True),('cached_dataset',['x']),
                    ('use_hf',True),('truncation_strategy','right'),('dataset_shuffle',False)]:
            bad=dict(values);bad[k]=v
            with self.assertRaises(RuntimeError):n.validate_native_args(types.SimpleNamespace(**bad))
    def test_order_and_multiplicity_drift_fails(self):
        a=[{'messages':[1]},{'messages':[2]}]
        for b in [list(reversed(a)),a+a]:
            with self.assertRaises(RuntimeError):n.check_record(n.dataset_record(a),n.dataset_record(b),'test')
    def test_final_checkpoint_needs_actual_terminal_record(self):
        with tempfile.TemporaryDirectory() as d:
            root=pathlib.Path(d);ck=root/'checkpoint-103';ck.mkdir()
            state={'global_step':103,'max_steps':103,'epoch':1.0}
            (ck/'trainer_state.json').write_text(json.dumps(state))
            with self.assertRaises(RuntimeError):r.verify_final_checkpoint(root,ck)
            log=root/'logging.jsonl'
            log.write_text(json.dumps({'global_step':103,'last_model_checkpoint':str(ck)})+'\n')
            r.verify_final_checkpoint(root,ck)
            log.write_text(json.dumps({'global_step':104,'last_model_checkpoint':str(ck)})+'\n')
            with self.assertRaises(RuntimeError):r.verify_final_checkpoint(root,ck)
    def test_native_guard_preserves_objects_and_rejects_drift(self):
        values=dict(dataset=n.SOURCES,split_dataset_ratio=0,max_length=2048,truncation_strategy='delete',
                    seed=42,data_seed=42,dataset_shuffle=True,use_hf=False,
                    model_name=[SPEC['name_zh'],SPEC['name_en']],model_author=[SPEC['author_zh'],SPEC['author_en']])
        data=[{'messages':['test']}];filtered=[{'messages':['test'],'lengths':12}]
        class Pipeline:
            args=types.SimpleNamespace(**values,get_template_kwargs=lambda:{'max_length':2048})
            def _get_dataset(self):return data,None
            def _encode_dataset(self,train,val,pre_process=True):return filtered,None
        module=types.ModuleType('swift.pipelines.train.sft');module.SwiftSft=Pipeline
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d)/'e.json'
            expected={'native_input':n.dataset_record(data),'native_retained':n.dataset_record(filtered),
                      'template_kwargs':{'max_length':2048},'versions':{},'spec':SPEC}
            p.write_text(json.dumps(expected))
            with patch.dict(sys.modules,{'swift.pipelines.train.sft':module}),\
                 patch.dict(os.environ,{'NATIVE_PREFLIGHT_REPORT':str(p),'NATIVE_PREFLIGHT_SHA256':r.sha(p)}):
                import native_guard
                importlib.reload(native_guard)
                obj=Pipeline();self.assertIs(obj._get_dataset()[0],data)
                self.assertIs(obj._encode_dataset(data,None)[0],filtered)
                with self.assertRaises(RuntimeError):obj._encode_dataset(data,None,pre_process=False)
                data.append({'messages':['changed']})
                with self.assertRaises(RuntimeError):obj._get_dataset()

if __name__=='__main__':unittest.main()
