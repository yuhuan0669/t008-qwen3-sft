"""Verify, retrieve local evidence and remove only this diagnostic pod."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time

D=Path(__file__).resolve().parent;R=D.parents[2]
K=['kubectl','--context','lmas00-direct','--request-timeout=30s'];POD='t008-source-gradient-20261101'
def call(*args):return subprocess.run(K+list(args),capture_output=True,check=True)
def obj(*args):return json.loads(call(*args).stdout)
done=obj('-n','swift','exec',POD,'--','cat','/tmp/diag/results/completed.json')
assert done['complete'] and done['optimizer_steps']==done['new_generated_answers']==0
assert obj('-n','swift','exec',POD,'--','cat','/tmp/diag/gpu-exit.json')['exit_code']==0
numeric=obj('-n','swift','exec',POD,'--','cat','/tmp/diag/results/fp64-gradient-verification.json')
assert numeric['verified'] and numeric['weights_unchanged']
assert obj('-n','swift','exec',POD,'--','cat','/tmp/diag/numeric-exit.json')['exit_code']==0
native=obj('-n','swift','exec',POD,'--','cat','/tmp/diag/results/native-projection-verification.json')
assert native['complete'] and native['weights_unchanged'] and native['rows']==1047
blob=call('-n','swift','exec',POD,'--','tar','czf','-','-C','/tmp/diag',
          'inputs','results','diagnose.py','verify_numeric.py','cpu.log','gpu.log','numeric.log','cpu-exit.json','gpu-exit.json','numeric-exit.json').stdout
(D/'results.tar.gz').write_bytes(blob)
with tarfile.open(fileobj=io.BytesIO(blob),mode='r:gz') as t:
    for m in t.getmembers():assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and not m.issym() and not m.islnk()
    for name,h in done['files_sha256'].items():assert hashlib.sha256(t.extractfile('results/'+name).read()).hexdigest()==h,name
    assert t.extractfile('diagnose.py').read()==(D/'diagnose.py').read_bytes()
    assert t.extractfile('verify_numeric.py').read()==(D/'verify_numeric.py').read_bytes()
    assert t.extractfile('inputs/manifest.json').read()==(D/'inputs/manifest.json').read_bytes()
    assert json.loads(t.extractfile('results/fp64-gradient-verification.json').read())==numeric
    assert json.loads(t.extractfile('results/native-projection-verification.json').read())==native
    for m in t.getmembers():
        if m.name.startswith('results/') or m.name in ['cpu.log','gpu.log','numeric.log','cpu-exit.json','gpu-exit.json','numeric-exit.json']:
            t.extract(m,D,filter='data')
call('-n','swift','delete','pod',POD,'--ignore-not-found','--wait=false')
deadline=time.monotonic()+55
while obj('-n','swift','get','pods','-l','t008-diagnostic=source-gradient-20261101','-o','json')['items']:
    if time.monotonic()>deadline:raise TimeoutError('Diagnostic pod still terminating')
    time.sleep(2)
before=json.loads((D/'uat-before.json').read_text());live=obj('-n','vllm','get','deployment','vllm','-o','json')
assert live['metadata']['uid']==before['metadata']['uid'] and live['spec']==before['spec']
assert live['spec']['replicas']==live['status'].get('readyReplicas',0)==0
assert not obj('-n','vllm','get','pods','-l','app=vllm','-o','json')['items']
out={'utc':datetime.now(timezone.utc).isoformat(),'uat_replicas':0,'uat_ready_replicas':0,'uat_spec_unchanged':True,
     'task_pod_deleted':True,'uat_restored':False,'automatic_restore_authorized':False,
     'archive_bytes':len(blob),'archive_sha256':hashlib.sha256(blob).hexdigest(),
     'optimizer_steps':0,'new_generations':0,'new_model_candidate':False}
(D/'final-runtime.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
