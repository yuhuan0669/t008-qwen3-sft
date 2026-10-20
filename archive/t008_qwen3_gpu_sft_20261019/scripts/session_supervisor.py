"""One authorized GPU window: pause -> Smoke -> Full -> restore, including failures.
Uses existing local kubectl authority; creates no RBAC/Secret or release changes.
"""
from __future__ import annotations
import datetime,hashlib,json,math,pathlib,signal,subprocess,sys,time
ROOT=pathlib.Path(__file__).resolve().parents[1]
AUTH=json.loads((ROOT/'evidence/owner_authorization.json').read_text());RUN=AUTH['run_id']
PREP=RUN+'-prep';WORK='/work/'+RUN
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
STATE={'run_id':RUN,'phase':'PREPARING','events':[],'gpu_window_started':False,'vllm_restored':False}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def event(phase,**kwargs):
 STATE.update(phase=phase,updated_at_utc=now(),**kwargs)
 STATE['events'].append({'at_utc':now(),'phase':phase,**kwargs})
 try:(ROOT/'evidence/session_state.json').write_text(json.dumps(STATE,ensure_ascii=False,indent=2)+'\n')
 except OSError:pass  # Recovery must not depend on a writable evidence disk.
 try:print(json.dumps({'phase':phase,**kwargs},ensure_ascii=False),flush=True)
 except OSError:pass
def cmd(*args,timeout=45,check=True):
 p=subprocess.run(K+list(args),capture_output=True,text=True,timeout=timeout)
 if check and p.returncode:raise RuntimeError('kubectl '+args[0]+' failed: '+p.stderr[:500])
 return p

