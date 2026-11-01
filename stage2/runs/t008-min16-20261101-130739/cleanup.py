from pathlib import Path
import subprocess,json
D=Path(__file__).resolve().parent;K=['kubectl','--context','lmas00-direct','--request-timeout=30s'];complete=json.loads((D/'evaluation/complete.json').read_text());assert complete['count']==176 and complete['technical_retries']==0
before=json.loads((D/'uat-before.json').read_text());after=json.loads(subprocess.check_output(K+['-n','vllm','get','deploy','vllm','-o','json']));assert before['spec']==after['spec'] and after['spec']['replicas']==0
(D/'uat-after.json').write_text(json.dumps(after,indent=2))
subprocess.run(K+['-n','swift','delete','job','-l','t008-run='+D.name,'--wait=true','--timeout=40s'],check=True)
subprocess.run(K+['-n','swift','delete','pod','-l','t008-run='+D.name,'--wait=true','--timeout=40s'],check=True)
p=json.loads(subprocess.check_output(K+['-n','swift','get','pods','-l','t008-run='+D.name,'-o','json']));assert not p['items']
(D/'cleanup.json').write_text(json.dumps({'task_pods_removed':True,'uat_spec_unchanged':True,'uat_replicas':0,'restored':False,'deployed':False},indent=2));print('Task workloads removed, UAT remains paused')
