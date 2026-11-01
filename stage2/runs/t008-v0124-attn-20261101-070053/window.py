"""Pause UAT by explicit instruction. No restore action or restore watchdog."""
from pathlib import Path
import datetime,json,subprocess,sys,time
O=Path(__file__).resolve().parent;R=O.parents[2];run=O.name
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
def call(*args):return subprocess.run(K+list(args),capture_output=True,text=True,check=True)
def now():return datetime.datetime.now(datetime.timezone.utc)
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def check_paused():
 original=json.loads((O/'vllm-before.json').read_text())
 live=json.loads(call('-n','vllm','get','deployment','vllm','-o','json').stdout)
 expected=dict(original['spec']);expected['replicas']=0
 assert live['metadata']['uid']==original['metadata']['uid'] and live['spec']==expected,'UAT changed beyond authorized replica pause'
 pods=json.loads(call('-n','vllm','get','pods','-l','app=vllm','-o','json').stdout)['items']
 return live,pods
def pause():
 assert not (O/'window.json').exists(),'Do not recreate the execution window'
 original=json.loads(call('-n','vllm','get','deployment','vllm','-o','json').stdout)
 initial=json.loads((O/'uat-preflight.json').read_text())
 assert original['metadata']['uid']==initial['metadata']['uid'] and original['spec']==initial['spec']
 assert original['spec']['replicas']==original['status'].get('readyReplicas')==1
 save(O/'vllm-before.json',original)
 start=now();spec=json.loads((O/'training-config.json').read_text())
 auth={'run_id':run,'experiment_approved':True,'uat_pause_approved':True,
       'approved_data_sha256':spec['dataset_sha256'],'window_start_utc':start.isoformat(),
       'window_end_utc':(start+datetime.timedelta(minutes=90)).isoformat(),
       'window_end_meaning':'Experiment execution ceiling only; UAT stays paused afterwards.',
       'decision_ref':'继续。暂停UAT后，不用恢复，直到我说恢复。',
       'uat_policy':'KEEP_PAUSED_UNTIL_EXPLICIT_USER_RESTORE','automatic_restore_authorized':False,'max_full_runs':1}
 save(O/'window.json',auth)
 save(O/'window-state.json',{'started_at_utc':start.isoformat(),'paused':False,'restored':False,'automatic_restore':False})
 patch=[{'op':'test','path':'/metadata/resourceVersion','value':original['metadata']['resourceVersion']},
        {'op':'test','path':'/spec/replicas','value':1},{'op':'replace','path':'/spec/replicas','value':0}]
 call('-n','vllm','patch','deployment','vllm','--type=json','-p',json.dumps(patch))
 state=json.loads((O/'window-state.json').read_text());state['paused']=True;save(O/'window-state.json',state)
 hold={'active':True,'run_id':run,'started_at_utc':start.isoformat(),
       'instruction':auth['decision_ref'],'automatic_restore_authorized':False,
       'deployment':'vllm/vllm','expected_replicas':0,
       'original_deployment_snapshot':str((O/'vllm-before.json').relative_to(R)),
       'restore_condition':'Only after a new explicit user instruction to restore UAT.'}
 save(R/'stage2/uat-pause-hold.json',hold)
 print(json.dumps(auth,ensure_ascii=False),flush=True)
def cleanup():
 # Remove only this experiment's GPU workloads; never scale or patch UAT here.
 for kind in ['jobs','pods']:
  objects=json.loads(call('-n','swift','get',kind,'-l','t008-run='+run,'-o','json').stdout)['items']
  for obj in objects:
   if kind=='pods' and not any(c.get('resources',{}).get('limits',{}).get('nvidia.com/gpu') for c in obj['spec']['containers']):continue
   call('-n','swift','delete',kind,obj['metadata']['name'],'--ignore-not-found','--wait=false')
 deadline=time.monotonic()+180
 while True:
  pods=json.loads(call('-n','swift','get','pods','-l','t008-run='+run,'-o','json').stdout)['items']
  gpu=[p['metadata']['name'] for p in pods if any(c.get('resources',{}).get('limits',{}).get('nvidia.com/gpu') for c in p['spec']['containers'])]
  if not gpu:break
  if time.monotonic()>deadline:raise TimeoutError('Task GPU pods still terminating: '+str(gpu))
  time.sleep(3)
 live,uatpods=check_paused();assert not uatpods and not live['status'].get('readyReplicas',0)
 save(O/'uat-paused-final.json',live)
 state=json.loads((O/'window-state.json').read_text())
 state.update(paused=True,restored=False,task_gpu_cleaned=True,uat_spec_equal_except_replicas=True,checked_at_utc=now().isoformat())
 save(O/'window-state.json',state);print(json.dumps(state),flush=True)
if __name__=='__main__':{'pause':pause,'cleanup':cleanup}[sys.argv[1]]()
