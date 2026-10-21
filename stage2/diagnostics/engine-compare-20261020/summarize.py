"""Normalize stop reasons and visible answers; keep reasoning in raw evidence only."""
from collections import Counter, defaultdict
from pathlib import Path
import json

D = Path(__file__).resolve().parent
R = D / 'results'
cases = [json.loads(s) for s in (D / 'cases.jsonl').read_text().splitlines()]
lookup = {json.dumps(r['messages'], ensure_ascii=False, sort_keys=True): r for r in cases}
cpu = json.loads((D / 'cpu-check.json').read_text())
expected = {(r['group'], r['id']): r['tokens'] for r in cpu['prompt_checks']}
rows = []

for path in sorted(R.glob('swift-raw-*.jsonl')):
    group = path.stem.removeprefix('swift-raw-')
    model, mode, cap = group.removesuffix('-control').split('-')
    control = group.endswith('-control')
    for line in path.read_text().splitlines():
        raw = json.loads(line)
        for request, response in zip(raw['requests'], raw['responses']):
            case = lookup[json.dumps(request['messages'], ensure_ascii=False, sort_keys=True)]
            choice = response['choices'][0]
            content = choice['message']['content'] or ''
            closed = '</think>' in content
            body = content.split('</think>', 1)[1].strip() if closed else content.strip()
            if mode == 'thinking' and not closed:
                body = ''
            assert response['usage']['prompt_tokens'] == expected[(group.removesuffix('-control'), case['id'])]
            rows.append({'engine': 'Swift infer', 'model': model, 'mode': mode, 'cap': int(cap),
                'id': case['id'], 'case_id': case['case_id'], 'system_variant': case['system_variant'],
                'finish_reason': choice['finish_reason'], 'usage': response['usage'],
                'visible_body': body, 'empty_body': not body, 'closed_think': closed,
                'length_seed_control': control,
                'seconds': raw['elapsed_seconds'], 'source': str(path.relative_to(D))})

for line in (R / 'vllm-results.jsonl').read_text().splitlines():
    raw = json.loads(line)
    choice = raw['response']['choices'][0]
    body = (choice['message'].get('content') or '').strip()
    case = raw['case']
    assert raw['input_ids_verified']
    rows.append({'engine': 'vLLM chat', 'model': raw['model'], 'mode': raw['mode'], 'cap': raw['cap'],
        'id': case['id'], 'case_id': case['case_id'], 'system_variant': case['system_variant'],
        'finish_reason': choice['finish_reason'], 'usage': raw['response']['usage'],
        'visible_body': body, 'empty_body': not body, 'seconds': raw['seconds'],
        'length_seed_control': False,
        'source': 'results/vllm-results.jsonl'})

assert Counter(r['engine'] for r in rows) == {'Swift infer': 44, 'vLLM chat': 42}
keys = [(r['engine'], r['model'], r['mode'], r['cap'], r['id'], r['length_seed_control']) for r in rows]
assert len(keys) == len(set(keys)) == 86
groups = defaultdict(list)
for r in rows:
    groups[(r['engine'], r['model'], r['mode'], r['cap'])].append(r)
summary = []
for key, values in sorted(groups.items()):
    summary.append(dict(zip(['engine', 'model', 'mode', 'cap'], key), count=len(values),
                       empty_body=sum(r['empty_body'] for r in values),
                       length=sum(r['finish_reason'] == 'length' for r in values),
                       completion_tokens=sum(r['usage']['completion_tokens'] for r in values)))
(D / 'normalized.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
(D / 'summary.json').write_text(json.dumps({'requests': 86, 'groups': summary}, ensure_ascii=False, indent=2) + '\n')
text = ['# 推理引擎对照：可见正文', '',
        '原版 base 与最新 loss3 候选；仅开发诊断，不作正式验收。',
        '两后端提示词已对齐；随机采样输出不要求逐字相同。此文件仅展示可见正文。', '']
for case in cases:
    text += ['## ' + case['id'], '', case['messages'][-1]['content'], '',
             'System：' + ('无' if case['system_variant'] == 'none' else '现有原文'), '']
    for row in sorted([r for r in rows if r['id'] == case['id']],
                      key=lambda r: (r['mode'], r['cap'], r['model'], r['engine'])):
        suffix = ' / 独立同种子长度对照' if row['length_seed_control'] else ''
        text += [f"### {row['mode']} / {row['cap']} / {row['model']} / {row['engine']}{suffix}", '',
                 f"停止：{row['finish_reason']}；输出 token：{row['usage']['completion_tokens']}。", '',
                 row['visible_body'] or '（可见正文为空）', '']
(D / 'ANSWERS.md').write_text('\n'.join(text) + '\n')
print(json.dumps({'requests': len(rows), 'groups': summary}, ensure_ascii=False))
