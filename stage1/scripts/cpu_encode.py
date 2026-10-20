"""Real Swift CPU data path only. Never constructs a model, Trainer or ClearML Task."""
from pathlib import Path
import os,json,hashlib,importlib.metadata as md,sys
import torch
assert not torch.cuda.is_available() and not list(Path('/dev').glob('nvidia*'))
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data';E=ROOT/'evidence';E.mkdir(exist_ok=True)
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.pipelines.train.sft import SwiftSft

def args_for(path):
 return SftArguments(model='/base',model_type='qwen3',template='qwen3',dataset=[str(path)],
  use_cpu=True,report_to=['none'],add_version=False,output_dir='/work/stage1/evidence/no-training-output',
  split_dataset_ratio=0,dataset_shuffle=False,dataset_num_proc=1,
  max_length=2048,truncation_strategy='raise',loss_scale='default+ignore_empty_think',preserve_thinking=False,
  seed=42,data_seed=42,torch_dtype='bfloat16')
args=args_for(D/'prepared.jsonl')
processor=get_processor('/base',model_type='qwen3',download_model=False)
unbounded=get_template(processor,**args.get_template_kwargs());unbounded.max_length=None;unbounded.set_mode('train')
rows=[json.loads(l) for l in (D/'prepared.jsonl').read_text().splitlines()]
audit=[];cache={}
for i,r in enumerate(rows):
 k=json.dumps(r['messages'],sort_keys=True,ensure_ascii=False)
 if k not in cache:
  try:
   enc=unbounded.encode(r,return_length=True);ids=enc['input_ids'];labels=enc['labels'];assert len(ids)==len(labels)
   assert all(y==-100 or x==y for x,y in zip(ids,labels))
   cache[k]={'tokens':len(ids),'supervised_tokens':sum(y!=-100 for y in labels)}
  except Exception as e: cache[k]={'error':type(e).__name__+': '+str(e)[:300]}
 audit.append({'row':i,**cache[k]})
(E/'prepared-encoding.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in audit))
from finalize_data import finalize
manifest=finalize()
args=args_for(D/'train.jsonl');loaded,val=args.load_dataset();final=[json.loads(l) for l in (D/'train.jsonl').read_text().splitlines()]
assert val is None or len(val)==0
assert [r['messages'] for r in loaded]==[r['messages'] for r in final]
template=get_template(processor,**args.get_template_kwargs());template.set_mode('train')
class Stub:
 def _save_val_dataset(self,val):assert val is None or len(val)==0
stub=Stub();stub.args=args;stub.template=template
method=getattr(SwiftSft._encode_dataset,'__wrapped__',SwiftSft._encode_dataset)
encoded,val=method(stub,loaded,val)
assert len(encoded)==len(final)
# Actual encoded pipeline may retain messages plus lengths; verify ordered members when exposed.
if 'messages' in encoded.column_names:assert [r['messages'] for r in encoded]==[r['messages'] for r in final]
actual=[]
for i,r in enumerate(final):
 enc=template.encode(r,return_length=True);ids=enc['input_ids'];labels=enc['labels']
 assert len(ids)<=2048 and any(x!=-100 for x in labels)
 assert all(y==-100 or x==y for x,y in zip(ids,labels))
 actual.append({'row':i,'tokens':len(ids),'supervised_tokens':sum(x!=-100 for x in labels)})
# Empty-think prefix mask verification against a real revised example.
probe=next(r for r in final if r['dataset']=='swift/self-cognition')
enc=template.encode(probe,return_length=True)
supervised_text=processor.decode([x for x,y in zip(enc['input_ids'],enc['labels']) if y!=-100])
assert '<think>' not in supervised_text and '</think>' not in supervised_text
assert probe['messages'][-1]['content'].split('</think>',1)[1].strip() in supervised_text
# Prompt consistency compares generation prefix only, not training answer sequence.
prompt_checks=[]
for think in [False,True]:
 prompt=processor.apply_chat_template(probe['messages'][:-1],tokenize=False,add_generation_prompt=True,enable_thinking=think)
 prompt_checks.append({'enable_thinking':think,'prompt':prompt,'input_token_count':len(processor.encode(prompt,add_special_tokens=False))})
(E/'prompt-probe.json').write_text(json.dumps(prompt_checks,ensure_ascii=False,indent=2)+'\n')
(E/'train-encoding.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in actual))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
small={p.name:sha(p) for p in Path('/base').iterdir() if p.is_file() and p.suffix in ('.json','.jinja') and p.stat().st_size<30_000_000}
report={'verified':True,'dataset_sha256':sha(D/'train.jsonl'),'rows':len(final),'actual_loader_rows':len(loaded),'actual_pipeline_rows':len(encoded),'ordered_members_verified':True,'zero_overlength':True,'zero_empty_supervision':True,'zero_silent_drop':True,'max_tokens':max(x['tokens'] for x in actual),'loss_scale':args.loss_scale,'template_kwargs':args.get_template_kwargs(),'empty_think_mask_verified':True,'empty_think_supervised_text':supervised_text,'versions':{x:md.version(x) for x in ['ms-swift','transformers','peft','torch','tokenizers','datasets','modelscope']},'tokenizer_config_sha256':small,'weights_loaded':False,'trainer_created':False,'gpu_available':False,'clearml_task_created':False,'pipeline_output_columns':encoded.column_names}
(E/'encoding-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n')
print(json.dumps({k:report[k] for k in ['verified','rows','max_tokens','zero_silent_drop','empty_think_mask_verified']}))
