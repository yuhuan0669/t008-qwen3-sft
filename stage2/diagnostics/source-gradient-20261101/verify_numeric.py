"""FP64 audit of native-vs-chunked gradient checks; no optimization or generation."""
import hashlib
import json
import os
from pathlib import Path
import time
os.environ.setdefault('TORCHINDUCTOR_CACHE_DIR','/tmp/torchinductor_diag')
import torch
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint
from transformers import AutoModelForCausalLM
from peft import PeftModel
from swift.trainers.seq2seq_trainer import per_token_loss_func
from diagnose import read, save, sha, D, I, O, BASE

started=time.monotonic(); p=read(I/'protocol.json'); rows=read(O/'encoded-training.json')
assert read(O/'completed.json')['complete']
a=p['adapters']['step50']
for name,meta in a['files'].items(): assert sha(Path(a['path'])/name)==meta['sha256']
torch.set_num_threads(4); torch.manual_seed(42)
model=AutoModelForCausalLM.from_pretrained(BASE,local_files_only=True,dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa')
model=PeftModel.from_pretrained(model,a['path'],is_trainable=True,local_files_only=True)
model.config.use_cache=False;model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
model.enable_input_require_grads();model.train()
for m in model.modules():
    if isinstance(m,torch.nn.Dropout):m.eval()
params=[v for _,v in model.named_parameters() if v.requires_grad]; base=model.get_base_model()
def memhash():
    h=hashlib.sha256()
    for v in params:h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()
before=memhash()
selected=[min((r for r in rows if r['group']==g),key=lambda r:len(r['input_ids'])) for g in ['general','identity','business']]
selected.append(max((r for r in rows if r['group']=='general'),key=lambda r:len(r['input_ids'])))
results=[]
for row in selected:
    x=torch.tensor([row['input_ids']],device='cuda'); y=torch.tensor([row['labels']],device='cuda')
    w=torch.tensor([row['loss_scale']],dtype=torch.float32,device='cuda'); values=[];vectors=[]
    for dense in [True,False]:
        model.zero_grad(set_to_none=True)
        if dense:
            out=model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=False)
            loss=(per_token_loss_func(out,y)*torch.roll(w,-1,-1).reshape(-1)).sum()/row['valid_tokens']
        else:
            h=base.model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=False).last_hidden_state
            positions=(y[0,1:]!=-100).nonzero().reshape(-1);hidden=h[0,positions];targets=y[0,positions+1];weights=w[0,positions+1]
            def head(hh,yy,ww):return (F.cross_entropy(base.lm_head(hh).float(),yy,reduction='none')*ww).sum()
            loss=sum(checkpoint(head,hidden[j:j+64],targets[j:j+64],weights[j:j+64],use_reentrant=False) for j in range(0,len(positions),64))/row['valid_tokens']
        values.append(float(loss.detach()));loss.backward();vectors.append(torch.cat([v.grad.detach().reshape(-1) for v in params]).cpu().double())
        del loss
        if dense:del out
        else:del h,hidden,targets,weights
        model.zero_grad(set_to_none=True);torch.cuda.empty_cache()
    u,v=vectors;relative=float((u-v).norm()/u.norm());cos=float(torch.dot(u,v)/(u.norm()*v.norm()))
    result={'group':row['group'],'line':row['lines'][0],'tokens':len(row['input_ids']),'native_ce':values[0],'chunked_ce':values[1],
            'gradient_relative_error_fp64':relative,'gradient_cosine_fp64':cos}
    assert abs(values[0]-values[1])<2e-4 and relative<.025 and .9997<cos<=1.000000001,result
    results.append(result);print(json.dumps(result),flush=True);del vectors,u,v
after=memhash();assert before==after
save('fp64-gradient-verification.json',{'verified':True,'checks':results,'memory_hash_before':before,'memory_hash_after':after,
    'weights_unchanged':True,'optimizer_steps':0,'new_generations':0,'seconds':time.monotonic()-started,
    'correction':'Original short-row precheck used float32 cosine on 21.8M dimensions and produced values slightly above1. Ignore those cosine values. FP64 check here supersedes them. Primary group/probe effects already used FP64.',
    'remaining_precision_limit':'BF16 GEMM shape differences produce approximately one-percent gradient differences; weak or sign-sensitive effects are not causal findings.'})

