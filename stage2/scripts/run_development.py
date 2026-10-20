"""Run public development prompts only against the task-owned evaluation endpoint."""
import argparse,concurrent.futures,json,time,urllib.request,datetime,threading
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--endpoint',required=True);p.add_argument('--data-root',required=True);p.add_argument('--models',required=True,help='A=t008-base,C_old=t008-old or C_new=t008-new');p.add_argument('--output',required=True);p.add_argument('--cases');p.add_argument('--no-system-variants',action='store_true');p.add_argument('--concurrency',type=int,default=8);a=p.parse_args()
r=Path(a.data_root);protocol=json.loads((r/'protocol.json').read_text());system=(r/'custom-system.txt').read_text();cases=[json.loads(x) for x in (r/'development-24.jsonl').read_text().splitlines()]
if a.cases:cases=[x for x in cases if x['id'] in a.cases.split(',')]
conditions=[]
for item in a.models.split(','):
 cond,model=item.split('=',1);conditions.append((cond,model,None))
 if not a.no_system_variants:conditions.append(({'A':'B','C_old':'D_old','C_new':'D_new'}[cond],model,system))
out=Path(a.output);out.parent.mkdir(parents=True,exist_ok=True)
if out.exists():raise FileExistsError(out)
lock=threading.Lock()
def generate(case,cond,model,sysmsg,mode):
 messages=[{'role':'system','content':sysmsg}] if sysmsg else [];turns=[];start=time.monotonic();cfg=protocol['modes'][mode]
 for text in case['user_turns']:
  messages.append({'role':'user','content':text});body={'model':model,'messages':messages,'temperature':cfg['temperature'],'top_p':cfg['top_p'],'top_k':cfg['top_k'],'max_tokens':cfg['max_tokens'],'min_p':cfg['min_p'],'seed':42,'chat_template_kwargs':{'enable_thinking':cfg['enable_thinking']}}
  try:
   req=urllib.request.Request(a.endpoint.rstrip('/')+'/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
   with urllib.request.urlopen(req,timeout=600) as response:data=json.load(response)
   choice=data['choices'][0];msg=choice['message'];content=msg.get('content') or '';turns.append({'user':text,'assistant':content,'reasoning':msg.get('reasoning',msg.get('reasoning_content')),'finish_reason':choice['finish_reason'],'usage':data.get('usage',{})});messages.append({'role':'assistant','content':content})
  except Exception as e:turns.append({'user':text,'error':type(e).__name__+': '+str(e)});break
 result={'id':case['id'],'category':case['category'],'condition':cond,'model':model,'mode':mode,'turns':turns,'seconds':round(time.monotonic()-start,3)}
 with lock:
  with out.open('a') as f:f.write(json.dumps(result,ensure_ascii=False)+'\n')
  print(json.dumps({'id':case['id'],'condition':cond,'mode':mode,'errors':sum('error' in t for t in turns),'seconds':result['seconds']}),flush=True)
 return result
jobs=[(c,cond,model,sysmsg,mode) for c in cases for cond,model,sysmsg in conditions for mode in protocol['modes']]
t0=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=a.concurrency) as pool:results=list(pool.map(lambda x:generate(*x),jobs))
summary={'cases':len(results),'requests':sum(len(x['turns']) for x in results),'errors':sum('error' in t for x in results for t in x['turns']),'empty_answers':sum(not t.get('assistant') for x in results for t in x['turns'] if 'error' not in t),'length_finishes':sum(t.get('finish_reason')=='length' for x in results for t in x['turns']),'output_tokens':sum(t.get('usage',{}).get('completion_tokens',0) for x in results for t in x['turns']),'wall_seconds':time.monotonic()-t0,'concurrency':a.concurrency}
Path(str(out)+'.summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary),flush=True)
