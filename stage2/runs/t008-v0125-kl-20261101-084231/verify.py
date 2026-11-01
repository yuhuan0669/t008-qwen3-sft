"""Verify saved evidence only. Does not train, infer, or change a service."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math
import struct
import tarfile
import zipfile

D = Path(__file__).resolve().parent
R = D.parents[2]
V = R / 'stage1/variants/stage1-cpu-v0.1.22'
P = R / 'stage2/variants/base-retention-review'

def read(p):
    return json.loads(p.read_text())

def jl(p):
    return [json.loads(s) for s in p.read_text().splitlines()]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

for name, digest in read(V / 'FILES.sha256.json')['files'].items():
    assert sha(V / name) == digest, name
binding = read(D / 'execution-code-binding.json')
for name, digest in binding['sha256'].items():
    assert sha(D / name) == digest, name
for name in ['retention.py', 'retention-config.json', 'membership.json']:
    assert (D / 'retention' / name).read_bytes() == (P / name).read_bytes(), name

full = read(D / 'outputs/full/run_manifest.json')
smoke = read(D / 'outputs/smoke/run_manifest.json')
cpu = read(D / 'cpu-report.json')
kl_cpu = read(D / 'retention-cpu-report.json')
assert full['training_verified'] and full['global_step'] == 66 and full['epoch'] == 1.0
assert smoke['training_verified'] and smoke['global_step'] == 3
assert full['command'] == read(D / 'expected-full-command.json')
assert full['source_commit'] == binding['source_git_commit']
assert full['data_sha256'] == cpu['dataset_sha256'] == kl_cpu['dataset_sha256'] == sha(V / 'train.jsonl')
assert full['rows'] == cpu['rows'] == cpu['actual_loader_rows'] == cpu['actual_pipeline_rows'] == 1047
assert cpu['identity_exposures'] == 234 and cpu['max_tokens'] == 2041
assert cpu['overlength_rows'] == cpu['silent_dropped_rows'] == cpu['truncated_rows'] == 0
assert cpu['all_identity_answer_weights_verified3'] and cpu['prompt_and_empty_think_masked']
assert all(not any(m['role'] == 'system' for m in row['messages']) for row in jl(V / 'train.jsonl'))
assert kl_cpu['verified'] and kl_cpu['native_encoded_rows_checked'] == 1047
assert kl_cpu['totals'] == {'retention_rows': 770, 'retention_tokens': 917954, 'rows': 1047,
                           'supervised_tokens': 928890, 'weighted_units': 946600.0}
modules = {'q_proj', 'k_proj', 'v_proj', 'o_proj', 'gate_proj', 'up_proj', 'down_proj'}
for manifest in [smoke, full]:
    assert manifest['retention_metrics_verified']
    assert manifest['retention']['coefficient'] == manifest['retention']['temperature'] == 1
    assert manifest['retention']['retention_rows'] == 770
    for key, name in [('config_sha256', 'retention-config.json'), ('plugin_sha256', 'retention.py'),
                      ('membership_sha256', 'membership.json')]:
        assert manifest['retention'][key] == sha(D / 'retention' / name)
    assert manifest['adapter_scope']['verified']
    assert manifest['adapter_scope']['parameter_count'] == 21823488
    assert manifest['adapter_scope']['tensor_count'] == 504
    assert set(manifest['adapter_scope']['target_modules']) == modules
    scalars = read(D / ('outputs/' + manifest['mode'] + '/training-scalars.json'))['scalars']
    assert all(math.isfinite(x['value']) for x in scalars)
    values = [x['value'] for x in scalars if x['tag'] == 'train/retention_kl_general_microbatch_mean']
    assert values and max(values) > 1e-8

model = read(D / 'model-local-copy.json')
assert model['verified'] and model['adapter_files_verified']
assert sha(R / model['path']) == full['adapter_package_sha256'] == full['clearml_model_readback_sha256']
with zipfile.ZipFile(R / model['path']) as z:
    cfg = json.loads(z.read('adapter_config.json'))
    assert set(cfg['target_modules']) == modules
    assert cfg['r'] == 8 and cfg['lora_alpha'] == 32 and cfg['lora_dropout'] == 0.05
    data = z.read('adapter_model.safetensors')
    n = struct.unpack('<Q', data[:8])[0]
    tensors = {k: v for k, v in json.loads(data[8:8 + n]).items() if k != '__metadata__'}
    assert sum(math.prod(t['shape']) for t in tensors.values()) == 21823488
    assert len(tensors) == 504
    assert all('.lora_' in k and any('.' + m + '.' in k for m in modules) for k in tensors)

complete = read(D / 'evaluation/complete.json')
results = jl(D / 'evaluation/results.jsonl')
assert complete['count'] == len(results) == 208
assert sha(D / 'evaluation/results.jsonl') == complete['results_sha256']
assert complete['attempts'] == 208 + complete['technical_retries']
assert read(D / 'evaluation/server-input-verification.json') == {'matched': 80, 'all_equal': True}
raw = read(D / 'raw-evidence-readback.json')
archive = D / raw['local_path']
assert raw['verified'] and sha(archive) == raw['sha256']
with tarfile.open(archive) as t:
    for result in results:
        path = result['raw_path']
        assert json.load(t.extractfile(path + '/request.json')) == result['request']
        assert json.load(t.extractfile(path + '/response.raw.json')) == result['response']
rows = jl(D / 'evaluation/combined.jsonl')
assert len(rows) == 832
assert Counter(r['model'] for r in rows) == dict.fromkeys(
    ['original_base', 'v0.1.14', 'candidate_v0.1.22', 'candidate_v0.1.25'], 208)
assert len({(r['model'], r['group'], r['case_id'], r['repeat']) for r in rows}) == 832
reuse = read(D / 'evaluation/reuse-summary.json')
assert sha(R / reuse['source']) == reuse['source_sha256']
assert sha(D / 'evaluation/reused-responses.jsonl') == reuse['selected_sha256']
semantic = read(D / 'evaluation/semantic-summary.json')
queue = read(D / 'evaluation/review-queue.json')
assert semantic['slots'] == 832 and semantic['unreviewed_slots'] == semantic['unreviewed_unique'] == 0
for name, digest in semantic['input_binding']['files_sha256'].items():
    assert sha(D / 'evaluation' / name) == digest, name
review = read(D / 'evaluation/review-evidence.json')
assert review['slots'] == 832 and review['unique_reviewed'] == semantic['unique_reviewed']
assert review['new_unique_root_read'] == queue['new_unique_review_required']
assert sha(D / 'evaluation' / review['archive']) == review['archive_sha256']
for name, digest in review['files_sha256'].items():
    assert sha(D / 'evaluation' / name) == digest, name

state = read(D / 'window-state.json')
final = read(D / 'final-runtime-readback.json')
assert state['paused'] and not state['restored'] and not state['automatic_restore']
assert state['task_gpu_cleaned'] and state['uat_spec_equal_except_replicas']
before = read(D / 'vllm-before.json')
paused = read(D / 'uat-paused-final.json')
expected = dict(before['spec'])
expected['replicas'] = 0
assert expected == paused['spec'] and before['metadata']['uid'] == paused['metadata']['uid']
assert final['spec_equal_except_replicas'] and final['replicas'] == final['ready_replicas'] == 0
assert not final['remaining_task_workloads']
hold = read(R / 'stage2/uat-pause-hold.json')
assert hold['active'] and hold['run_id'] == state['inherited_pause_run']
assert not hold['automatic_restore_authorized']
out = {
    'verified': True, 'utc': datetime.now(timezone.utc).isoformat(),
    'data_rows': 1047, 'data_changed': False, 'identity_exposures': 234,
    'identity_loss_multiplier': 3, 'full_steps': 66, 'full_runs': 1, 'smoke_steps': 3,
    'trainable_parameters': 21823488, 'target_modules': sorted(modules),
    'retention_coefficient': 1, 'retention_temperature': 1,
    'retention_rows': 770, 'retention_tokens': 917954, 'retention_metrics_verified': True,
    'new_generations': 208, 'reused_responses': 624, 'reviewed_unique': semantic['unique_reviewed'],
    'unreviewed_slots': 0, 'raw_request_response_pairs_verified': 208, 'server_input_matches': 80,
    'technical_retries': complete['technical_retries'], 'uat_paused': True, 'uat_restored': False,
    'deployment_spec_equal_except_replicas': True, 'automatic_restore_authorized': False,
    'model_deployed': False, 'external_judge_called': False, 'quality_accepted': False,
    'files_sha256': {str(p.relative_to(D)): sha(p) for p in [
        D / 'outputs/full/run_manifest.json', D / 'evaluation/semantic-summary.json',
        D / 'evaluation/review-evidence.json', D / 'RESULT.md',
        D / 'raw-evidence-readback.json', D / 'final-runtime-readback.json']}
}
(D / 'execution-verification.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out))
