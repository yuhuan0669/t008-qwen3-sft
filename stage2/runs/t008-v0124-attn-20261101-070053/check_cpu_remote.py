"""Re-encode unchanged data and instantiate only a meta-device model for module checks."""
from pathlib import Path
from collections import Counter
from copy import deepcopy
import hashlib,importlib,importlib.metadata as md,json,sys

D=Path(sys.argv[1]);spec=json.loads((D/'stage1/training/run-spec.json').read_text())
ref=json.loads((D/'stage1/evidence/encoding-report.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
import torch
assert not torch.cuda.is_available()
from transformers import AutoConfig,AutoModelForCausalLM,HfArgumentParser
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from peft import LoraConfig,get_peft_model
versions={k:md.version(k) for k in ref['versions']};assert versions==ref['versions']
for name,h in ref['normalization_source_hashes'].items():assert sha(Path(importlib.import_module(name).__file__))==h,name
for name,h in ref['tokenizer_config_sha256'].items():assert sha(Path('/base')/name)==h,name
argv=[x.replace('/work/',str(D)+'/') for x in spec['full_argv'][2:]]
argv[argv.index('--dataset')+1]=str(D/'stage1/data/train.jsonl')
argv+=['--use_cpu','true','--report_to','none','--add_version','false','--dataset_num_proc','1','--output_dir','/tmp/t008-attention-cpu-check']
args,=HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv)
assert set(args.target_modules)=={'q_proj','k_proj','v_proj','o_proj'}
assert args.system is None and args.preserve_thinking is False and args.loss_scale=='default+t008_identity3_ignore_empty_think'
import identity_loss3
assert sha(Path(identity_loss3.__file__))==ref['loss_plugin_sha256']
data=D/'stage1/data/train.jsonl';assert sha(data)==spec['dataset_sha256']==ref['dataset_sha256']
rows=[json.loads(s) for s in data.read_text().splitlines()]
assert len(rows)==1047 and sum(r['dataset'] in ref['category_definition']['identity'] for r in rows)==234
assert not any(m['role']=='system' for r in rows for m in r['messages'])
loaded,val=args.load_dataset()
key=lambda r:json.dumps(r['messages'],sort_keys=True,ensure_ascii=False)
assert Counter(map(key,loaded))==Counter(map(key,rows))
processor=get_processor('/base',model_type='qwen3',download_model=False)
kwargs=args.get_template_kwargs();kwargs['truncation_strategy']='raise'
template=get_template(processor,**kwargs);template.set_mode('train')
assert not template.loss_scale.is_binary_loss_scale
prior_template=get_template(processor,**ref['template_kwargs']);prior_template.set_mode('train')
cache={};totals=Counter();maximum=0;encoded_hash=hashlib.sha256()
for r in rows:
 k=key(r)
 if k not in cache:
  value=template.encode(deepcopy(r));prior=prior_template.encode(deepcopy(r))
  fields={f:value[f] for f in ['input_ids','labels','loss_scale']}
  assert all(fields[f]==prior[f] for f in fields)
  assert len(fields['input_ids'])<=2048 and any(y!=-100 for y in fields['labels'])
  assert set(fields['loss_scale'])<={0.0,1.0,3.0}
  cache[k]=fields
 fields=cache[k];maximum=max(maximum,len(fields['input_ids']))
 totals.update(input_tokens=len(fields['input_ids']),supervised_tokens=sum(y!=-100 for y in fields['labels']),weighted_token_units=sum(fields['loss_scale']))
 encoded_hash.update(json.dumps(fields,sort_keys=True,separators=(',',':')).encode()+b'\n')
assert dict(totals)==ref['totals']['after'] and maximum==ref['max_tokens']==2041
# No base weights are loaded; the model exists only as shapes on the meta device.
config=AutoConfig.from_pretrained('/base',local_files_only=True)
with torch.device('meta'):
 model=AutoModelForCausalLM.from_config(config,attn_implementation='eager')
 model=get_peft_model(model,LoraConfig(task_type='CAUSAL_LM',r=8,lora_alpha=32,lora_dropout=.05,
                                     target_modules=args.target_modules,bias='none'))
trainable={n:p.numel() for n,p in model.named_parameters() if p.requires_grad}
assert trainable and all('.lora_' in n and any('.'+m+'.' in n for m in args.target_modules) for n in trainable)
assert sum(trainable.values())==7667712
assert all(p.device.type=='meta' for p in model.parameters())
report={'verified':True,'dataset_sha256':sha(data),'rows':1047,'identity_exposures':234,
        'native_encoding_equal_rows':1047,'native_encoding_sha256':encoded_hash.hexdigest(),
        'totals':dict(totals),'max_tokens':maximum,'overlength_rows':0,'silent_dropped_rows':0,
        'system_rows':0,'target_modules':sorted(args.target_modules),'trainable_parameters':sum(trainable.values()),
        'trainable_tensor_count':len(trainable),'layer_count':config.num_hidden_layers,
        'base_weights_loaded':False,'model_device':'meta','gpu_used':False,'training_started':False,
        'versions':versions,'identity_plugin_sha256':sha(Path(identity_loss3.__file__)),
        'note':'Full native input_ids/labels/loss_scale equal to the frozen v0.1.22 template; only LoRA target modules change.'}
out=Path('/work')/D.name/'cpu-module-check.json';out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report),flush=True)
