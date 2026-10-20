"""Complete the already-authorized single Full, public development and UAT restoration."""
from pathlib import Path
import subprocess,json,time,sys,hashlib,tarfile,datetime
R=Path(__file__).resolve().parent;ROOT=R.parents[2];run=R.name;K=['kubectl','--context','lmas00-direct','--request-timeout=30s','-n','swift'];prep=run+'-prep'
def call(args,**kw):return subprocess.run(K+args,check=True,**kw)
def readremote(path):return subprocess.check_output(K+['exec',prep,'--','cat',path])
def event(s):print(datetime.datetime.now(datetime.timezone.utc).isoformat()+' '+s,flush=True)
def download_evidence():
 for mode in ['smoke','full']:
  d=R/'outputs'/mode;d.mkdir(parents=True,exist_ok=True)
  for name in ['run_manifest.json','train.log','training-scalars.json']:
   try:(d/name).write_bytes(readremote('/work/'+run+'/outputs/'+mode+'/'+name))
   except subprocess.CalledProcessError:pass
try:
 while True:
  j=json.loads(subprocess.check_output(K+['get','job',run+'-full','-o','json']))
  if j['status'].get('failed'):raise RuntimeError('Full job failed; no automatic retraining')
  if j['status'].get('succeeded'):break
  result=subprocess.run(K+['exec',prep,'--','tail','-c','600','/work/'+run+'/outputs/full/train.log'],capture_output=True,text=True)
  event(result.stdout.replace('\r','\n')[-450:]);time.sleep(30)
 download_evidence();m=json.loads((R/'outputs/full/run_manifest.json').read_text());assert m['training_verified'] and m['global_step']==80 and m['status']=='TRAINED_CANDIDATE' and m['epoch']==1.0
 event('Full passed 80/80; preparing identical-template evaluation')
 call(['apply','-f',str(R/'eval-service.json')]);call(['apply','-f',str(R/'eval-pod.json')])
 call(['wait','--for=condition=Ready','pod/'+run+'-eval','--timeout=600s'])
 (R/'evaluation-binding.json').write_bytes(readremote('/work/'+run+'/evaluation-binding.json'))
 # Verify actual server prompt ids against the bound template, without generation.
 probe="""import json,hashlib,urllib.request
from pathlib import Path
from transformers import AutoTokenizer
t=Path('/input/evaluation/thinking-prefill.jinja').read_text();tok=AutoTokenizer.from_pretrained('/base',local_files_only=True);checks=[]
for mode in [True,False]:
 for model in ['t008-base','t008-new']:
  messages=[{'role':'user','content':'麻烦报一下你的模型全称。'}];b={'model':model,'messages':messages,'chat_template_kwargs':{'enable_thinking':mode},'max_tokens':16};req=urllib.request.Request('http://127.0.0.1:8000/v1/chat/completions/render',data=json.dumps(b).encode(),headers={'Content-Type':'application/json'});actual=json.load(urllib.request.urlopen(req));expect=tok.apply_chat_template(messages,chat_template=t,tokenize=True,add_generation_prompt=True,enable_thinking=mode);expect=expect['input_ids'] if hasattr(expect,'keys') else expect;assert actual['token_ids']==expect;checks.append({'model':model,'thinking':mode,'match':True})
print(json.dumps({'checks':checks,'template_sha256':hashlib.sha256(t.encode()).hexdigest()}))"""
 (R/'server-template-check.json').write_bytes(subprocess.check_output(K+['exec',run+'-eval','--','python3','-c',probe]))
 event('Server render check passed; 24 public development cases on A/B/C/D, both modes')
 call(['exec',run+'-eval','--','python3','/input/stage2/scripts/run_development.py','--endpoint','http://127.0.0.1:8000/v1','--data-root','/input/evaluation','--models','A=t008-base,C_new=t008-new','--output','/runwork/development/all-24.jsonl','--concurrency','8'])
 (R/'development').mkdir(exist_ok=True)
 for name in ['all-24.jsonl','all-24.jsonl.summary.json']:(R/'development'/name).write_bytes(readremote('/work/'+run+'/development/'+name))
 event('24-case development finished; EvalScope public IFEval/GSM8K on A and C_new')
 subprocess.run([sys.executable,str(R/'run_public_development.py')],check=True,cwd=ROOT)
 event('Public evaluation complete')
except BaseException as e:
 (R/'execution-error.json').write_text(json.dumps({'error':repr(e),'time':datetime.datetime.now(datetime.timezone.utc).isoformat()})+'\n');event('Error recorded: '+repr(e));raise
finally:
 download_evidence()
 try:
  logs=subprocess.check_output(K+['logs',run+'-eval'],stderr=subprocess.DEVNULL);(R/'eval-server.log').write_bytes(logs)
 except subprocess.CalledProcessError:pass
 event('Restoring original UAT')
 subprocess.run([sys.executable,str(R/'window.py'),'restore'],cwd=ROOT,check=True)
 call(['delete','service',run+'-eval','--ignore-not-found'])
 event('Original UAT restored and healthy')
