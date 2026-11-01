from pathlib import Path
import sys,json,torch
from types import SimpleNamespace
D=Path('/data')/sys.argv[1];sys.path[:0]=[str(D/'code'),str(D/'deps'),str(D/'identity')]
import identity_loss3
from transformers import Qwen3Config,Qwen3ForCausalLM
from swift.trainers.seq2seq_trainer import Seq2SeqTrainer
from swift.model import get_processor
from swift.template import get_template
from copy import deepcopy
p=get_processor('/base',model_type='qwen3',download_model=False)
ts=[]
for strategy in ['default+t008_identity3_ignore_empty_think','default+ignore_empty_think']:
 t=get_template(p,template_type='qwen3',max_length=2048,truncation_strategy='raise',loss_scale=strategy,preserve_thinking=False);t.set_mode('train');ts.append(t)
torch.set_num_threads(2);torch.manual_seed(42)
m=Qwen3ForCausalLM(Qwen3Config(vocab_size=37,hidden_size=16,intermediate_size=32,num_hidden_layers=2,num_attention_heads=2,num_key_value_heads=1,head_dim=8,max_position_embeddings=256));m.model_info=SimpleNamespace(is_moe_model=False);m.eval()
stub=SimpleNamespace(model=m,template=ts[0],model_accepts_loss_kwargs=True,compute_loss_func=None,label_smoother=None,_loss_shifts_labels=True,args=SimpleNamespace(enable_dft_loss=False,enable_channel_loss=False,use_liger_kernel=False,past_index=-1,tuner_backend='peft',average_tokens_across_devices=True,world_size=1,n_gpu=1),accelerator=SimpleNamespace(unwrap_model=lambda x:x,num_processes=1,parallelism_config=None),_compute_acc=lambda *a,**k:None)
results=[]
for row in [json.loads(x) for x in (D/'train.jsonl').read_text().splitlines()]:
 vals=[]
 for t in ts:
  b=t.data_collator([t.encode(deepcopy(row))]);b['input_ids']%=37;b['labels']=torch.where(b['labels']==-100,b['labels'],b['labels']%37);den=(b['labels']!=-100).sum();m.zero_grad();stub.template=t
  loss=Seq2SeqTrainer.compute_loss(stub,m,b,False,den);loss.backward();grad=torch.cat([v.grad.reshape(-1) for v in m.parameters() if v.grad is not None]);vals.append((loss.detach(),grad.clone(),int(den)))
 assert vals[0][2]==vals[1][2] and torch.allclose(vals[0][0],vals[1][0],atol=1e-7) and torch.allclose(vals[0][1],vals[1][1],atol=1e-7)
 results.append({'loss':float(vals[0][0]),'denominator':vals[0][2],'loss_gradient_equal':True})
(D/'loss-equivalence.json').write_text(json.dumps({'pass':True,'rows':results,'tiny_random_model':True,'optimizer_steps':0}));print('16 native Swift loss and gradient comparisons passed')
