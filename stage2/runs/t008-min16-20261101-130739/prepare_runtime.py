from pathlib import Path
import json,hashlib,subprocess
R=Path('/Users/ben/aiws/codex/keywords/t008_qwen3_sft');D=Path(__file__).resolve().parent;V=R/'stage2/variants/minimal16-diagnostic-review-v0.1';OLD=R/'stage2/runs/t008-v0127-generalonly-20261101-121120'
(D/'protocol.json').write_bytes((V/'protocol.json').read_bytes())
(D/'cpu.py').write_text('''from pathlib import Path
import sys,json,copy,torch,importlib.metadata as md
D=Path('/data')/sys.argv[1];sys.path[:0]=[str(D/'code'),str(D/'deps'),str(D/'identity')]
import identity_loss3
from swift.model import get_processor
from swift.template import get_template
processor=get_processor('/base',model_type='qwen3',download_model=False)
rows=[json.loads(x) for x in (D/'train.jsonl').read_text().splitlines()]
templates=[]
for loss in ['default+t008_identity3_ignore_empty_think','default+ignore_empty_think']:
 t=get_template(processor,template_type='qwen3',max_length=2048,truncation_strategy='raise',loss_scale=loss,preserve_thinking=False);t.set_mode('train');templates.append(t)
reports=[];encoded=[]
for i,row in enumerate(rows):
 a,b=[t.encode(copy.deepcopy(row)) for t in templates];ba,bb=[t.data_collator([e]) for t,e in zip(templates,[a,b])]
 assert a['input_ids']==b['input_ids'] and a['labels']==b['labels']
 # Binary strategy represents zero weights through ignored labels; compare effective weights.
 def weights(batch):return (batch['labels']!=-100).float()*batch.get('loss_scale',torch.ones_like(batch['labels']))
 wa,wb=weights(ba),weights(bb);assert torch.equal(wa,wb)
 assert not (wa>1).any() and wa.sum()>0
 assert len(a['input_ids'])<=2048 and identity_loss3.message_key(row['messages']) not in templates[0].loss_scale.identity_keys
 active=[j for j,v in enumerate(wa[0].tolist()) if v];text=processor.tokenizer.decode([a['input_ids'][j] for j in active])
 assert row['messages'][1]['content'].split('</think>')[-1].strip() in text
 assert active[0]>len(processor.tokenizer.encode(row['messages'][0]['content'],add_special_tokens=False))
 reports.append({'line':i+1,'input_ids':a['input_ids'],'decoded_tokens':[processor.tokenizer.decode([x]) for x in a['input_ids']],'labels':a['labels'],'loss_scale':ba.get('loss_scale').tolist(),'effective_mask':wa.tolist(),'supervised_text':text,'valid_tokens':int((ba['labels']!=-100).sum()),'effective_tokens':int(wa.sum())})
 encoded.append(a)
(D/'encoded.json').write_text(json.dumps(encoded));(D/'cpu-rows.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2));(D/'cpu-report.json').write_text(json.dumps({'pass':True,'rows':len(rows),'max_tokens':max(len(a['input_ids']) for a in encoded),'optimizer_steps':0,'effective_masks_equal':True,'versions':{n:md.version(n) for n in ['ms-swift','torch','transformers','peft']}}));print((D/'cpu-report.json').read_text())
''')
(D/'train.py').write_text('''from pathlib import Path
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
  with (O/'updates.jsonl').open('a') as f:f.write(json.dumps({'before_step':state.global_step+1,'lr':[g['lr'] for g in opt.param_groups],'gradient_norm_after_clip':norm})+'\\n')
 def on_step_end(self,args,state,control,**kw):
  if state.global_step in [1,2,4,8]:self.snap(state.global_step)
class Run(SwiftSft):
 def train(self,t):
  orig=t.compute_loss
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
''')
# keep original recipe; native Swift run plus observation callback, no optimizer Smoke.
a=json.loads((OLD/'training-config.json').read_text())['full_argv'][2:];i=a.index('--external_plugins');a=a[:i]+['--external_plugins','/input/identity/identity_loss3.py']
for key,val in {'--dataset':'/input/train.jsonl','--max_steps':'8','--save_steps':'8','--save_total_limit':'1','--logging_steps':'1','--output_dir':'/runwork/trainer','--report_to':'tensorboard','--truncation_strategy':'raise'}.items():
 if key in a:a[a.index(key)+1]=val
 else:a +=[key,val]
a+=['--add_version','false'];(D/'argv.json').write_text(json.dumps(a,indent=2))
files={x:(D/x).read_text() for x in ['cpu.py','train.py','argv.json']};files['train.jsonl']=(V/'train.jsonl').read_text()
for x in ['identity_loss3.py','identity-keys.json']:files['identity/'+x]=(R/'stage1/variants/stage1-cpu-v0.1.22'/x).read_text()
payload={'run':D.name,'sha':hashlib.sha256(files['train.jsonl'].encode()).hexdigest(),'files':dict(files,**{'stage1/data/train.jsonl':files['train.jsonl']})}
k=['kubectl','--context','lmas00-direct','-n','swift'];p=subprocess.run(k+['exec','-i',D.name+'-prep','--','python3','-c',(OLD/'prepare_remote.py').read_text()],input=json.dumps(payload),text=True,capture_output=True,check=True);(D/'input-binding.json').write_text(p.stdout)
p=subprocess.run(k+['exec',D.name+'-prep','--','python3','/data/'+D.name+'/cpu.py',D.name],text=True,capture_output=True);(D/'cpu.log').write_text(p.stdout+p.stderr);print(p.returncode,p.stdout,p.stderr[-2500:])
