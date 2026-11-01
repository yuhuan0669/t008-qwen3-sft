"""Collect the completed run after UAT restoration, then delete only its CPU prep pod."""
from pathlib import Path
import json,subprocess,sys
D=Path(__file__).resolve().parent
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
assert json.loads((D/'window-state.json').read_text())['restored']
subprocess.run([sys.executable,str(D/'verify_restoration.py')],check=True)
if not (D/'model-local-copy.json').exists():
    subprocess.run([sys.executable,str(D/'collect_model.py')],check=True)
subprocess.run([sys.executable,str(D/'collect_raw.py')],check=True)
subprocess.run(K+['-n','swift','delete','pod',D.name+'-prep','--ignore-not-found','--wait=false'],check=True)
subprocess.run(K+['-n','swift','wait','--for=delete','pod/'+D.name+'-prep','--timeout=30s'],check=True)
before=json.loads((D/'vllm-before.json').read_text())
after=json.loads(subprocess.check_output(K+['-n','vllm','get','deployment','vllm','-o','json']))
pods=json.loads(subprocess.check_output(K+['-n','swift','get','pods','-l','t008-run='+D.name,'-o','json']))
jobs=json.loads(subprocess.check_output(K+['-n','swift','get','jobs','-l','t008-run='+D.name,'-o','json']))
remaining=[x['metadata']['name'] for x in pods['items']+jobs['items']]
assert before['spec']==after['spec'] and after['status'].get('readyReplicas')==1 and not remaining
report={'spec_equal':True,'ready_replicas':1,'remaining_task_workloads':remaining}
(D/'final-runtime-readback.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
