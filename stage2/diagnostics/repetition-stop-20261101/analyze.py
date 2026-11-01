"""Validate and summarize existing fixed-text scores; no model calls."""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text())
protocol = read(D / 'inputs/protocol.json')
done = read(D / 'results/completed.json')
raw = (D / 'results/scores.jsonl').read_bytes()
assert done['scores_sha256'] == hashlib.sha256(raw).hexdigest()
rows = [json.loads(x) for x in raw.decode().splitlines()]
assert len(rows) == len({(r['model'], r['probe_id'], r['reference']) for r in rows}) == 252
probes = read(D / 'inputs/probes.json')['probes']
assert len(probes) == 21
summary = []
for p in probes:
    group = [r for r in rows if r['probe_id'] == p['id']]
    assert len(group) == 12 and len({r['prompt_sha256'] for r in group}) == 1
    s = {k: p[k] for k in ['id', 'case_id', 'category', 'group', 'role']}
    active = 'thinking' if p['group'].startswith('thinking') else 'nonthinking'
    s.update(active_sampling=active, models={})
    for model in protocol['models']:
        rr = [r for r in group if r['model'] == model]
        assert len(rr) == 3 and all(r['first'] == rr[0]['first'] for r in rr)
        def stopping(profile):
            tokens = rr[0]['first'][profile]['tokens']
            return {'im_end_probability': tokens['151645']['probability'],
                'im_end_rank': tokens['151645']['rank'],
                'other_eos_probability': tokens['151643']['probability'],
                'close_think_probability': tokens['151668']['probability'],
                'close_think_rank': tokens['151668']['rank']}
        s['models'][model] = {'stopping_raw': stopping('raw'),
            'stopping_filtered': stopping(active), 'alternatives': {}}
        for r in rr:
            tid = str(r['token_scores'][0]['id'])
            raw_first = r['first']['raw']['tokens'][tid]
            filtered = r['first'][active]['tokens'][tid]
            s['models'][model]['alternatives'][r['reference']] = {
                'first_token_id': int(tid), 'raw_probability': raw_first['probability'],
                'raw_rank': raw_first['rank'], 'filtered_probability': filtered['probability'],
                'scored_tokens': r['target_tokens'], 'mean_nll': r['mean_nll'],
                'filtered_zero_tokens': r['sampling_profiles'][active]['zero_target_tokens']}
    summary.append(s)
out = {'validated_scores': 252, 'cases': 8, 'positions': 21, 'models': protocol['models'],
    'all_prefix_hashes_equal_across_models': True, 'same_first_distribution_for_all_alternatives': True,
    'score_file_sha256': hashlib.sha256(raw).hexdigest(), 'probes': summary}
(D / 'SUMMARY.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n')
lines = ['# 逐位置概率对照', '',
    '以下为固定前缀下的条件概率，均非新生成错误率。过滤使用该案例实际模式的采样参数；EOS列为 `im_end`，另一个配置结束符的概率保存在SUMMARY.json。平均NLL只对应给定续文的前48 Token，不能视作整个正确或错误答案类别的概率。', '']
for s in summary:
    lines += [f"## {s['id']}", '', f"{s['role']}；{s['active_sampling']}。", '',
        '|权重|固定续文|首Token原始概率|原始排名|过滤后概率|平均NLL|过滤掉的目标Token数|',
        '|---|---|---:|---:|---:|---:|---:|']
    for model, m in s['models'].items():
        for name, a in m['alternatives'].items():
            lines.append(f"|{model}|{name}|{a['raw_probability']:.6%}|{a['raw_rank']}|{a['filtered_probability']:.6%}|{a['mean_nll']:.4f}|{a['filtered_zero_tokens']}/{a['scored_tokens']}|")
    lines += ['']
(D / 'DETAILS.md').write_text('\n'.join(lines).rstrip() + '\n')
print(json.dumps({k: v for k,v in out.items() if k != 'probes'}))
for s in summary:
    print('\n' + s['id'])
    for name, m in s['models'].items():
        print(name, 'EOS', f"{m['stopping_raw']['im_end_probability']:.5g}/{m['stopping_filtered']['im_end_probability']:.5g}",
            'closeThink', f"{m['stopping_raw']['close_think_probability']:.5g}/{m['stopping_filtered']['close_think_probability']:.5g}",
            [(k, round(a['raw_probability'], 5), round(a['filtered_probability'], 5), round(a['mean_nll'], 3)) for k,a in m['alternatives'].items()])
