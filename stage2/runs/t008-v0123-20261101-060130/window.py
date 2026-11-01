"""Current user-approved window and task-owned cleanup. No model or training calls."""
from pathlib import Path
import datetime,json,subprocess,sys,time,hashlib
O=Path(__file__).resolve().parent;R=O.parents[2];run=O.name
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
def call(*args):return subprocess.run(K+list(args),capture_output=True,text=True,check=True)
def now():return datetime.datetime.now(datetime.timezone.utc)
def restore():
 state=O/'window-state.json';s=json.loads(state.read_text())
 if s.get('restored'):return
 # Only this run's training jobs and GPU-bearing Pods are removed.
 jobs=json.loads(call('-n','swift','get','jobs','-l','t008-run='+run,'-o','json').stdout)
 for j in jobs['items']:call('-n','swift','delete','job',j['metadata']['name'],'--ignore-not-found','--wait=false')
 pods=json.loads(call('-n','swift','get','pods','-l','t008-run='+run,'-o','json').stdout)
 for p in pods['items']:
  if any(c.get('resources',{}).get('limits',{}).get('nvidia.com/gpu') for c in p['spec']['containers']):call('-n','swift','delete','pod',p['metadata']['name'],'--ignore-not-found','--wait=false')
 orig=json.loads((O/'vllm-before.json').read_text())
 live=json.loads(call('-n','vllm','get','deployment','vllm','-o','json').stdout)
 if live['metadata']['uid']!=orig['metadata']['uid']:raise RuntimeError('UAT Deployment identity changed; do not overwrite another deployment')
 call('-n','vllm','scale','deployment/vllm','--replicas='+str(orig['spec']['replicas']))

 for _ in range(20):
  rr=subprocess.run(K+['-n','vllm','rollout','status','deployment/vllm','--timeout=30s'],capture_output=True,text=True)
  if rr.returncode==0:break
 else:raise RuntimeError('UAT rollout did not become ready')
 after=json.loads(call('-n','vllm','get','deployment','vllm','-o','json').stdout)
 if after['spec']!=orig['spec']:raise RuntimeError('Restored service spec differs; inspect concurrent changes')
 p=json.loads(call('-n','vllm','get','pods','-l','app=vllm','-o','json').stdout)['items']
 if not p:raise RuntimeError('No restored vLLM pod')
 health=call('-n','vllm','exec',p[0]['metadata']['name'],'--','python3','-c',"import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status)").stdout.strip()
 if health!='200':raise RuntimeError('Restored model health failed')
 models=json.loads(call('-n','vllm','exec',p[0]['metadata']['name'],'--','python3','-c',"import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/v1/models',timeout=8).read().decode())").stdout)
 assert {'octa-carbon-v1','octa-carbon-sft-v0114','octa-carbon-sft-v0116'}<={m['id'] for m in models['data']}
 (O/'models-restored.json').write_text(json.dumps(models,indent=2)+'\n')
 (O/'uat-restored.json').write_text(json.dumps(after,indent=2)+'\n')
 s.update(restored=True,paused=False,restored_at_utc=now().isoformat(),service_spec_equal=True,health_status=200);state.write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(s),flush=True)
def pause():
 if (O/'window.json').exists():raise RuntimeError('Window already exists; do not recreate authorization')
 original=json.loads(call('-n','vllm','get','deployment','vllm','-o','json').stdout)
 initial=json.loads((O/'uat-preflight.json').read_text())
 assert original['metadata']['uid']==initial['metadata']['uid'] and original['spec']==initial['spec'],'UAT changed since preflight'
 assert original['status'].get('readyReplicas')==original['spec']['replicas']==1
 (O/'vllm-before.json').write_text(json.dumps(original,indent=2)+'\n')
 start=now();end=start+datetime.timedelta(minutes=90)
 auth={'run_id':run,'experiment_approved':True,'uat_pause_approved':True,'approved_data_sha256':'71df7fdc84f4144e91ee3d6f8df4710c21f55c50137f674f9e9de0c2dc6f2cef','window_start_utc':start.isoformat(),'window_end_utc':end.isoformat(),'restore_start_utc':(end-datetime.timedelta(minutes=15)).isoformat(),'decision_ref':'Current user 你做吧 authorizes the agreed mode-allocation experiment: 64 existing Chinese general exposures become nonthinking, same answers, rows, identity234/loss3 and other parameters. One fresh-base Smoke3 and Full66, then 208 Chinese generations. Standing user permission 可无需授权就暂停UAT applies. Restore original UAT; no deployment or extra Full. 90-minute operational ceiling, not a user deadline.','restoration_owner':'Current implementation agent','uat_coordination':'Owner directly confirmed immediate pause','max_full_runs':1}
 (O/'window.json').write_text(json.dumps(auth,ensure_ascii=False,indent=2)+'\n');(O/'window-state.json').write_text(json.dumps({'started_at_utc':start.isoformat(),'restored':False,'paused':False},indent=2)+'\n')
 # Dedicated local watchdog survives a chat interruption and begins recovery 15 min before deadline.
 with (O/'watchdog.log').open('a') as f:
  p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'watch'],cwd=R,stdout=f,stderr=subprocess.STDOUT,start_new_session=True)
 (O/'watchdog-pid.txt').write_text(str(p.pid)+'\n')
 patch=[{'op':'test','path':'/metadata/resourceVersion','value':original['metadata']['resourceVersion']},{'op':'test','path':'/spec/replicas','value':1},{'op':'replace','path':'/spec/replicas','value':0}]
 call('-n','vllm','patch','deployment','vllm','--type=json','-p',json.dumps(patch))
 s=json.loads((O/'window-state.json').read_text());s['paused']=True;(O/'window-state.json').write_text(json.dumps(s,indent=2)+'\n');print(json.dumps(auth,ensure_ascii=False),flush=True)
def watch():
 auth=json.loads((O/'window.json').read_text());deadline=datetime.datetime.fromisoformat(auth['restore_start_utc'])
 while now()<deadline:
  if json.loads((O/'window-state.json').read_text()).get('restored'):return
  time.sleep(20)
 for i in range(12):
  try:restore();return
  except Exception as e:print(type(e).__name__+': '+str(e),flush=True);time.sleep(30)
 raise RuntimeError('Automatic recovery failed; inspect watchdog log')
if __name__=='__main__':{'pause':pause,'restore':restore,'watch':watch}[sys.argv[1]]()
