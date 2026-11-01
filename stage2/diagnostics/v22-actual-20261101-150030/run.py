from pathlib import Path
import json,urllib.request,subprocess,time,os,signal,hashlib,math
import torch
from safetensors.torch import load_file,save_file
from transformers import AutoTokenizer
D=Path('/tmp/pathdiag');O=D/'results';O.mkdir(exist_ok=True)
def save(f,x):(O/f).write_text(json.dumps(x,ensure_ascii=False,indent=2))
b=json.loads((D/'runtime-binding.json').read_text());a=b['adapters']['v22'];src=Path(a['path']);zero=D/'zero';zero.mkdir()
for f,v in a['files'].items():assert hashlib.sha256((src/f).read_bytes()).hexdigest()==v['sha256']
t=load_file(str(src/'adapter_model.safetensors'));counts={}
for k in t:
 if 'lora_B' in k:t[k]=torch.zeros_like(t[k]);counts[k]=t[k].numel()
assert len(counts)>0
save_file(t,str(zero/'adapter_model.safetensors'));(zero/'adapter_config.json').write_bytes((src/'adapter_config.json').read_bytes());save('zero-audit.json',{'zero_B_count':len(counts),'only_B_changed':True,'source':a,'config_sha256':hashlib.sha256((zero/'adapter_config.json').read_bytes()).hexdigest()});del t
args=b['server_argv'];i=args.index('--lora-modules');args=args[:i]+['--lora-modules',json.dumps({'name':'zero','path':str(zero),'base_model_name':'octa-carbon-v1'}),json.dumps({'name':'v22','path':str(src),'base_model_name':'octa-carbon-v1'}),'--max-cpu-loras','2'];args[args.index('--chat-template')+1]=str(D/'thinking-prefill.jinja');save('server-args.json',args)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def req(route,body=None):
 r=urllib.request.Request('http://127.0.0.1:8000'+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
 try:
  with op.open(r,timeout=300) as z:return json.loads(z.read())
 except urllib.error.HTTPError as e:
  print(e.code,e.read().decode(),flush=True);raise
f=(O/'server.log').open('w');s=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
try:
 for _ in range(200):
  assert s.poll() is None,'server exited'
  try:req('/health');break
  except Exception:time.sleep(3)
 else:raise RuntimeError('server timeout')
 tok=AutoTokenizer.from_pretrained('/base',local_files_only=True);h=json.loads((D/'historical-anchor.json').read_text());body=h['request'];q=body['messages'][-1]['content'];assert body['messages'][0]['content']==(D/'system.txt').read_text()
 p=tok.apply_chat_template(body['messages'],chat_template=(D/'thinking-prefill.jinja').read_text(),tokenize=True,add_generation_prompt=True,enable_thinking=False)
 if hasattr(p,'keys'):p=p['input_ids']
 save('encoded.json',{'prompt_ids':p,'question':q,'historical_target_ids':tok.encode(q,add_special_tokens=False),'eos':tok.eos_token_id})
 for arm in ['zero','v22']:
  z=req('/v1/chat/completions/render',{**body,'model':arm});assert z['token_ids']==p
 rows=[]
 for n in range(10):
  for arm in ['zero','v22']:
   z={**body,'model':arm,'seed':2026110100+n,'logprobs':True,'top_logprobs':20,'return_token_ids':True,'return_tokens_as_token_ids':True}
   r=req('/v1/chat/completions',z);rows.append({'arm':arm,'repeat':n,'request':z,'response':r});save('generations.json',rows);print('generation',arm,n,r['choices'][0]['message'].get('content'),flush=True)
 # Freeze historical canonical path and, if available, actual token paths of reproduced exact echoes.
 target=tok.encode(q,add_special_tokens=False)+[tok.eos_token_id];paths={'historical_canonical':target}
 for r in rows:
  c=r['response']['choices'][0]
  if c['message'].get('content')==q:
   ids=c.get('token_ids')
   if ids:
    if ids[-1]!=tok.eos_token_id:ids=ids+[tok.eos_token_id]
    if ids not in paths.values():paths['actual_'+r['arm']+'_'+str(r['repeat'])]=ids
 save('paths.json',paths)
 probes=[]
 for name,target in paths.items():
  for arm in ['zero','v22','zero_repeat']:
   for j,tid in enumerate(target):
    z={'model':'zero' if arm=='zero_repeat' else arm,'prompt':p+target[:j],'max_tokens':1,'temperature':0,'logprobs':20,'return_tokens_as_token_ids':True,'return_token_ids':True,'stream':False}
    r=req('/v1/completions',z);probes.append({'path':name,'arm':arm,'position':j,'target_id':tid,'target_text':tok.decode([tid]),'request':z,'response':r});save('probes.json',probes)
   print('probed',name,arm,len(target),flush=True)
 save('complete.json',{'generations':len(rows),'prefix_probes':len(probes),'training':False,'paths':list(paths),'input_verified':True})
finally:
 if s.poll() is None:
  os.killpg(s.pid,signal.SIGTERM)
  try:s.wait(timeout=40)
  except subprocess.TimeoutExpired:os.killpg(s.pid,signal.SIGKILL);s.wait()
 f.close()
