"""Collect this diagnostic and delete its pod; preserve the explicit UAT hold."""
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import time

D = Path(__file__).resolve().parent; R = D.parents[2]
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']
pod = 't008-kl-context-20261101'
def call(*args): return subprocess.run(K + list(args), capture_output=True, check=True)
def obj(*args): return json.loads(call(*args).stdout)
exit_status = obj('-n', 'swift', 'exec', pod, '--', 'cat', '/tmp/diag/exit.json')
assert exit_status['exit_code'] == 0, exit_status
complete = obj('-n', 'swift', 'exec', pod, '--', 'cat', '/tmp/diag/results/completed.json')
assert complete['complete'] and complete['scores'] == 174 and complete['kl_comparisons'] == 184
blob = call('-n', 'swift', 'exec', pod, '--', 'tar', 'czf', '-', '-C', '/tmp/diag',
            'inputs', 'results', 'diagnose.py', 'gpu.log', 'exit.json', 'attempt1.log', 'attempt1-exit.json').stdout
(D / 'results.tar.gz').write_bytes(blob)
with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as t:
    for m in t.getmembers():
        assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts and not m.issym() and not m.islnk()
    for name, digest in complete['files_sha256'].items():
        assert hashlib.sha256(t.extractfile('results/' + name).read()).hexdigest() == digest, name
    # Verify before extracting; do not overwrite locally versioned input code.
    assert t.extractfile('diagnose.py').read() == (D / 'diagnose.py').read_bytes()
    assert t.extractfile('inputs/manifest.json').read() == (D / 'inputs/manifest.json').read_bytes()
    for m in t.getmembers():
        if m.name.startswith('results/') or m.name in ['gpu.log', 'exit.json', 'attempt1.log', 'attempt1-exit.json']:
            t.extract(m, D, filter='data')
call('-n', 'swift', 'delete', 'pod', pod, '--ignore-not-found', '--wait=false')
deadline = time.monotonic() + 55
while obj('-n', 'swift', 'get', 'pods', '-l', 't008-diagnostic=kl-context-20261101', '-o', 'json')['items']:
    if time.monotonic() > deadline: raise TimeoutError('Diagnostic pod remains; do not restore UAT')
    time.sleep(2)
hold = json.loads((R / 'stage2/uat-pause-hold.json').read_text())
assert hold['active'] and not hold['automatic_restore_authorized']
before = json.loads((D / 'uat-before.json').read_text())
live = obj('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json')
assert live['metadata']['uid'] == before['metadata']['uid'] and live['spec'] == before['spec']
assert live['spec']['replicas'] == live['status'].get('readyReplicas', 0) == 0
assert not obj('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json')['items']
result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'replicas': 0, 'ready_replicas': 0,
    'uat_spec_unchanged': True, 'task_pod_deleted': True, 'uat_restored': False, 'automatic_restore_authorized': False,
    'archive_sha256': hashlib.sha256(blob).hexdigest(), 'archive_bytes': len(blob)}
(D / 'final-runtime.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
