from pathlib import Path
import json,os
from transformers import HfArgumentParser
from swift.arguments import SftArguments
import torch
R=Path('/work/stage1');spec=json.loads((R/'training/run-spec.json').read_text());argv=spec['full_argv'][2:]
parser=HfArgumentParser(SftArguments);ns,unknown=parser.parse_known_args(argv);assert not unknown,unknown
# No model load; only dataclass/config initialization under CPU overrides.
a,=parser.parse_args_into_dataclasses(argv+['--use_cpu','true','--report_to','none','--add_version','false','--output_dir','/work/stage1/evidence/recipe-only'])
assert str(a.training_args.device)=='cpu' and not torch.cuda.is_available()
assert a.dataset==['/work/stage1/data/train.jsonl'] and a.max_length==2048 and a.loss_scale=='default+ignore_empty_think'
assert a.preserve_thinking is False
assert a.lora_dropout==0.05 and a.truncation_strategy=='delete' and a.dataset_shuffle is True
from swift.pipelines.train.sft import SwiftSft
assert getattr(SwiftSft._encode_dataset,'_t008_local_guard',False)
loaded,val=a.load_dataset()
from swift.model import get_processor
from swift.template import get_template
processor=get_processor('/base',model_type='qwen3',download_model=False)
template=get_template(processor,**a.get_template_kwargs());template.set_mode('train')
class Stub:
 def _save_val_dataset(self,val):assert val is None or len(val)==0
stub=Stub();stub.args=a;stub.template=template
encoded,val=SwiftSft._encode_dataset(stub,loaded,val)
assert len(encoded)==spec['dataset_rows']
# Inject a missing row into the member check; it must reject it.
import importlib.util
sp=importlib.util.spec_from_file_location('guard_test',R/'training/local_data_guard.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
mini=[{'messages':[{'role':'user','content':'a'}]},{'messages':[{'role':'user','content':'b'}]}]
try:g.verify_members(mini,mini,mini[:1])
except RuntimeError:pass
else:raise AssertionError('Guard accepted deletion')
out={'verified':True,'unknown_flags':unknown,'dataset':a.dataset,'max_length':a.max_length,'loss_scale':a.loss_scale,'preserve_thinking':a.preserve_thinking,'lora_dropout':a.lora_dropout,'dataset_shuffle':a.dataset_shuffle,'truncation_strategy':a.truncation_strategy,'guarded_pipeline_rows':len(encoded),'missing_row_rejection_verified':True,'weights_loaded':False,'trainer_created':False,'cpu_overrides':['use_cpu=true','report_to=none','add_version=false','output_dir=recipe-only']}
(R/'evidence/recipe-validation.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
