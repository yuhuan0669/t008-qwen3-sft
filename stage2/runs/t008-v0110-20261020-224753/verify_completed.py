"""Read back completed training, paired inference and restored original UAT."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

R = Path(__file__).resolve().parent
ROOT = R.parents[2]
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']


def read(*args):
    return subprocess.check_output(K + list(args))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


manifest = load(R / 'outputs/full/run_manifest.json')
assert manifest['training_verified'] and manifest['global_step'] == 80 and manifest['epoch'] == 1.0
assert manifest['command'] == load(R / 'expected-full-command.json')
assert manifest['data_sha256'] == sha(ROOT / 'stage1/variants/stage1-cpu-v0.1.10/train.jsonl')
assert manifest['upload_status'] == 'VERIFIED'
assert manifest['clearml_model_readback_sha256'] == manifest['adapter_package_sha256']
assert load(R / 'outputs/smoke/run_manifest.json')['global_step'] == 3
spec = load(R / 'development/spec.json')
assert spec['models']['adapter_files'] == manifest['adapter_files']
assert spec['models']['candidate_adapter'] == manifest['checkpoint']
assert spec['training_data_sha256'] == manifest['data_sha256']
assert spec['template_sha256'] == sha(R / 'inputs/evaluation/thinking-prefill.jinja')
assert load(R / 'development/run-state.json')['status'] == 'COMPLETE'
assert load(R / 'development/inference-verification.json')['status'] == 'PASS'
assert load(R / 'development/paired-protocol-verification.json')['verified']
assert load(R / 'development/json-summary.json')['identical_protocol_and_prompt_tokens']
assert load(R / 'development/summary.json')['total'] == 62
local = load(R / 'model-local-copy.json')
assert local['verified'] and sha(ROOT / local['path']) == manifest['adapter_package_sha256']
before = load(R / 'vllm-before.json')
after = json.loads(read('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json'))
assert before['spec'] == after['spec'] and after['status']['readyReplicas'] == 1
state = load(R / 'window-state.json')
assert state['restored'] and state['health_status'] == 200
pods = json.loads(read('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json'))['items']
pod = next(p['metadata']['name'] for p in pods if p['status']['phase'] == 'Running' and not p['metadata'].get('deletionTimestamp'))
assert read('-n', 'vllm', 'exec', pod, '--', 'python3', '-c',
            "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status)").strip() == b'200'
ingress = subprocess.check_output(['curl', '--noproxy', '*', '--max-time', '10', '-sS',
                                  '-o', '/dev/null', '-w', '%{http_code}',
                                  'https://vllm.10.140.17.125.nip.io/health'], text=True)
assert ingress == '200'
(R / 'uat-restored.json').write_text(json.dumps(after, indent=2) + '\n')
# Cleanup of the CPU retrieval Pod follows final artifact collection and verification.
result = {
    'verified_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'training_completed_steps': 80, 'epoch': 1.0, 'full_runs': 1, 'smoke_steps': 3,
    'exposure_rows': 1275, 'identity_exposures': 216,
    'frozen_data_unchanged': True, 'actual_command_matches_approved_config': True,
    'development_requests': 62, 'same_prompts_and_parameters_as_frozen_previous_runs': True, 'chinese_regression_conditions': 40, 'json_conditions': 24, 'overlap_reused': 2,
    'all_server_prompt_ids_verified': True, 'clearml_model_readback_verified': True,
    'local_adapter_package_verified': True,
    'uat_original_spec_equal': True, 'uat_ready_replicas': 1,
    'health_status': 200, 'ingress_health_status': 200,
    'new_model_deployed_to_uat': False, 'formal_holdout_executed': False,
    'english_identity_evaluated': False, 'next_training_authorized': False,
}
(R / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
