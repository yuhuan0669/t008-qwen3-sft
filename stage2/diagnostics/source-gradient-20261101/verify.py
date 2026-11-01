"""Verify the completed, read-only gradient diagnostic and its archived inputs."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
R = D.parents[2]
O = D / 'results'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

binding = read(D / 'input-binding.json')
manifest = read(D / 'inputs/manifest.json')
assert sha(D / 'inputs/manifest.json') == binding['manifest_sha256']
for name, meta in manifest['files'].items():
    assert sha(D / 'inputs' / name) == meta['sha256'], name
    assert (D / 'inputs' / name).stat().st_size == meta['bytes'], name
assert sha(R / 'stage1/variants/stage1-cpu-v0.1.22/train.jsonl') == binding['dataset_sha256']
assert sha(R / 'stage1/variants/stage1-cpu-v0.1.22/inference-system.txt') == binding['system_sha256']

done = read(O / 'completed.json')
assert done['complete'] and done['weights_unchanged']
assert done['optimizer_steps'] == done['new_generated_answers'] == 0
assert done['source_gradients'] == 1336 and done['probe_gradients'] == 60
for name, digest in done['files_sha256'].items():
    assert sha(O / name) == digest, name
cpu = read(O / 'encoding-check.json')
assert cpu == read(D / 'cpu-check.json')
assert cpu['native_masks_and_weights_match_all_rows'] and cpu['source_hashes_match']
assert cpu['rows'] == 1047 and cpu['unique_encodings'] == 668 and cpu['max_train_tokens'] == 2041
assert sum(g['rows'] for g in cpu['groups'].values()) == 1047
assert sum(g['valid_tokens'] for g in cpu['groups'].values()) == 928890
assert sum(g['weighted_units'] for g in cpu['groups'].values()) == 946600
for model in ['step50', 'step66']:
    state = read(O / (model + '-summary.json'))
    assert state['weights_unchanged'] and state['optimizer_steps'] == 0
    assert state['adapter_memory_sha256_before'] == state['adapter_memory_sha256_after']
    assert state['all_exposures_accounted'] == 1047
    assert state['all_valid_tokens_accounted'] == 928890

numeric = read(O / 'fp64-gradient-verification.json')
assert numeric['verified'] and numeric['weights_unchanged']
assert len(numeric['checks']) == 4
for check in numeric['checks']:
    assert abs(check['native_ce'] - check['chunked_ce']) < 2e-4
    assert check['gradient_relative_error_fp64'] < .025
    assert .9997 < check['gradient_cosine_fp64'] <= 1.000000001
native = read(O / 'native-projection-verification.json')
assert native['complete'] and native['weights_unchanged']
assert native['rows'] == 1047 and native['unique_encodings'] == 668
assert len(native['projections']) == 120
assert native['optimizer_steps'] == native['new_generations'] == 0
assert native['raw_sign_disagreements'] == 0 and native['scaled_sign_disagreements'] == 1

summary = read(D / 'SUMMARY.json')
assert summary['numeric_verification_status'] == 'COMPLETE_NATIVE_CROSSCHECK'
assert summary['max_row_group_relative_difference'] < 1e-4
assert summary['row_group_sign_disagreements'] == 0
sensitive = [e for e in summary['probe_directions'] if e['status'] == 'implementation_sensitive']
assert len(sensitive) == 1 and sensitive[0]['source'] == 'general'
assert sensitive[0]['probe'] == 'T021-R3300-G0456/observed_end/no_system'
identity = [e for e in summary['probe_directions'] if e['family'] == 'identity' and e['source'] == 'identity']
assert len(identity) == 8 and all(e['status'].startswith('decrease') for e in identity)

runtime = read(D / 'final-runtime.json')
assert runtime['uat_spec_unchanged'] and runtime['task_pod_deleted']
assert runtime['uat_replicas'] == runtime['uat_ready_replicas'] == 0
assert not runtime['uat_restored'] and not runtime['automatic_restore_authorized']
assert sha(D / 'results.tar.gz') == runtime['archive_sha256']
assert (D / 'results.tar.gz').stat().st_size == runtime['archive_bytes']

out = {
    'verified_at_utc': datetime.now(timezone.utc).isoformat(),
    'mechanical_verification_passed': True,
    'diagnostic_scope': 'Frozen v0.1.22 checkpoints50/66; full1047 exposures;30 fixed nonthinking token contrasts per checkpoint',
    'primary_source_backprops': 1336, 'primary_probe_backprops': 60,
    'additional_native_source_backprops': 668, 'additional_native_probe_backprops': 30,
    'source_exposures_each_checkpoint': 1047,
    'native_projection_pairs': 120, 'native_projection_sign_sensitive_pairs': 1,
    'sign_sensitive_pair_excluded_from_stable_findings': True,
    'original_fp32_cosine_superseded_by_fp64_audit': True,
    'training_data_unchanged': True, 'inference_system_unchanged': True,
    'weights_unchanged': True, 'optimizer_steps': 0, 'new_generated_answers': 0,
    'judge_calls': 0, 'new_training_candidate': False,
    'uat_still_paused': True, 'uat_spec_unchanged': True, 'diagnostic_pod_deleted': True,
    'quality_accepted': False, 'historical_causality_proven': False,
    'archive_sha256': runtime['archive_sha256'],
    'verified_artifacts_sha256': {n: sha(D / n) for n in [
        'REPORT.md', 'README.md', 'SUMMARY.json', 'protocol.json', 'input-binding.json', 'final-runtime.json',
        'diagnose.py', 'verify_numeric.py', 'analyze.py', 'collect.py',
        'results/fp64-gradient-verification.json', 'results/native-projection-verification.json']},
}
(D / 'verification.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in out.items() if k != 'verified_artifacts_sha256'}, ensure_ascii=False))
