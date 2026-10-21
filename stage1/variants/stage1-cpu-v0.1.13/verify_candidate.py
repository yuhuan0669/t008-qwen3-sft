"""Read current artifacts and prove data/config/native-CPU bindings; no cluster calls."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.12'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    manifest = read(D / 'manifest.json')
    for name, digest in manifest['files_sha256'].items():
        assert sha(D / name) == digest, name
    protected = read(D / 'protected-inputs.json')
    for name, digest in protected.items():
        assert sha(ROOT / name) == digest, name
    raw, previous = (D / 'train.jsonl').read_bytes(), (P / 'train.jsonl').read_bytes()
    assert raw.startswith(previous)
    rows = [json.loads(x) for x in raw.splitlines()]
    added = [json.loads(x) for x in (D / 'new-samples.jsonl').read_text().splitlines()]
    assert len(rows) == 1327 and len(added) == 12 and rows[1315:] == added
    review = ROOT / manifest['review_source']
    assert sha(review) == manifest['review_source_sha256']
    blocks = re.findall(r'^### (\d{2})｜([^\n]+)\n(.*?)(?=^### |^## |^---|\Z)', review.read_text(), re.M | re.S)
    assert len(blocks) == 12
    for row, (sid, title, text) in zip(added, blocks):
        turns = re.findall(r'\*\*(用户|助手)：\*\*\s*\n(.*?)(?=\n\*\*(?:用户|助手)：\*\*|\Z)', text, re.S)
        assert len(row['messages']) == len(turns)
        for m, (role, content) in zip(row['messages'], turns):
            assert m['role'] == ('user' if role == '用户' else 'assistant')
            expected = content.strip() if role == '用户' else '<think>\n\n</think>\n\n' + content.strip()
            assert m['content'] == expected, (sid, role)
    cfg, parent_cfg = read(D / 'training-config.json'), read(P / 'training-config.json')
    assert [v.replace(D.name, P.name) for v in cfg['full_argv']] == parent_cfg['full_argv']
    assert not cfg['execution_authorized'] and not cfg['resume'] and cfg['new_lora']
    assert sha(D / 'identity_loss3.py') == sha(P / 'identity_loss3.py')
    assert read(D / 'identity-keys.json')['identity_message_sha256'] == read(P / 'identity-keys.json')['identity_message_sha256']
    checked = read(D / 'cpu-check/training-config.checked.json')
    assert checked['full_argv'] == cfg['full_argv']
    assert checked['smoke_overrides'] == cfg['smoke_overrides']
    binding = read(D / 'cpu-check/input-binding.json')
    assert binding['training_config_sha256'] == sha(D / 'cpu-check/training-config.checked.json')
    assert binding['dataset_sha256'] == sha(D / 'train.jsonl') == cfg['dataset_sha256']
    assert binding['identity_keys_sha256'] == sha(D / 'identity-keys.json')
    assert binding['checker_sha256'] == sha(D / 'cpu-check/check_cpu.py')
    checked_manifest = read(D / 'cpu-check/manifest.checked.json')
    assert checked_manifest['files_sha256']['train.jsonl'] == sha(D / 'train.jsonl')
    stat = read(D / 'statistics.json')['after']
    assert dict(Counter(r['dataset'] for r in rows)) == stat['source_exposures']
    assert sum(sum(m['role'] == 'assistant' for m in r['messages']) for r in rows) == stat['assistant_turns']
    report = read(D / 'cpu-check/report.json')
    assert report['verified'] and report['rows'] == report['actual_loader_rows'] == report['actual_pipeline_rows'] == 1327
    assert report['unchanged_encoding_and_masks_rows'] == 1315
    assert report['new_boundary_rows_weight1'] and report['new_boundary_assistant_turns_supervised'] == 15
    for k in ['overlength_rows', 'truncated_rows', 'silent_dropped_rows', 'empty_supervision_rows', 'weight_mismatch_rows']:
        assert report[k] == 0, k
    assert report['dataset_sha256'] == sha(D / 'train.jsonl')
    assert report['source_exposures'] == stat['source_exposures']
    assert read(D / 'cpu-check/cpu-exit.json')['returncode'] == 0
    audit = [json.loads(x) for x in (D / 'cpu-check/row-checks.jsonl').read_text().splitlines()]
    assert len(audit) == 1327 and all(a['weight_verified'] for a in audit)
    assert all(a['unchanged_encoding_and_masks'] for a in audit[:1315])
    for name in ['custom-system.txt', 'rubric.md', 'json-schema-cases.jsonl']:
        assert sha(D / 'evaluation' / name) == sha(P / 'evaluation' / name)
    uat = read(D / 'cpu-check/uat-after-verification.json')
    assert uat['original_spec_equal'] and uat['cpu_pod_deleted'] and uat['after_ready'] == uat['after_available'] == 1
    assert not uat['gpu_requested'] and not uat['uat_mutation']
    runtime = read(D / 'cpu-check/runtime.json')
    assert not runtime['gpu_requested'] and 'nvidia.com/gpu' not in str(runtime['resources'])
    result = {'verified': True, 'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
              'version': D.name, 'rows': 1327, 'added_rows': 12, 'new_assistant_turns': 15,
              'old_rows_preserved_byte_for_byte': 1315, 'protected_files_unchanged': len(protected),
              'review_wording_preserved': True, 'training_hyperparameters_unchanged': True,
              'existing_exposures_and_identity_x3_unchanged': True, 'added_records_x1_and_weight1': True,
              'native_cpu_check_passed': True, 'training_started': False, 'inference_executed': False,
              'uat_mutation': False, 'gpu_requested': False, 'temporary_cpu_pod_deleted': True,
              'dataset_sha256': sha(D / 'train.jsonl'), 'manifest_sha256': sha(D / 'manifest.json'),
              'proof_limit': 'Encoding, lineage and configuration only; no quality or generalization claim.',
              'sync_status': 'LOCAL_GIT_ONLY'}
    (D / 'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
