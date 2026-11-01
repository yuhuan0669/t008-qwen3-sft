"""Summarize saved fixed-prefix probabilities, not answer quality rates."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import statistics

D = Path(__file__).resolve().parent
def jl(p): return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def mean(xs): return statistics.mean(xs)
scores = jl(D / 'results/scores.jsonl'); kl = jl(D / 'results/kl.jsonl')
prefixes = jl(D / 'results/prefixes.jsonl')
complete = json.loads((D / 'results/completed.json').read_text())
assert len(scores) == 174 and len(kl) == 184 and len(prefixes) == 102
for name, digest in complete['files_sha256'].items(): assert sha(D / 'results' / name) == digest

def cohort(row):
    return ('development_identity' if row['category'] == 'identity' else 'development_business') if row['source'] == 'development' else 'training_control'

pairs = defaultdict(dict)
for row in kl:
    key = (row['id'], row['position'], row['reference'])
    pairs[key][row['model']] = row
kl_pairs = []
for key, pair in pairs.items():
    a = pair['v0.1.22']; b = pair['v0.1.25']
    assert a['prefix_sha256'] == b['prefix_sha256'] and a.get('target_sha256') == b.get('target_sha256')
    kl_pairs.append({'id': key[0], 'case_id': a['case_id'], 'cohort': cohort(a), 'condition': a['condition'],
        'position': key[1], 'reference': key[2], 'v022': a['mean_kl'], 'v025': b['mean_kl'],
        'delta': b['mean_kl'] - a['mean_kl'], 'v022_tv': a['mean_total_variation'], 'v025_tv': b['mean_total_variation']})
by_group = defaultdict(list)
for row in kl_pairs: by_group[(row['cohort'], row['condition'], row['position'], row['reference'])].append(row)
kl_summary = []
for key, rows in by_group.items():
    a = mean(r['v022'] for r in rows); b = mean(r['v025'] for r in rows)
    kl_summary.append({'cohort': key[0], 'condition': key[1], 'position': key[2], 'reference': key[3], 'n': len(rows),
        'v022_mean_kl': a, 'v025_mean_kl': b, 'ratio_of_means': b / a if a else None,
        'v025_lower_cases': sum(r['delta'] < -1e-6 for r in rows),
        'v022_mean_tv': mean(r['v022_tv'] for r in rows), 'v025_mean_tv': mean(r['v025_tv'] for r in rows)})

by_id = defaultdict(dict)
for row in scores: by_id[(row['id'], row['model'])][row['reference']] = row
margins = []
for (identifier, model), refs in by_id.items():
    if 'expected' not in refs: continue
    a = refs['expected']; rival = 'question_copy' if 'question_copy' in refs else 'native_reference'; b = refs[rival]
    ks = {f'first{k}': min(k, a['tokens'], b['tokens']) for k in [8, 16, 32]}
    vals = {name: {'tokens_each': k, 'expected_nll': -mean(a['token_logp'][:k]),
                  'rival_nll': -mean(b['token_logp'][:k]),
                  'expected_advantage': mean(a['token_logp'][:k]) - mean(b['token_logp'][:k])} for name, k in ks.items()}
    margins.append({'id': identifier, 'case_id': a['case_id'], 'model': model, 'condition': a['condition'],
        'cohort': cohort(a), 'rival': rival, **vals})
mgroups = defaultdict(list)
for row in margins: mgroups[(row['cohort'], row['condition'], row['model'])].append(row)
margin_summary = []
for key, rows in mgroups.items():
    margin_summary.append({'cohort': key[0], 'condition': key[1], 'model': key[2], 'n': len(rows),
        **{name: {'expected_advantage_mean': mean(r[name]['expected_advantage'] for r in rows),
                  'expected_nll_mean': mean(r[name]['expected_nll'] for r in rows),
                  'rival_nll_mean': mean(r[name]['rival_nll'] for r in rows),
                  'expected_preferred_cases': sum(r[name]['expected_advantage'] > 0 for r in rows)} for name in ['first8', 'first16', 'first32']}})

copy_support = []
for row in scores:
    if row['source'] != 'development' or row['reference'] != 'question_copy': continue
    ps = row['filtered_probabilities']
    copy_support.append({'id': row['id'], 'case_id': row['case_id'], 'model': row['model'],
        'condition': row['condition'], 'tokens': row['tokens'],
        'first_filtered_zero_position_1based': next((i + 1 for i, p in enumerate(ps) if p == 0), None),
        'first8_supported': all(p > 0 for p in ps[:8]),
        'first32_supported': all(p > 0 for p in ps),
        'first8_fixed_path_probability': math.prod(ps[:8])})
cgroups = defaultdict(list)
for row in copy_support: cgroups[(row['condition'], row['model'])].append(row)
copy_summary = [{'condition': key[0], 'model': key[1], 'n': len(rows),
    'first8_supported_paths': sum(r['first8_supported'] for r in rows),
    'first32_supported_paths': sum(r['first32_supported'] for r in rows)} for key, rows in cgroups.items()]

enc = {r['id']: r for r in json.loads((D/'results/encoded.json').read_text())}
identity_starts = []
for row in prefixes:
    if row['source'] != 'development' or row['category'] != 'identity': continue
    target = enc[row['id']]['targets']['expected'][0]
    wanted = next(t for t in row['wanted_tokens'] if t['id'] == target)
    identity_starts.append({'id': row['id'], 'case_id': row['case_id'], 'model': row['model'],
        'condition': row['condition'], 'expected_first_token': wanted, 'top1': row['top8'][0]})

out = {'complete': True, 'scores': len(scores), 'prefix_distributions': len(prefixes), 'kl_comparisons': len(kl),
    'kl_summary': kl_summary, 'kl_pairs': kl_pairs, 'margin_summary': margin_summary, 'margins': margins,
    'copy_support_summary': copy_summary, 'copy_support_by_case': copy_support,
    'identity_first_tokens': identity_starts,
    'support_interpretation': 'Post-hoc summary of preregistered filtered-token probabilities on frozen paths. Exact path support is not a free-generation echo rate and excludes alternative tokenizations, paraphrases and vLLM numerical differences.',
    'identity_interpretation': 'The expected first token belongs to one frozen correct wording. It is not an exhaustive set of valid answer starts or a complete-answer identity score.',
    'files_sha256': {str(p.relative_to(D)): sha(p) for p in [D/'inputs/manifest.json', D/'diagnose.py', Path(__file__),
        D/'results/completed.json', D/'results/scores.jsonl', D/'results/kl.jsonl', D/'results/prefixes.jsonl']},
    'limits': json.loads((D/'inputs/protocol.json').read_text())['limits'],
    'margin_definition': 'Mean logp(expected fixed head) minus mean logp(rival fixed head), on equal token counts within each pair; positive favors the selected expected wording only.'}
(D/'SUMMARY.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
text = ['# 固定前缀概率与分布逐题对照', '', '只评分固定文本，不代表自由生成正确率。参考文本及逐token结果仅本地保存。', '']
cases = {c['id']: c for c in json.loads((D/'inputs/cases.json').read_text())['cases']}
for cid, c in cases.items():
    text += ['## '+cid, '', c['question'], '', '固定文本：', '', *[f'- {k}：{v}' for k,v in c['references'].items()], '',
             '| 条件 | 模型 | 前8 token正确文本NLL | 对照NLL | 正确文本优势 |', '|---|---|---:|---:|---:|']
    for row in margins:
        if row['case_id'] == cid:
            v = row['first8']; text.append(f"| {row['condition']} | {row['model']} | {v['expected_nll']:.4f} | {v['rival_nll']:.4f} | {v['expected_advantage']:.4f} |")
    text += ['', '| 条件 | 位置 | 固定文本 | KL v0.1.22 | KL v0.1.25 |', '|---|---|---|---:|---:|']
    for row in kl_pairs:
        if row['case_id'] == cid: text.append(f"| {row['condition']} | {row['position']} | {row['reference'] or '首token'} | {row['v022']:.4f} | {row['v025']:.4f} |")
    text.append('')
text += ['## 既有评分的补充分析', '',
    '以下只汇总已保存的概率，没有追加GPU调用。某条固定复制路径进入采样支持集，不等于实际会完整复述；退出支持集也不等于排除了其他近似复述路径。', '',
    '| 条件 | 模型 | 前8 token路径受支持 | 前32 token路径受支持 |', '|---|---|---:|---:|']
for row in copy_summary:
    text.append(f"| {row['condition']} | {row['model']} | {row['first8_supported_paths']}/{row['n']} | {row['first32_supported_paths']}/{row['n']} |")
text += ['', '| 身份题 | 条件 | 模型 | 固定正确首token | 原始概率 | 过滤后概率 | 概率最高首token | 原始概率 |', '|---|---|---|---|---:|---:|---|---:|']
for row in identity_starts:
    a, b = row['expected_first_token'], row['top1']
    text.append(f"| {row['case_id']} | {row['condition']} | {row['model']} | {a['token']} | {a['probability']:.6g} | {a['filtered_probability']:.6g} | {b['token']} | {b['probability']:.6g} |")
(D/'DETAILS.md').write_text('\n'.join(text)+'\n')
print(json.dumps({'scores': len(scores), 'copy_support_summary': copy_summary,
    'identity_example': [r for r in identity_starts if r['case_id'] == 'E17-ID06' and r['condition'] == 'nt_no_system']}, ensure_ascii=False))
