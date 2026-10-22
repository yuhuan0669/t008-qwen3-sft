"""Mechanical checks only; semantic judgments are recorded separately."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import math

O = Path(__file__).resolve().parent


def schema_valid(value, schema):
    types = schema.get('type', [])
    if isinstance(types, str): types = [types]
    fits = {'object': isinstance(value, dict), 'array': isinstance(value, list),
            'string': isinstance(value, str), 'integer': type(value) is int,
            'number': type(value) in [int, float] and math.isfinite(value),
            'boolean': type(value) is bool, 'null': value is None}
    if types and not any(fits[x] for x in types): return False
    if isinstance(value, dict):
        props = schema.get('properties', {})
        if not set(schema.get('required', [])) <= set(value): return False
        if schema.get('additionalProperties') is False and not set(value) <= set(props): return False
        return all(schema_valid(v, props[k]) for k, v in value.items() if k in props)
    if isinstance(value, list): return all(schema_valid(v, schema.get('items', {})) for v in value)
    return True


def strict_equal(value, expected):
    if isinstance(expected, dict):
        return isinstance(value, dict) and set(value) == set(expected) and all(strict_equal(value[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(value, list) and len(value) == len(expected) and all(strict_equal(x, y) for x, y in zip(value, expected))
    return type(value) is type(expected) and value == expected


def main():
    cases = {x['id']: x for x in map(json.loads, (O / 'scenarios.jsonl').read_text().splitlines())}
    rows = [json.loads(x) for x in (O / 'results/results.jsonl').read_text().splitlines()]
    assert len(rows) == len({r['id'] for r in rows}) == 120
    spec = json.loads((O / 'spec.json').read_text())
    buckets = defaultdict(list); normalized = []
    for r in rows:
        assert 'error' not in r and r['input_ids_verified'] is True
        response = r['response']; c = response['choices'][0]; msg = c['message']
        content = msg.get('content') or ''
        thinking = msg.get('reasoning') or msg.get('reasoning_content') or ''
        assert any(x['role'] == 'system' and x['content'] == (O/'custom-system.txt').read_text() for x in r['request']['messages'])
        item = dict(id=r['id'], model=r['model'], mode=r['mode'], seed=r['seed'],
            case_id=r['case_id'], turn=r['turn'], category=r['category'],
            question=r['request']['messages'][-1]['content'], content=content, reasoning=thinking,
            empty=not content.strip(), length=c['finish_reason'] in ['length', 'max_tokens'],
            finish_reason=c['finish_reason'], completion_tokens=response['usage']['completion_tokens'],
            seconds=r['seconds'], checks=r['checks'])
        if r['category'] == 'json':
            case = cases[r['case_id']]
            assert r['request']['response_format'] == case['response_format']
            try:
                obj = json.loads(content, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
                item.update(json_parse=True, json_schema=schema_valid(obj, case['response_format']['json_schema']['schema']),
                            json_exact=strict_equal(obj, case['expected_for_scoring_only']))
            except (ValueError, TypeError): item.update(json_parse=False, json_schema=False, json_exact=False)
        normalized.append(item); buckets[(r['model'], r['mode'])].append(item)
    summary = []
    for (model, mode), group in sorted(buckets.items()):
        js = [r for r in group if r['category'] == 'json']
        summary.append(dict(model=model, mode=mode, requests=len(group), empty=sum(r['empty'] for r in group),
            length=sum(r['length'] for r in group), finish_reasons=dict(Counter(r['finish_reason'] for r in group)),
            json_requests=len(js), json_parse=sum(r['json_parse'] for r in js),
            json_schema=sum(r['json_schema'] for r in js), json_exact=sum(r['json_exact'] for r in js),
            completion_tokens=sum(r['completion_tokens'] for r in group), seconds=round(sum(r['seconds'] for r in group), 2)))
    # Same initial input IDs across models; subsequent turns deliberately use each model's true reply.
    groups=defaultdict(list)
    for r in rows:
        if r['turn']==1: groups[(r['case_id'],r['mode'],r['seed'])].append(r)
    for key, group in groups.items():
        assert len(group)==2
        assert all(x['server_render']['token_ids']==group[0]['server_render']['token_ids'] for x in group)
        requests=[dict(x['request'],model='normalized') for x in group]
        assert all(x==requests[0] for x in requests)
    assert len(groups)==60
    (O/'normalized.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in normalized))
    (O/'mechanical-summary.json').write_text(json.dumps(dict(total=120, first_turn_groups_verified=60,
        groups=summary, api_errors=0, training=False),ensure_ascii=False,indent=2)+'\n')
    sections=['# 中文对照：完整可见回答\n\n每个场景内按模式、种子、模型排列；思考保存在normalized.jsonl，评分单独登记。\n']
    for case_id, scenario in cases.items():
        sections.append('## '+case_id+' — '+scenario['category']+'\n')
        for x in sorted([r for r in normalized if r['case_id']==case_id],key=lambda r:(r['mode'],r['seed'],r['model'],r['turn'])):
            sections.append('### '+x['id']+'\n\n'+x['question']+'\n\n'+(x['content'] or '**空正文**')+
                '\n\n停止='+x['finish_reason']+'；输出token='+str(x['completion_tokens'])+'\n')
    (O/'ANSWERS.md').write_text('\n'.join(sections))
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__': main()
