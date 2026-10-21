"""Append the 12 reviewed conversations; CPU preparation only, never train."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import re
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARENT = D.parent / 'stage1-cpu-v0.1.12'
REVIEW = ROOT / 'stage1/review/company-boundaries-12-review-v0.1.md'
PARENT_SHA = '89da792c5b91a4b5cecda1a90322edc03fdc1f43e6bd0a52082c35e49e81ec8f'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def key(row):
    messages = [{'role': m['role'], 'content': m['content']} for m in row['messages']]
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def save_jsonl(name, rows):
    (D / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))


def rebind(value):
    if isinstance(value, str):
        return value.replace(PARENT.name, D.name)
    if isinstance(value, list):
        return [rebind(x) for x in value]
    if isinstance(value, dict):
        return {k: rebind(v) for k, v in value.items()}
    return value


def main():
    assert sha(PARENT / 'train.jsonl') == PARENT_SHA
    raw_parent = (PARENT / 'train.jsonl').read_bytes()
    parent = [json.loads(x) for x in raw_parent.splitlines()]
    assert len(parent) == 1315 and raw_parent.endswith(b'\n')
    text = REVIEW.read_text()
    blocks = re.findall(r'^### (\d{2})｜([^\n]+)\n(.*?)(?=^### |^## |^---|\Z)', text, re.M | re.S)
    assert len(blocks) == 12
    added, changes, mapping = [], [], []
    for n, (sid, title, body) in enumerate(blocks, 1):
        assert sid == f'{n:02}'
        turns = re.findall(r'\*\*(用户|助手)：\*\*\s*\n(.*?)(?=\n\*\*(?:用户|助手)：\*\*|\Z)', body, re.S)
        assert len(turns) == (4 if n in (4, 8, 12) else 2)
        messages = []
        for i, (role, content) in enumerate(turns):
            assert role == ('用户' if i % 2 == 0 else '助手')
            content = content.strip()
            assert content and '<think>' not in content and '</think>' not in content
            messages.append({'role': 'user' if role == '用户' else 'assistant',
                             'content': content if role == '用户' else '<think>\n\n</think>\n\n' + content})
        row = {'dataset': 't008/company-boundary-v1', 'messages': messages}
        assert key(row) not in {key(r) for r in parent + added}
        added.append(row)
        changes.append({'id': f'BOUNDARY-{sid}', 'title': title, 'operation': 'add',
                        'line_one_based': len(parent) + n, 'row_zero_based': len(parent) + n - 1,
                        'before': None, 'after': row, 'review_sample_id': sid,
                        'source': str(REVIEW.relative_to(ROOT)), 'source_sha256': sha(REVIEW),
                        'provenance': 'User-approved synthetic Chinese dialogue; hypothetical material explicitly marked in user turns.',
                        'encoding_only_change': 'Wrap assistant body in empty think block; wording unchanged; no /no_think or synthetic reasoning.',
                        'exposures_per_epoch': 1, 'answer_loss_weight': 1})
    assert sum(sum(m['role'] == 'assistant' for m in r['messages']) for r in added) == 15
    data = raw_parent + ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in added).encode()
    target = D / 'train.jsonl'
    if target.exists():
        assert target.read_bytes() == data, 'Do not overwrite a different candidate'
    else:
        target.write_bytes(data)
    rows = parent + added
    digest = sha(target)
    parent_map = [json.loads(x) for x in (PARENT / 'train-map.jsonl').read_text().splitlines()]
    for i, row in enumerate(rows):
        previous = parent_map[i] if i < len(parent) else None
        mapping.append({'row_zero_based': i, 'line_one_based': i + 1,
                        'parent_version': PARENT.name, 'parent_row_zero_based': i if previous else None,
                        'messages_sha256': key(row), 'parent_messages_sha256': key(row) if previous else None,
                        'source': row['dataset'], 'group': previous['group'] if previous else 'positioning',
                        'operation': 'preserve' if previous else 'add',
                        'change_id': None if previous else changes[i - len(parent)]['id'],
                        'provenance_detail': '../' + PARENT.name + '/train-map.jsonl' if previous else 'changes.jsonl'})
    save_jsonl('new-samples.jsonl', added)
    save_jsonl('changes.jsonl', changes)
    save_jsonl('train-map.jsonl', mapping)
    identity = json.loads((PARENT / 'identity-keys.json').read_text())
    identity.update(dataset_path=str(target.relative_to(ROOT)), dataset_sha256=digest)
    assert not {key(r) for r in added} & set(identity['identity_message_sha256'])
    save('identity-keys.json', identity)
    aliases = json.loads((PARENT / 'native-identity-key-aliases.json').read_text())
    aliases.update(dataset_sha256=digest, evidence='../' + PARENT.name + '/native-identity-key-aliases.json',
                   reason='Same 1315 parent rows and unchanged native preprocessing; inherit exact four identity aliases.')
    save('native-identity-key-aliases.json', aliases)
    shutil.copyfile(PARENT / 'identity_loss3.py', D / 'identity_loss3.py')
    shutil.copytree(PARENT / 'evaluation', D / 'evaluation', dirs_exist_ok=True)
    ev = rebind(json.loads((PARENT / 'evaluation-config.json').read_text()))
    # Keep the historical test/protocol references exact; no new evaluation is authorized.
    for field in ['additional_development_path', 'validation_plan']:
        ev[field] = json.loads((PARENT / 'evaluation-config.json').read_text())[field]
    ev.update(purpose='v0.1.13 CPU preparation only; inference not authorized.', execution_authorized=False)
    save('evaluation-config.json', ev)
    cfg_before = json.loads((PARENT / 'training-config.json').read_text())
    cfg = rebind(deepcopy(cfg_before))
    cfg.update(plan='company-boundary-12-additions', data_version=D.name, config_revision='company-boundary-v0.1.13',
               dataset_rows=len(rows), dataset_sha256=digest, estimated_full_optimizer_steps=math.ceil(len(rows) / 16),
               recipe_change='Append 12 approved Chinese dialogues, x1; preserve all 1315 parent rows and identity x3.',
               execution_authorized=False, resource_window=None, status='LOCAL_READY_CPU_PENDING',
               runtime_validation='PENDING fresh native Swift CPU encoding; not training authorization.',
               cpu_validation_report=None)
    assert [x.replace(D.name, PARENT.name) for x in cfg['full_argv']] == cfg_before['full_argv']
    save('training-config.json', cfg)
    before_stats = json.loads((PARENT / 'statistics.json').read_text())['after']
    after_stats = deepcopy(before_stats)
    after_stats.update(rows=len(rows), unique_message_records=len({key(r) for r in rows}),
                       source_exposures=dict(Counter(r['dataset'] for r in rows)),
                       group_exposures=dict(Counter(m['group'] for m in mapping)),
                       assistant_turns=before_stats['assistant_turns'] + 15,
                       multiturn_records=before_stats['multiturn_records'] + 3)
    after_stats['record_format_exposures']['positioning/empty_think'] += 12
    after_stats['assistant_turn_mode_counts']['positioning/empty_think'] += 15
    save('statistics.json', {'version': D.name, 'parent': PARENT.name, 'parent_sha256': PARENT_SHA,
                            'train_sha256': digest, 'before': before_stats, 'after': after_stats,
                            'added_rows': 12, 'changed_parent_rows': 0, 'removed_rows': 0,
                            'unchanged_parent_raw_lines': 1315, 'new_assistant_turns': 15,
                            'supervised_tokens': {'status': 'PENDING_NATIVE_SWIFT_ENCODING'}})
    save('config-diff.json', {'parent': str((PARENT / 'training-config.json').relative_to(ROOT)),
                             'parent_sha256': sha(PARENT / 'training-config.json'),
                             'argv_changes': [{'before': a, 'after': b} for a, b in zip(cfg_before['full_argv'], cfg['full_argv']) if a != b],
                             'training_hyperparameters_unchanged': True, 'loss_plugin_bytes_unchanged': True,
                             'identity_matching_keys_unchanged': True, 'normalization_rule_unchanged': True,
                             'old_rows_and_exposures_unchanged': True, 'added_rows_x1': 12,
                             'dataset_rows': {'before': 1315, 'after': 1327},
                             'estimated_steps': {'before': 83, 'after': 83}, 'native_cpu_encoding_executed': False})
    save('manifest.json', {'version': D.name, 'parent': PARENT.name, 'parent_sha256': PARENT_SHA,
                          'dataset': 'train.jsonl', 'dataset_sha256': digest, 'rows': len(rows),
                          'files_sha256': {'train.jsonl': digest},
                          'review_source': str(REVIEW.relative_to(ROOT)), 'review_source_sha256': sha(REVIEW),
                          'added_rows': 12, 'parent_rows_preserved_byte_for_byte': 1315,
                          'training_authorized': False, 'training_started': False, 'inference_executed': False,
                          'sync_status': 'LOCAL_GIT_ONLY'})
    (D / 'SAMPLES.md').write_text('> 原审阅稿快照：下文状态文字保留稿件形成时的表述。用户已批准将这12条纳入v0.1.13候选数据；尚未批准训练。实际编码仅为助手正文添加空think块，正文逐字不变。\n\n' + REVIEW.read_text())
    print(json.dumps({'rows': len(rows), 'added': len(added), 'sha256': digest, 'hyperparameters_unchanged': True}))


if __name__ == '__main__':
    main()
