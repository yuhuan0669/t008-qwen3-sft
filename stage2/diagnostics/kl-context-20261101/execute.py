"""Run only this read-only diagnostic pod; never scale or restore UAT."""
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
def call(*args, data=None): return subprocess.run(K + list(args), input=data, capture_output=True, check=True)
def obj(*args): return json.loads(call(*args).stdout)
def save(n, x): (D / n).write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')

hold = json.loads((R / 'stage2/uat-pause-hold.json').read_text())
assert hold['active'] and not hold['automatic_restore_authorized']
before = obj('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json')
old = json.loads((R / hold['original_deployment_snapshot']).read_text())
expected = dict(old['spec']); expected['replicas'] = 0
assert before['metadata']['uid'] == old['metadata']['uid'] and before['spec'] == expected
assert not obj('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json')['items']
owners = [p for p in obj('get', 'pods', '-A', '-o', 'json')['items']
          if p['status']['phase'] not in ['Succeeded', 'Failed'] and
          any(c.get('resources', {}).get('limits', {}).get('nvidia.com/gpu') for c in p['spec'].get('containers', []))]
assert not owners, [(p['metadata']['namespace'], p['metadata']['name']) for p in owners]
save('uat-before.json', before)
save('runtime-preflight.json', {'utc': datetime.now(timezone.utc).isoformat(), 'uat_replicas': 0,
    'uat_spec_equal_except_replicas': True, 'active_gpu_owners': [], 'automatic_restore_authorized': False})
spec = json.loads((D / 'pod-gpu.json').read_text())
call('create', '-f', '-', data=json.dumps(spec).encode())
for attempt in range(40):
    state = obj('-n', 'swift', 'get', 'pod', pod, '-o', 'json')
    if any(c['type'] == 'Ready' and c['status'] == 'True' for c in state['status'].get('conditions', [])): break
    if state['status'].get('phase') == 'Failed': raise RuntimeError('Diagnostic pod failed before start')
    time.sleep(2)
else: raise TimeoutError('Diagnostic pod readiness timeout')
gpu = call('-n', 'swift', 'exec', pod, '--', 'nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader').stdout.decode().strip()
save('gpu-before.json', {'query': gpu})
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:gz') as t:
    t.add(D / 'inputs', arcname='inputs')
    t.add(D / 'diagnose.py', arcname='diagnose.py')
call('-n', 'swift', 'exec', '-i', pod, '--', 'tar', 'xzf', '-', '-C', '/tmp/diag', data=buf.getvalue())
runner = "import json,subprocess;from pathlib import Path;r=subprocess.run(['python3','/tmp/diag/diagnose.py'],stdout=open('/tmp/diag/gpu.log','w'),stderr=subprocess.STDOUT);Path('/tmp/diag/exit.json').write_text(json.dumps({'exit_code':r.returncode}))"
launcher = 'import subprocess;subprocess.Popen(["python3","-c",' + repr(runner) + '],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)'
call('-n', 'swift', 'exec', pod, '--', 'python3', '-c', launcher)
save('execution-start.json', {'utc': datetime.now(timezone.utc).isoformat(), 'pod': pod,
    'script_sha256': hashlib.sha256((D / 'diagnose.py').read_bytes()).hexdigest(),
    'input_manifest_sha256': hashlib.sha256((D / 'inputs/manifest.json').read_bytes()).hexdigest(),
    'new_generated_answers': 0, 'training': False, 'uat_restore': False})
print(json.dumps({'started': True, 'pod': pod, 'gpu': gpu}), flush=True)
