"""Read back restoration and two health samples; no generation or mutation."""
from datetime import datetime, timezone
from pathlib import Path
import json, subprocess, time
D=Path(__file__).resolve().parent
K=['kubectl','--context','lmas00-direct','--request-timeout=20s']
def read(p):return json.loads(p.read_text())
state=read(D/'window-state.json');assert state['restored'] and not state['paused']
before=read(D/'vllm-before.json')
after=json.loads(subprocess.check_output(K+['-n','vllm','get','deployment','vllm','-o','json']))
assert after['spec']==before['spec'] and after['status'].get('readyReplicas')==1
models=read(D/'models-restored.json');aliases=[x['id'] for x in models['data']]
assert sorted(aliases)==sorted(['octa-carbon-v1','octa-carbon-sft-v0114','octa-carbon-sft-v0116'])
samples=[]
for attempt in range(12):
    p=subprocess.run(['curl','--noproxy','*','-sS','--max-time','10','-o','/dev/null','-w','%{http_code}',
        'https://vllm.10.140.17.125.nip.io/health'],capture_output=True,text=True)
    sample={'utc':datetime.now(timezone.utc).isoformat(),'status':p.stdout.strip(),'exit_code':p.returncode}
    samples.append(sample)
    if len(samples)>=2 and all(s['status']=='200' and s['exit_code']==0 for s in samples[-2:]):break
    time.sleep(5)
else:raise RuntimeError('Public health did not recover')
elapsed=(datetime.fromisoformat(state['restored_at_utc'])-datetime.fromisoformat(state['started_at_utc'])).total_seconds()
report={'verified':True,'deployment_spec_equal':True,'ready_replicas':1,'internal_health':state['health_status'],
    'public_health_samples':samples,'pause_to_verified_restore_seconds':elapsed,'aliases':aliases}
(D/'uat-health-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
