"""Read saved generations only. No inference, network requests or model changes."""
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
import hashlib
import json
import statistics

D = Path(__file__).resolve().parent


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, data):
    (D / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def main():
    path = D / 'results/results.jsonl'
    rows = [json.loads(x) for x in path.read_text().splitlines()]
    conditions = [json.loads(x) for x in (D / 'conditions.jsonl').read_text().splitlines()]
    spec = read(D / 'spec.json')
    assert read(D / 'results/complete.json')['results_sha256'] == sha(path)
    expected = {(c['case_id'], c['mode'], c['seed'], m) for c in conditions for m in spec['models']}
    assert len(rows) == len(expected) == 120
    assert {(r['case_id'], r['mode'], r['seed'], r['model']) for r in rows} == expected
    groups = defaultdict(list)
    normalized = []
    for r in rows:
        assert 'error' not in r and r['http_status'] == 200 and r['input_ids_verified']
        response = r['response']
        assert json.loads(r['response_raw']) == response
        assert response['model'] == r['model']
        assert response['usage']['prompt_tokens'] == len(r['server_render']['token_ids'])
        groups[(r['case_id'], r['mode'], r['seed'])].append(r)
        choice = response['choices'][0]
        answer = choice['message'].get('content') or ''
        question = r['request']['messages'][-1]['content']
        nq, na = ''.join(question.split()), ''.join(answer.split())
        ratio = SequenceMatcher(None, nq, na, autojunk=False).ratio()
        n = {k:r[k] for k in ['id', 'case_id', 'mode', 'model', 'seed', 'category', 'checks', 'seconds']}
        n.update(question=question, answer=answer, finish_reason=choice['finish_reason'],
                 empty=not answer.strip(), exact_echo=na == nq, near_echo_flag=ratio >= .9 and na != nq,
                 echo_similarity=ratio, response_id=response.get('id'), usage=response['usage'])
        normalized.append(n)
    for group in groups.values():
        assert len(group) == 3
        first = {k:v for k,v in group[0]['request'].items() if k != 'model'}
        for r in group:
            assert {k:v for k,v in r['request'].items() if k != 'model'} == first
            assert r['server_render']['token_ids'] == group[0]['server_render']['token_ids']
    schema = read(D / 'schema-validation.json')
    assert schema['results_sha256'] == sha(path)
    schema_by_id = {x['id']:x for x in schema['results']}
    assert len(schema_by_id) == 9 and all(x['valid'] for x in schema['results'])
    for r in normalized:
        if r['id'] in schema_by_id:
            value = json.loads(r['answer'])
            r['schema_valid'] = schema_by_id[r['id']]['valid']
            if r['case_id'] == 'D16-11':
                # Both strings express the supplied month. Keep literal and semantic checks separate.
                r['period_literal_match'] = value['period'] == '2026年9月'
                r['json_values_correct'] = value['period'] in ['2026年9月', '2026-09'] and value['electricity_kwh'] == 2460 and value['verified'] is True
            else:
                r['json_values_correct'] = sorted(value['items']) == sorted(['抄表日期', '用电单位']) and value['status'] == 'incomplete'
    (D / 'normalized.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in normalized))
    summary = {'results_sha256':sha(path), 'requests':120, 'first_turn_groups_verified':len(groups),
               'same_requests_except_model':True, 'same_server_input_ids':True,
               'raw_response_matches_parsed_response':True, 'models':{},
               'near_echo_rule':'Whitespace-normalized SequenceMatcher >= 0.9; manually inspect flags.',
               'json_date_rule':'2026-09 and 2026年9月 are the same supplied month; literal match recorded separately.',
               'scope':'Development only; no independent acceptance or population error-rate inference.'}
    for model in spec['models']:
        rr = [x for x in normalized if x['model'] == model]
        summary['models'][model] = {
            'requests':len(rr), 'modes':dict(Counter(x['mode'] for x in rr)),
            'finish_reasons':dict(Counter(x['finish_reason'] for x in rr)),
            'empty':sum(x['empty'] for x in rr), 'exact_echo':sum(x['exact_echo'] for x in rr),
            'near_echo_flags':sum(x['near_echo_flag'] for x in rr),
            'json_schema_pass':sum(x.get('schema_valid', False) for x in rr),
            'json_value_pass':sum(x.get('json_values_correct', False) for x in rr),
            'json_requests':sum('schema_valid' in x for x in rr),
            'median_seconds_by_mode':{mode:round(statistics.median(x['seconds'] for x in rr if x['mode']==mode),3) for mode in spec['modes']}}
    save('mechanical-summary.json', summary)
    lines = ['# v0.1.16：120 次中文开发回答', '',
             '原始请求、响应、思考内容见 [results/results.jsonl](results/results.jsonl)。本页展示可见正文；没有重新生成。', '']
    for c in conditions:
        lines += [f"## {c['case_id']} · {c['mode']} · seed {c['seed']}", '', c['messages'][-1]['content'], '']
        for model in spec['models']:
            x = next(x for x in normalized if (x['case_id'],x['mode'],x['seed'],x['model'])==(c['case_id'],c['mode'],c['seed'],model))
            lines += [f"### {model}", '', x['answer'].strip(), '']
    (D / 'ANSWERS.md').write_text('\n'.join(lines))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
