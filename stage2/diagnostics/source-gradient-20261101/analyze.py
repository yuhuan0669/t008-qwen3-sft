"""Summarize directional evidence without treating derivatives as model accuracy."""
from collections import defaultdict
from pathlib import Path
import hashlib
import json
import math
import statistics

D = Path(__file__).resolve().parent; O = D / 'results'
def read(p): return json.loads(p.read_text())
def lines(p): return [json.loads(s) for s in p.read_text().splitlines()]
def save(p, v): p.write_text(json.dumps(v, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
def sign(x): return 1 if x > 0 else -1 if x < 0 else 0
effects = lines(O / 'probe-effects.jsonl'); rows = lines(O / 'row-effects.jsonl')
done = read(O / 'completed.json'); cpu = read(O / 'encoding-check.json')
assert done['complete'] and done['optimizer_steps'] == done['new_generated_answers'] == 0
assert len(effects) == 2 * 30 * 6 and len(rows) == 2 * cpu['unique_encodings']
assert len({(e['model'],e['id'],e['source']) for e in effects}) == len(effects)
assert len({(r['model'],r['key']) for r in rows}) == len(rows)
family = {'echo': 'copy_loop', 'body_loop': 'copy_loop', 'identity': 'identity', 'fact': 'fact', 'normal': 'normal_stop'}
bins = defaultdict(list)
for e in effects: bins[(e['model'], family[e['category']], e['condition'], e['source'])].append(e)
summaries = []
for (model, fam, condition, source), es in sorted(bins.items()):
    summaries.append({'model':model,'family':fam,'condition':condition,'source':source,'n':len(es),
        'raw_increases_bad':sum(e['raw_effect']>0 for e in es),
        'scaled_increases_bad':sum(e['adam_scaled_effect']>0 for e in es),
        'both_increase_bad':sum(e['raw_effect']>0 and e['adam_scaled_effect']>0 for e in es),
        'both_decrease_bad':sum(e['raw_effect']<0 and e['adam_scaled_effect']<0 for e in es),
        'metric_sign_disagreement':sum(sign(e['raw_effect'])!=sign(e['adam_scaled_effect']) for e in es),
        'mean_raw_effect':statistics.mean(e['raw_effect'] for e in es),
        'mean_scaled_effect':statistics.mean(e['adam_scaled_effect'] for e in es),
        'median_raw_cosine':statistics.median(e['raw_score_direction_cosine'] for e in es),
        'median_scaled_cosine':statistics.median(e['adam_score_direction_cosine'] for e in es)})
by_key={(e['model'],e['id'],e['source']):e for e in effects}
native=read(O/'native-projection-verification.json') if (O/'native-projection-verification.json').exists() else None
native_by={}
if native:
    assert native['complete'] and native['weights_unchanged']
    native_by={(e['probe'],e['source']):e for e in native['projections']}
    for pid in {e['id'] for e in effects}:
        for group,parts in [('other',['business','format']),('all',['general','identity','business','format'])]:
            native_by[(pid,group)]={k:sum(native_by[(pid,g)][k] for g in parts) for k in ['raw_effect','adam_scaled_effect']}
stable=[]
for e in effects:
    if e['model']!='step50':continue
    other=by_key[('step66',e['id'],e['source'])]
    signs=[sign(x[k]) for x in [e,other] for k in ['raw_effect','adam_scaled_effect']]
    status='increase_both_metrics_both_checkpoints' if signs==[1]*4 else 'decrease_both_metrics_both_checkpoints' if signs==[-1]*4 else 'mixed'
    native_match=None
    if native:
        check=native_by[(e['id'],e['source'])]
        native_match=all(sign(check[k])==sign(other[k]) for k in ['raw_effect','adam_scaled_effect'])
        if not native_match:status='implementation_sensitive'
    stable.append({'probe':e['id'],'case_id':e['case_id'],'family':family[e['category']],
                   'condition':e['condition'],'source':e['source'],'status':status,
                   'native_step66_signs_match':native_match,
                   'minimum_abs_cosine':min(abs(x[k]) for x in [e,other] for k in ['raw_score_direction_cosine','adam_score_direction_cosine'])})
stable_summary=[]
for fam in ['copy_loop','identity','fact','normal_stop']:
    for condition in ['no_system','system']:
        for source in ['general','identity','business','format','other','all']:
            es=[e for e in stable if e['family']==fam and e['condition']==condition and e['source']==source]
            stable_summary.append({'family':fam,'condition':condition,'source':source,'n':len(es),
                 'increase':sum(e['status'].startswith('increase') for e in es),
                 'decrease':sum(e['status'].startswith('decrease') for e in es),'mixed':sum(e['status']=='mixed' for e in es),
                 'implementation_sensitive':sum(e['status']=='implementation_sensitive' for e in es)})
# The sums of individual source records should reproduce the grouped dot products.
sum_checks=[]
for model in ['step50','step66']:
    selected=[r for r in rows if r['model']==model]
    assert sum(r['multiplicity'] for r in selected)==1047
    assert sum(r['multiplicity']*r['valid_tokens'] for r in selected)==928890
    for group in ['general','identity','business','format']:
        rs=[r for r in selected if r['group']==group]
        assert sum(r['multiplicity'] for r in rs)==cpu['groups'][group]['rows']
        for fam in ['copy_loop','identity','fact','normal_stop']:
            es=[e for e in effects if e['model']==model and e['source']==group and family[e['category']]==fam]
            for key in ['raw_effect','adam_scaled_effect']:
                a=sum(r[key][fam] for r in rs);b=statistics.mean(e[key] for e in es)
                # Float32 row projections are diagnostic rankings; authoritative group projections use FP64.
                relative=abs(a-b)/max(abs(a),abs(b),1e-10)
                sum_checks.append({'model':model,'group':group,'family':fam,'metric':key,
                    'row_sum':a,'group_mean':b,'relative_difference':relative,'sign_matches':sign(a)==sign(b)})
top_rows={}
for model in ['step50','step66']:
    for fam in ['copy_loop','identity','fact','normal_stop']:
        for metric in ['raw_effect','adam_scaled_effect']:
            selected=sorted((r for r in rows if r['model']==model),key=lambda x:x[metric][fam])
            top_rows[f'{model}/{fam}/{metric}']={'decreasing':selected[:8],'increasing':selected[-8:][::-1]}
scores={(e['model'],e['id']):e for e in lines(O/'probe-scores.jsonl')}
score_changes=[]
for (model,pid),a in scores.items():
    if model!='step50':continue
    b=scores[('step66',pid)]
    score_changes.append({'probe':pid,'family':family[a['category']],'condition':a['condition'],
        'score_step50':a['score'],'score_step66':b['score'],'change':b['score']-a['score'],
        'bad_probability_step50':a['bad_probability'],'bad_probability_step66':b['bad_probability'],
        'good_probability_step50':a['good_probability'],'good_probability_step66':b['good_probability']})
out={'checkpoints':['step50','step66'],'source_population':cpu['groups'],
     'numeric_verification_status':'COMPLETE_NATIVE_CROSSCHECK' if native else 'PENDING',
     'native_source_coherence':native['source_coherence'] if native else None,
     'local_derivative_summary':summaries,'cross_checkpoint_direction':stable_summary,
     'probe_directions':stable,'row_group_reconciliation':sum_checks,
     'max_row_group_relative_difference':max(x['relative_difference'] for x in sum_checks),
     'row_group_sign_disagreements':sum(not x['sign_matches'] for x in sum_checks),
     'top_record_candidates':top_rows,'actual_saved_checkpoint_score_changes':score_changes,
     'models':{m:read(O/(m+'-summary.json')) for m in ['step50','step66']},
     'quality_claim':False,'historical_causal_claim':False,'new_training':False,'new_generations':0,
     'scope':'Local derivatives over full frozen training corpus and 30 chosen token contrasts. Not generation error rates or proof of an exclusive causal source.'}
save(D/'SUMMARY.json',out)
text=['# 分来源梯度逐位置结果','','正值：该来源的负梯度方向提高选定错误Token相对支持；负值：降低。不是回答错误率。','',
      '|位置|来源|50步原始／Adam缩放|66步原始／Adam缩放|一致性|','|---|---|---:|---:|---|']
for e in stable:
    a=by_key[('step50',e['probe'],e['source'])];b=by_key[('step66',e['probe'],e['source'])]
    text.append(f"|{e['probe']}|{e['source']}|{a['raw_effect']:.5g} / {a['adam_scaled_effect']:.5g}|{b['raw_effect']:.5g} / {b['adam_scaled_effect']:.5g}|{e['status']}|")
(D/'DETAILS.md').write_text('\n'.join(text)+'\n')
print(json.dumps({'effects':len(effects),'row_gradients':len(rows),'max_row_group_relative_difference':out['max_row_group_relative_difference'],
                   'row_group_sign_disagreements':out['row_group_sign_disagreements'],'cross_checkpoint_direction':stable_summary},ensure_ascii=False))
