"""Offline consistency check for the completed diagnostic; no cluster calls."""
import ast
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import tarfile

D = Path(__file__).resolve().parent
R = D.parents[2]
def read(p): return json.loads(p.read_text())
def jl(p): return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def ih(ids): return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()
def close(a, b): assert math.isclose(a, b, rel_tol=1e-5, abs_tol=5e-6), (a, b)

protocol = read(D/'inputs/protocol.json')
manifest = read(D/'inputs/manifest.json')
binding = read(D/'input-binding.json')
started = read(D/'execution-start.json')
complete = read(D/'results/completed.json')
encoding = read(D/'results/encoding-check.json')
summary = read(D/'SUMMARY.json')
final = read(D/'final-runtime.json')
assert sha(D/'inputs/manifest.json') == binding['input_manifest_sha256'] == started['input_manifest_sha256'] == encoding['input_manifest_sha256']
assert sha(D/'diagnose.py') == started['script_sha256'] == encoding['script_sha256']
for name, meta in manifest['files'].items():
    p = D/'inputs'/name
    assert sha(p) == meta['sha256'] and p.stat().st_size == meta['bytes'], name
for name, digest in complete['files_sha256'].items(): assert sha(D/'results'/name) == digest, name
for name, digest in summary['files_sha256'].items(): assert sha(D/name) == digest, name
assert sha(D/'inputs/system.txt') == binding['system_sha256'] == encoding['system_sha256']
assert sha(D/'inputs/thinking-prefill.jinja') == binding['template_sha256'] == encoding['template_sha256']
dataset = R/'stage1/variants/stage1-cpu-v0.1.22/train.jsonl'
assert sha(dataset) == binding['dataset_sha256']
data = jl(dataset)
assert len(data) == 1047
selected = read(D/'inputs/training-controls.json')
assert selected['dataset_sha256'] == binding['dataset_sha256']
assert [r['line'] for r in selected['rows']] == binding['training_control_lines']
for row in selected['rows']: assert data[row['line']-1] == row['row']
assert len(selected['rows']) == 6 and len(read(D/'inputs/cases.json')['cases']) == 12

groups = read(D/'results/encoded.json')
encoded = {g['id']: g for g in groups}
assert len(groups) == len(encoded) == 34
models = protocol['models']
assert models == ['base', 'v0.1.22', 'v0.1.25']
expected_scores = {(g['id'], model, ref) for g in groups for model in models for ref in g['targets']}
expected_prefixes = {(g['id'], model) for g in groups for model in models}
expected_kl = {(g['id'], model, position, ref) for g in groups for model in models[1:]
               for position, ref in [('first', None)] + [('path', ref) for ref in g['targets']]}
scores = jl(D/'results/scores.jsonl')
prefixes = jl(D/'results/prefixes.jsonl')
kls = jl(D/'results/kl.jsonl')
assert len(scores) == len(expected_scores) == complete['scores'] == 174
assert len(prefixes) == len(expected_prefixes) == complete['prefix_distributions'] == 102
assert len(kls) == len(expected_kl) == complete['kl_comparisons'] == 184
assert {(r['id'], r['model'], r['reference']) for r in scores} == expected_scores
assert {(r['id'], r['model']) for r in prefixes} == expected_prefixes
assert {(r['id'], r['model'], r['position'], r['reference']) for r in kls} == expected_kl
pm = {(r['id'], r['model']): r for r in prefixes}
for row in [*scores, *prefixes, *kls]:
    g = encoded[row['id']]
    assert row['prefix_sha256'] == ih(g['prefix'])
    for k in ['source', 'category', 'condition', 'case_id']: assert row[k] == g[k]
