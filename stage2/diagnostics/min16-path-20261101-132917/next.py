from pathlib import Path
import json,urllib.request,subprocess,os,signal,time
D=Path('/tmp/pathdiag');O=D/'next';O.mkdir(exist_ok=True);b=json.loads((D/'runtime-binding.json').read_text());encoded=json.loads((D/'results/encoded.json').read_text());op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def req(route,body=None):
 r=urllib.request.Request('http://127.0.0.1:8000'+route,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 with op.open(r,timeout=300) as p:return json.loads(p.read() or 'null')
args=json.loads((D/'results/server-args.json').read_text());f=(O/'server.log').open('w');s=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
try:
 for _ in range(200):
  assert s.poll() is None
  try:req('/health');break
  except Exception:time.sleep(3)
 else:raise RuntimeError('server timeout')
 rows=[]
 for arm in ['original_base','step0','step2','step4','step8']:
  for c in [False,True]:
   e=next(x for x in encoded if x['condition']==c and x['reference']=='echo_no_system')
   for name,n in [('start',0),('after_shared27',27),('before_handback',40)]:
    body={'model':b['aliases'][arm],'prompt':e['prompt_ids']+e['target_ids'][:n],'max_tokens':1,'temperature':0,'logprobs':20,'stream':False};r=req('/v1/completions',body);rows.append({'arm':arm,'condition':c,'probe':name,'request':body,'response':r});(O/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2));print(arm,c,name,r['choices'][0]['text'],flush=True)
 (O/'complete.json').write_text(json.dumps({'requests':len(rows),'returned_single_tokens':sum(x['response']['usage']['completion_tokens'] for x in rows),'new_full_answers':0,'training':False}))
finally:
 if s.poll() is None:
  os.killpg(s.pid,signal.SIGTERM)
  try:s.wait(timeout=40)
  except subprocess.TimeoutExpired:os.killpg(s.pid,signal.SIGKILL);s.wait()
