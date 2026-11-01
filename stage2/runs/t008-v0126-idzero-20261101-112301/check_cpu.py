"""Check every native encoding and actual Swift loss on a tiny random model."""
from collections import Counter
from copy import deepcopy
import hashlib, importlib.metadata as md, inspect, json, os, sys
from pathlib import Path
from types import SimpleNamespace
D=Path('/data')/sys.argv[1]
sys.path[:0]=[str(D/'code'),str(D/'deps'),str(D/'ablation'),str(D/'stage1/variants/stage1-cpu-v0.1.22')]
import torch
from transformers import Qwen3Config,Qwen3ForCausalLM,Trainer,HfArgumentParser,set_seed
from peft import LoraConfig,get_peft_model
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.trainers.seq2seq_trainer import Seq2SeqTrainer
import identity_loss3
from identity_zero import make_compute_loss, token_key, install
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not torch.cuda.is_available()
ref=read(D/'stage1/evidence/encoding-report.json');cfg=read(D/'ablation/config.json')
assert all(md.version(n)==v for n,v in ref['versions'].items())
assert sha(D/'stage1/data/train.jsonl')==ref['dataset_sha256']==cfg['dataset_sha256']
assert sha(D/'stage1/variants/stage1-cpu-v0.1.22/identity_loss3.py')==ref['loss_plugin_sha256']
assert sha(Path(inspect.getfile(Seq2SeqTrainer)))==cfg['native_trainer_sha256']
members=read(D/'ablation/membership.json')['members']
processor=get_processor('/base',model_type='qwen3',download_model=False)
template=get_template(processor,**ref['template_kwargs']);template.set_mode('train')
rows=[json.loads(s) for s in (D/'stage1/data/train.jsonl').read_text().splitlines()]
identity={'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
stub=SimpleNamespace(accelerator=SimpleNamespace(num_processes=1),template=template,label_smoother=None)
def passthrough(self,model,inputs,return_outputs,num_items):return inputs,num_items
wrapped=make_compute_loss(passthrough,members)
seen=Counter();totals=Counter();checks=[]
for line,row in enumerate(rows,1):
    enc=template.encode(deepcopy(row));key=token_key(enc['input_ids']);isid=row['dataset'] in identity
    assert members[key]['identity']==isid and len(enc['input_ids'])<=2048
    batch=template.data_collator([enc]);before={k:v.clone() for k,v in batch.items() if isinstance(v,torch.Tensor)}
    valid=int((batch['labels']!=-100).sum());den=torch.tensor(valid+17)
    out,observed=wrapped(stub,None,batch,False,den)
    assert observed is den
    for k in ['input_ids','labels','attention_mask']:assert torch.equal(out[k],before[k])
    assert torch.equal(out['loss_scale'],before['loss_scale']*(0 if isid else 1))
    totals.update(rows=1,identity=int(isid),valid_tokens=valid,weighted_before=int(before['loss_scale'].sum()),weighted_after=int(out['loss_scale'].sum()))
    seen[key]+=1
    checks.append({'line':line,'key':key,'identity':isid,'valid_tokens':valid,'labels_unchanged':True,'denominator_unchanged':True,'weights_only_change':True})
assert seen==Counter({k:v['multiplicity'] for k,v in members.items()})
assert totals==Counter(rows=1047,identity=234,valid_tokens=928890,weighted_before=946600,weighted_after=920027)
# Compare actual loader order under the same args and data seed; the appended
# plugin only wraps compute_loss and does not touch loader or RNG.
spec=read(D/'stage1/training/run-spec.json');argv=[x.replace('/work/',str(D)+'/') for x in spec['full_argv'][2:]]
argv[argv.index('--dataset')+1]=str(D/'stage1/data/train.jsonl')
argv+=['--use_cpu','true','--report_to','none','--add_version','false','--output_dir','/tmp/idzero-cpu','--dataset_num_proc','1']
args,=HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv)
set_seed(42);loaded,_=args.load_dataset();seq=[identity_loss3.message_key(x['messages']) for x in loaded]
assert len(seq)==1047
set_seed(42);loaded2,_=args.load_dataset();assert seq==[identity_loss3.message_key(x['messages']) for x in loaded2]

