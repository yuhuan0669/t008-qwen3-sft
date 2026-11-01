"""Read-only verification of the completed run; never launches cluster work."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import math

D = Path(__file__).resolve().parent
R = D.parents[2]
V = R / 'stage1/variants/stage1-cpu-v0.1.22'

def read(path):
    return json.loads(path.read_text())

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines()]

frozen = read(V / 'FILES.sha256.json')['files']
for name, expected in frozen.items():
    assert sha(V / name) == expected, name
for name, expected in read(D / 'config-diff.json')['unchanged_artifacts'].items():
    assert sha(R / name) == expected, name
for name, expected in read(D / 'execution-code-binding.json')['sha256'].items():
    assert sha(D / name) == expected, name

full = read(D / 'outputs/full/run_manifest.json')
smoke = read(D / 'outputs/smoke/run_manifest.json')
cpu = read(D / 'cpu-report.json')
assert full['command'] == read(D / 'expected-full-command.json')
assert full['identity_loss_multiplier']==1 and full['loss_plugin_sha256']==sha(D/'loss/identity_loss3.py')
assert full['training_verified'] and full['training_exit_code'] == 0
assert full['global_step'] == 66 and full['epoch'] == 1
assert smoke['training_verified'] and smoke['global_step'] == 3
assert full['rows'] == cpu['rows'] == cpu['actual_loader_rows'] == cpu['actual_pipeline_rows'] == 1047
assert full['data_sha256'] == sha(V / 'train.jsonl') == cpu['dataset_sha256']
assert cpu['max_tokens'] == 2041
assert not any(cpu[k] for k in ['overlength_rows', 'truncated_rows', 'silent_dropped_rows', 'empty_supervision_rows'])
assert cpu['prompt_and_empty_think_masked'] and cpu['identity_multiplier_after']==1 and cpu['all_input_ids_labels_identical']
scalars = read(D / 'outputs/full/training-scalars.json')
assert all(math.isfinite(x['value']) for x in scalars['scalars'])
local_model = read(D / 'model-local-copy.json')
assert local_model['verified'] and local_model['adapter_files_verified']
assert sha(R / local_model['path']) == full['adapter_package_sha256'] == full['clearml_model_readback_sha256']

complete = read(D / 'evaluation/complete.json')
assert complete['count'] == complete['attempts'] == 556 and complete['technical_retries'] == 0
assert sha(D / 'evaluation/results.jsonl') == complete['results_sha256']
assert read(D / 'evaluation/server-input-verification.json') == {'matched': 196, 'all_equal': True}
binding = read(D / 'evaluation/runtime-binding.json')
alias = binding['aliases']['candidate_v0.1.22-loss1']
adapter = binding['adapters']['candidate_v0.1.22-loss1']
assert adapter['files'] == full['adapter_files'] and D.name in adapter['path']
served = {x['id']: x for x in read(D / 'evaluation/models.json')['data']}
assert served[alias]['root'] == adapter['path']
assert binding['server_argv'] == read(D / 'evaluation/vllm-command.json')
assert all(x['request']['model'] == x['response']['model'] == alias
           for x in lines(D / 'evaluation/results.jsonl'))
raw = read(D / 'raw-content-verification.json')
assert raw['verified'] and raw['requests_and_responses_equal_to_results'] == 556
assert sha(D / 'evaluation/raw-evidence.tar.gz') == raw['archive_sha256']
rows = lines(D / 'evaluation/combined.jsonl')
slots = {(r['model'], r['group'], r['case_id'], r['repeat']) for r in rows}
assert len(slots) == len(rows) == 2780
assert Counter(r['model'] for r in rows) == dict.fromkeys(['original_base', 'v0.1.14', 'v0.1.16', 'candidate_v0.1.22','candidate_v0.1.22-loss1'], 556)

reuse = read(D / 'evaluation/reuse-summary.json')
assert sha(R / reuse['source']) == reuse['source_sha256']
assert sha(D / 'evaluation/reused-responses.jsonl') == reuse['selected_sha256']
prior_summary_path = R / reuse['semantic_summary_path']
assert sha(prior_summary_path) == reuse['semantic_summary_sha256']
prior_summary = read(prior_summary_path)
for name, expected in prior_summary['input_binding']['files_sha256'].items():
    assert sha(prior_summary_path.parent / name) == expected
summary = read(D / 'evaluation/semantic-summary.json')
assert summary['slots'] == 2780 and summary['unique_reviewed'] == summary['unique_answers']
assert summary['unreviewed_slots'] == summary['unreviewed_unique'] == 0
for name, expected in summary['input_binding']['files_sha256'].items():
    assert sha(D / 'evaluation' / name) == expected, name
labels = {v['review_id']: v for p in (D / 'evaluation/review').glob('verdicts-*.jsonl') for v in lines(p)}
for v in lines(D / 'evaluation/review/root-corrections.jsonl'):
    labels[v['review_id']].update(v['corrected'])
assert hashlib.sha256(json.dumps(labels, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest() == summary['input_binding']['effective_labels_sha256']
review_archive = read(D / 'evaluation/review-evidence.json')
assert sha(D / review_archive['archive']) == review_archive['archive_sha256']
for name, expected in review_archive['files'].items():
    assert sha(D / 'evaluation' / name) == expected, name

health = read(D / 'uat-health-verification.json')
state = read(D / 'window-state.json')
assert state['restored'] and not state['paused'] and state['service_spec_equal']
assert read(D / 'vllm-before.json')['spec'] == read(D / 'uat-restored.json')['spec']
assert health['verified'] and health['ready_replicas'] == 1 and health['internal_health'] == 200
assert len(health['public_health_samples']) == 2 and all(x['status'] == '200' for x in health['public_health_samples'])
assert health['aliases'] == ['octa-carbon-v1', 'octa-carbon-sft-v0114', 'octa-carbon-sft-v0116']
final_runtime = read(D / 'final-runtime-readback.json')
assert final_runtime['ready_replicas'] == 1 and final_runtime['spec_equal']
assert not final_runtime['remaining_task_workloads']

result = {
    'verified_at_utc': datetime.now(timezone.utc).isoformat(),
    'execution_verified': True, 'frozen_files_unchanged': len(frozen),
    'rows': 1047, 'identity_exposures': 234, 'data_sha256': full['data_sha256'],
    'smoke_steps': 3, 'full_runs': 1, 'full_steps': 66, 'epoch': 1,
    'only_training_change': 'identity multiplier3->1', 'native_encoding_compared': True,
    'adapter_sha256': full['adapter_package_sha256'], 'clearml_and_local_model_verified': True,
    'new_generations': 556, 'technical_retries': 0, 'server_token_sequences_matched': 196,
    'inference_adapter_and_request_alias_verified': True,
    'raw_pairs_verified': 556, 'comparison_slots': 2780, 'reused_slots': 2224,
    'reviewed_unique': summary['unique_reviewed'], 'unreviewed_slots': 0,
    'root_correction_count': len(lines(D / 'evaluation/review/root-corrections.jsonl')),
    'local_semantic_archive_verified': True,
    'uat_restored': True, 'deployment_spec_equal': True, 'health_http': 200,
    'quality_accepted': False, 'new_model_deployed': False,
    'next_training_authorized': False, 'external_judge_called': False,
    'evidence_sha256': {str(p.relative_to(D)): sha(p) for p in [
        D / 'outputs/full/run_manifest.json', D / 'outputs/smoke/run_manifest.json',
        D / 'evaluation/semantic-summary.json', D / 'evaluation/review/root-audit.json',
        D / 'uat-health-verification.json', D / 'raw-content-verification.json',
        D / 'final-runtime-readback.json', D / 'evaluation/review-evidence.json']}
}
(D / 'execution-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(result, ensure_ascii=False))
