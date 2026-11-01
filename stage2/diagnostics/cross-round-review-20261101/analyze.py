"""Local retrospective of saved answers/labels; no model, Judge or cluster calls."""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re

D = Path(__file__).resolve().parent
R = D.parents[2]
sources = {}
checks = []


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def record(p):
    sources[os.path.relpath(p, R)] = sha(p)
    return p


def read(p):
    return json.loads(record(p).read_text())


def jl(p):
    return [json.loads(line) for line in record(p).read_text().splitlines() if line.strip()]


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


RUNS = [
    ('17', 't008-v0117-20261031-100924'),
    ('18', 't008-v0118-20261031-120357'),
    ('22', 't008-v0122-20261101-031736'),
    ('22-loss1', 't008-v0122-loss1-20261101-040341'),
    ('23', 't008-v0123-20261101-060130'),
    ('24', 't008-v0124-attn-20261101-070053'),
    ('25', 't008-v0125-kl-20261101-084231'),
    ('26', 't008-v0126-idzero-20261101-112301'),
    ('27', 't008-v0127-generalonly-20261101-121120'),
]
loaded = {}
for version, name in RUNS:
    run = R / 'stage2/runs' / name
    e = run / 'evaluation'
    record(run / 'RESULT.md')
    p = e / 'review-evidence.json'
    if p.exists():
        manifest = read(p)
        files = manifest.get('files_sha256', manifest.get('files', {}))
        for f, expected in files.items():
            assert sha(e / f) == expected, (name, f, 'saved evidence mismatch')
        checks.append({'run': name, 'existing_manifest_files_verified': len(files)})
    else:
        checks.append({'run': name, 'existing_manifest_files_verified': 0,
                       'note': 'No review-evidence manifest; source hashes recorded now, not retroactive proof.'})
    labels = {}
    for p in sorted((e / 'review').glob('verdicts-*.jsonl')):
        for v in jl(p):
            assert v['review_id'] not in labels, (name, 'duplicate label')
            labels[v['review_id']] = v
    p = e / 'review/root-corrections.jsonl'
    if p.exists():
        for v in jl(p):
            labels[v['review_id']].update(v['corrected'])
    cases = {c['id']: c for c in read(e / 'cases.json')['items']}
    rows = jl(e / 'combined.jsonl')
    cfg = read(e / 'evaluation-config.json')
    summary = read(e / 'semantic-summary.json')
    loaded[version] = dict(run=name, rows=rows, labels=labels, cases=cases, config=cfg, summary=summary)

# Keep the existing 28-question cohort and the previously selected 11-question
# historical base-pass subset. Do not select a new cohort by candidate results.
old = read(R / 'stage2/diagnostics/kl-failure-attribution-20261101/SUMMARY.json')
ids = old['cohorts']['all_business']['case_ids']
core_ids = old['cohorts']['base_three_core_pass']['case_ids']
assert len(ids) == 28 and len(core_ids) == 11 and set(core_ids) <= set(ids)
base = loaded['25']
echo_ids = [cid for cid in ids if base['cases'][cid]['group'].startswith('复述/')]
assert len(echo_ids) == 16
for data in loaded.values():
    for cid in ids:
        assert data['cases'][cid]['question'] == base['cases'][cid]['question'], (data['run'], cid)
        assert data['cases'][cid]['messages'] == base['cases'][cid]['messages'], (data['run'], cid, 'messages')
    for key in ['system_sha256', 'chat_template', 'request_modes', 'seed_policy']:
        assert data['config'][key] == base['config'][key], (data['run'], key)

LABEL_FIELDS = ['task', 'facts', 'unsupported', 'harmful_help', 'near_echo', 'repetitive_loop']
reused = {}
conflicts = []
for version, data in loaded.items():
    for r in data['rows']:
        if r['group'] != 'nt_system' or r['case_id'] not in ids:
            continue
        key = (r['model'], r['case_id'], r['repeat'])
        v = data['labels'][r['review_id']]
        assert v['read_complete']
        val = (hashlib.sha256(r['answer'].encode()).hexdigest(), tuple(v[f] for f in LABEL_FIELDS))
        if key in reused and reused[key]['value'] != val:
            conflicts.append({'slot': key, 'versions': [reused[key]['version'], version],
                              'answer_changed': reused[key]['value'][0] != val[0],
                              'label_changed': reused[key]['value'][1] != val[1]})
        else:
            reused[key] = {'version': version, 'value': val}


def stats(rs, labels):
    out = dict.fromkeys(['n', 'echo', 'task_fail', 'facts_fail', 'task_or_fact_fail',
                        'unsupported_fail', 'loop', 'any_fail', 'uncertain'], 0)
    for r in rs:
        v = labels[r['review_id']]
        t, f, u = (v[k] == 'fail' for k in ['task', 'facts', 'unsupported'])
        out['n'] += 1
        for k, flag in [('echo', r['exact_echo'] or v['near_echo']), ('task_fail', t),
                        ('facts_fail', f), ('task_or_fact_fail', t or f),
                        ('unsupported_fail', u), ('loop', v['repetitive_loop']),
                        ('any_fail', t or f or u or v['harmful_help'] or v['repetitive_loop']),
                        ('uncertain', any(v[k] == 'uncertain' for k in ['task', 'facts', 'unsupported']))]:
            out[k] += int(bool(flag))
    return out


selected = [('原版', '25', 'original_base'), ('v0.1.14', '25', 'v0.1.14'),
            ('v0.1.16', '22', 'v0.1.16')]
