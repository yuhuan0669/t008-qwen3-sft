"""Collect artifacts and remove only this experiment's prep pod; keep UAT paused."""
from pathlib import Path
from datetime import datetime,timezone
import json,subprocess,sys
D=Path(__file__).resolve().parent
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
state=json.loads((D/'window-state.json').read_text())
assert state['paused'] and not state['restored'] and state['task_gpu_cleaned']
if not (D/'model-local-copy.json').exists():
    subprocess.run([sys.executable,str(D/'collect_model.py')],check=True)
subprocess.run([sys.executable,str(D/'collect_raw.py')],check=True)
subprocess.run(K+['-n','swift','delete','pod',D.name+'-prep','--ignore-not-found','--wait=false'],check=True)
subprocess.run(K+['-n','swift','wait','--for=delete','pod/'+D.name+'-prep','--timeout=30s'],check=True)
before=json.loads((D/'vllm-before.json').read_text())
after=json.loads(subprocess.check_output(K+['-n','vllm','get','deployment','vllm','-o','json']))
pods=json.loads(subprocess.check_output(K+['-n','swift','get','pods','-l','t008-run='+D.name,'-o','json']))
jobs=json.loads(subprocess.check_output(K+['-n','swift','get','jobs','-l','t008-run='+D.name,'-o','json']))
uatpods=json.loads(subprocess.check_output(K+['-n','vllm','get','pods','-l','app=vllm','-o','json']))
remaining=[x['metadata']['name'] for x in pods['items']+jobs['items']]
expected=dict(before['spec']);expected['replicas']=0
assert expected==after['spec'] and after['metadata']['uid']==before['metadata']['uid']
assert after['spec']['replicas']==0 and after['status'].get('readyReplicas',0)==0
assert not remaining and not uatpods['items']
report={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'spec_equal_except_replicas':True,
        'replicas':0,'ready_replicas':0,'uat_paused':True,'uat_restored':False,
        'automatic_restore_authorized':False,'remaining_task_workloads':remaining,
        'uat_pods':[],'restore_condition':'User explicitly requests restoration.'}
(D/'final-runtime-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
