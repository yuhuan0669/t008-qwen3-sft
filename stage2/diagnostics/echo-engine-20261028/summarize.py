"""Describe saved results; never invoke a model or infer correctness from no echo."""
import collections
import csv
import difflib
import hashlib
import json
import re
import statistics
from pathlib import Path

D = Path(__file__).resolve().parent
question = (D / 'question.txt').read_text()
compact = lambda s: re.sub(r'\s+', '', s)
rows = []
reviews = {}
for name in ['manual-review-vllm.json', 'manual-review-pt.json']:
    if (D / name).exists():
        for item in json.loads((D / name).read_text())['annotations']:
            reviews[(item['backend'], item['id'])] = item
for name in ['vllm-results.jsonl', 'pt-results.jsonl']:
    path = D / name
    if not path.exists():
        continue
    for line in path.read_text().splitlines():
        r = json.loads(line)
        answer = r['response']['choices'][0]['message'].get('content') or ''
        exact = answer.strip() == question.strip()
        ratio = difflib.SequenceMatcher(None, compact(question), compact(answer)).ratio()
        review = reviews.get((r['backend'], r['id']), {})
        rows.append({'backend': r['backend'], 'arm': r['arm'], 'id': r['id'], 'seed': r['seed'],
            'answer': answer, 'exact_echo': exact, 'near_echo_candidate': not exact and ratio >= .90,
            'near_echo_confirmed': review.get('near_echo', False),
            'other_copy_failure': review.get('other_copy_failure', False),
            'similarity': ratio, 'finish_reason': r['response']['choices'][0]['finish_reason'],
            'output_tokens': r['response']['usage']['completion_tokens'], 'seconds': r['seconds']})
groups = {}
for key in sorted({(r['backend'], r['arm']) for r in rows}):
    group = [r for r in rows if (r['backend'], r['arm']) == key]
    groups['/'.join(key)] = {'n': len(group), 'exact': sum(r['exact_echo'] for r in group),
        'near_candidates': sum(r['near_echo_candidate'] for r in group),
        'finish_reasons': dict(collections.Counter(r['finish_reason'] for r in group)),
        'median_seconds': statistics.median(r['seconds'] for r in group),
        'mean_output_tokens': statistics.mean(r['output_tokens'] for r in group)}
(D / 'summary-provisional.json').write_text(json.dumps({'groups': groups,
    'near_echo_candidates_require_manual_review': True, 'total_responses': len(rows)}, ensure_ascii=False, indent=2)+'\n')
with (D / 'answers.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['backend'])
    writer.writeheader()
    writer.writerows(rows)
text = ['# 80次跨引擎对照原始回答', '', '> 标记结合既定相似度规则及逐条复核。重复原题两遍单列，不回改近似阈值。未复述不等于任务合格。', '', '## 原题', '', question, '']
for r in sorted(rows, key=lambda x: (x['backend'], x['arm'], x['seed'])):
    label = '完全复述' if r['exact_echo'] else ('近似复述' if r['near_echo_confirmed'] else
        ('重复原题两遍（单列）' if r['other_copy_failure'] else
        ('近似候选待复核' if r['near_echo_candidate'] else '未列为复述')))
    text += [f"## {r['backend']} / {r['id']} / {label}", '', r['answer'], '',
        f"finish={r['finish_reason']}；输出{r['output_tokens']} Token；{r['seconds']:.2f}秒。", '']
(D / 'ANSWERS.md').write_text('\n'.join(text))
print(json.dumps({'total': len(rows), 'groups': groups}, ensure_ascii=False, indent=2))
