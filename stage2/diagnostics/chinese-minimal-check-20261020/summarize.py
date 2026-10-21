"""Normalize saved responses; content acceptance remains an explicit review."""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
raw = [json.loads(s) for s in (ROOT / 'results/results.jsonl').read_text().splitlines()]
spec = json.loads((ROOT / 'spec.json').read_text())
expected = [json.loads(s) for s in (ROOT / 'cases.jsonl').read_text().splitlines()]
assert [r['case']['id'] for r in raw] == [r['id'] for r in expected]
normalized = []
for r, case in zip(raw, expected):
    assert r['case'] == case and 'error' not in r
    response = r['response']
    choice = response['choices'][0]
    message = choice['message']
    text = message.get('content') or ''
    reasoning = message.get('reasoning') or message.get('reasoning_content') or ''
    assert r['input_ids_verified']
    assert len(r['server_render']['token_ids']) == response['usage']['prompt_tokens']
    assert r['request']['model'] == 't008-loss3'
    assert r['request']['seed'] == case['seed']
    config = spec['modes'][case['mode']]
    assert all(r['request'][k] == v for k, v in config.items() if k != 'enable_thinking')
    assert r['request']['chat_template_kwargs']['enable_thinking'] == config['enable_thinking']
    normalized.append({'id': case['id'], 'case_id': case['case_id'], 'mode': case['mode'],
        'system_variant': case['system_variant'], 'seed': case['seed'],
        'question': case['messages'][-1]['content'], 'text': text,
        'reasoning_chars': len(reasoning), 'content_chars': len(text),
        'empty_body': not bool(text.strip()), 'finish_reason': choice['finish_reason'],
        'usage': response['usage'], 'seconds': r['seconds'],
        'expected_name_present': '能碳章鱼垂直大模型' in text,
        'expected_company_present': '能碳章鱼（湖北）人工智能科技有限公司' in text})
(ROOT / 'normalized.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in normalized))
summary = {'total': len(normalized), 'empty_bodies': sum(x['empty_body'] for x in normalized),
           'finish_reasons': dict(Counter(x['finish_reason'] for x in normalized)),
           'conditions': dict(Counter(x['system_variant'] for x in normalized)),
           'generated_tokens': sum(x['usage']['completion_tokens'] for x in normalized),
           'generation_seconds': sum(x['seconds'] for x in normalized),
           'note': 'Mechanical counts only; name presence does not establish semantic correctness.'}
(ROOT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
lines = ['# 40次中文推理复测：逐题可见正文', '',
         '模型为既有 v0.1.8 身份损失×3候选，未训练。existing＝原System；proposed＝新System；none＝不加System。这里只展示可见正文，原生返回保存在results/results.jsonl。', '']
for x in normalized:
    lines += [f"## {x['id']}", '', f"提问：{x['question']}", '',
              f"结束原因：{x['finish_reason']}；生成token：{x['usage']['completion_tokens']}；正文字符：{x['content_chars']}。", '',
              x['text'] if x['text'] else '（空正文）', '', '---', '']
(ROOT / 'ANSWERS.md').write_text('\n'.join(lines))
verification = {'status': 'PASS', 'request_count': len(normalized), 'planned_request_count': 40,
                'exact_case_order': True, 'server_prompt_tokens_equal': True,
                'request_configuration_equal': True, 'errors': 0,
                'runtime_preflight': json.loads((ROOT / 'results/runtime-preflight.json').read_text())['status'],
                'training_run': False, 'quality_acceptance': 'NOT_ESTABLISHED_BY_MECHANICAL_CHECK'}
(ROOT / 'inference-verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False))
