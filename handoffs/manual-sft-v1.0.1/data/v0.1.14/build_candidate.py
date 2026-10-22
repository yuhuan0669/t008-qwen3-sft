"""Remove the two company-founding examples and one System phrase; never train."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.13'
REMOVED = {1276, 1277}  # One-based parent lines, never candidate row numbers.
PARENT_SHA = '70f7321bc2f277f898dbc6e845eb626cb61300bcb9adebe3273dcbe173ac4d9a'
PHRASE = '成立于2026年7月8日，'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def key(row):
    messages = [{'role': m['role'], 'content': m['content']} for m in row['messages']]
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def save(name, obj):
    (D / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def jsonl(name, rows):
    (D / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in rows))


def main():
    assert sha(P / 'train.jsonl') == PARENT_SHA
    original = (P / 'train.jsonl').read_bytes().splitlines(keepends=True)
    assert len(original) == 1327
    parent = list(map(json.loads, original))
    found = {i + 1 for i, r in enumerate(parent) if '2026年7月8日' in str(r['messages'])}
    assert found == REMOVED
    raw = b''.join(line for i, line in enumerate(original, 1) if i not in REMOVED)
    if (D / 'train.jsonl').exists():
        assert (D / 'train.jsonl').read_bytes() == raw
    else:
        (D / 'train.jsonl').write_bytes(raw)
    assert PHRASE.encode() not in raw and '2026年7月8日'.encode() not in raw
    rows = [json.loads(x) for x in raw.splitlines()]
    digest = sha(D / 'train.jsonl')
    before_map = [json.loads(x) for x in (P / 'train-map.jsonl').read_text().splitlines()]
    mapping, changes = [], []
    for i, row in enumerate(parent):
        if i + 1 in REMOVED:
            changes.append({'operation': 'remove', 'parent_line_one_based': i + 1,
                            'parent_row_zero_based': i, 'candidate_row_zero_based': None,
                            'reason': 'User requested removal of company founding date from training data.',
                            'before': row, 'after': None, 'messages_sha256': key(row)})
        else:
            n = len(mapping)
            mapping.append({'row_zero_based': n, 'line_one_based': n + 1,
                            'parent_version': P.name, 'parent_row_zero_based': i,
                            'parent_line_one_based': i + 1, 'operation': 'preserve',
                            'source': row['dataset'], 'group': before_map[i]['group'],
                            'messages_sha256': key(row), 'parent_messages_sha256': key(row),
                            'provenance_detail': '../' + P.name + '/train-map.jsonl'})
    assert len(rows) == len(mapping) == 1325
    jsonl('train-map.jsonl', mapping)
    jsonl('removed.jsonl', changes)
    jsonl('changes.jsonl', changes)
    removed_keys = {key(parent[i - 1]) for i in REMOVED}
    binding = json.loads((P / 'identity-keys.json').read_text())
    for name in ['identity_message_sha256', 'raw_identity_message_sha256']:
        binding[name] = [k for k in binding[name] if k not in removed_keys]
    binding.update(dataset_path=str((D / 'train.jsonl').relative_to(ROOT)), dataset_sha256=digest,
                   identity_exposures=234, unique_messages=len(binding['raw_identity_message_sha256']),
                   matching_key_count=len(binding['identity_message_sha256']))
    save('identity-keys.json', binding)
    aliases = json.loads((P / 'native-identity-key-aliases.json').read_text())
    aliases.update(dataset_sha256=digest, evidence='../' + P.name + '/native-identity-key-aliases.json',
                   reason='Retain the same four normalized identity aliases; parent line numbers shift after two removals.')
    for a in aliases['aliases']:
        old = a['line_one_based']
        a['line_one_based'] = old - sum(n < old for n in REMOVED)
    save('native-identity-key-aliases.json', aliases)
    shutil.copyfile(P / 'identity_loss3.py', D / 'identity_loss3.py')
    (D / 'evaluation').mkdir(exist_ok=True)
    system_before = (P / 'evaluation/custom-system.txt').read_text()
    assert system_before.count(PHRASE) == 1
    (D / 'evaluation/custom-system.txt').write_text(system_before.replace(PHRASE, ''))
    shutil.copyfile(P / 'evaluation/json-schema-cases.jsonl', D / 'evaluation/json-schema-cases.jsonl')
    ev = json.loads((P / 'evaluation-config.json').read_text())
    ev.update(purpose='v0.1.14 CPU only; founding date removed from active System. Historical evaluation references retained, not executed.',
              execution_authorized=False, system_path=str((D / 'evaluation/custom-system.txt').relative_to(ROOT)),
              system_sha256=sha(D / 'evaluation/custom-system.txt'))
    save('evaluation-config.json', ev)
    cfg_before = json.loads((P / 'training-config.json').read_text())
    cfg = deepcopy(cfg_before)
    cfg['full_argv'] = [x.replace(P.name, D.name) for x in cfg['full_argv']]
    cfg['smoke_overrides']['output_dir'] = cfg['smoke_overrides']['output_dir'].replace(P.name, D.name)
    cfg.update(plan='remove-company-founding-date', data_version=D.name, config_revision='remove-founding-date-v0.1.14',
               dataset_rows=1325, dataset_sha256=digest, execution_authorized=False, resource_window=None,
               status='LOCAL_READY_CPU_PENDING', runtime_validation='PENDING fresh native CPU encoding.',
               recipe_change='Remove only parent lines 1276/1277 and the company founding-date System phrase; preserve all other data and hyperparameters.',
               evaluation_config=str((D / 'evaluation-config.json').relative_to(ROOT)), cpu_validation_report=None,
               estimated_full_optimizer_steps=math.ceil(len(rows) / 16))
    assert [x.replace(D.name, P.name) for x in cfg['full_argv']] == cfg_before['full_argv']
    save('training-config.json', cfg)
    before_stats = json.loads((P / 'statistics.json').read_text())['after']
    after_stats = deepcopy(before_stats)
    after_stats.update(rows=1325, unique_message_records=len({key(r) for r in rows}),
                       source_exposures=dict(Counter(r['dataset'] for r in rows)),
                       group_exposures=dict(Counter(x['group'] for x in mapping)),
                       assistant_turns=before_stats['assistant_turns'] - 2)
    for name in ['record_format_exposures', 'assistant_turn_mode_counts']:
        after_stats[name]['identity/empty_think'] -= 1
        after_stats[name]['identity/nonempty_think'] -= 1
    after_stats['identity_first_user_language_marker']['first_user_has_han'] -= 2
    save('statistics.json', {'version': D.name, 'parent': P.name, 'before': before_stats, 'after': after_stats,
                             'added_rows': 0, 'removed_rows': 2, 'changed_retained_rows': 0,
                             'unchanged_parent_raw_lines': 1325, 'removed_parent_lines_one_based': sorted(REMOVED),
                             'supervised_tokens': {'status': 'PENDING_NATIVE_SWIFT_ENCODING'}})
    save('config-diff.json', {'parent': str((P / 'training-config.json').relative_to(ROOT)),
                             'argv_changes': [{'before': a, 'after': b} for a, b in zip(cfg_before['full_argv'], cfg['full_argv']) if a != b],
                             'training_hyperparameters_unchanged': True, 'loss_plugin_bytes_unchanged': True,
                             'remaining_exposures_and_weights_unchanged': True, 'identity_index_removed_only_date_keys': sorted(removed_keys),
                             'dataset_rows': {'before': 1327, 'after': 1325}, 'identity_exposures': {'before': 236, 'after': 234},
                             'estimated_steps': {'before': 83, 'after': 83}, 'system_removed_only': PHRASE,
                             'native_cpu_encoding_executed': False})
    save('manifest.json', {'version': D.name, 'parent': P.name, 'parent_sha256': PARENT_SHA,
                          'train_sha256': digest, 'dataset_sha256': digest, 'rows': 1325,
                          'files_sha256': {'train.jsonl': digest}, 'removed_rows': 2,
                          'removed_parent_lines_one_based': sorted(REMOVED), 'retained_parent_rows': 1325,
                          'training_authorized': False, 'training_started': False, 'inference_executed': False,
                          'sync_status': 'LOCAL_GIT_ONLY'})
    print(json.dumps({'rows': 1325, 'removed': 2, 'sha256': digest, 'system_sha256': ev['system_sha256']}))


if __name__ == '__main__':
    main()
