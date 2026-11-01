"""Summarize frozen criteria from reviewed saved answers; no model calls."""
from collections import Counter
from pathlib import Path
import hashlib
import json

D = Path(__file__).resolve().parent
summary = json.loads((D / 'semantic-summary.json').read_text())
models = ['original_base', 'v0.1.14', 'candidate_v0.1.22', 'candidate_v0.1.25']
rows = [json.loads(s) for s in (D / 'combined.jsonl').read_text().splitlines()]
cases = {c['id']: c for c in json.loads((D / 'cases.json').read_text())['items']}
labels = {}
for path in sorted((D / 'review').glob('verdicts-*.jsonl')):
    for v in map(json.loads, path.read_text().splitlines()):
        labels[v['review_id']] = v
for v in map(json.loads, (D / 'review/root-corrections.jsonl').read_text().splitlines()):
    labels[v['review_id']].update(v['corrected'])

results = {}
for model in models:
    groups = [v for v in summary['groups'] if v['model'] == model]
    out = {}
    for group in ['nt_system', 'nt_no_system', 'thinking_system']:
        selected = [v for v in groups if v['group'] == group]
        business = Counter()
        for v in selected:
            if v['family'] not in ['all', 'identity', 'json']:
                business.update({k: value for k, value in v.items() if isinstance(value, int)})
        slots = [r for r in rows if r['model'] == model and r['group'] == group
                 and cases[r['case_id']]['group'] not in ['identity', 'json']]
        business['any_confirmed_task_fact_unsupported_harm_loop_failure'] = sum(
            any(labels[r['review_id']][k] == 'fail' for k in ['task', 'facts', 'unsupported'])
            or labels[r['review_id']]['harmful_help'] or labels[r['review_id']]['repetitive_loop']
            for r in slots)
        identity = next((v for v in selected if v['family'] == 'identity'), None)
        out[group] = {
            'all': next(v for v in selected if v['family'] == 'all'),
            'business': dict(business),
            'echo_primary': next(v for v in summary['primary_echo']
                                 if v['model'] == model and v['group'] == group),
            'identity': identity,
            'identity_complete': identity['n'] - identity['identity_delivery_fail'],
            'json': next((v for v in selected if v['family'] == 'json'), None),
        }
    out['loops_total'] = sum(out[g]['all']['loop'] for g in out if isinstance(out[g], dict))
    out['truncated_total'] = sum(out[g]['all']['truncated'] for g in out if isinstance(out[g], dict))
    results[model] = out

parent = results['candidate_v0.1.22']
candidate = results['candidate_v0.1.25']
checks = {
    'nt_system_echo_decreased': candidate['nt_system']['echo_primary']['echo'] < parent['nt_system']['echo_primary']['echo'],
    'nt_no_system_echo_decreased': candidate['nt_no_system']['echo_primary']['echo'] < parent['nt_no_system']['echo_primary']['echo'],
    'loops_decreased': candidate['loops_total'] < parent['loops_total'],
    'task_failures_not_increased_each_condition': all(candidate[g]['business']['task_fail'] <= parent[g]['business']['task_fail']
        for g in ['nt_system', 'nt_no_system', 'thinking_system']),
    'fact_failures_not_increased_each_condition': all(candidate[g]['business']['facts_fail'] <= parent[g]['business']['facts_fail']
        for g in ['nt_system', 'nt_no_system', 'thinking_system']),
    'no_system_identity_not_decreased': candidate['nt_no_system']['identity_complete'] >= parent['nt_no_system']['identity_complete'],
}
result = {
    'semantic_summary_sha256': hashlib.sha256((D / 'semantic-summary.json').read_bytes()).hexdigest(),
    'decision_plan_sha256': hashlib.sha256((D / 'decision-plan.json').read_bytes()).hexdigest(),
    'models': results, 'direction_checks': checks,
    'combined_direction_criteria_met': all(checks.values()),
    'recommendation': 'DO_NOT_RELEASE; mixed diagnostic result, no automatic additional Full.',
    'limits': summary['limits'],
    'counting_note': 'Failure dimensions overlap. Identity complete excludes uncertain, loop, empty, length and unsupported failure; sentence-count issues separate.',
}
(D / 'decision-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'direction_checks': checks, 'combined_direction_criteria_met': result['combined_direction_criteria_met']}))
