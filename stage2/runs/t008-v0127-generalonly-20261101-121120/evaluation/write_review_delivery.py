"""Render existing reviewed outputs locally. No model or network calls."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import tarfile

D = Path(__file__).resolve().parent


def jl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


rows = jl(D / 'combined.jsonl')
queue = json.loads((D / 'review-queue.json').read_text())
summary = json.loads((D / 'semantic-summary.json').read_text())
cases = {c['id']: c for c in json.loads((D / 'cases.json').read_text())['items']}
labels = {}
for path in sorted((D / 'review').glob('verdicts-*.jsonl')):
    for item in jl(path):
        assert item['review_id'] not in labels
        labels[item['review_id']] = item
for item in jl(D / 'review/root-corrections.jsonl'):
    labels[item['review_id']].update(item['corrected'])

models = ['original_base', 'candidate_v0.1.26', 'candidate_v0.1.22', 'candidate_v0.1.27']
groups = ['nt_system', 'nt_no_system', 'thinking_system']
by_case = defaultdict(list)
for row in rows:
    by_case[row['case_id']].append(row)


def render(case_ids, title):
    out = [f'# {title}', '',
           f"仅整理已有原始响应与判词，没有新调用。历史判词{queue['inherited_unique_labels']}份继承，本轮{queue['new_unique_review_required']}份去重正文由主Agent全文复核；不属于独立盲审。",
           '模型为原版、v0.1.14、v0.1.22身份×3、v0.1.27。复述与循环分开；引用题面后正常作答不算复述。', '',
           '本文件包含完整诊断题和回答，仅本地保存。', '']
    for cid in case_ids:
        out += [f'## {cid}', '', cases[cid]['question'], '',
                '判据：' + '；'.join(cases[cid]['criteria']), '']
        for row in sorted(by_case[cid], key=lambda r: (groups.index(r['group']), models.index(r['model']), r['repeat'])):
            v = labels[row['review_id']]
            echo = row['exact_echo'] or v['near_echo']
            source = (f"`{row['source_file']}` 第{row['source_line']}行"
                      if 'source_file' in row else f"`{row['raw_path']}`；请求ID `{row['request_id']}`")
            out += [f"### {row['model']} · {row['group']} · 第{row['repeat']}次", '',
                    f"复述={bool(echo)}；正文循环={v['repetitive_loop']}；任务={v['task']}；事实={v['facts']}；无依据新增={v['unsupported']}；截断={row['truncated']}。", '',
                    v['note'], '', row['answer'] or '（正文为空）', '',
                    f"证据：{source}；审核对象 `{row['review_id']}`。", '']
    return '\n'.join(out)


(D / 'BY_QUESTION.md').write_text(render(by_case, '四模型同题回答对照'))
examples = ['T021-C900-B3-G035', 'T021-R3300-G0670', 'T021-R3300-N0184',
            'T021-C900-B4-G033', 'T021-B8-N009', 'D16-05', 'D16-07', 'E17-ID06']
(D / 'EXAMPLES.md').write_text(render(examples, '典型问题完整对照'))

files = [D / 'cases.json', D / 'combined.jsonl', D / 'results.jsonl',
         D / 'BY_QUESTION.md', D / 'EXAMPLES.md',
         *sorted((D / 'review').glob('verdicts-*.jsonl')),
         D / 'review/root-corrections.jsonl', D / 'review/bundle-root.jsonl']
archive = D / 'semantic-evidence.tar.gz'
with tarfile.open(archive, 'w:gz') as tar:
    for path in files:
        tar.add(path, arcname=str(path.relative_to(D)))

manifest = {
    'slots': len(rows), 'unique_reviewed': len(labels), 'inherited_unique': queue['inherited_unique_labels'],
    'new_unique_root_read': queue['new_unique_review_required'], 'unreviewed_slots': summary['unreviewed_slots'],
    'review_type': 'Historical corrected labels plus nonblind root review; no external Judge or new subagents.',
    'corrections': len(jl(D / 'review/root-corrections.jsonl')), 'archive': archive.name, 'archive_sha256': sha(archive),
    'files_sha256': {str(p.relative_to(D)): sha(p) for p in files},
    'raw_request_response_archive': 'raw-evidence.tar.gz',
}
(D / 'review-evidence.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: manifest[k] for k in ['slots', 'unique_reviewed', 'new_unique_root_read', 'unreviewed_slots']}))