# BF16 head shape changes slightly alter gradients. Verify all source projections
# at step66 with the unmodified native dense loss, not only small loss values.
from peft.utils.save_and_load import set_peft_model_state_dict
from safetensors.torch import load_file
a=p['adapters']['step66'];sd=load_file(str(Path(a['path'])/'adapter_model.safetensors'),device='cpu')
set_peft_model_state_dict(model,sd,adapter_name='default');del sd
native_before=memhash();probes=read(O/'encoded-probes.json');qs=[]
opt=torch.load(Path(a['path'])/'optimizer.pt',map_location='cpu',weights_only=True);pg=opt['param_groups'][0]
pre=torch.cat([1./((opt['state'][i]['exp_avg_sq'].reshape(-1)/(1.-pg['betas'][1]**66)).sqrt()+pg['eps']) for i in pg['params']]).double()
del opt
for probe in probes:
    model.zero_grad(set_to_none=True);x=torch.tensor([probe['prefix']],device='cuda')
    logits=model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=False,logits_to_keep=1).logits[0,-1].float()
    q=logits[probe['bad']]-logits[probe['good']];q.backward()
    qs.append(torch.cat([v.grad.detach().reshape(-1) for v in params]).cpu())
    del q,logits
model.zero_grad(set_to_none=True);torch.cuda.empty_cache()
original={(e['id'],e['source']):e for e in [json.loads(s) for s in (O/'probe-effects.jsonl').read_text().splitlines()] if e['model']=='step66'}
native_effects=[];counter=0;coherence={}
for group in p['groups']:
    aggregate=torch.zeros(sum(v.numel() for v in params),dtype=torch.float64,device='cuda')
    sum_weighted_norms=0.
    for row in (r for r in rows if r['group']==group):
        model.zero_grad(set_to_none=True);x=torch.tensor([row['input_ids']],device='cuda');y=torch.tensor([row['labels']],device='cuda')
        w=torch.tensor([row['loss_scale']],dtype=torch.float32,device='cuda')
        out=model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=False)
        loss=(per_token_loss_func(out,y)*torch.roll(w,-1,-1).reshape(-1)).sum()/row['valid_tokens']
        loss.backward();g=torch.cat([v.grad.detach().reshape(-1) for v in params])
        coefficient=row['multiplicity']*row['valid_tokens']/p['all_valid_tokens']
        aggregate.add_(g.double(),alpha=coefficient)
        sum_weighted_norms+=float(g.double().norm())*coefficient
        del out,loss,g;counter+=1
        if counter%50==0:print(json.dumps({'phase':'native_projection_check','group':group,'done':counter,'total':len(rows),'seconds':time.monotonic()-started}),flush=True)
    vec=aggregate.cpu();del aggregate
    coherence[group]={'aggregate_norm':float(vec.norm()),'sum_exposure_weighted_row_norms':sum_weighted_norms,
                      'alignment_ratio':float(vec.norm())/sum_weighted_norms,
                      'meaning':'Norm of summed source gradient / sum of individual exposure-weighted gradient norms. Descriptive within-source cancellation, not causality.'}
    for probe,qg in zip(probes,qs):
        raw=-float(torch.dot(qg.double(),vec));scaled=-float(torch.dot(qg.double(),vec*pre));prior=original[(probe['id'],group)]
        native_effects.append({'model':'step66','probe':probe['id'],'source':group,'raw_effect':raw,'adam_scaled_effect':scaled,
            'original_raw_effect':prior['raw_effect'],'original_adam_scaled_effect':prior['adam_scaled_effect'],
            'raw_sign_matches':(raw>0)==(prior['raw_effect']>0),'scaled_sign_matches':(scaled>0)==(prior['adam_scaled_effect']>0),
            'raw_relative_difference':abs(raw-prior['raw_effect'])/max(abs(raw),abs(prior['raw_effect']),1e-12),
            'scaled_relative_difference':abs(scaled-prior['adam_scaled_effect'])/max(abs(scaled),abs(prior['adam_scaled_effect']),1e-12)})
    del vec;model.zero_grad(set_to_none=True);torch.cuda.empty_cache()
native_after=memhash();assert native_before==native_after
save('native-projection-verification.json',{'complete':True,'checkpoint':66,'rows':1047,'unique_encodings':counter,
    'projections':native_effects,'source_coherence':coherence,'raw_sign_disagreements':sum(not e['raw_sign_matches'] for e in native_effects),
    'scaled_sign_disagreements':sum(not e['scaled_sign_matches'] for e in native_effects),
    'weights_unchanged':True,'memory_sha256_before':native_before,'memory_sha256_after':native_after,
    'optimizer_steps':0,'new_generations':0,'elapsed_seconds_including_short_checks':time.monotonic()-started,
    'rule':'Use native directions for step66 sensitivity checks. Do not draw a firm direction claim where implementations disagree.'})
print('NATIVE_PROJECTION_VERIFIED',flush=True)
