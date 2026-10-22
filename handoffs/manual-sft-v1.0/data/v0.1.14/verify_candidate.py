"""Local readback only: prove the two removals, System edit and CPU evidence."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.13'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    manifest = read(D / 'manifest.json')
    for name, digest in manifest['files_sha256'].items():
        assert sha(D / name) == digest, name
    protected = read(D / 'protected-inputs.json')
    for name, digest in protected.items():
        assert sha(ROOT / name) == digest, name
    parent_lines = (P / 'train.jsonl').read_bytes().splitlines(keepends=True)
    remaining = [(i, line) for i, line in enumerate(parent_lines) if i not in [1275, 1276]]
    assert (D / 'train.jsonl').read_bytes() == b''.join(line for i, line in remaining)
    rows = [json.loads(line) for i, line in remaining]
    assert len(rows) == 1325
    for text in [(D / 'train.jsonl').read_text(), (D / 'evaluation/custom-system.txt').read_text()]:
        assert not any(s in text for s in ['2026年7月8日', '2026-07-08', '2026/7/8'])
    assert (D / 'evaluation/custom-system.txt').read_text() == (P / 'evaluation/custom-system.txt').read_text().replace('成立于2026年7月8日，', '')
    changes = [json.loads(s) for s in (D / 'removed.jsonl').read_text().splitlines()]
    assert [c['parent_line_one_based'] for c in changes] == [1276, 1277]
    cfg, parent_cfg = read(D / 'training-config.json'), read(P / 'training-config.json')
    assert [s.replace(D.name, P.name) for s in cfg['full_argv']] == parent_cfg['full_argv']
    assert not cfg['execution_authorized'] and cfg['max_full_runs'] == 1
    assert sha(D / 'identity_loss3.py') == sha(P / 'identity_loss3.py')
    removed_keys = {c['messages_sha256'] for c in changes}
    keys, parent_keys = read(D / 'identity-keys.json'), read(P / 'identity-keys.json')
    for k in ['identity_message_sha256', 'raw_identity_message_sha256']:
        assert set(keys[k]) == set(parent_keys[k]) - removed_keys
    assert keys['identity_exposures'] == 234 and keys['unique_messages'] == 228
    checked = read(D / 'cpu-check/training-config.checked.json')
    assert checked['full_argv'] == cfg['full_argv'] and checked['smoke_overrides'] == cfg['smoke_overrides']
    binding = read(D / 'cpu-check/input-binding.json')
    assert binding['training_config_sha256'] == sha(D / 'cpu-check/training-config.checked.json')
    assert binding['dataset_sha256'] == sha(D / 'train.jsonl') == cfg['dataset_sha256']
    assert binding['identity_keys_sha256'] == sha(D / 'identity-keys.json')
    assert binding['checker_sha256'] == sha(D / 'cpu-check/check_cpu.py')
    report = read(D / 'cpu-check/report.json')
    assert report['verified'] and report['rows'] == report['actual_loader_rows'] == report['actual_pipeline_rows'] == 1325
    assert report['unchanged_encoding_and_masks_rows'] == 1325
    assert report['retained_identity_exposures'] == 234 and report['all_234_identity_exposures_answer_weight3']
    for k in ['overlength_rows', 'truncated_rows', 'silent_dropped_rows', 'empty_supervision_rows', 'weight_mismatch_rows']:
        assert report[k] == 0, k
    assert report['company_date_absent_from_train_and_system'] and report['new_boundary_rows_weight1']
    assert read(D / 'cpu-check/cpu-exit.json')['returncode'] == 0
    lineage = [json.loads(x) for x in (D / 'train-map.jsonl').read_text().splitlines()]
    audit = [json.loads(x) for x in (D / 'cpu-check/row-checks.jsonl').read_text().splitlines()]
    assert len(lineage) == len(audit) == 1325
    assert [x['parent_row_zero_based'] for x in lineage] == [i for i, line in remaining]
    assert all(x['weight_verified'] and x['unchanged_encoding_and_masks'] for x in audit)
    stats = read(D / 'statistics.json')['after']
    assert dict(Counter(r['dataset'] for r in rows)) == stats['source_exposures'] == report['source_exposures']
    assert sum(sum(m['role'] == 'assistant' for m in r['messages']) for r in rows) == stats['assistant_turns']
    ev = read(D / 'evaluation-config.json')
    assert ev['system_sha256'] == sha(ROOT / ev['system_path'])
    assert ev['chat_template'] == read(P / 'evaluation-config.json')['chat_template']
    assert sha(D / 'evaluation/json-schema-cases.jsonl') == sha(P / 'evaluation/json-schema-cases.jsonl')
    uat = read(D / 'cpu-check/uat-after-verification.json')
    assert uat['original_spec_equal'] and uat['cpu_pod_deleted'] and uat['after_ready'] == uat['after_available'] == 1
    assert not uat['gpu_requested'] and not uat['uat_mutation']
    result = {'verified': True, 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
              'version': D.name, 'rows': 1325, 'removed_parent_lines_one_based': [1276, 1277],
              'retained_rows_byte_for_byte_and_masks_unchanged': 1325,
              'founding_date_absent_from_train_and_system': True, 'only_system_date_phrase_removed': True,
              'remaining_exposures_unchanged': True, 'training_hyperparameters_unchanged': True,
              'remaining_identity_exposures_x3': 234, 'boundary_records_x1': 12,
              'protected_files_unchanged': len(protected), 'native_cpu_verified': True,
              'training_started': False, 'inference_executed': False, 'gpu_requested': False,
              'uat_mutation': False, 'temporary_cpu_pod_deleted': True,
              'dataset_sha256': sha(D / 'train.jsonl'), 'manifest_sha256': sha(D / 'manifest.json'),
              'proof_limit': 'Data and CPU preparation only; removal does not erase dates from existing LoRA weights or prove hallucinations fixed.',
              'sync_status': 'LOCAL_GIT_ONLY'}
    (D / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
