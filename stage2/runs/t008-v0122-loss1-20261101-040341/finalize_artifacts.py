"""Collect completed run artifacts after UAT restoration; never generate or train."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib,json,subprocess,sys,tarfile
D=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
assert read(D/'window-state.json')['restored']
assert read(D/'evaluation/complete.json')['count']==556
scripts=['verify_restoration.py']
if not (D/'model-local-copy.json').exists():scripts.append('collect_model.py')
else:
    model=read(D/'model-local-copy.json')
    assert model['verified']
    assert hashlib.sha256((D.parents[2]/model['path']).read_bytes()).hexdigest()==model['sha256']
scripts.append('collect_raw.py')
for script in scripts:
    subprocess.run([sys.executable,str(D/script)],cwd=D,check=True)
rows=[json.loads(x) for x in (D/'evaluation/results.jsonl').read_text().splitlines()]
archive=D/'evaluation/raw-evidence.tar.gz'
with tarfile.open(archive) as t:
    for r in rows:
        for name,value in [('request.json',r['request']),('response.raw.json',r['response'])]:
            f=t.extractfile(r['raw_path']+'/'+name)
            assert f is not None and json.load(f)==value,(r['case_id'],r['repeat'],name)
dump(D/'raw-content-verification.json',{'requests_and_responses_equal_to_results':len(rows),'verified':True,
    'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()})
if not (D/'evaluation/review-queue.json').exists():
    subprocess.run([sys.executable,str(D/'evaluation/prepare_review.py')],cwd=D,check=True)
else:
    queue=read(D/'evaluation/review-queue.json')
    assert queue['slots']==2780 and queue['new_slots']==556
K=['kubectl','--context','lmas00-direct','--request-timeout=20s']
subprocess.run(K+['-n','swift','delete','pod',D.name+'-prep','--wait=false'],check=True)
dep=json.loads(subprocess.check_output(K+['-n','vllm','get','deployment','vllm','-o','json']))
pods=json.loads(subprocess.check_output(K+['get','pods','-A','-o','json']))
jobs=json.loads(subprocess.check_output(K+['-n','swift','get','jobs','-o','json']))
remaining=[x['metadata']['name'] for x in pods['items']+jobs['items'] if x['metadata']['name'].startswith(D.name)]
assert dep['spec']==read(D/'vllm-before.json')['spec'] and dep['status'].get('readyReplicas')==1
assert all(x==D.name+'-prep' for x in remaining),remaining
dump(D/'final-runtime-readback.json',{'at_utc':datetime.now(timezone.utc).isoformat(),
    'ready_replicas':1,'spec_equal':True,'remaining_task_workloads':remaining,
    'note':'CPU prep deletion requested; if listed here, it was terminating at readback.'})
print('Completed raw readback and review preparation; UAT preserved.',flush=True)
