from pathlib import Path
import json,urllib.request,subprocess,time,os,signal,hashlib,math,importlib.metadata
D=Path('/tmp/pathdiag');O=D/'results';O.mkdir(exist_ok=True);data=json.loads((D/'inputs.json').read_text());binding=json.loads((D/'runtime-binding.json').read_text());op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def req(route,obj=None):
 r=urllib.request.Request('http://127.0.0.1:8000'+route,data=None if obj is None else json.dumps(obj,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
 with op.open(r,timeout=300) as x:return json.loads(x.read() or 'null')
def save(f,o):(O/f).write_text(json.dumps(o,ensure_ascii=False,indent=2))
from transformers import AutoTokenizer
tok=AutoTokenizer.from_pretrained('/base',local_files_only=True);template=(D/'thinking-prefill.jinja').read_text();system=(D/'system.txt').read_text();prepared=[]
for condition in [False,True]:
 messages=([{'role':'system','content':system}] if condition else [])+[{'role':'user','content':data['question']}]
 p=tok.apply_chat_template(messages,chat_template=template,tokenize=True,add_generation_prompt=True,enable_thinking=False)
 if hasattr(p,'keys'):p=p['input_ids']
 refs={**data['references'],'historical_greedy':data['historical_greedy']['original_base']['greedy_'+str(condition)]}
 for name,answer in refs.items():
  a=tok.encode(answer,add_special_tokens=False);assert tok.encode(tok.decode(p)+answer,add_special_tokens=False)==p+a
  prepared.append({'condition':condition,'reference':name,'prompt_ids':p,'target_ids':a,'text':answer,'messages':messages})
save('encoded.json',prepared)
for arm,obj in binding['adapters'].items():
 for f,v in obj['files'].items():assert hashlib.sha256((Path(obj['path'])/f).read_bytes()).hexdigest()==v['sha256']
args=binding['server_argv'];args[args.index('--chat-template')+1]=str(D/'thinking-prefill.jinja');save('server-args.json',args);save('versions.json',{x:importlib.metadata.version(x) for x in ['vllm','torch','transformers','peft']})
log=(O/'server.log').open('w');s=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
try:
 deadline=time.monotonic()+600
 while True:
  assert s.poll() is None,'server exited'
  try:req('/health');break
  except Exception:pass
  if time.monotonic()>deadline:raise RuntimeError('server timeout')
  time.sleep(3)
 records=[]
 for arm in ['original_base','step0','step2','step4','step8']:
  for i,x in enumerate(prepared):
   model=binding['aliases'][arm]
   if x['reference']=='correct':
    rendered=req('/v1/chat/completions/render',{'model':model,'messages':x['messages'],'chat_template_kwargs':{'enable_thinking':False},'max_tokens':2048})
    assert rendered['token_ids']==x['prompt_ids']
   body={'model':model,'prompt':x['prompt_ids']+x['target_ids'],'max_tokens':0,'echo':True,'logprobs':20,'temperature':0,'stream':False}
   response=req('/v1/completions',body);assert response['usage']['completion_tokens']<=1
   save(f'raw-{arm}-{i}.json',{'request':body,'response':response})
   lp=response['choices'][0]['logprobs'];n=len(x['prompt_ids']);vals=lp['token_logprobs'][n:];assert len(vals)==len(x['target_ids']) and all(v is not None for v in vals)
   rec={'usage':response['usage'],'arm':arm,'condition':x['condition'],'reference':x['reference'],'tokens':len(vals),'mean_nll':-sum(vals)/len(vals),'sum_logp':sum(vals),'token_logprobs':vals,'target_ids':x['target_ids'],'tokens_text':[tok.decode([i]) for i in x['target_ids']],'top_logprobs':lp['top_logprobs'][n:]}
   records.append(rec);save('scores.json',records);print(arm,x['condition'],x['reference'],rec['mean_nll'],flush=True)
 save('complete.json',{'forwards':len(records),'returned_new_answer_tokens':0,'internal_completion_tokens':sum(r['usage']['completion_tokens'] for r in records),'optimizer_steps':0,'training':False,'all_adapters_hash_verified':True,'all_model_prompt_ids_verified':True})
finally:
 if s.poll() is None:
  os.killpg(s.pid,signal.SIGTERM)
  try:s.wait(timeout=40)
  except subprocess.TimeoutExpired:os.killpg(s.pid,signal.SIGKILL);s.wait()
 log.close()
