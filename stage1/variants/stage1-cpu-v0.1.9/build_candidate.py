"""Materialize only the five reviewed replacements; no training or inference."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
REL = D.relative_to(ROOT).as_posix()
PARENT = ROOT / 'stage1/variants/stage1-cpu-v0.1.8'
LOSS3 = ROOT / 'stage2/variants/identity-loss3-review'
PROPOSAL = ROOT / 'stage2/variants/chinese-minimal-review-v0.1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, obj):
    (D / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def key(messages):
    value = [{'role': m['role'], 'content': m['content']} for m in messages]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


proposal = json.loads((PROPOSAL / 'proposal.json').read_text())
assert sha(PARENT / 'train.jsonl') == proposal['source_files'][str((PARENT / 'train.jsonl').relative_to(ROOT))]['sha256']
assert sha(LOSS3 / 'training-config.json') == proposal['source_files'][str((LOSS3 / 'training-config.json').relative_to(ROOT))]['sha256']
before_lines = (PARENT / 'train.jsonl').read_bytes().splitlines(keepends=True)
after_lines = before_lines.copy()
changes = proposal['sample_changes']
for change in changes:
    i = change['parent_train_row_zero_based']
    assert json.loads(before_lines[i]) == change['before']
    assert sum(json.loads(line) == change['before'] for line in before_lines) == 1
    assert change['existing_exposures_of_this_exact_record'] == change['replacement_exposures'] == 1
    assert change['before']['dataset'] == change['after']['dataset']
    assert [m for m in change['before']['messages'] if m['role'] != 'assistant'] == [m for m in change['after']['messages'] if m['role'] != 'assistant']
    after_lines[i] = (json.dumps(change['after'], ensure_ascii=False) + '\n').encode()
    assert sum(json.loads(line) == change['after'] for line in after_lines) == 1
changed = [i for i, (a, b) in enumerate(zip(before_lines, after_lines)) if a != b]
assert changed == [894, 936, 1260, 1264, 1270]
target = b''.join(after_lines)
if (D / 'train.jsonl').exists():
    assert (D / 'train.jsonl').read_bytes() == target, 'Refuse to overwrite a different candidate'
else:
    (D / 'train.jsonl').write_bytes(target)
rows, old_rows = [json.loads(x) for x in after_lines], [json.loads(x) for x in before_lines]
assert len(rows) == len(old_rows) == 1275
counts = Counter(r['dataset'] for r in rows)
assert counts == Counter(r['dataset'] for r in old_rows)
assert all(a['messages'][0] == b['messages'][0] for a, b in zip(rows, old_rows))
digest = sha(D / 'train.jsonl')
(D / 'changes.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in changes))
(D / 'train-map.jsonl').write_text(''.join(json.dumps({
    'row_zero_based': i, 'parent_row_zero_based': i,
    'parent_messages_sha256': key(a['messages']), 'messages_sha256': key(b['messages']),
    'source': b['dataset'], 'changed': i in changed,
}) + '\n' for i, (a, b) in enumerate(zip(old_rows, rows))))
identity_keys = sorted({key(r['messages']) for r in rows if r['dataset'] == 'swift/self-cognition'})
save('identity-keys.json', {'dataset_path': REL + '/train.jsonl', 'dataset_sha256': digest,
                          'identity_exposures': 216, 'unique_messages': len(identity_keys),
                          'identity_message_sha256': identity_keys})
shutil.copyfile(LOSS3 / 'identity_loss3.py', D / 'identity_loss3.py')
cfg = json.loads((LOSS3 / 'training-config.json').read_text())
old_argv = cfg['full_argv'].copy()
replacements = {
    '/work/stage1/variants/stage1-cpu-v0.1.8/train.jsonl': '/work/' + REL + '/train.jsonl',
    '/work/stage2/variants/identity-loss3-review/identity_loss3.py': '/work/' + REL + '/identity_loss3.py',
    '/runwork/stage1-cpu-v0.1.8-identity-loss3/full/checkpoints': '/runwork/stage1-cpu-v0.1.9/full/checkpoints',
}
cfg['full_argv'] = [replacements.get(x, x) for x in old_argv]
cfg['smoke_overrides']['output_dir'] = '/runwork/stage1-cpu-v0.1.9/smoke/checkpoints'
cfg.update(plan='chinese-minimal-review-v0.1', data_version=D.name,
           dataset_sha256=digest, execution_authorized=False, resource_window=None,
           status='CPU_CHECK_PENDING_NO_TRAINING_AUTHORIZATION', config_revision='chinese-minimal-v0.1.9',
           recipe_change='Five reviewed Chinese response replacements; same identity x3 loss implementation and all training hyperparameters',
           runtime_validation='Pending actual Swift CPU encoding and loss-mask check',
           evaluation_config=REL + '/evaluation-config.json',
           cpu_validation_report=REL + '/cpu-check/report.json')
save('training-config.json', cfg)
save('config-diff.json', {
    'parent': 'stage2/variants/identity-loss3-review/training-config.json',
    'parent_sha256': sha(LOSS3 / 'training-config.json'),
    'argv_changes': [{'argument': next(x for x in reversed(old_argv[:i]) if x.startswith('--')), 'before': a, 'after': b}
                     for i, (a, b) in enumerate(zip(old_argv, cfg['full_argv'])) if a != b],
    'smoke_output_dir_changed_only': True,
    'training_hyperparameters_unchanged': True, 'loss_plugin_bytes_unchanged': True,
    'identity_key_index_regenerated_for_two_changed_identity_records': True,
    'normalization_rule_unchanged': True,
    'new_supervision': 'Two nonempty identity thoughts and their answer/EOS at x3; three positioning thoughts/answers/EOS at x1. Valid token count changes; denominator rule does not.',
})
(D / 'evaluation').mkdir(exist_ok=True)
shutil.copyfile(PROPOSAL / 'custom-system.proposed.txt', D / 'evaluation/custom-system.txt')
ev = json.loads((PARENT / 'evaluation-config.json').read_text())
ev.update(system_path=REL + '/evaluation/custom-system.txt', system_sha256=sha(D / 'evaluation/custom-system.txt'),
          purpose='Bind future Chinese development evaluation to the verified template, revised System, and mode budgets; no execution authorized',
          prior_scope='40 inference checks on the existing loss3 adapter, not v0.1.9 model quality',
          prior_protocol_check='stage2/diagnostics/chinese-minimal-check-20261020/REPORT.md',
          english_identity='DEFERRED; existing English development cases retained as history',
          seed=42, identity_seeds=[42, 43, 44], concurrency=1,
          server_seed=42, max_model_len=8192, repetition_penalty=1.0)
ev['request_modes'] = deepcopy(proposal['inference']['modes_proposed'])
for mode in ev['request_modes'].values():
    mode['chat_template_kwargs'] = {'enable_thinking': mode.pop('enable_thinking')}
save('evaluation-config.json', ev)
save('validation.json', {'verified_local_structure': True, 'actual_swift_cpu_check': 'PENDING',
                       'parent_sha256': sha(PARENT / 'train.jsonl'), 'dataset_sha256': digest,
                       'rows': len(rows), 'source_exposures': dict(counts),
                       'changed_rows_zero_based': changed, 'unchanged_raw_lines': 1270,
                       'all_user_turns_unchanged': True, 'added_rows': 0, 'removed_rows': 0,
                       'english_changes': 0, 'generic_changes': 0,
                       'training_started': False, 'inference_executed': False})
save('manifest.json', {'version': D.name, 'status': 'CPU_CHECK_PENDING_NO_TRAINING_AUTHORIZATION',
                      'parent_version': PARENT.name, 'parent_path': str((PARENT / 'train.jsonl').relative_to(ROOT)),
                      'parent_sha256': sha(PARENT / 'train.jsonl'), 'train_path': REL + '/train.jsonl',
                      'train_sha256': digest, 'rows': len(rows), 'changed_rows_zero_based': changed,
                      'source_exposures': dict(counts), 'added_rows': 0, 'removed_rows': 0,
                      'training_started': False, 'sync_status': 'LOCAL_GIT_ONLY',
                      'files_sha256': {'train.jsonl': digest}})
print(json.dumps({'version': D.name, 'rows': len(rows), 'changed': len(changed),
                  'data_sha256': digest, 'identity_keys': len(identity_keys)}))
