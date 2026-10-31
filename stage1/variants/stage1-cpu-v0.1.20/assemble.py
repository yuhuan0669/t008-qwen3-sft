"""Assemble reviewed patches against frozen v0.1.14; never invoke a model."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import math
import shutil

D = Path(__file__).resolve().parent
R = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.14'
IDENTITY = {'swift/self-cognition', 't008/chinese-identity-v1', 't008/company-facts-v1'}

def read(path):
    return json.loads(path.read_text())

def jl(path):
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def key(messages):
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()

def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def save_jl(name, values):
    (D / name).write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in values))

def apply_decision(record, decision):
    assert key(record['messages']) == decision['source_messages_sha256'], decision['id']
    action = decision['action']
    assert action in {'retain', 'repair', 'quarantine'}, decision
    if action != 'repair':
        assert not decision.get('replacements') and not decision.get('assistant_after'), decision['id']
        return deepcopy(record) if action == 'retain' else None
    assert [m['role'] for m in record['messages']] == ['user', 'assistant']
    old = record['messages'][1]['content']
    new = decision.get('assistant_after')
    if new is None:
        new = old
        assert decision.get('replacements'), decision['id']
        for patch in decision['replacements']:
            assert patch['old'] and patch['count'] > 0
            assert new.count(patch['old']) == patch['count'], (decision['id'], patch['old'][:100])
            new = new.replace(patch['old'], patch['new'])
    assert new != old and isinstance(new, str), decision['id']
    assert new.count('<think>') == old.count('<think>') == 1, decision['id']
    assert new.count('</think>') == old.count('</think>') == 1, decision['id']
    assert new.startswith('<think>') and new.split('</think>', 1)[0].replace('<think>', '').strip(), decision['id']
    assert new.split('</think>', 1)[1].strip(), decision['id']
    after = deepcopy(record)
    after['messages'][1]['content'] = new
    return after

def collect(require_complete=False):
    parent = jl(P / 'train.jsonl')
    ledger = {x['id']: x for x in jl(D / 'source-review-ledger.jsonl')}
    assignments = read(D / 'review/assignments.json')
    decisions = {x['id']: x for x in jl(D / 'inherited-decisions.jsonl')}
    report = {}
    for shard, assignment in assignments.items():
        path = D / assignment['output']
        items = jl(path) if path.exists() else []
        ids = [x['id'] for x in items]
        assert len(ids) == len(set(ids)), ('duplicate', shard)
        assert set(ids) <= set(assignment['ids']), ('foreign ID', shard)
        for x in items:
            assert x['id'] not in decisions and x['read_complete'] is True
            assert x['prior_status'] == ledger[x['id']]['status']
            assert x.get('reason') and x.get('evidence'), ('missing explanation', x['id'])
            x['review_file'] = str(path.relative_to(D))
            decisions[x['id']] = x
        report[shard] = {'completed': len(items), 'expected': len(assignment['ids']),
                         'actions': dict(Counter(x['action'] for x in items))}
    corrections = D / 'review/root-corrections.jsonl'
    if corrections.exists():
        items = jl(corrections)
        assert len(items) == len({x['id'] for x in items})
        for x in items:
            assert x['id'] in decisions and x.get('root_reason')
            x['previous_decision'] = decisions[x['id']]
            decisions[x['id']] = x
    for sid, decision in decisions.items():
        entry = ledger[sid]
        assert decision['source_messages_sha256'] == entry['messages_sha256'], sid
        first = parent[entry['train_rows_one_based'][0] - 1]
        after = apply_decision(first, decision)
        for line in entry['train_rows_one_based']:
            assert parent[line - 1] == first, sid
        if after is not None:
            assert after['messages'][0] == first['messages'][0] and after['dataset'] == first['dataset']
    if require_complete:
        assert set(decisions) == set(ledger), ('pending IDs', sorted(set(ledger) - set(decisions)))
    return parent, ledger, decisions, report

def stats(rows, mapping):
    return {'rows': len(rows), 'source_exposures': dict(Counter(x['dataset'] for x in rows)),
            'identity_exposures': sum(x['dataset'] in IDENTITY for x in rows),
            'system_rows': sum(any(m['role'] == 'system' for m in x['messages']) for x in rows),
            'language_exposures': dict(Counter(x['language'] for x in mapping)),
            'thinking_rows': sum(any(m['role'] == 'assistant' and m['content'].split('</think>', 1)[0].replace('<think>', '').strip()
                                     for m in x['messages']) for x in rows)}

def build():
    assert not (D / 'FILES.sha256.json').exists(), 'Frozen candidate: create a new version.'
    for path, h in read(D / 'source-bindings.json').items():
        assert sha(R / path) == h, path
    parent, ledger, decisions, report = collect(require_complete=True)
    assert len(parent) == 1325 and len(decisions) == 518
    parent_lines = (P / 'train.jsonl').read_bytes().splitlines(keepends=True)
    parent_map = jl(P / 'train-map.jsonl')
    # Historical language labels refer to identical first-user texts, not new semantic assessment.
    language_ref = jl(D.parent / 'stage1-cpu-v0.1.17/train-map.jsonl')[:1325]
    by_line = {line: sid for sid, x in ledger.items() for line in x['train_rows_one_based']}
    assert len(by_line) == 1030
    rows, mapping, raw, changes, quarantined = [], [], [], [], []
    for i, (before, oldmap, line) in enumerate(zip(parent, parent_map, parent_lines), 1):
        sid = by_line.get(i)
        decision = decisions.get(sid)
        action = decision['action'] if decision else 'retain'
        after = apply_decision(before, decision) if decision else deepcopy(before)
        if action != 'retain':
            changes.append({'sample_id': sid, 'operation': action, 'parent_line_one_based': i,
                            'candidate_line_one_based': len(rows) + 1 if after else None,
                            'reason': decision['reason'], 'before': before, 'after': after})
        if after is None:
            quarantined.append({'sample_id': sid, 'parent_line_one_based': i,
                                'reason': decision['reason'], 'record': before})
            continue
        rows.append(after)
        raw.append(line if action == 'retain' else (json.dumps(after, ensure_ascii=False) + '\n').encode())
        mapping.append({**oldmap, 'row_zero_based': len(rows) - 1, 'line_one_based': len(rows),
                        'candidate_line_one_based': len(rows), 'parent_version': P.name,
                        'parent_row_zero_based': i - 1, 'parent_line_one_based': i,
                        'operation': 'preserve' if action == 'retain' else 'repair', 'sample_audit_id': sid,
                        'language': language_ref[i - 1]['language'],
                        'parent_messages_sha256': key(before['messages']), 'messages_sha256': key(after['messages'])})
    assert len(rows) + len(quarantined) == 1325
    assert [x for x in rows if x['dataset'] != 'swift/Qwen3-SFT-Mixin'] == [x for x in parent if x['dataset'] != 'swift/Qwen3-SFT-Mixin']
    assert not any(m['role'] == 'system' for x in rows for m in x['messages'])
    (D / 'train.jsonl').write_bytes(b''.join(raw))
    save_jl('train-map.jsonl', mapping)
    save_jl('changes.jsonl', changes)
    save_jl('quarantine.jsonl', quarantined)
    save_jl('decisions.jsonl', [decisions[sid] for sid in sorted(decisions)])
    for name in ['identity-keys.json', 'identity_loss3.py', 'native-identity-key-aliases.json']:
        shutil.copyfile(P / name, D / name)
    cfg = deepcopy(read(P / 'training-config.json'))
    cfg.update(plan='v0114-content-cleaning', data_version=D.name, parent_dataset_version=P.name,
               parent_dataset_sha256=sha(P / 'train.jsonl'), dataset_sha256=sha(D / 'train.jsonl'),
               dataset_rows=len(rows), status='PREPARED_PENDING_CPU_NO_TRAINING', execution_authorized=False,
               runtime_validation='Pending final native CPU encoding',
               recipe_change='Only reviewed general-data repairs/quarantine relative to v0.1.14; no training System or later task additions.',
               config_revision='v0114-content-cleaning-v0.1.20', estimated_full_optimizer_steps=math.ceil(len(rows) / 16),
               cpu_validation_report=str((D / 'cpu-check/report.json').relative_to(R)),
               evaluation_config=str((D / 'evaluation-config.json').relative_to(R)),
               before_gpu=['User reviews the concrete data, supervision statistics and training proposal, then authorizes training.'])
    cfg['full_argv'] = [x.replace(P.name, D.name) for x in cfg['full_argv']]
    cfg['smoke_overrides']['output_dir'] = cfg['smoke_overrides']['output_dir'].replace(P.name, D.name)
    save('training-config.json', cfg)
    prior_maps = [{**m, 'language': language_ref[i]['language']} for i, m in enumerate(parent_map)]
    repaired = sum(x['operation'] == 'repair' for x in changes)
    summary = {'before': stats(parent, prior_maps), 'after': stats(rows, mapping),
               'decisions': dict(Counter(x['action'] for x in decisions.values())),
               'repaired_exposures': repaired, 'quarantined_exposures': len(quarantined),
               'untouched_rows': len(rows) - repaired, 'cpu_tokens': 'pending',
               'prior_status_to_action': {s: dict(Counter(x['action'] for x in decisions.values() if x['prior_status'] == s))
                                        for s in sorted({x['prior_status'] for x in decisions.values()})}}
    save('statistics.json', summary)
    save('config-diff.json', {'parent': P.name, 'hyperparameters_unchanged': True,
                            'rows_before': 1325, 'rows_after': len(rows),
                            'estimated_steps_before': 83, 'estimated_steps_after': math.ceil(len(rows) / 16),
                            'training_system_rows': 0, 'identity_exposures': 234,
                            'data_change_affects_token_mix_and_scheduler_horizon': True,
                            'execution_authorized': False})
    save('manifest.json', {'version': D.name, 'parent': P.name, 'parent_sha256': sha(P / 'train.jsonl'),
                          'status': 'PREPARED_PENDING_CPU_NO_TRAINING', 'rows': len(rows),
                          'files_sha256': {n: sha(D / n) for n in ['train.jsonl', 'train-map.jsonl', 'changes.jsonl',
                                                                 'quarantine.jsonl', 'decisions.jsonl', 'training-config.json']}})
    table = ['# 518 种通用记录的处置', '', '逐条列明保留、修正或隔离。原审核标签不是错误率；继承未发现明显问题的记录不称为本轮重新独审。', '',
             '|ID|原标签|处置|原行号|理由|', '|---|---|---|---|---|']
    samples = ['# 修正前后原文', '', '仅供审阅。修改前文字可能含已发现错误；隔离原文另见 quarantine.jsonl。']
    for sid, decision in sorted(decisions.items()):
        old = parent[ledger[sid]['train_rows_one_based'][0] - 1]
        action = decision['action']
        label = {'retain': '保留', 'repair': '修正', 'quarantine': '隔离'}[action]
        table.append(f'|{sid}|{decision["prior_status"]}|{label}|'+','.join(map(str, ledger[sid]['train_rows_one_based']))+'|'+decision['reason'].replace('|', '\\|').replace('\n', ' ')+'|')
        if action != 'repair':
            continue
        new = apply_decision(old, decision)
        before, after = old['messages'][1]['content'], new['messages'][1]['content']
        diff = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile='before', tofile='after'))
        samples += ['', f'## {sid}', '', decision['reason'], '', '**题目（不变）**', old['messages'][0]['content'], '',
                    '**差异**', '````diff', diff, '````', '', '<details><summary>修改前完整回答</summary>', '',
                    '````text', before, '````', '', '</details>', '', '**修改后完整回答**', '````text', after, '````']
    (D / 'CHANGES.md').write_text('\n'.join(table) + '\n')
    (D / 'SAMPLES.md').write_text('\n'.join(samples) + '\n')
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    if args.build:
        build()
    else:
        _, _, decisions, progress = collect()
        print(json.dumps({'review_progress': progress, 'total_dispositions': len(decisions)}, ensure_ascii=False))
