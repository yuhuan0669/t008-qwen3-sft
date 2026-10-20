"""Exercise installed Swift plugin on CPU using frozen native-loaded evidence.
Replays snapshot only for verification; it is never a training data input.
"""
import argparse, hashlib, json, os, pathlib
p=argparse.ArgumentParser();p.add_argument('--proof',required=True);p.add_argument('--out',required=True);a=p.parse_args()
proof=pathlib.Path(a.proof);r=json.loads(proof.read_text())
os.environ['NATIVE_PREFLIGHT_REPORT']=str(proof)
os.environ['NATIVE_PREFLIGHT_SHA256']=hashlib.sha256(proof.read_bytes()).hexdigest()
from transformers import HfArgumentParser
from swift.arguments import SftArguments
args,=HfArgumentParser(SftArguments).parse_args_into_dataclasses(r['formal_command'][2:]+['--use_cpu','true','--report_to','none','--add_version','false'])
from datasets import Dataset
from swift.model import get_processor
from swift.template import get_template
from swift.pipelines.train.sft import SwiftSft
from native_recipe import dataset_record
raw=[json.loads(x) for x in (proof.parent/'native-loaded.jsonl').read_text().splitlines()]
ds=Dataset.from_list(raw)
# The genuine wrapper still invokes the actual original _get_dataset; source
# HTTP was already tested by cpu-check. This replay fixes only its load return.
args.load_dataset=lambda:(ds,None)
pipeline=object.__new__(SwiftSft);pipeline.args=args
pipeline.template=get_template(get_processor('/base',model_type='qwen3',download_model=False),**args.get_template_kwargs())
pipeline.template.set_mode('train')
assert pipeline._get_dataset()[0] is ds
retained,val=pipeline._encode_dataset(ds,None)
assert dataset_record(retained)==r['native_retained'] and val is None
results={'actual_installed_plugin_loaded':True,'get_dataset_preserves_object':True,'actual_encode_guard_positive':True}
def rejects(name,call):
    try:call()
    except RuntimeError as exc: results[name]={'blocked':True,'reason':str(exc)}
    else: raise AssertionError(name+' unexpectedly passed')
original=os.environ['NATIVE_PREFLIGHT_SHA256']
os.environ['NATIVE_PREFLIGHT_SHA256']='0'*64
rejects('report_sha_tamper',pipeline._get_dataset)
os.environ['NATIVE_PREFLIGHT_SHA256']=original
saved=args.model_name;args.model_name=['WRONG','WRONG']
rejects('identity_tamper',pipeline._get_dataset);args.model_name=saved
saved=args.cached_dataset;args.cached_dataset=['BYPASS']
rejects('cached_data_bypass',pipeline._get_dataset);args.cached_dataset=saved
rejects('skip_preprocessing',lambda:pipeline._encode_dataset(ds,None,pre_process=False))
args.load_dataset=lambda:(Dataset.from_list(raw[::-1]),None)
rejects('input_order_tamper',pipeline._get_dataset)
results.update(weights_loaded=False,trainer_created=False,clearml_task_created=False,gpu_training_started=False)
pathlib.Path(a.out).write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False))
