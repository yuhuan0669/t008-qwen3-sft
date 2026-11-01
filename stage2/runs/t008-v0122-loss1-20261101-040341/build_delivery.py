"""Create local-only full-answer views and a hashed review evidence archive."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import tarfile

D = Path(__file__).resolve().parent
E = D / 'evaluation'


def read(path):
    return json.loads(path.read_text())


def lines(path):
    return [json.loads(x) for x in path.read_text().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


summary = read(E / 'semantic-summary.json')
assert summary['unreviewed_slots'] == 0
labels = {}
for path in sorted((E / 'review').glob('verdicts-*.jsonl')):
    for item in lines(path):
        assert item['review_id'] not in labels
        labels[item['review_id']] = item
for correction in lines(E / 'review/root-corrections.jsonl'):
    labels[correction['review_id']].update(correction['corrected'])
cases = {x['id']: x for x in read(E / 'cases.json')['items']}
groups = defaultdict(list)
for row in lines(E / 'combined.jsonl'):
    groups[row['case_id']].append(row)
model_order = ['original_base', 'v0.1.14', 'v0.1.16', 'candidate_v0.1.22', 'candidate_v0.1.22-loss1']
condition_order = ['nt_system', 'nt_no_system', 'thinking_system']


def section(case_id):
    case = cases[case_id]
    out = [f'## {case_id}', '', case['question'], '', '判据：' + '；'.join(case['criteria']), '']
    for row in sorted(groups[case_id], key=lambda x: (condition_order.index(x['group']), model_order.index(x['model']), x['repeat'])):
        v = labels[row['review_id']]
        out += [f"### {row['group']} · {row['model']} · 第{row['repeat']}次", '',
                f"任务={v['task']}；事实={v['facts']}；无依据新增={v['unsupported']}；"
                f"复述={row['exact_echo'] or v['near_echo']}；循环={v['repetitive_loop']}；"
                f"结束={row['finish_reason']}；审核ID={row['review_id']}", '',
                v['note'], '']
        fence = '```'
        while fence in row['answer']:
            fence += '`'
        out += [fence, row['answer'] or '（可见正文为空）', fence, '']
    return '\n'.join(out)


header = '# 五模型逐题对照\n\n2780份回答；其中本轮556份、同协议历史复用2224份。回答全文保留，原始请求和推理段另见results.jsonl与原始归档。开发诊断集，不是独立验收或总体失败率。\n\n'
(E / 'BY_QUESTION.md').write_text(header + '\n'.join(section(x) for x in cases))
example_ids = ['T021-SP60-G10', 'D16-05', 'D16-07', 'E17-ID07', 'D16-12']
for metric in ['near_echo', 'repetitive_loop', 'harmful_help']:
    found = next((r['case_id'] for rows in groups.values() for r in rows
                  if r['model'] == 'candidate_v0.1.22-loss1' and labels[r['review_id']][metric]
                  and r['case_id'] not in example_ids), None)
    if found:
        example_ids.append(found)
(E / 'EXAMPLES.md').write_text('# 典型问题完整对照\n\n按空正文、身份、JSON及各异常首次命中选例；保留所选题的全部模型、条件、轮次，不用个例替代汇总。\n\n'
                               + '\n'.join(section(x) for x in example_ids))
paths = [E / name for name in ['cases.json', 'combined.jsonl', 'results.jsonl', 'review-guidance.md',
                               'BY_QUESTION.md', 'EXAMPLES.md']]
paths += sorted(p for p in (E / 'review').iterdir() if p.is_file() and p.suffix in {'.json', '.jsonl', '.md'})
archive = E / 'semantic-evidence.tar.gz'
with tarfile.open(archive, 'w:gz') as tf:
    for path in paths:
        tf.add(path, arcname=str(path.relative_to(E)))
dump(E / 'review-evidence.json', {
    'archive': str(archive.relative_to(D)), 'archive_sha256': sha(archive), 'bytes': archive.stat().st_size,
    'local_only': True, 'comparison_slots': summary['slots'], 'reviewed_unique': len(labels),
    'files': {str(p.relative_to(E)): sha(p) for p in paths}})
print(json.dumps({'comparison_slots': summary['slots'], 'reviewed_unique': len(labels),
                  'archive_sha256': sha(archive), 'examples': example_ids}, ensure_ascii=False))