torch.set_num_threads(2);torch.manual_seed(42)
base=Qwen3ForCausalLM(Qwen3Config(vocab_size=37,hidden_size=16,intermediate_size=32,num_hidden_layers=2,num_attention_heads=2,num_key_value_heads=1,head_dim=8,max_position_embeddings=64))
model=get_peft_model(base,LoraConfig(r=2,lora_alpha=4,lora_dropout=.05,target_modules='all-linear',task_type='CAUSAL_LM'))
model.model_info=SimpleNamespace(is_moe_model=False)
with torch.no_grad():
    for n,p in model.named_parameters():
        if 'lora_B' in n:p.normal_(0,.03)
model.train();model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
stub=SimpleNamespace(model=model,template=template,model_accepts_loss_kwargs=True,compute_loss_func=None,label_smoother=None,_loss_shifts_labels=True,
 args=SimpleNamespace(enable_dft_loss=False,enable_channel_loss=False,use_liger_kernel=False,past_index=-1,tuner_backend='peft',average_tokens_across_devices=True,world_size=1,n_gpu=1),
 accelerator=SimpleNamespace(unwrap_model=lambda m:m,num_processes=1,parallelism_config=None),_compute_acc=lambda *a,**k:None)
def batch(isid):
    off=10 if isid else 0
    return {'input_ids':torch.tensor([[2,3,4,5,6]])+off,'attention_mask':torch.ones(1,5,dtype=torch.long),
            'labels':torch.tensor([[-100,-100,4+off,5+off,6+off]]),
            'loss_scale':torch.tensor([[0.,0.,3.,3.,1.]]) if isid else torch.tensor([[0.,0.,1.,1.,1.]])}
toy={token_key(batch(i)['input_ids'][0].tolist()):{'identity':i,'valid_tokens':3} for i in [False,True]}
native=Seq2SeqTrainer.compute_loss;wrapped=make_compute_loss(native,toy)
den=Trainer._get_num_items_in_batch(stub,[batch(False),batch(True)],torch.device('cpu'));assert int(den)==6
def value(fn,isid,selected=False):
    b=batch(isid)
    if selected:Seq2SeqTrainer.prepare_logits_to_keep(stub,b)
    model.zero_grad(set_to_none=True);torch.manual_seed(99)
    loss=fn(stub,model,b,False,den);loss.backward()
    grad=torch.cat([p.grad.reshape(-1) for p in model.parameters() if p.requires_grad])
    return loss.detach(),grad.clone(),torch.get_rng_state()
g0=value(native,False);g1=value(wrapped,False)
assert all(torch.equal(a,b) for a,b in zip(g0,g1))
i0=value(native,True);i1=value(wrapped,True)
assert float(i0[0])>0 and float(i1[0])==0 and not bool(i1[1].any())
assert torch.equal(i0[2],i1[2])
for isid in [False,True]:
    a=value(wrapped,isid);b=value(wrapped,isid,True)
    assert torch.allclose(a[0],b[0],atol=1e-7) and torch.allclose(a[1],b[1],atol=1e-7)
install(D/'ablation/config.json');assert getattr(Seq2SeqTrainer.compute_loss,'_t008_identity_zero',False)
out={'verified':True,'rows':1047,'identity_rows':234,'totals':dict(totals),
 'full_native_encoding_checked':True,'all_labels_input_ids_masks_unchanged':True,'all_native_denominators_preserved':True,
 'nonidentity_native_loss_gradient_rng_bitwise_equal':True,'identity_loss_gradient_zero_including_eos':True,
 'identity_forward_rng_progression_unchanged':True,'native_logits_to_keep_checked':True,'same_seed_loader_order_reproduced':True,
 'loader_order_sha256':hashlib.sha256(json.dumps(seq).encode()).hexdigest(),
 'old_full_minibatch_trace_available':False,'runtime_microbatch_audit_required':True,
 'native_trainer_sha256':cfg['native_trainer_sha256'],'plugin_sha256':sha(D/'ablation/identity_zero.py'),
 'model_weights_loaded':False,'tiny_random_model_only':True,'optimizer_steps':0,'gpu_used':False}
(D/'ablation-cpu-report.json').write_text(json.dumps(out,indent=2)+'\n')
(D/'ablation-row-checks.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in checks))
print(json.dumps(out),flush=True)
