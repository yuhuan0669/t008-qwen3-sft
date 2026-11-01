"""Reanalyze frozen reviewed answers offline; no inference, cluster or Judge calls."""
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
R = D.parents[2]
E = R/'stage2/runs/t008-v0125-kl-20261101-084231/evaluation'
MODELS = ['original_base', 'v0.1.14', 'candidate_v0.1.22', 'candidate_v0.1.25']
def read(p): return json.loads(p.read_text())
def jl(p): return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, obj): p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')

evidence = read(E/'review-evidence.json')
for name, digest in evidence['files_sha256'].items(): assert sha(E/name) == digest, name
labels = {}
for p in sorted((E/'review').glob('verdicts-*.jsonl')):
    for v in jl(p):
        assert v['review_id'] not in labels
        labels[v['review_id']] = v
for v in jl(E/'review/root-corrections.jsonl'): labels[v['review_id']].update(v['corrected'])
all_cases = read(E/'cases.json')['items']
cases = {c['id']: c for c in all_cases}
assert len(all_cases) == len(cases)
all_rows = jl(E/'combined.jsonl')
rows = [r for r in all_rows if r['group'] == 'nt_system' and cases[r['case_id']]['group'] not in ['identity', 'json']]
by = defaultdict(lambda: defaultdict(list))
for r in rows:
    assert labels[r['review_id']]['read_complete']
    by[r['case_id']][r['model']].append(r)
assert len(rows) == 336 and len(by) == 28
for cm in by.values():
    assert set(cm) == set(MODELS)
    for rs in cm.values(): assert sorted(r['repeat'] for r in rs) == [1, 2, 3]
notes = read(D/'review-notes.json')
assert set(notes['case_notes']) == set(by)

def stats(rs):
    s = dict.fromkeys(['n', 'echo', 'loop', 'task_fail', 'task_uncertain', 'facts_fail', 'facts_uncertain',
        'unsupported_fail', 'unsupported_uncertain', 'harmful_help', 'task_or_fact_fail', 'any_fail', 'non_echo', 'non_echo_facts_fail'], 0)
    for r in rs:
        v = labels[r['review_id']]; echo = bool(r['exact_echo'] or v['near_echo'])
        task = v['task'] == 'fail'; facts = v['facts'] == 'fail'; unsupported = v['unsupported'] == 'fail'
        s['n'] += 1
        for key, value in [('echo', echo), ('loop', v['repetitive_loop']), ('task_fail', task), ('facts_fail', facts),
            ('unsupported_fail', unsupported), ('harmful_help', v['harmful_help']),
            ('task_or_fact_fail', task or facts),
            ('any_fail', task or facts or unsupported or v['harmful_help'] or v['repetitive_loop']),
            ('non_echo', not echo), ('non_echo_facts_fail', not echo and facts)]: s[key] += int(value)
        for key in ['task','facts','unsupported']: s[key+'_uncertain'] += int(v[key] == 'uncertain')
    return s

per_case = []
for cid, cm in by.items():
    st = {model: stats(cm[model]) for model in MODELS}
    base, old, new = (st[m] for m in ['original_base','candidate_v0.1.22','candidate_v0.1.25'])
    per_case.append({'case_id': cid, 'models': st,
        'base_three_core_pass': all(labels[r['review_id']]['task'] == labels[r['review_id']]['facts'] == 'pass' for r in cm['original_base']),
        'echo_decreased_vs_v022': new['echo'] < old['echo'],
        'facts_increased_vs_v022': new['facts_fail'] > old['facts_fail'],
        'review_note': notes['case_notes'][cid],
        'references': {m:[{'repeat':r['repeat'], 'review_id':r['review_id']} for r in sorted(cm[m], key=lambda r:r['repeat'])] for m in MODELS}})

cohorts = {
    'all_business': [c['case_id'] for c in per_case],
    'base_three_core_pass': [c['case_id'] for c in per_case if c['base_three_core_pass']],
    'base_observed_core_failure': [c['case_id'] for c in per_case if not c['base_three_core_pass']],
    'echo_decreased': [c['case_id'] for c in per_case if c['echo_decreased_vs_v022']],
    'echo_not_decreased': [c['case_id'] for c in per_case if not c['echo_decreased_vs_v022']],
    'facts_up_with_echo_down': [c['case_id'] for c in per_case if c['facts_increased_vs_v022'] and c['echo_decreased_vs_v022']],
    'facts_up_without_echo_down': [c['case_id'] for c in per_case if c['facts_increased_vs_v022'] and not c['echo_decreased_vs_v022']],
}
aggregates = {name: {'questions': len(ids), 'case_ids': ids,
    'models': {m:stats([r for r in rows if r['case_id'] in ids and r['model']==m]) for m in MODELS}} for name, ids in cohorts.items()}
assert aggregates['base_three_core_pass']['questions'] == 11
assert all(r['models']['original_base']['task_or_fact_fail'] > 0 for r in per_case if not r['base_three_core_pass'])
prior = read(E/'decision-result.json')['models']
for m in MODELS:
    for k in ['n','task_fail','facts_fail','unsupported_fail','harmful_help','echo']:
        assert aggregates['all_business']['models'][m][k] == prior[m]['nt_system']['business'][k], (m,k)
    assert aggregates['all_business']['models'][m]['any_fail'] == prior[m]['nt_system']['business']['any_confirmed_task_fact_unsupported_harm_loop_failure']

