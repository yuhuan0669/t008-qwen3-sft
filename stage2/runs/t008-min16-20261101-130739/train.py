from pathlib import Path
import json,sys,torch,hashlib,collections,subprocess
D=Path('/input');O=Path('/runwork');sys.path.insert(0,str(D/'identity'))
import identity_loss3
from transformers import TrainerCallback
from swift.pipelines.train.sft import SwiftSft
from swift.arguments import SftArguments
assert json.loads((D/'cpu-report.json').read_text())['pass']
assert not (O/'training-started.json').exists()
(O/'gpu-before.txt').write_text(subprocess.check_output(['nvidia-smi','--query-compute-apps=pid,used_memory','--format=csv'],text=True))
encoded=json.loads((D/'encoded.json').read_text());seen=collections.Counter()
class Observe(TrainerCallback):
 def __init__(self,t):self.t=t
 def snap(self,step):
  t=self.t;m=t.model;was=m.training;m.eval();loss=[]
  with torch.no_grad():
   for e in encoded:
    b=t._prepare_inputs(t.template.data_collator([e]));loss.append(float(t.compute_loss(m,b)))
  # BA norms measure the effective delta without constructing full model copies.
  delta=0.
  with torch.no_grad():
   for mod in m.modules():
    if hasattr(mod,'lora_A') and 'default' in mod.lora_A:
     a=mod.lora_A['default'].weight.float();b=mod.lora_B['default'].weight.float();delta+=float(((b@a)*mod.scaling['default']).square().sum())
  p=O/f'checkpoint-{step}';m.save_pretrained(p)
  (O/f'observe-{step}.json').write_text(json.dumps({'step':step,'per_row_loss':loss,'effective_delta_l2':delta**.5,'seen_training_rows':dict(seen)}));m.train(was)
 def on_train_begin(self,args,state,control,**kw):self.snap(0)
 def on_pre_optimizer_step(self,args,state,control,**kw):
  opt=kw['optimizer'];model=kw['model'];norm=sum(float(p.grad.float().square().sum()) for p in model.parameters() if p.requires_grad and p.grad is not None)**.5
  with (O/'updates.jsonl').open('a') as f:f.write(json.dumps({'before_step':state.global_step+1,'lr':[g['lr'] for g in opt.param_groups],'gradient_norm_after_clip':norm})+'\n')
 def on_step_end(self,args,state,control,**kw):
  if state.global_step in [1,2,4,8]:self.snap(state.global_step)
class Run(SwiftSft):
 def train(self,t):
  orig=t.compute_loss
  clip=t.accelerator.clip_grad_norm_
  def observed_clip(*a,**kw):
   value=clip(*a,**kw)
   with (O/'preclip.jsonl').open('a') as f:f.write(json.dumps({'step':t.state.global_step+1,'norm':float(value)})+'\n')
   return value
  t.accelerator.clip_grad_norm_=observed_clip
  def tracked(model,inputs,*a,**kw):
   if model.training:
    for ids in inputs['input_ids'].tolist():seen[hashlib.sha256(json.dumps(ids).encode()).hexdigest()]+=1
   return orig(model,inputs,*a,**kw)
  t.compute_loss=tracked;t.add_callback(Observe(t));(O/'training-started.json').write_text(json.dumps({'one_run':True}))
  result=super().train(t)
  assert t.state.global_step==8 and sum(seen.values())==128 and len(seen)==16 and set(seen.values())=={8},dict(seen)
  (O/'training-complete.json').write_text(json.dumps({'steps':8,'exposures':128,'unique':16,'per_row':8,'log_history':t.state.log_history},indent=2));return result
argv=json.loads((D/'argv.json').read_text());args=SftArguments(argv) if False else None
Run(argv).main()
