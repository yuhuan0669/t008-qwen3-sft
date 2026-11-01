"""Stage isolated input; verify the existing UAT pause without changing service."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess
O=Path(__file__).resolve().parent;R=O.parents[2];V=R/'stage1/variants/stage1-cpu-v0.1.22'
K=['kubectl','--context','lmas00-direct','--request-timeout=30s'];run=O.name
subprocess.run(K+['create','-f',str(O/'prep-pod.json')],check=True)
subprocess.run(K+['-n','swift','wait','--for=condition=Ready','pod/'+run+'-prep','--timeout=30s'],check=True)
files={
 'stage1/data/train.jsonl':(V/'train.jsonl').read_text(),
 'stage1/data/manifest.json':(V/'manifest.json').read_text(),
 'stage1/training/run-spec.json':(O/'training-config.json').read_text(),
 'stage1/training/local_data_guard.py':(R/'stage1/training/local_data_guard.py').read_text(),
 'stage1/evidence/encoding-report.json':(O/'cpu-report.json').read_text(),
 'stage2/scripts/run_local_sft.py':(O/'run_local_sft.py').read_text(),
}
for n in ['identity_loss3.py','identity-keys.json']:files['stage1/variants/stage1-cpu-v0.1.22/'+n]=(V/n).read_text()
for n in ['identity_zero.py','config.json','membership.json']:files['ablation/'+n]=(O/'ablation'/n).read_text()
for p in (O/'inputs/evaluation').iterdir():files['evaluation/'+p.name]=p.read_text()
payload={'run':run,'sha':hashlib.sha256((V/'train.jsonl').read_bytes()).hexdigest(),'files':files}
r=subprocess.run(K+['-n','swift','exec','-i',run+'-prep','--','python3','-c',(O/'prepare_remote.py').read_text()],input=json.dumps(payload),text=True,capture_output=True,check=True)
readback=json.loads(r.stdout)
for n,t in files.items():assert readback['file_hashes'][n]==hashlib.sha256(t.encode()).hexdigest(),n
(O/'runtime-input-readback.json').write_text(json.dumps(readback,indent=2)+'\n')
pods=json.loads(subprocess.check_output(K+['get','pods','-A','-o','json']))
gpu=[{'namespace':p['metadata']['namespace'],'name':p['metadata']['name'],'phase':p['status']['phase'],'node':p['spec'].get('nodeName')} for p in pods['items'] if any(c.get('resources',{}).get('limits',{}).get('nvidia.com/gpu') for c in p['spec']['containers'])]
(O/'gpu-workloads-before.json').write_text(json.dumps(gpu,indent=2)+'\n')
active=[p for p in gpu if p['phase'] not in ['Succeeded','Failed']];assert not active,active
hold=json.loads((R/'stage2/uat-pause-hold.json').read_text());assert hold['active'] and not hold['automatic_restore_authorized']
before=json.loads((R/hold['original_deployment_snapshot']).read_text())
uat=json.loads(subprocess.check_output(K+['-n','vllm','get','deployment','vllm','-o','json']))
expected=dict(before['spec']);expected['replicas']=0
assert uat['metadata']['uid']==before['metadata']['uid'] and uat['spec']==expected
assert uat['spec']['replicas']==0 and uat['status'].get('readyReplicas',0)==0
assert not json.loads(subprocess.check_output(K+['-n','vllm','get','pods','-l','app=vllm','-o','json']))['items']
(O/'uat-preflight.json').write_text(json.dumps(uat,indent=2)+'\n')
(O/'vllm-before.json').write_text(json.dumps(before,indent=2)+'\n')
(O/'preflight-state.json').write_text(json.dumps({'checked_at_utc':datetime.now(timezone.utc).isoformat(),'active_gpu_workloads':active,'uat_replicas':0,'uat_paused':True,'service_changed':False,'physical_gpu_process_check':'Performed by smoke wrapper before weight loading'},indent=2)+'\n')
print(json.dumps({'input_hashes_verified':len(files),'active_gpu_workloads':active,'uat_paused':True,'service_changed':False}))