selected += [('v0.1.' + v, v, 'candidate_v0.1.' + v) for v, _ in RUNS]
models = []
for title, version, model in selected:
    data = loaded[version]
    rs = [r for r in data['rows'] if r['group'] == 'nt_system' and r['case_id'] in ids and r['model'] == model]
    assert len(rs) == 84, (title, len(rs))
    for cid in ids:
        assert sorted(r['repeat'] for r in rs if r['case_id'] == cid) == [1, 2, 3]
    identity = [g for g in data['summary']['groups'] if g['model'] == model and g['group'] == 'nt_no_system' and g['family'] == 'identity']
    assert len(identity) == 1 and identity[0]['n'] == 24
    models.append({'model': title, 'source_run': data['run'], 'saved_model_id': model,
                   'business_28': stats(rs, data['labels']),
                   'echo_16': stats([r for r in rs if r['case_id'] in echo_ids], data['labels']),
                   'base_pass_11': stats([r for r in rs if r['case_id'] in core_ids], data['labels']),
                   'no_system_identity_complete': 24 - identity[0]['identity_delivery_fail'],
                   'identity_n': 24,
                   'per_case': {cid: stats([r for r in rs if r['case_id'] == cid], data['labels']) for cid in ids}})

# Recheck the previously overlooked, already completed module ablation.
module = R / 'stage2/diagnostics/module-ablation-20261101'
verification = read(module / 'verification.json')
for f, expected in verification['files_sha256'].items():
    assert sha(module / f) == expected, f
completed = read(module / 'results/completed.json')
for stem, count in [('generations', 128), ('scores', 256)]:
    p = module / 'results' / (stem + '.jsonl')
    assert sha(p) == completed[stem + '_sha256']
    assert len(jl(p)) == count
assert completed['complete'] and completed['adapter_memory_unchanged']
checks.append({'module_ablation': 'complete', 'generations': 128, 'fixed_scores': 256,
               'saved_manifest_and_raw_hashes_verified': True})

out = {'scope': 'Existing saved labels only; no new semantic review or model requests.',
       'business_case_ids': ids, 'echo_case_ids': echo_ids, 'historical_base_pass_case_ids': core_ids,
       'models': models, 'reused_answer_or_label_conflicts': conflicts,
       'slots_per_model': 84, 'total_model_condition_slots': 84 * len(models),
       'limits': ['Failure-enriched development subset, not population accuracy.',
                  'Historical unseeded/non-interleaved requests are not paired random trajectories.',
                  'The 11-question cohort was selected on three historical base task/fact passes; not stable gold.',
                  'Zero task/fact failure does not exclude unsupported details; uncertainty remains separate.',
                  'Identity scores use saved complete-delivery rubric, not name occurrence or System compliance.']}
save('COMPARISON.json', out)
lines = ['# 统一口径对照', '',
         '只重算已有回答与已有判词，不新增推理或Judge，不重新逐份语义审核。', '',
         '业务题固定为既有28题，每题3次；复述列固定为其中16题，每题3次。全部非思考＋同版System；身份另取无System的8题×3次。', '',
         '|版本|复述 /48|任务失败 /84|事实失败 /84|任务或事实失败 /84|至少一项明确失败 /84|无System身份完整 /24|历史原版三次核心通过的11题：任务或事实失败 /33|',
         '|---|---:|---:|---:|---:|---:|---:|---:|']
for m in models:
    b = m['business_28']
    lines.append('| ' + ' | '.join(map(str, [m['model'], m['echo_16']['echo'], b['task_fail'], b['facts_fail'],
        b['task_or_fact_fail'], b['any_fail'], m['no_system_identity_complete'], m['base_pass_11']['task_or_fact_fail']])) + ' |')
lines += ['', '“至少一项明确失败”合并任务、事实、无依据补充、有害帮助或循环；各分项可重叠，不能相加。待核项未计明确失败，也未判定为通过。', '',
          '这些题来自失败集，不是总体错误率；11题是在旧结果上选出的诊断子集，不是新留出集，也不是原版永久全对。原版在该33份回答中仍有7份无依据补充和2份相关待核。', '',
          f'重复引用同一历史答案的内容/主要标签差异记录：{len(conflicts)}。不是每轮重新生成了原版。', '',
          '来源、逐题数字与文件哈希见 [COMPARISON.json](COMPARISON.json) 和 [EVIDENCE.json](EVIDENCE.json)。本表用于修正跨轮比较口径，不作新验收。']
(D / 'COMPARISON.md').write_text('\n'.join(lines) + '\n')
# Preserve references to the diagnostic reports used for the retrospective.
# This checks local links and records their current bytes; it does not relabel
# old outputs or claim to have rerun the associated experiments.
report_links = []
for name in ['REPORT.md', 'EXPERIMENTS.md']:
    doc = D / name
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        p = (D / target).resolve()
        if p.parent == D:
            continue
        assert p.is_file(), (name, target, 'missing reference')
        record(p)
        report_links.append(os.path.relpath(p, R))
checks.append({'retrospective_source_links_verified': len(set(report_links))})
save('EVIDENCE.json', {'checks': checks, 'source_sha256': sources,
                       'new_training': 0, 'new_generations': 0, 'new_gradient_computations': 0,
                       'judge_calls': 0, 'cluster_access': False, 'uat_changed': False,
                       'script_sha256': sha(Path(__file__))})
print(json.dumps({'models': len(models), 'answer_slots': out['total_model_condition_slots'],
                  'source_files': len(sources), 'conflicts': len(conflicts), 'checks': checks}, ensure_ascii=False))
