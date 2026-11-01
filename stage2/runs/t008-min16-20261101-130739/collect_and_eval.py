from pathlib import Path
import json,hashlib,subprocess,time,tarfile
D=Path(__file__).resolve().parent;E=D/'evaluation';K=['kubectl','--context','lmas00-direct','--request-timeout=30s'];k=K+['-n','swift'];prep=D.name+'-prep'
def read(path):return subprocess.check_output(k+['exec',prep,'--','cat',path])
while True:
 j=json.loads(subprocess.check_output(k+['get','job',D.name+'-full3','-o','json']))
 if j['status'].get('failed'):raise RuntimeError('Training failed; inspect before any retry')
 if j['status'].get('succeeded'):break
 time.sleep(10)
(D/'train.log').write_bytes(subprocess.check_output(k+['logs','job/'+D.name+'-full3']))
for f in ['training-complete.json','updates.jsonl','preclip.jsonl','gpu-before.txt']+[f'observe-{x}.json' for x in [0,1,2,4,8]]:(D/f).write_bytes(read('/work/'+D.name+'/'+f))
assert json.loads((D/'training-complete.json').read_text())['steps']==8
b=json.loads((D/'eval-base-binding.json').read_text());argv=b['server_argv'];argv=argv[:argv.index('--lora-modules')]+['--lora-modules']
for step in [0,2,4,8]:
 path='/work/'+D.name+'/checkpoint-'+str(step);files={}
 for f in ['adapter_config.json','adapter_model.safetensors']:
  raw=read(path+'/'+f);files[f]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};out=D/'adapters'/f'checkpoint-{step}';out.mkdir(parents=True,exist_ok=True);(out/f).write_bytes(raw)
 alias='step'+str(step);mounted=path.replace('/work/','/models-work/');b['adapters'][alias]={'path':mounted,'files':files};argv.append(json.dumps({'name':b['aliases'][alias],'path':mounted,'base_model_name':'octa-carbon-v1'}))
argv+=['--max-cpu-loras','4'];b['server_argv']=argv;(E/'runtime-binding.json').write_text(json.dumps(b,indent=2))
print('Training and four checkpoint hashes verified',flush=True)
subprocess.run(k+['create','-f',str(D/'eval-pod.json')],check=True)
for _ in range(12):
 p=subprocess.run(k+['wait','--for=condition=Ready','pod/'+D.name+'-eval','--timeout=30s'],capture_output=True)
 if p.returncode==0:break
else:raise RuntimeError('Eval pod not ready')
with subprocess.Popen(['tar','-C',str(E),'-cf','-',*[p.name for p in E.iterdir()]],stdout=subprocess.PIPE) as sender:
 subprocess.run(k+['exec','-i',D.name+'-eval','--','tar','-C','/runwork/evaluation','-xf','-'],stdin=sender.stdout,check=True);sender.stdout.close();assert sender.wait()==0
with (E/'runner.log').open('w') as log:p=subprocess.run(k+['exec',D.name+'-eval','--','python3','/runwork/evaluation/run.py'],stdout=log,stderr=subprocess.STDOUT)
print('Evaluation exit',p.returncode,flush=True)
with (D/'evaluation-raw.tar').open('wb') as f:subprocess.run(k+['exec',prep,'--','tar','-C','/work/'+D.name,'-cf','-','evaluation'],stdout=f,check=True)
with tarfile.open(D/'evaluation-raw.tar') as t:t.extractall(D,filter='data')
print('Collected evaluation',flush=True)
