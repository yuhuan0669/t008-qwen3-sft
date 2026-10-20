#!/usr/bin/env python3
"""Generate real evaluation outputs; does NOT assign correctness or pass/fail.
Test JSONL: {id, messages:[...last user...]} OR {id,user_turns:[...]},
optional category. Expected answers/rubrics, if present, are never sent to model.
"""
from __future__ import annotations
import argparse, hashlib, json, time, datetime, sys
from pathlib import Path
from run_identity import base_fingerprint

def file_sha(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1024*1024),b''): h.update(part)
    return h.hexdigest()

def verify_base_model(model_dir, run):
    actual=base_fingerprint(model_dir)
    if actual!=run.get('base_files'):
        raise RuntimeError('Actual base model files do not match frozen training hashes')
    return hashlib.sha256(json.dumps(actual,ensure_ascii=False,sort_keys=True).encode()).hexdigest()


def classify_answer(raw, think, special_markers):
    unexpected=not think and ('<think>' in raw or '</think>' in raw)
    closed='</think>' in raw
    answer=raw.split('</think>',1)[1] if closed else ('' if think or unexpected else raw)
    for marker in special_markers:
        if marker: answer=answer.replace(marker,'')
    return answer.strip(), closed, unexpected


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',required=True); p.add_argument('--adapter')
    p.add_argument('--cases',required=True); p.add_argument('--output',required=True)
    p.add_argument('--system-file'); p.add_argument('--run-manifest',required=True); p.add_argument('--mode',choices=['thinking','nonthinking'],required=True)
    p.add_argument('--seed',type=int,default=42);p.add_argument('--max-new-tokens',type=int)
    a=p.parse_args()
    run=json.loads(Path(a.run_manifest).read_text(encoding='utf-8'))
    if run.get('status')!='TRAINED_CANDIDATE':
        raise RuntimeError('Independent evaluation requires the completed FULL candidate, not smoke')
    if not run.get('clearml_output_model_id') or not run.get('adapter_package_sha256'):
        raise RuntimeError('Run manifest lacks registered output Adapter')
    if a.adapter:
        adapter_path=Path(a.adapter)
        registered_files=run.get('adapter_files',{})
        if not registered_files: raise RuntimeError('No registered Adapter file digest list')
        for name,record in registered_files.items():
            candidate=adapter_path/name
            if not candidate.is_file() or file_sha(candidate)!=record['sha256']:
                raise RuntimeError(f'Adapter missing or mismatched: {name}')
        if adapter_path.resolve()!=Path(run['checkpoint']).resolve():
            raise RuntimeError('Adapter is not the frozen full-run checkpoint')
    base_hash=verify_base_model(a.model,run)
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed
    if not torch.cuda.is_available(): raise RuntimeError('Run only in the authorized GPU evaluation container')
    cases=[json.loads(s) for s in Path(a.cases).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    if len({x['id'] for x in cases})!=len(cases): raise ValueError('Duplicate test IDs')
    if Path(a.output).exists(): raise FileExistsError(a.output)
    tok=AutoTokenizer.from_pretrained(a.model,local_files_only=True)
    model=AutoModelForCausalLM.from_pretrained(a.model,local_files_only=True,
                 torch_dtype=torch.bfloat16,device_map={'':0},attn_implementation='sdpa')
    if a.adapter:
        from peft import PeftModel
        model=PeftModel.from_pretrained(model,a.adapter,is_trainable=False,local_files_only=True)
    model.eval()
    system=Path(a.system_file).read_text(encoding='utf-8') if a.system_file else None
    think=a.mode=='thinking';cap=a.max_new_tokens or (4096 if think else 1024)
    eos_ids=model.generation_config.eos_token_id
    eos_ids=eos_ids if isinstance(eos_ids,list) else [eos_ids]
    Path(a.output).parent.mkdir(parents=True,exist_ok=True)
    with open(a.output,'x',encoding='utf-8') as out:
        for row in cases:
            if 'user_turns' in row:
                hist=[]; turns=row['user_turns']
            else:
                hist=[dict(m) for m in row['messages'][:-1]]
                if row['messages'][-1]['role']!='user': raise ValueError('Case must end in user')
                turns=[row['messages'][-1]['content']]
            if any(m['role']=='system' for m in hist):
                raise ValueError('Case-embedded system prompt would confound A/B/C/D; use --system-file')
            for step,user in enumerate(turns):
                hist.append({'role':'user','content':user})
                ms=([{'role':'system','content':system}] if system else [])+hist
                text=tok.apply_chat_template(ms,tokenize=False,add_generation_prompt=True,enable_thinking=think)
                inputs=tok(text,return_tensors='pt',add_special_tokens=False).to(model.device)
                window=getattr(model.config,'max_position_embeddings',None)
                if window and inputs['input_ids'].shape[-1]+cap>window: raise ValueError('Evaluation context exceeds model window')
                local_seed=a.seed+int(hashlib.sha256(f"{row['id']}:{step}".encode()).hexdigest()[:8],16)%100000
                set_seed(local_seed); start=time.monotonic()
                with torch.inference_mode():
                    result=model.generate(**inputs,max_new_tokens=cap,do_sample=True,
                           temperature=0.6 if think else 0.7,top_p=0.95 if think else 0.8,
                           top_k=20,min_p=0.0,pad_token_id=tok.pad_token_id or tok.eos_token_id)
                ids=result[0,inputs['input_ids'].shape[-1]:].tolist()
                raw=tok.decode(ids,skip_special_tokens=False)
                # Unexpected think tags invalidate a nonthinking final answer.
                answer,closed,unexpected=classify_answer(raw,think,
                    [tok.eos_token,tok.pad_token,'<|im_end|>','<|endoftext|>'])
                ended=bool(ids and ids[-1] in eos_ids)
                rec={'id':row['id'],'turn':step,'category':row.get('category'),
                     'mode':a.mode,'adapter':a.adapter,'system_used':system is not None,
                     'seed':local_seed,'input_messages':ms,'raw_output':raw,'final_answer':answer,
                     'output_tokens':len(ids),'finished_eos':ended,
                     'hit_length_limit':len(ids)>=cap and not ended,
                     'thinking_closed':closed if think else None,
                     'unexpected_think_tag':unexpected,
                     'elapsed_seconds':time.monotonic()-start}
                out.write(json.dumps(rec,ensure_ascii=False)+'\n');out.flush()
                if not answer: break  # mark incomplete; don't invent an assistant turn
                hist.append({'role':'assistant','content':answer})
    # Metadata stays with the result in controlled storage. It never contains answers or test text.
    metadata={'schema':'identity-eval-v1.2','run_id':run['run_id'],
              'train_task_id':run.get('clearml_task_id'),
              'run_manifest_sha256':file_sha(a.run_manifest),
              'base_manifest_files_sha256':base_hash,
              'adapter_package_sha256':run.get('adapter_package_sha256'),
              'cases_sha256':file_sha(a.cases),'cases_count':len(cases),
              'system_sha256':file_sha(a.system_file) if a.system_file else None,
              'mode':a.mode,'seed':a.seed,'max_new_tokens':cap,
              'temperature':0.6 if think else 0.7,
              'top_p':0.95 if think else 0.8,'top_k':20,
              'output_sha256':file_sha(a.output),
              'adapter_used':bool(a.adapter),'inference_engine':'transformers+peft',
              'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    Path(a.output+'.meta.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    # Labels are evaluated separately by deterministic checks and a non-author reviewer.
if __name__=='__main__': main()