def get(*args):return json.loads(cmd(*args,'-o','json').stdout)
def read_file(path):return json.loads(cmd('-n','swift','exec',PREP,'--','cat',path).stdout)
def spec_hash(spec):return hashlib.sha256(json.dumps(spec,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def capture_job(mode):
 name=RUN+'-'+mode
 job=get('-n','swift','get','job',name)
 pods=get('-n','swift','get','pods','-l','job-name='+name)
 (ROOT/'evidence'/('actual-job-'+mode+'.json')).write_text(json.dumps(job,indent=2)+'\n')
 (ROOT/'evidence'/('actual-pods-'+mode+'.json')).write_text(json.dumps(pods,indent=2)+'\n')
 logs=cmd('-n','swift','logs','job/'+name,'--all-containers=true',timeout=60,check=False)
 (ROOT/'evidence'/('k8s-'+mode+'.log')).write_text(logs.stdout)
 return job,pods

def wait_job(mode,seconds):
 deadline=time.monotonic()+seconds;last_phase=None
 while time.monotonic()<deadline:
  job=get('-n','swift','get','job',RUN+'-'+mode)
  statuses={c['type']:c.get('status') for c in job.get('status',{}).get('conditions',[])}
  if statuses.get('Failed')=='True':
   capture_job(mode);raise RuntimeError(mode+' Job failed; see preserved pod/log evidence')
  if statuses.get('Complete')=='True':
   capture_job(mode);return
  pods=get('-n','swift','get','pods','-l','job-name='+RUN+'-'+mode)
  phases=[p['status'].get('phase') for p in pods['items']]
  if phases!=last_phase:
   event(mode.upper()+'_RUNNING',pod_phases=phases);last_phase=phases
  time.sleep(10)
 raise TimeoutError(mode+' bounded runtime exceeded')

def stage_verified(mode):
 data=read_file(WORK+'/outputs/'+mode+'/run_manifest.json')
 if data.get('training_exit_code')!=0 or data.get('metrics_registration_error'):
  raise RuntimeError(mode+' wrapper/training did not pass')
 step=int(pathlib.PurePosixPath(data['checkpoint']).name.split('-')[-1])
 cp='/work/'+RUN+'/outputs/'+mode+'/checkpoints/'+str(pathlib.PurePosixPath(data['checkpoint']).relative_to('/runwork/outputs/'+mode+'/checkpoints'))
 state=read_file(cp+'/trainer_state.json')
 if mode=='smoke':
  if data.get('status')!='SMOKE_COMPLETE' or step!=3 or state.get('global_step')!=3 or state.get('max_steps')!=3:
   raise RuntimeError('Smoke must prove actual 3/3 optimizer steps')
 else:
  if (data.get('status')!='TRAINED_CANDIDATE' or step!=state.get('global_step') or step!=state.get('max_steps')
      or float(state.get('epoch') or 0)<0.999 or not data.get('clearml_output_model_id')
      or data.get('adapter_package_sha256')!=data.get('clearml_model_readback_sha256')):
   raise RuntimeError('Full terminal/checkpoint/remote model evidence incomplete')
 for row in state.get('log_history',[]):
  for key in ('loss','train_loss','grad_norm'):
   if key in row and not math.isfinite(float(row[key])):
    raise RuntimeError(mode+' non-finite '+key)
 finite_query="""import hashlib,json,pathlib,sys,torch
from safetensors import safe_open
p=pathlib.Path(sys.argv[1]);config=json.loads((p/'adapter_config.json').read_text())
assert config['r']==8 and config['lora_alpha']==32 and config['peft_type']=='LORA'
f=p/'adapter_model.safetensors';assert f.is_file() and f.stat().st_size>0
with safe_open(f,framework='pt',device='cpu') as reader:
 keys=list(reader.keys());assert keys and any('lora_A' in k for k in keys) and any('lora_B' in k for k in keys)
 assert all(torch.isfinite(reader.get_tensor(k)).all().item() for k in keys)
 result={'tensor_count':len(keys),'all_tensors_finite':True,'r':8,'lora_alpha':32,'weights_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'weights_bytes':f.stat().st_size}
print(json.dumps(result))"""
 finite=json.loads(cmd('-n','swift','exec',PREP,'--','python3','-c',finite_query,cp,timeout=60).stdout)
 (ROOT/'evidence'/(mode+'-adapter-validation.json')).write_text(json.dumps(finite,indent=2)+'\n')
 # Require actual terminal pipeline logging record for both stages. Smoke must
 # not use a stale checkpoint or just a wrapper intermediate status.
 query="""import json,pathlib,sys;root=pathlib.Path(sys.argv[1]);out=[]
for p in root.rglob('logging.jsonl'):
 for ln in p.read_text().splitlines():
  try:r=json.loads(ln)
  except ValueError:continue
  if r.get('global_step') is not None and r.get('last_model_checkpoint'):out.append(r)
print(json.dumps(out))"""
 records=json.loads(cmd('-n','swift','exec',PREP,'--','python3','-c',query,WORK+'/outputs/'+mode+'/checkpoints').stdout)
 if len(records)!=1 or records[0]['global_step']!=step or pathlib.PurePosixPath(records[0]['last_model_checkpoint']).name!=pathlib.PurePosixPath(data['checkpoint']).name:
  raise RuntimeError(mode+' terminal pipeline record does not match checkpoint')
 for name in ('run_manifest.json','training-metrics.json'):
  p=cmd('-n','swift','exec',PREP,'--','cat',WORK+'/outputs/'+mode+'/'+name)
  (ROOT/'evidence'/(mode+'-'+name)).write_text(p.stdout)
 (ROOT/'evidence'/(mode+'-terminal-state.json')).write_text(json.dumps({'trainer_state':state,'pipeline_terminal':records[0]},indent=2)+'\n')
 return data

def stop_owned_gpu_jobs():
 errors=[]
 for mode in ('smoke','full'):
  name=RUN+'-'+mode
  try:
   job=cmd('-n','swift','get','job',name,'-o','json',check=False)
   if job.returncode:
    if 'NotFound' not in job.stderr:errors.append(name+': lookup failed')
    continue
   obj=json.loads(job.stdout)
   if obj['metadata'].get('labels',{}).get('t008-run')!=RUN:
    errors.append(name+': ownership mismatch');continue
   try:capture_job(mode)
   except Exception as exc:errors.append(name+': evidence capture '+type(exc).__name__)
   finally:
    # Evidence/log failures must never prevent releasing this run's GPU.
    deleted=cmd('-n','swift','delete','job',name,'--wait=false',check=False)
    if deleted.returncode and 'NotFound' not in deleted.stderr:errors.append(name+': delete failed')
  except Exception as exc:
   errors.append(name+': '+type(exc).__name__)
 deadline=time.monotonic()+180
 while time.monotonic()<deadline:
  try:
   pods=get('-n','swift','get','pods','-l','t008-run='+RUN)
   gpu=[p for p in pods['items'] if p['metadata'].get('labels',{}).get('stage') in ('smoke','full')]
   if not gpu:
    if errors:event('GPU_CLEANUP_EVIDENCE_WARNING',warnings=errors)
    return
   # Retry deletion for any own job still holding a pod after transient errors.
   for mode in {p['metadata']['labels']['stage'] for p in gpu}:
    cmd('-n','swift','delete','job',RUN+'-'+mode,'--wait=false','--ignore-not-found',check=False)
  except Exception as exc:errors.append('drain: '+type(exc).__name__)
  time.sleep(3)
 raise TimeoutError('Own GPU pods did not drain: '+str(errors[-5:]))

def restore(original):
 event('RESTORING_VLLM')
 try:stop_owned_gpu_jobs()
 except Exception as exc:event('GPU_JOB_CLEANUP_WARNING',cleanup_error=str(exc))
 current=get('-n','vllm','get','deployment','vllm')
 if current['metadata']['uid']!=original['metadata']['uid']:
  raise RuntimeError('Original vLLM Deployment UID changed; cannot safely restore another deployment')
 cmd('-n','vllm','scale','deployment/vllm','--replicas='+str(original['spec']['replicas']))
 deadline=time.monotonic()+900
 while time.monotonic()<deadline:
  current=get('-n','vllm','get','deployment','vllm')
  if current['status'].get('readyReplicas',0)==original['spec']['replicas'] and current['status'].get('observedGeneration',0)>=current['metadata']['generation']:
   p=subprocess.run(['/usr/bin/curl','--silent','--show-error','--max-time','15','--output','/dev/null','--write-out','%{http_code} %{ssl_verify_result}','https://vllm.10.140.17.125.nip.io/health'],capture_output=True,text=True)
   if p.returncode==0 and p.stdout=='200 0':
    if spec_hash(current['spec'])!=spec_hash(original['spec']):raise RuntimeError('Restored replica but vLLM config differs from saved original')
    result={'at_utc':now(),'deployment_uid':current['metadata']['uid'],'original_replicas':original['spec']['replicas'],'ready_replicas':current['status']['readyReplicas'],
     'spec_sha256':spec_hash(current['spec']),'spec_matches_original':True,'https_health':200,'tls_verified':True}
    pods=get('-n','vllm','get','pods','-l','app=vllm')
    (ROOT/'evidence/vllm-after-pods.json').write_text(json.dumps(pods,indent=2)+'\n')
    (ROOT/'evidence/vllm-restoration.json').write_text(json.dumps(result,indent=2)+'\n')
    event('VLLM_RESTORED',vllm_restored=True);return
  time.sleep(10)
 raise TimeoutError('vLLM restoration did not reach ready + verified HTTPS health within 15 minutes')

def main():
 original=json.loads((ROOT/'private/vllm_before.json').read_text())
 paused=False;failure=None
 try:
  pre=get('-n','swift','get','job',RUN+'-preflight')
  if not any(c['type']=='Complete' and c.get('status')=='True' for c in pre.get('status',{}).get('conditions',[])):
   raise RuntimeError('Final actual PVC/SDK CPU preflight must finish before any vLLM pause')
  result=read_file(WORK+'/runtime_preflight.json');assert result['verified'] and result['trainer_created'] is False
  (ROOT/'evidence/runtime_preflight.json').write_text(json.dumps(result,indent=2)+'\n');capture_job('preflight')
  current=get('-n','vllm','get','deployment','vllm')
  if current['metadata']['uid']!=original['metadata']['uid'] or spec_hash(current['spec'])!=spec_hash(original['spec']):
   raise RuntimeError('vLLM changed since saved restore point')
  hpa=get('-n','vllm','get','hpa')
  if any(x['spec']['scaleTargetRef'].get('name')=='vllm' for x in hpa['items']):raise RuntimeError('vLLM has active autoscaler; no unapproved controller changes')
  for mode in ('smoke','full'):
   cmd('create','--dry-run=server','-f',str(ROOT/'evidence'/('job-'+mode+'.json')))
  event('PAUSING_VLLM',gpu_window_started=True)
  # Set finally-restore intent BEFORE attempting the scale mutation. A network
  # failure after server acceptance must still trigger recovery.
  paused=True
  cmd('-n','vllm','scale','deployment/vllm','--current-replicas='+str(original['spec']['replicas']),'--replicas=0')
  deadline=time.monotonic()+180
  while time.monotonic()<deadline:
   if not get('-n','vllm','get','pods','-l','app=vllm')['items']:break
   time.sleep(3)
  else:raise TimeoutError('vLLM pods did not drain')
  event('VLLM_PAUSED')
  for mode in ('smoke','full'):
   event(mode.upper()+'_SUBMITTING')
   cmd('create','-f',str(ROOT/'evidence'/('job-'+mode+'.json')))
   wait_job(mode,7500 if mode=='full' else 2100)
   data=stage_verified(mode)
   event(mode.upper()+'_VERIFIED',**{mode+'_task_id':data.get('clearml_task_id'),mode+'_model_id':data.get('clearml_output_model_id')})
 except BaseException as exc:
  failure=exc;event('FAILED',error=type(exc).__name__+': '+str(exc))
 finally:
  if paused:
   try:restore(original)
   except BaseException as exc:
    event('RESTORE_FAILED',restore_error=type(exc).__name__+': '+str(exc))
    if failure is None:failure=exc
  if failure is None:event('TRAINING_CANDIDATE_RESTORED',training_verified=True)
  else:event('STOPPED_WITH_FAILURE',training_verified=False)
 if failure:sys.exit(1)

def interrupted(signum,frame):raise InterruptedError('Supervisor received signal '+str(signum))
if __name__=='__main__':
 signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
 main()
