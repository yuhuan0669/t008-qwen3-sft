"""Summarize fixed diagnostic outputs; no calls to models or cluster."""
from pathlib import Path
import json, math, collections
R=Path(__file__).resolve().parent
D=R/'results'
def read(n):return [json.loads(l) for l in (D/n).read_text().splitlines()]
rows=read('training-scores.jsonl');probes=read('probe-scores.jsonl');gens=read('generations.jsonl')
summary={'training':{},'probe_pairs':[]}
for owner in ['Full2','v017','v018']:
 summary['training'][owner]={}
 for model in ['base',owner]:
  rs=[r for r in rows if r['target_version']==owner and r['model']==model]
  named=[r for r in rs if r['score']['name_token_count']]
  ts=[t for r in named for t in r['score']['tokens'] if t['names']]
  first=[next(t for t in r['score']['tokens'] if t['names']) for r in named]
  loss=-sum(t['log_probability'] for t in ts)/len(ts)
  summary['training'][owner][model]={'unique_records':len(rs),'name_bearing_records':len(named),'name_token_nll':loss,'name_token_geomean_probability':math.exp(-loss),'first_name_token_top1_records':sum(t['rank']==1 for t in first),'first_name_token_arithmetic_mean_probability':sum(t['probability'] for t in first)/len(first),'all_answer_nll':sum(r['score']['mean_nll']*r['score']['supervised_tokens'] for r in rs)/sum(r['score']['supervised_tokens'] for r in rs)}
for p in probes:
 s=p['score'];first=next((t for t in s['tokens'] if t['names']),None)
 summary['probe_pairs'].append({k:p[k] for k in ['model','id','target_version','prefix_kind']}|{'nll':s['mean_nll'],'name_nll':s['name_mean_nll'],'first_name_token':first})
summary['generation_count']=len(gens)
summary['budget_exhaustions']=[{k:g[k] for k in ['model','id','mode','output_tokens']} for g in gens if g['budget_exhausted']]
(R/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
lines=['# 六问、双模式原始正文对照','', '无 System、贪婪生成；各候选按各自版本名称解释。Thinking 没有闭合时正文记为缺测。','']
for g in gens:
 lines.extend(['## '+g['model']+' / '+g['id']+' / '+g['mode'],'','提问：'+g['user'],'','正文：', '', g['answer'] if g['answer'] is not None else '（没有闭合思考块，未取得正文）','', '输出token：'+str(g['output_tokens'])+'；预算耗尽：'+str(g['budget_exhausted']),''])
(R/'ANSWERS.md').write_text('\n'.join(lines))
print(json.dumps(summary['training'],ensure_ascii=False,indent=2))
print('generation_count',len(gens),'budget_exhaustions',summary['budget_exhaustions'])
