from pathlib import Path
import json,urllib.request,subprocess,time,os,signal,hashlib,importlib.metadata
from transformers import AutoTokenizer
D=Path('/tmp/pathdiag');O=D/'results';O.mkdir(exist_ok=True)
def save(f,x):(O/f).write_text(json.dumps(x,ensure_ascii=False,indent=2))
b=json.loads((D/'runtime-binding.json').read_text());verified={}
for arm,a in b['adapters'].items():
 verified[arm]={}
 for f in ['adapter_config.json','adapter_model.safetensors']:
  digest=hashlib.sha256((Path(a['path'])/f).read_bytes()).hexdigest();assert digest==a['files'][f]['sha256'];verified[arm][f]=digest
save('weights-before.json',verified)
args=b['server_argv'];args=args[:args.index('--lora-modules')]+['--lora-modules']+[json.dumps({'name':arm,'path':a['path'],'base_model_name':'octa-carbon-v1'}) for arm,a in b['adapters'].items()]+['--max-cpu-loras','4'];args[args.index('--chat-template')+1]=str(D/'thinking-prefill.jinja');save('server-args.json',args);save('versions.json',{x:importlib.metadata.version(x) for x in ['vllm','torch','transformers','peft']})
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def req(route,body=None):
 r=urllib.request.Request('http://127.0.0.1:8000'+route,data=None if body is None else json.dumps(body,ensure_ascii=False).encode(),headers={'Content-Type':'application/json'})
 with op.open(r,timeout=300) as z:return json.loads(z.read() or 'null')
log_handle=(O/'server.log').open('w');s=subprocess.Popen(args,stdout=log_handle,stderr=subprocess.STDOUT,start_new_session=True)
try:
 for _ in range(200):
  assert s.poll() is None,'server exited'
  try:req('/health');break
  except Exception:time.sleep(3)
 else:raise RuntimeError('server timeout')
 tok=AutoTokenizer.from_pretrained('/base',local_files_only=True);h=json.loads((D/'historical-anchor.json').read_text());body=h['request'];q=body['messages'][-1]['content'];assert body['messages'][0]['content']==(D/'system.txt').read_text()
 p=tok.apply_chat_template(body['messages'],chat_template=(D/'thinking-prefill.jinja').read_text(),tokenize=True,add_generation_prompt=True,enable_thinking=False)
 if hasattr(p,'keys'):p=p['input_ids']
 e=json.loads((D/'encoded-parent.json').read_text());target=tok.encode(q,add_special_tokens=False)+[tok.eos_token_id];assert p==e['prompt_ids'] and target==e['historical_target_ids']+[e['eos']]
 for arm in b['adapters']:
  z=req('/v1/chat/completions/render',{**body,'model':arm});assert z['token_ids']==p
 save('encoded.json',e);probes=[]
 for arm in ['v22_50','v22_66','v26','v27','v22_66_repeat']:
  for j,tid in enumerate(target):
   z={'model':b['aliases'][arm],'prompt':p+target[:j],'max_tokens':1,'temperature':0,'logprobs':20,'return_tokens_as_token_ids':True,'return_token_ids':True,'stream':False}
   r=req('/v1/completions',z);probes.append({'path':'historical_canonical','arm':arm,'position':j,'target_id':tid,'target_text':tok.decode([tid]),'request':z,'response':r});save('probes.json',probes)
  print('probed',arm,len(target),flush=True)
 for arm,a in b['adapters'].items():
  for f,digest in verified[arm].items():assert hashlib.sha256((Path(a['path'])/f).read_bytes()).hexdigest()==digest
 save('complete.json',{'prefix_probes':len(probes),'returned_tokens':sum(x['response']['usage']['completion_tokens'] for x in probes),'new_full_answers':0,'training':False,'input_ids_verified':True,'weights_before_after_verified':True})
finally:
 if s.poll() is None:
  os.killpg(s.pid,signal.SIGTERM)
  try:s.wait(timeout=40)
  except subprocess.TimeoutExpired:os.killpg(s.pid,signal.SIGKILL);s.wait()
 log_handle.close()
