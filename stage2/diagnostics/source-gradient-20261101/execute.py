"""Launch one derivative-only job in the already-created read-only diagnostic pod."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

D = Path(__file__).resolve().parent; R = D.parents[2]
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']
POD = 't008-source-gradient-20261101'
def call(*args, data=None): return subprocess.run(K + list(args), input=data, capture_output=True, check=True)
def obj(*args): return json.loads(call(*args).stdout)
parser = argparse.ArgumentParser(); parser.add_argument('--cpu-only', action='store_true'); args = parser.parse_args()
hold = json.loads((R / 'stage2/uat-pause-hold.json').read_text())
assert hold['active'] and not hold['automatic_restore_authorized']
before = json.loads((D / 'uat-before.json').read_text())
live = obj('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json')
assert live['spec'] == before['spec'] and live['spec']['replicas'] == 0
assert live['metadata']['uid'] == before['metadata']['uid']
assert not obj('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json')['items']
gpu = call('-n', 'swift', 'exec', POD, '--', 'nvidia-smi', '--query-gpu=name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader').stdout.decode().strip()
if not args.cpu_only:
    result = obj('-n', 'swift', 'exec', POD, '--', 'cat', '/tmp/diag/cpu-exit.json')
    assert result['exit_code'] == 0
    result = obj('-n', 'swift', 'exec', POD, '--', 'cat', '/tmp/diag/results/encoding-check.json')
    assert result['verified'] and result['rows'] == 1047 and result['probes'] == 30
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode='w:gz') as t:
    t.add(D / 'inputs', arcname='inputs'); t.add(D / 'diagnose.py', arcname='diagnose.py')
call('-n', 'swift', 'exec', '-i', POD, '--', 'tar', 'xzf', '-', '-C', '/tmp/diag', data=buf.getvalue())
mode = 'cpu' if args.cpu_only else 'gpu'
command = ['python3', '/tmp/diag/diagnose.py'] + (['--cpu-only'] if args.cpu_only else [])
runner = f"import subprocess,json;from pathlib import Path;r=subprocess.run({command!r},stdout=open('/tmp/diag/{mode}.log','w'),stderr=subprocess.STDOUT);Path('/tmp/diag/{mode}-exit.json').write_text(json.dumps({{'exit_code':r.returncode}}))"
launcher = 'import subprocess;subprocess.Popen(["python3","-c",' + repr(runner) + '],start_new_session=True,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)'
call('-n', 'swift', 'exec', POD, '--', 'python3', '-c', launcher)
record = {'mode': mode, 'utc': datetime.now(timezone.utc).isoformat(), 'pod': POD, 'gpu_before': gpu,
          'script_sha256': hashlib.sha256((D / 'diagnose.py').read_bytes()).hexdigest(),
          'manifest_sha256': hashlib.sha256((D / 'inputs/manifest.json').read_bytes()).hexdigest(),
          'optimizer_steps': 0, 'new_generated_answers': 0, 'uat_restore': False}
(D / (mode + '-execution-start.json')).write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps(record))
