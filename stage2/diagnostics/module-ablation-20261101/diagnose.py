"""Inference-only module ablation. Base/adapters mounted read-only; no optimizer."""
import argparse, ast, hashlib, importlib.metadata as md, inspect, json, math, os, time
from pathlib import Path

os.environ.setdefault('TORCHINDUCTOR_CACHE_DIR','/tmp/torchinductor_diag')
D=Path('/tmp/diag'); I=D/'inputs'; O=D/'results'; BASE=Path('/base')
O.mkdir(exist_ok=True)
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        while b:=f.read(8*1024*1024): h.update(b)
    return h.hexdigest()
def save(n,o): (O/n).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def append(n,o):
    with (O/n).open('a') as f:f.write(json.dumps(o,ensure_ascii=False,allow_nan=False)+'\n')
def ih(ids): return hashlib.sha256(json.dumps(ids).encode()).hexdigest()
def load_filter(torch):
    tree=ast.parse((I/'vllm_topk_topp_source.py').read_text())
    node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='apply_top_k_top_p_pytorch')
    scope={'torch':torch};exec(compile(ast.Module(body=[node],type_ignores=[]),'<frozen-vllm-filter>','exec'),scope)
    fn=scope[node.name]
    assert torch.isfinite(fn(torch.tensor([[4.,3.,2.,1.]]),torch.tensor([2]),torch.tensor([.8]))).tolist()==[[True,True,False,False]]
    return fn

def prepare():
    import torch
    from transformers import AutoTokenizer
    from peft.tuners.lora.layer import Linear
    p=read(I/'protocol.json')
    for n,m in read(I/'manifest.json')['files'].items():assert sha(I/n)==m['sha256'],n
    versions={k:md.version(k) for k in p['versions']};assert versions==p['versions'],versions
    for m in read(I/'base-files.json'):assert sha(BASE/m['path'])==m['sha256'],m['path']
    for n,m in p['adapter']['files'].items():assert sha(Path(p['adapter']['path'])/n)==m['sha256'],n
    source=inspect.getsource(Linear.forward)
    assert 'self.scaling[active_adapter]' in source and 'self.disable_adapters' in source
    (O/'peft-linear-forward.py').write_text(source)
    tok=AutoTokenizer.from_pretrained(BASE,local_files_only=True)
    template=(I/'thinking-prefill.jinja').read_text();system=(I/'system.txt').read_text()
    cases=read(I/'cases.json')['cases'];enc=[];details=[]
    for c in cases:
        for with_system in [False,True]:
            messages=([{'role':'system','content':system}] if with_system else [])+[{'role':'user','content':c['question']}]
            rendered=tok.apply_chat_template(messages,chat_template=template,tokenize=False,add_generation_prompt=True,enable_thinking=False)
            prefix=tok.encode(rendered,add_special_tokens=False);targets={}
            for ref,answer in c['references'].items():
                whole=tok(rendered+answer,add_special_tokens=False,return_offsets_mapping=True)
                assert whole['input_ids'][:len(prefix)]==prefix,(c['id'],ref,'BPE prefix mismatch')
                target=whole['input_ids'][len(prefix):][:p['max_target_tokens']]
                assert target and len(prefix)+len(target)<=p['max_context_tokens']
                name='能碳章鱼垂直大模型';start=(rendered+answer).find(name,len(rendered))
                offsets=whole['offset_mapping'][len(prefix):len(prefix)+len(target)]
                name_positions=[j for j,(a,b) in enumerate(offsets) if start>=0 and b>start and a<start+len(name)]
                targets[ref]={'ids':target,'product_positions':name_positions,'complete_reference':len(whole['input_ids'])-len(prefix)==len(target)}
                details.append({'case_id':c['id'],'system':with_system,'reference':ref,'prefix_sha256':ih(prefix),'prompt_tokens':len(prefix),'target_tokens':len(target),'complete_reference':targets[ref]['complete_reference']})
            assert len(prefix)+p['sampling']['max_new_tokens']<=p['max_context_tokens']
            enc.append({'case':c,'system':with_system,'messages':messages,'rendered':rendered,'prefix':prefix,'targets':targets})
    assert len(enc)==32 and len(details)*4==p['expected_scores']==256
    load_filter(torch)
    save('encoding-details.json',details)
    save('encoding-check.json',{'verified':True,'cases':16,'contexts':32,'scores':256,'generations':128,'versions':versions,'all_hashes_match':True,'BPE_boundaries_match':True,'max_prompt_tokens':max(len(x['prefix']) for x in enc),'system_sha256':sha(I/'system.txt'),'template_sha256':sha(I/'thinking-prefill.jinja'),'script_sha256':sha(Path(__file__)),'peft_forward_sha256':sha(O/'peft-linear-forward.py')})
    print('CPU_CHECK_OK',flush=True)
    return tok,p,enc

