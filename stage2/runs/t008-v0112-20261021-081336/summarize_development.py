"""Normalize saved responses; content acceptance remains an explicit review."""
from collections import Counter
import hashlib
import json
from pathlib import Path

RUN = Path(__file__).resolve().parent
ROOT = RUN / 'development'
raw = [json.loads(s) for s in (ROOT / 'results.jsonl').read_text().splitlines()]
spec = json.loads((ROOT / 'spec.json').read_text())
expected = [json.loads(s) for s in (RUN / 'inputs/evaluation/cases.jsonl').read_text().splitlines()]
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
    assert r['request']['model'] == 't008-new'
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
lines = ['# 62次中文推理复测：逐题可见正文', '',
         '模型为本轮 v0.1.12 新LoRA。existing＝原System；proposed＝新System；none＝不加System。这里只展示可见正文，原生返回保存在results.jsonl。', '']
for x in normalized:
    lines += [f"## {x['id']}", '', f"提问：{x['question']}", '',
              f"结束原因：{x['finish_reason']}；生成token：{x['usage']['completion_tokens']}；正文字符：{x['content_chars']}。", '',
              x['text'] if x['text'] else '（空正文）', '', '---', '']
(ROOT / 'ANSWERS.md').write_text('\n'.join(lines))
verification = {'status': 'PASS', 'request_count': len(normalized), 'planned_request_count': 62,
                'exact_case_order': True, 'server_prompt_tokens_equal': True,
                'request_configuration_equal': True, 'errors': 0,
                'runtime_preflight': json.loads((ROOT / 'runtime-preflight.json').read_text())['status'],
                'training_run': True, 'quality_acceptance': 'NOT_ESTABLISHED_BY_MECHANICAL_CHECK'}
(ROOT / 'inference-verification.json').write_text(json.dumps(verification, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False))

# Compare with the frozen previous run; do not regenerate or overwrite its outputs.
PARENT = RUN.parents[2] / 'stage2/runs/t008-v0110-20261020-224753/development'
old = [json.loads(x) for x in (PARENT / 'results.jsonl').read_text().splitlines()]
prior_spec = json.loads((PARENT / 'spec.json').read_text())
for key in ['modes', 'versions', 'template_sha256', 'server_seed', 'concurrency', 'repetition_penalty', 'max_model_len', 'systems_sha256']:
    assert spec[key] == prior_spec[key], key
pairs = []
assert len(old) == 62 and len(raw) == 62
for before, after in zip(old, raw):
    assert before['case'] == after['case']
    assert before['server_render']['token_ids'] == after['server_render']['token_ids']
    assert {k:v for k,v in before['request'].items() if k!='model'} == {k:v for k,v in after['request'].items() if k!='model'}
    a,b = before['response']['choices'][0],after['response']['choices'][0]
    pairs.append({'id':after['case']['id'],'before_text':a['message'].get('content') or '',
                  'after_text':b['message'].get('content') or '',
                  'before_finish':a['finish_reason'],'after_finish':b['finish_reason'],
                  'before_completion_tokens':before['response']['usage']['completion_tokens'],
                  'after_completion_tokens':after['response']['usage']['completion_tokens']})
(ROOT / 'paired-outputs.json').write_text(json.dumps(pairs,ensure_ascii=False,indent=2)+'\n')
(ROOT / 'paired-protocol-verification.json').write_text(json.dumps({
 'verified':True,'pairs':len(pairs),'identical_prompts_and_generation_parameters':True,
 'baseline_is_frozen_previous_run_not_rerun':True,'formal_acceptance':False,
 'baseline':'stage2/runs/t008-v0110-20261020-224753/development/results.jsonl'
},indent=2)+'\n')
