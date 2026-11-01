"""Collect completed diagnostic evidence and delete only its pod; never restore UAT."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,io,json,subprocess,tarfile,time
D=Path(__file__).resolve().parent;R=D.parents[2];K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
pod='t008-module-ablation-20261101'
def call(*args):return subprocess.run(K+list(args),capture_output=True,check=True)
def obj(*args):return json.loads(call(*args).stdout)
if (D/'results.tar.gz').exists() and (D/'results/completed.json').exists():
    exit_status=json.loads((D/'exit.json').read_text());complete=json.loads((D/'results/completed.json').read_text())
    blob=(D/'results.tar.gz').read_bytes()
else:
    exit_status=obj('-n','swift','exec',pod,'--','cat','/tmp/diag/exit.json')
    complete=obj('-n','swift','exec',pod,'--','cat','/tmp/diag/results/completed.json')
    blob=call('-n','swift','exec',pod,'--','tar','czf','-','-C','/tmp/diag','inputs','results','diagnose.py','gpu.log','exit.json').stdout
assert exit_status['exit_code']==0
assert complete['complete'] and complete['scores']==256 and complete['generations']==128
(D/'results.tar.gz').write_bytes(blob)
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as t:
    for m in t.getmembers():assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and not m.issym() and not m.islnk()
    for n,h in [('results/scores.jsonl',complete['scores_sha256']),('results/generations.jsonl',complete['generations_sha256'])]:assert hashlib.sha256(t.extractfile(n).read()).hexdigest()==h
    t.extractall(D,filter='data')
call('-n','swift','delete','pod',pod,'--ignore-not-found','--wait=false')
deadline=time.monotonic()+55
while obj('-n','swift','get','pods','-l','t008-diagnostic=module-ablation-20261101','-o','json')['items']:
    if time.monotonic()>deadline:raise TimeoutError('Diagnostic pod remains; UAT must still stay paused')
    time.sleep(3)
hold=json.loads((R/'stage2/uat-pause-hold.json').read_text());assert hold['active'] and not hold['automatic_restore_authorized']
original=json.loads((R/hold['original_deployment_snapshot']).read_text())
live=obj('-n','vllm','get','deployment','vllm','-o','json');expected=dict(original['spec']);expected['replicas']=0
assert live['metadata']['uid']==original['metadata']['uid'] and live['spec']==expected
assert not obj('-n','vllm','get','pods','-l','app=vllm','-o','json')['items']
assert not obj('-n','swift','get','pods','-l','t008-diagnostic=module-ablation-20261101','-o','json')['items']
result={'checked_at_utc':datetime.now(timezone.utc).isoformat(),'replicas':live['spec']['replicas'],'ready_replicas':live['status'].get('readyReplicas',0),'spec_equal_except_replicas':True,'task_pod_deleted':True,'uat_restored':False,'automatic_restore_authorized':False,'archive_sha256':hashlib.sha256(blob).hexdigest(),'archive_bytes':len(blob)}
assert result['replicas']==result['ready_replicas']==0
(D/'final-runtime.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