def run():
    import torch
    from transformers import AutoModelForCausalLM, GenerationConfig, LogitsProcessor
    from peft import PeftModel
    from peft.tuners.lora.layer import LoraLayer
    tok,p,enc=prepare();assert torch.cuda.is_available()
    assert not (O/'scores.jsonl').exists() and not (O/'generations.jsonl').exists(),'No overwrite'
    t0=time.monotonic();fn=load_filter(torch);cfg=p['sampling']
    model=AutoModelForCausalLM.from_pretrained(BASE,local_files_only=True,dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa')
    model=PeftModel.from_pretrained(model,p['adapter']['path'],adapter_name='probe',is_trainable=False,local_files_only=True)
    model.eval();model.requires_grad_(False);assert not any(x.requires_grad for x in model.parameters())
    modules=[]
    for name,m in model.named_modules():
        if isinstance(m,LoraLayer) and 'probe' in m.lora_A:
            leaf=name.rsplit('.',1)[1];kind='attention' if leaf in {'q_proj','k_proj','v_proj','o_proj'} else 'mlp'
            assert leaf in {'q_proj','k_proj','v_proj','o_proj','gate_proj','up_proj','down_proj'} and not m.merged
            modules.append((name,m,kind,float(m.scaling['probe'])))
    assert len(modules)==252 and sum(k=='attention' for _,_,k,_ in modules)==144
    def digest():
        h=hashlib.sha256()
        for name,param in model.named_parameters():
            if '.lora_' in name:h.update(name.encode());h.update(param.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
        return h.hexdigest()
    before=digest()
    def set_arm(arm):
        active=[]
        for name,m,kind,original in modules:
            enabled=arm=='all_on' or arm==kind+'_only'
            m.scaling['probe']=original if enabled else 0.0
            if enabled:active.append(name)
        assert len(active)=={'all_on':252,'attention_only':144,'mlp_only':108,'all_off':0}[arm]
        save('modules-'+arm+'.json',{'arm':arm,'active_modules':active,'disabled':252-len(active),'original_scale_values':sorted({s for _,_,_,s in modules})})
    def logits(prefix,target=None):
        target=target or [];x=torch.tensor([prefix+target[:-1]],device='cuda')
        with torch.inference_mode():out=model(input_ids=x,attention_mask=torch.ones_like(x),use_cache=False,logits_to_keep=max(1,len(target)))
        return out.logits[0].float()
    set_arm('all_off');z=logits(enc[0]['prefix'])
    with model.disable_adapter():z_disabled=logits(enc[0]['prefix'])
    assert torch.equal(z,z_disabled),'Zero scaling must equal disabling adapter'
    save('ablation-check.json',{'zero_scaling_equals_disabled':True,'max_logit_difference':(z-z_disabled).abs().max().item(),'attention_modules':144,'mlp_modules':108,'total_modules':252,'adapter_memory_sha256_before':before})
    del z,z_disabled
    stop_ids=read(BASE/'generation_config.json')['eos_token_id'];stop_ids=[stop_ids] if isinstance(stop_ids,int) else stop_ids
    class FrozenFilter(LogitsProcessor):
        def __call__(self,input_ids,scores):
            b=scores.shape[0]
            return fn(scores.float()/cfg['temperature'],torch.full((b,),cfg['top_k'],device=scores.device),torch.full((b,),cfg['top_p'],device=scores.device))
    gc=GenerationConfig(do_sample=True,temperature=1.0,top_k=0,top_p=1.0,repetition_penalty=1.0,max_new_tokens=cfg['max_new_tokens'],eos_token_id=stop_ids,pad_token_id=tok.pad_token_id or stop_ids[0],use_cache=True)
    scores=gens=0
    for arm in p['arms']:
        set_arm(arm)
        for e in enc:
            c=e['case'];prefix=e['prefix'];first=logits(prefix)[-1]
            for ref,target_info in e['targets'].items():
                target=target_info['ids'];ls=logits(prefix,target);ls[0]=first
                y=torch.tensor(target,device='cuda');lp=ls.log_softmax(-1).gather(1,y[:,None]).squeeze(1)
                filtered=fn(ls.clone()/cfg['temperature'],torch.full((len(y),),cfg['top_k'],device='cuda'),torch.full((len(y),),cfg['top_p'],device='cuda'))
                probs=filtered.softmax(-1).gather(1,y[:,None]).squeeze(1).tolist();nps=target_info['product_positions']
                append('scores.jsonl',{'arm':arm,'case_id':c['id'],'category':c['category'],'system':e['system'],'reference':ref,'prefix_sha256':ih(prefix),'target_sha256':ih(target),'target_text':tok.decode(target),'tokens':len(target),'complete_reference':target_info['complete_reference'],'mean_nll':-lp.mean().item(),'sum_logp':lp.sum().item(),'product_name_nll':-lp[nps].mean().item() if nps else None,'product_token_count':len(nps),'filtered_zero_tokens':sum(v==0 for v in probs),'filtered_first_probability':probs[0],'token_logp':lp.tolist(),'filtered_probabilities':probs})
                scores+=1
            del ls,lp,filtered,y,first
            if e['system']!=c['generation_system']:continue
            for seed in p['seeds']:
                torch.manual_seed(seed);torch.cuda.manual_seed_all(seed);start=time.monotonic()
                x=torch.tensor([prefix],device='cuda')
                with torch.inference_mode():out=model.generate(input_ids=x,attention_mask=torch.ones_like(x),generation_config=gc,logits_processor=[FrozenFilter()])
                ids=out[0,len(prefix):].tolist();stopped=bool(ids and ids[-1] in stop_ids)
                answer=tok.decode(ids[:-1] if stopped else ids,skip_special_tokens=False)
                append('generations.jsonl',{'arm':arm,'case_id':c['id'],'category':c['category'],'system':e['system'],'seed':seed,'messages':e['messages'],'prefix_sha256':ih(prefix),'prompt_tokens':len(prefix),'token_ids':ids,'answer':answer,'output_tokens':len(ids),'finish_reason':'stop' if stopped else 'length','seconds':time.monotonic()-start})
                gens+=1
                save('progress.json',{'arm':arm,'scores':scores,'generations':gens,'elapsed_seconds':time.monotonic()-t0})
                print(json.dumps({'arm':arm,'case_id':c['id'],'seed':seed,'scores':scores,'generated':gens,'tokens':len(ids),'elapsed_seconds':round(time.monotonic()-t0,1)}),flush=True)
                del x,out
    set_arm('all_on');after=digest();assert after==before
    for n,m in p['adapter']['files'].items():assert sha(Path(p['adapter']['path'])/n)==m['sha256']
    assert scores==p['expected_scores'] and gens==p['expected_generations']
    save('completed.json',{'complete':True,'scores':scores,'generations':gens,'seconds':time.monotonic()-t0,'adapter_memory_unchanged':True,'adapter_memory_sha256':after,'scores_sha256':sha(O/'scores.jsonl'),'generations_sha256':sha(O/'generations.jsonl'),'gpu_peak_allocated_bytes':torch.cuda.max_memory_allocated(),'training':False,'judge_calls':0,'deployment':False,'uat_restore':False})
    print('DIAGNOSTIC_COMPLETED',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cpu-only',action='store_true');args=parser.parse_args()
    prepare() if args.cpu_only else run()
