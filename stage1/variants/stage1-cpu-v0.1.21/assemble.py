"""Build a reviewed derivative of frozen v0.1.20. No model calls."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import argparse
import difflib
import hashlib
import json
import math
import re
import shutil

D = Path(__file__).resolve().parent
R = D.parents[2]
P = D.parent / 'stage1-cpu-v0.1.20'
IDENTITY = {'swift/self-cognition', 't008/chinese-identity-v1', 't008/company-facts-v1'}

def read(p):
    return json.loads(p.read_text())

def jl(p):
    return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()

def key(messages):
    return digest([{'role': m['role'], 'content': m['content']} for m in messages])

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def sj(name, rows):
    (D / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))

def split_think(text):
    assert text.startswith('<think>') and text.count('<think>') == text.count('</think>') == 1
    return text[7:].split('</think>', 1)

def as_record(item):
    if item['id'].startswith('I'):
        return deepcopy(item['record'])
    x = item['record']
    return {'dataset': 'swift/Qwen3-SFT-Mixin', 'messages': [
        {'role': 'user', 'content': x['question']},
        {'role': 'assistant', 'content': '<think>' + x['thinking'] + '</think>' + x['answer']}]}

def apply_decision(item, decision):
    assert decision['id'] == item['id'] and decision['source_sha256'] == item['source_sha256']
    assert decision['read_complete'] is True and decision['reason'].strip()
    assert decision['action'] in {'retain', 'repair', 'quarantine'}
    before = as_record(item)
    if decision['action'] != 'repair':
        assert not decision.get('after'), (item['id'], 'unexpected replacement')
        return before if decision['action'] == 'retain' else None
    value = decision['after']
    if item['id'].startswith('G'):
        assert set(value) == {'id', 'question', 'thinking', 'answer'}
        assert value['id'] == item['id'] and value['question'] == item['record']['question']
        assert value['thinking'].strip() and value['answer'].strip()
        after = as_record({'id': item['id'], 'record': value})
    else:
        assert set(value) == set(before)
        after = deepcopy(value)
    assert after != before and after['dataset'] == before['dataset'], item['id']
    assert [m['role'] for m in after['messages']] == [m['role'] for m in before['messages']]
    for old, new in zip(before['messages'], after['messages']):
        if old['role'] != 'assistant':
            assert old == new, (item['id'], 'prompt changed')
        else:
            ot, ob = split_think(old['content'])
            nt, nb = split_think(new['content'])
            assert nb.strip() and bool(ot.strip()) == bool(nt.strip()), (item['id'], 'mode changed')
    return after

def collect(complete=False):
    assignments = read(D / 'review/assignments.json')
    inputs, decisions, progress = {}, {}, {}
    for label, spec in assignments.items():
        batch = jl(D / spec['input'])
        assert [x['id'] for x in batch] == spec['ids']
        inputs.update({x['id']: x for x in batch})
        path = D / spec['output']
        results = jl(path) if path.exists() else []
        assert len({x['id'] for x in results}) == len(results)
        assert {x['id'] for x in results} <= set(spec['ids'])
        for x in results:
            assert x['id'] not in decisions
            decisions[x['id']] = {**x, 'review_file': spec['output']}
        progress[label] = {'expected': len(batch), 'completed': len(results),
                           'actions': dict(Counter(x['action'] for x in results))}
    override = D / 'review/root-corrections.jsonl'
    if override.exists():
        rows = jl(override)
        assert len(rows) == len({x['id'] for x in rows})
        for x in rows:
            assert x['id'] in decisions and x['root_reason'].strip()
            decisions[x['id']] = {**x, 'supersedes': decisions[x['id']]}
    for sid, d in decisions.items():
        item = inputs[sid]
        if sid.startswith('G') and d['action'] == 'repair':
            # Keep the parent's <think>/answer whitespace envelope. Reviewers
            # edit content, not the serialization convention being compared.
            adjusted = []
            for field in ('thinking', 'answer'):
                source = item['record'][field]
                leading = re.match(r'^\s*', source).group()
                trailing = re.search(r'\s*$', source).group()
                value = leading + d['after'][field].strip() + trailing
                if value != d['after'][field]:
                    adjusted.append(field)
                    d['after'][field] = value
            if adjusted:
                d['parent_whitespace_envelope_restored'] = adjusted
        assert digest(item['record']) == item['source_sha256']
        apply_decision(item, d)
        actual = [x['issue_id'] for x in d['issue_dispositions']]
        assert len(actual) == len(set(actual)) and set(actual) == {x['issue_id'] for x in item['external_issues']}, (sid, 'issue coverage')
        assert all(x['status'] in {'accept', 'partly_accept', 'not_adopted', 'needs_verification'}
                   and x['reason'].strip() for x in d['issue_dispositions'])
    if complete:
        assert set(inputs) == set(decisions), ('pending', sorted(set(inputs) - set(decisions)))
    return inputs, decisions, progress

def stats(rows):
    return {'rows': len(rows), 'source_exposures': dict(Counter(r['dataset'] for r in rows)),
            'identity_exposures': sum(r['dataset'] in IDENTITY for r in rows),
            'unique_message_records': len({key(r['messages']) for r in rows}),
            'system_rows': sum(any(m['role'] == 'system' for m in r['messages']) for r in rows),
            'thinking_rows': sum(any(m['role'] == 'assistant' and split_think(m['content'])[0].strip()
                                     for m in r['messages']) for r in rows)}

def build():
    assert not (D / 'FILES.sha256.json').exists(), 'Frozen candidate: create another version.'
    for path, h in read(D / 'source-bindings.json').items():
        assert sha(Path(path)) == h, path
    inputs, decisions, progress = collect(complete=True)
    parent, oldmap = jl(P / 'train.jsonl'), jl(P / 'train-map.jsonl')
    oldraw = (P / 'train.jsonl').read_bytes().splitlines(keepends=True)
    by_line = {}
    for sid, item in inputs.items():
        line_numbers = item.get('parent_lines') or [item['parent_line']]
        for line in line_numbers:
            assert line not in by_line and parent[line - 1] == as_record(item)
            by_line[line] = sid
    assert len(parent) == 1069 and len(by_line) == 1008
    rows, mapping, raw, changes, quarantine = [], [], [], [], []
    for line, (before, m) in enumerate(zip(parent, oldmap), 1):
        sid = by_line.get(line)
        d = decisions.get(sid)
        action = d['action'] if d else 'retain'
        after = apply_decision(inputs[sid], d) if d else deepcopy(before)
        if action != 'retain':
            changes.append({'sample_id': sid, 'operation': action, 'parent_line_one_based': line,
                            'candidate_line_one_based': len(rows) + 1 if after else None,
                            'reason': d['reason'], 'before': before, 'after': after})
        if after is None:
            quarantine.append({'sample_id': sid, 'parent_line_one_based': line,
                               'reason': d['reason'], 'record': before})
            continue
        rows.append(after)
        raw.append(oldraw[line - 1] if action == 'retain' else (json.dumps(after, ensure_ascii=False) + '\n').encode())
        mapping.append({**m, 'row_zero_based': len(rows) - 1, 'line_one_based': len(rows),
            'candidate_line_one_based': len(rows), 'parent_version': P.name,
            'parent_row_zero_based': line - 1, 'parent_line_one_based': line,
            'v14_line_one_based': m['parent_line_one_based'],
            'operation': 'preserve' if action == 'retain' else 'repair',
            'sample_audit_id': sid, 'parent_messages_sha256': key(before['messages']),
            'messages_sha256': key(after['messages']),
            'provenance_detail': '../' + P.name + '/train-map.jsonl',
            'source_label_is_lineage_not_verbatim_original': True})
    assert len(rows) + len(quarantine) == len(parent)
    assert sum(r['dataset'] in IDENTITY for r in rows) == 234
    assert [r for r,m in zip(rows,mapping) if not m['sample_audit_id']] == [r for i,r in enumerate(parent,1) if i not in by_line]
    (D / 'train.jsonl').write_bytes(b''.join(raw))
    sj('train-map.jsonl', mapping)
    sj('changes.jsonl', changes)
    sj('quarantine.jsonl', quarantine)
    sj('decisions.jsonl', [decisions[s] for s in sorted(decisions)])
    shutil.copyfile(P / 'identity_loss3.py', D / 'identity_loss3.py')
    raw_keys = sorted({key(r['messages']) for r in rows if r['dataset'] in IDENTITY})
    # Native preprocessing aliases are measured later, never inferred from new text.
    save('identity-keys.json', {'dataset_path': str((D / 'train.jsonl').relative_to(R)),
        'dataset_sha256': sha(D / 'train.jsonl'), 'identity_exposures': 234,
        'unique_messages': len(raw_keys), 'identity_sources': sorted(IDENTITY),
        'raw_identity_message_sha256': raw_keys, 'identity_message_sha256': raw_keys,
        'matching_key_count': len(raw_keys), 'native_preprocessing_alias_count': 0,
        'native_alias_status': 'PENDING_NATIVE_CPU_CAPTURE'})
    cfg = deepcopy(read(P / 'training-config.json'))
    cfg.update(plan='v0120-external-review-repair', data_version=D.name,
        parent_dataset_version=P.name, parent_dataset_sha256=sha(P / 'train.jsonl'),
        dataset_sha256=sha(D / 'train.jsonl'), dataset_rows=len(rows),
        status='PREPARED_PENDING_CPU_NO_TRAINING', execution_authorized=False,
        runtime_validation='Pending native CPU encoding and regenerated identity hash bindings',
        recipe_change='Content repairs/quarantine only; no new samples, System, mode conversion or exposure increase.',
        config_revision='external-review-v0.1.21', estimated_full_optimizer_steps=math.ceil(len(rows)/16),
        cpu_validation_report=str((D / 'cpu-check/report.json').relative_to(R)),
        evaluation_config=str((D / 'evaluation-config.json').relative_to(R)))
    cfg['full_argv'] = [s.replace(P.name, D.name) for s in cfg['full_argv']]
    cfg['smoke_overrides']['output_dir'] = cfg['smoke_overrides']['output_dir'].replace(P.name,D.name)
    save('training-config.json', cfg)
    for name in ['evaluation-config.json', 'inference-system.txt']:
        shutil.copyfile(P / name, D / name)
    summary = {'before': stats(parent), 'after': stats(rows),
        'general_decisions': dict(Counter(d['action'] for sid,d in decisions.items() if sid.startswith('G'))),
        'identity_decisions': dict(Counter(d['action'] for sid,d in decisions.items() if sid.startswith('I'))),
        'repaired_exposures': sum(x['operation']=='repair' for x in changes),
        'quarantined_exposures': len(quarantine),
        'untouched_raw_rows': sum(m['operation']=='preserve' for m in mapping),
        'out_of_scope_preserved_rows': 61, 'cpu_tokens': 'pending'}
    save('statistics.json',summary)
    save('config-diff.json', {'parent':P.name, 'hyperparameters_unchanged':True,
        'loss_plugin_source_unchanged':sha(D/'identity_loss3.py')==sha(P/'identity_loss3.py'),
        'identity_hash_bindings_regenerated_for_revised_answers':True,
        'thinking_modes_unchanged_for_retained_records':True, 'training_system_rows':0,
        'rows_before':len(parent),'rows_after':len(rows),
        'data_change_affects_supervised_tokens_and_scheduler_horizon':True,
        'execution_authorized':False})
    issue_results=[]
    for sid,d in sorted(decisions.items()):
        for x in d['issue_dispositions']:
            issue_results.append({**x,'sample_id':sid,'action':d['action']})
    issue_results += jl(D / 'review/cross-sample-decisions.jsonl')
    all_issues=jl(D / 'review/inputs/external-issues.jsonl')
    assert Counter(x['issue_id'] for x in issue_results)==Counter(x['issue_id'] for x in all_issues)
    sj('external-review-dispositions.jsonl',sorted(issue_results,key=lambda x:x['issue_id']))
    table=['# 修改清单','','相对冻结v0.1.20；通用按唯一记录、自我认知按原曝光行记录。61条其他样本原字节保留。',
           '', '|ID|处置|父版本行号|理由|','|---|---|---|---|']
    samples=['# 样本修改前后','','题干、曝光和模式保持；以下错误原文仅供核对。']
    labels={'retain':'保留','repair':'修正','quarantine':'隔离'}
    for sid,d in sorted(decisions.items()):
        item=inputs[sid]; nums=item.get('parent_lines') or [item['parent_line']]
        table.append('|'+sid+'|'+labels[d['action']]+'|'+','.join(map(str,nums))+'|'+d['reason'].replace('|','\\|').replace('\n',' ')+'|')
        if d['action']=='retain':continue
        before=as_record(item);after=apply_decision(item,d)
        bs='\n\n'.join(m['role']+':\n'+m['content'] for m in before['messages'])
        ns='\n\n'.join(m['role']+':\n'+m['content'] for m in after['messages']) if after else '[本轮隔离，未进入候选训练文件]'
        diff=''.join(difflib.unified_diff(bs.splitlines(True),ns.splitlines(True),fromfile='v0.1.20',tofile='v0.1.21'))
        samples+=['',f'## {sid}', '',d['reason'],'','````diff',diff,'````','',
                  '<details><summary>修改前全文</summary>','','````text',bs,'````','','</details>',
                  '', '**修改后全文**','','````text',ns,'````']
    (D/'CHANGES.md').write_text('\n'.join(table)+'\n')
    (D/'SAMPLES.md').write_text('\n'.join(samples)+'\n')
    print(json.dumps(summary,ensure_ascii=False))

if __name__ == '__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--build',action='store_true');args=ap.parse_args()
    if args.build:build()
    else:
        inputs,decisions,progress=collect()
        print(json.dumps({'progress':progress,'completed':len(decisions)},ensure_ascii=False))