# Full texts actually reread in this turn; the other labels are reused, not called a fresh blind review.
base_a = {'T021-C900-B3-G035':[1,2,3], 'T021-C900-B4-G115':[1], 'T021-C900-B4-G033':[1,3],
    'T021-R3300-G0910':[2], 'T021-P20-G0172':[2], 'T021-R3300-G0670':[2], 'T021-B8-N093':[1,3],
    'T021-R3300-G1038':[1,2,3], 'T021-B7-R237':[1], 'T021-B7-R072':[3], 'T021-R3300-G0741':[2]}
base_b = {'T021-R3300-G0243':[1,2,3], 'T021-B8-N009':[1,2,3], 'T021-R3300-G1202':[1,2,3],
    'T021-R3300-G1403':[1,3], 'T021-C900-B3-N031':[1,2,3], 'T021-P20-G0274':[2], 'T021-N300-N030':[2], 'T021-B6-G129':[2]}
assert not set(base_a) & set(base_b)
base_read = {**base_a, **base_b}
reread = []
for line, r in enumerate(all_rows, 1):
    if r not in rows: continue
    v = labels[r['review_id']]
    full = (r['model'] == 'candidate_v0.1.25' and (v['facts']=='fail' or (v['task'] in ['fail','uncertain'] and not (r['exact_echo'] or v['near_echo']))))
    full |= r['model'] == 'original_base' and r['repeat'] in base_read.get(r['case_id'], [])
    full |= (r['model'], r['case_id'], r['repeat']) in [('v0.1.14','T021-R3300-G1202',1), ('candidate_v0.1.22','T021-R3300-G1403',2)]
    if full: reread.append({'model':r['model'], 'case_id':r['case_id'], 'repeat':r['repeat'], 'review_id':r['review_id'],
        'source_line_1based':line, 'answer_sha256':hashlib.sha256(r['answer'].encode()).hexdigest()})
assert len(reread) == 75 and len({r['review_id'] for r in reread}) == 75
source_files = [E/'review-evidence.json', E/'cases.json', E/'combined.jsonl', E/'decision-result.json',
    *sorted((E/'review').glob('verdicts-*.jsonl')), E/'review/root-corrections.jsonl']
out = {'complete':True, 'condition':'nt_system', 'questions':28, 'answers_per_model':84, 'total_answer_slots':336,
    'source_labels_reused':True, 'historical_labels_changed':False, 'question_comparisons_reviewed':28,
    'full_text_targeted_reread':75, 'full_text_unique_reread':75, 'reread_by_model':{m:sum(r['model']==m for r in reread) for m in MODELS},
    'cohorts':aggregates, 'per_case':per_case, 'cross_metric_cautions':notes['cross_metric_cautions'],
    'inputs_sha256':{str(p.relative_to(R)):sha(p) for p in source_files},
    'script_sha256':sha(Path(__file__)), 'review_notes_sha256':sha(D/'review-notes.json'),
    'new_model_requests':0, 'judge_requests':0, 'training':False, 'cluster_accessed':False,
    'deployment':False, 'uat_restore':False, 'next_training_authorized':False,
    'limits':['Historical unpaired sampling batches; compare three-answer question groups, not arbitrary same-repeat causal transitions.',
        'Post-hoc failure-enriched development analysis, not overall accuracy, a new holdout or proof of a single training cause.',
        'Base-three-core-pass requires task/facts pass only; unsupported extras may remain and base outputs are not unreviewed training gold.',
        'Labels are multidimensional. Zero facts_fail does not establish that the base had no error of a related type.']}
save(D/'SUMMARY.json',out)
save(D/'readback-evidence.json',{'source':str((E/'combined.jsonl').relative_to(R)), 'sha256':sha(E/'combined.jsonl'), 'full_text_read':reread})

table=['# 28题归因对照', '', '非思考＋同一System，每模型每题3次。数字为“任务失败／事实失败／复述”，三个字段可能重叠。保留历史判词，不能逐重复轮次配成因果转移。', '',
    '| 题号 | 原版 | v0.1.14 | v0.1.22 | v0.1.25 | 本次核对 |', '|---|---|---|---|---|---|']
for c in per_case:
    numbers = [' / '.join(str(c['models'][m][k]) for k in ['task_fail','facts_fail','echo']) for m in MODELS]
    table.append('| '+' | '.join([c['case_id'],*numbers,c['review_note']])+' |')
table += ['', '本表不包含完整题面和回答；[既有逐题原文，仅本地](../../runs/t008-v0125-kl-20261101-084231/evaluation/BY_QUESTION.md)。',
    '本次全量重算336份已有判词，并对28题归类；定向全文回读75份回答，其中v0.1.25为39份、原版34份、v0.1.14与v0.1.22各1份。其余原文未在本轮重新逐份审核。']
(D/'CASE_REVIEW.md').write_text('\n'.join(table)+'\n')
details=['# 本轮定向回读记录', '', '本文件只记录本轮已读取的75份既有回答；其他判词继承。原始材料未改。', '']
for r in reread:
    row=all_rows[r['source_line_1based']-1]; v=labels[r['review_id']]
    details += [f"## {r['case_id']} · {r['model']} · {r['repeat']}", '', cases[r['case_id']]['question'], '', row['answer'], '',
        v['note'], '', f"原始记录：{r['review_id']}；combined.jsonl第{r['source_line_1based']}行。", '']
(D/'DETAILS.md').write_text('\n'.join(details)+'\n')
print(json.dumps({'questions':28,'slots':336,'full_text_reread':len(reread),
    'base_three_core_pass':aggregates['base_three_core_pass'], 'all_business':aggregates['all_business']},ensure_ascii=False))
