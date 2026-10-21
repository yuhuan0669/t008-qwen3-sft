"""Score entire visible answers as JSON; fenced payload scores are diagnostic only."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re

D = Path(__file__).resolve().parent
def same_types_and_values(a, b):
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return a.keys() == b.keys() and all(same_types_and_values(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same_types_and_values(x, y) for x, y in zip(a, b))
    return a == b

def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: ' + key)
        result[key] = value
    return result

def parse(text):
    def reject_constant(x):
        raise ValueError('Nonstandard JSON constant ' + x)
    return json.loads(text, object_pairs_hook=no_duplicate_keys, parse_constant=reject_constant)

rows = [json.loads(l) for l in (D / 'results/results.jsonl').read_text().splitlines()]
assert len(rows) == 48 and not any('error' in x for x in rows)
assert json.loads((D / 'results/run-state.json').read_text())['status'] == 'COMPLETE'
normalized = []
groups = {}
for row in rows:
    c = row['case']
    choice = row['response']['choices'][0]
    body = choice['message']['content'] or ''
    strict = False
    try:
        strict = same_types_and_values(parse(body), c['expected'])
        valid = True
    except (ValueError, TypeError):
        valid = False
    fenced = re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*', body, re.S | re.I)
    payload = body if fenced is None else fenced[1]
    try:
        content_correct = same_types_and_values(parse(payload), c['expected'])
    except (ValueError, TypeError):
        content_correct = False
    result = {'model': row['model_key'], 'id': c['id'], 'case_id': c['case_id'], 'mode': c['mode'],
              'seed': c['seed'], 'strict_pass': strict, 'whole_content_valid_json': valid,
              'content_correct_ignoring_outer_fence': content_correct, 'outer_code_fence': bool(fenced),
              'empty': not body.strip(), 'finish_reason': choice['finish_reason'],
              'tokens': row['response']['usage']['completion_tokens'], 'body': body,
              'seconds': row['seconds']}
    normalized.append(result)
    groups.setdefault((row['model_key'], c['mode']), []).append(result)
by_model = {key: {r['case']['id']: r for r in rows if r['model_key'] == key} for key in ['v018-loss3', 'v019']}
assert by_model['v018-loss3'].keys() == by_model['v019'].keys()
for case_id, old in by_model['v018-loss3'].items():
    new = by_model['v019'][case_id]
    assert old['case'] == new['case']
    assert old['server_render']['token_ids'] == new['server_render']['token_ids']
    assert {k: v for k, v in old['request'].items() if k != 'model'} == {k: v for k, v in new['request'].items() if k != 'model'}
pair = {model: {r['id']: r for r in normalized if r['model'] == model} for model in by_model}
paired = Counter(('both_pass' if a['strict_pass'] and b['strict_pass'] else 'new_only_pass' if b['strict_pass'] else 'old_only_pass' if a['strict_pass'] else 'both_fail')
                 for case_id, a in pair['v018-loss3'].items() for b in [pair['v019'][case_id]])
summary = {'requests': 48, 'pairs': 24, 'identical_protocol_and_prompt_tokens': True, 'formal_acceptance': False,
           'training_executed': False, 'groups': {m + '/' + mode: {'count': len(v), 'strict_pass': sum(r['strict_pass'] for r in v),
                'content_correct_ignoring_outer_fence': sum(r['content_correct_ignoring_outer_fence'] for r in v),
                'fences': sum(r['outer_code_fence'] for r in v)} for (m, mode), v in groups.items()},
           'paired_outcomes': dict(paired), 'empty': sum(r['empty'] for r in normalized),
           'length': sum(r['finish_reason'] == 'length' for r in normalized),
           'completion_tokens': sum(r['tokens'] for r in normalized), 'request_seconds': sum(r['seconds'] for r in normalized)}
(D / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
(D / 'normalized.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in normalized))
table = ['| 题目 / 模式 | v0.1.8 loss×3 | v0.1.9 |', '| --- | ---: | ---: |']
for case_id in ['DEV-07', 'JSON-NEW-01', 'JSON-NEW-02', 'JSON-NEW-03']:
    for mode in ['nonthinking', 'thinking']:
        values = [sum(r['strict_pass'] for r in normalized if r['model'] == m and r['case_id'] == case_id and r['mode'] == mode) for m in ['v018-loss3', 'v019']]
        table.append(f'| {case_id} / {mode} | {values[0]}/3 | {values[1]}/3 |')
answers = ['# 48 次 JSON 对照：原始可见正文\n', '评分使用完整正文，不剥离代码围栏。下方外层四反引号仅用于报告展示。\n']
for r in normalized:
    answers.extend([f"## {r['model']} / {r['id']}\n", f"严格通过：{r['strict_pass']}；字段内容正确（诊断）：{r['content_correct_ignoring_outer_fence']}；结束：{r['finish_reason']}。\n",
                    '````text\n' + r['body'] + '\n````\n'])
(D / 'ANSWERS.md').write_text('\n'.join(answers))
(D / 'score-table.md').write_text('\n'.join(table) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