for row in scores:
    g = encoded[row['id']]; target = g['targets'][row['reference']]
    n = len(target)
    assert 1 <= n <= 32 and row['tokens'] == n and row['prompt_tokens'] == len(g['prefix'])
    assert row['target_sha256'] == ih(target)
    assert all(len(row[k]) == n for k in ['token_logp', 'token_ranks', 'filtered_probabilities'])
    assert all(math.isfinite(v) and v <= 1e-6 for v in row['token_logp'])
    assert all(math.isfinite(v) and 0 <= v <= 1 for v in row['filtered_probabilities'])
    assert all(isinstance(v, int) and v >= 1 for v in row['token_ranks'])
    assert row['filtered_zero_tokens'] == sum(v == 0 for v in row['filtered_probabilities'])
    close(row['mean_nll'], -statistics.mean(row['token_logp']))
    close(row['sum_logp'], sum(row['token_logp']))
    first = next(v for v in pm[(row['id'], row['model'])]['wanted_tokens'] if v['id'] == target[0])
    close(first['probability'], math.exp(row['token_logp'][0]))
    close(first['filtered_probability'], row['filtered_probabilities'][0])
    assert first['rank'] == row['token_ranks'][0]
for row in kls:
    g = encoded[row['id']]
    n = 1 if row['position'] == 'first' else len(g['targets'][row['reference']])
    assert len(row['kl_base_to_adapter']) == n
    if row['position'] == 'path': assert row['target_sha256'] == ih(g['targets'][row['reference']])
    assert all(math.isfinite(v) and v >= -1e-6 for v in row['kl_base_to_adapter'])
    close(row['mean_kl'], statistics.mean(row['kl_base_to_adapter']))
    assert 0 <= row['mean_total_variation'] <= 1 + 1e-6
assert complete['adapter_memory_unchanged'] and encoding['base_and_adapter_hashes_match']
assert encoding['native_membership_all_retained'] and encoding['KL_formula_checked'] and encoding['sampling_filter_checked']
assert not any(complete[k] for k in ['training', 'backward_calls', 'new_generated_answers', 'judge_calls', 'deployment', 'uat_restore'])
calls = [n.func for n in ast.walk(ast.parse((D/'diagnose.py').read_text())) if isinstance(n, ast.Call)]
for fn in calls:
    name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ''
    assert name not in {'generate', 'backward', 'Trainer', 'SFTTrainer', 'AdamW', 'Adam', 'SGD'}
archive = D/'results.tar.gz'
assert sha(archive) == final['archive_sha256'] and archive.stat().st_size == final['archive_bytes']
with tarfile.open(archive) as tar:
    for name, digest in complete['files_sha256'].items():
        assert hashlib.sha256(tar.extractfile('results/'+name).read()).hexdigest() == digest
assert read(D/'exit.json')['exit_code'] == 0
assert read(D/'attempt1-exit.json')['exit_code'] == 1
assert read(D/'preflight-correction.json')['initial_model_scores'] == 0
assert final['replicas'] == final['ready_replicas'] == 0
assert final['uat_spec_unchanged'] and final['task_pod_deleted']
assert not final['uat_restored'] and not final['automatic_restore_authorized']
hold = read(R/'stage2/uat-pause-hold.json')
assert hold['active'] and not hold['automatic_restore_authorized']

out = {'verified': True, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
    'scores': len(scores), 'prefix_distributions': len(prefixes), 'kl_comparisons': len(kls),
    'all_expected_keys_unique_complete': True, 'same_prefix_and_target_ids_across_models': True,
    'finite_scores_and_valid_KL': True, 'first_token_scores_match_prefix_distribution': True,
    'native_training_membership_verified': True, 'input_and_result_hashes_match': True,
    'dataset_bytes_unchanged': True, 'adapter_memory_unchanged': True,
    'new_generated_answers': 0, 'training': False, 'deployment': False, 'judge_calls': 0,
    'uat_paused': True, 'uat_restored': False, 'task_pod_deleted': True,
    'runtime_evidence_time_utc': final['checked_at_utc'], 'live_cluster_calls_in_this_verifier': 0,
    'formal_acceptance': False, 'sync_status': 'LOCAL_GIT_ONLY',
    'files_sha256': {str(p.relative_to(D)): sha(p) for p in [D/'REPORT.md', D/'SUMMARY.json', D/'DETAILS.md',
        D/'input-binding.json', D/'diagnose.py', D/'analyze.py', Path(__file__), D/'final-runtime.json',
        D/'execution-start.json', D/'results/completed.json']}}
(D/'verification.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k != 'files_sha256'}))
