"""Read back this run's binding and original UAT; remove only its CPU prep pod."""
from pathlib import Path
import datetime, hashlib, json, subprocess

O = Path(__file__).resolve().parent
ROOT = O.parents[2]
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']

def read(*args):
    return subprocess.check_output(K + list(args))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load(p):
    return json.loads(p.read_text())

m = load(O / 'outputs/full/run_manifest.json')
assert m['training_verified'] and m['global_step'] == 80 and m['epoch'] == 1.0
assert m['command'] == load(O / 'expected-full-command.json')
assert m['data_sha256'] == sha(ROOT / 'stage1/variants/stage1-cpu-v0.1.8/train.jsonl')
binding = load(O / 'evaluation-binding.json')
assert binding['adapter_files'] == m['adapter_files'] and binding['data_sha256'] == m['data_sha256']
server = load(O / 'server-template-check.json')
assert all(x['match'] for x in server['checks'])
assert server['template_sha256'] == binding['template_sha256'] == 'ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d'
e = O / 'inputs/evaluation'
assert load(e / 'protocol.json')['custom_system']['sha256'] == sha(e / 'custom-system.txt')
old = ROOT / 'stage2/runs/t008-v018-20261020-145507/inputs/evaluation'
assert all(p.read_bytes() == (old / p.name).read_bytes() for p in e.iterdir())
special = load(O / 'development/all-24.jsonl.summary.json')
assert special['cases'] == 192 and special['requests'] == 200
public = load(O / 'development/public-comparison.json')
assert sum(x['requests'] for x in public['format']) == 160
assert not any(x['scoring_errors'] for x in public['metrics'])
local = load(O / 'model-local-copy.json')
assert local['verified'] and sha(ROOT / local['path']) == m['adapter_package_sha256']
before = load(O / 'vllm-before.json')
after = json.loads(read('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json'))
assert before['spec'] == after['spec'] and after['status']['readyReplicas'] == 1
state = load(O / 'window-state.json')
assert state['restored'] and state['health_status'] == 200
pods = json.loads(read('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json'))['items']
pod = next(p['metadata']['name'] for p in pods if p['status']['phase'] == 'Running' and not p['metadata'].get('deletionTimestamp'))
assert read('-n', 'vllm', 'exec', pod, '--', 'python3', '-c', "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status)").strip() == b'200'
read('-n', 'swift', 'delete', 'pod', O.name + '-prep', '--ignore-not-found', '--wait=false')
result = {
    'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'training_completed_steps': 80, 'epoch': 1.0, 'full_runs': 1,
    'exposure_rows': 1275, 'identity_exposures': 216,
    'frozen_data_unchanged': True, 'actual_command_matches_approved_config': True,
    'eval_inputs_equal_v018': True, 'server_template_verified': True,
    'specialized_requests': 200, 'public_requests': 160,
    'uat_original_spec_equal': True, 'uat_ready_replicas': 1, 'health_status': 200,
    'new_model_deployed_to_uat': False, 'formal_holdout_executed': False,
    'next_training_authorized': False,
}
(O / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
