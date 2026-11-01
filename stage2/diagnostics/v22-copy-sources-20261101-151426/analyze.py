from pathlib import Path
import json,math,re
D=Path(Path('/tmp/v22-sources-dir').read_text());O=D/'results';rows=json.loads((O/'probes.json').read_text());out=[]
for x in rows:
 top=x['response']['choices'][0]['logprobs']['top_logprobs'][0];v=sorted([(int(re.search(r'(\d+)$',k).group(1)),p) for k,p in top.items()],key=lambda x:-x[1])[:20];m=v[0][1];den=sum(math.exp((p-m)/.7) for _,p in v);kept=[];cum=0
 for t,p in v:
  p=math.exp((p-m)/.7)/den
  if cum<.8:kept.append((t,p));cum+=p
 norm=sum(p for _,p in kept);sample=next((p/norm for t,p in kept if t==x['target_id']),0);raw=next((p for t,p in v if t==x['target_id']),None)
 out.append({k:x[k] for k in ['arm','position','target_id','target_text']}|{'raw_logp':raw,'sample_p':sample})
(O/'probabilities.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));metrics={}
for arm in ['v22_50','v22_66','v26','v27','v22_66_repeat']:
 a=[x for x in out if x['arm']==arm];missing=[x['position'] for x in a if x['raw_logp'] is None];bad=[x['position'] for x in a if x['sample_p']==0];metrics[arm]={'raw_sum':sum(x['raw_logp'] for x in a) if not missing else None,'entry_sum':sum(x['raw_logp'] for x in a if x['position'] in [1,2,4]) if not any(i in missing for i in [1,2,4]) else None,'sample_logp':sum(math.log(x['sample_p']) for x in a) if not bad else None,'excluded':bad,'missing':missing}
threshold={k:max(.01,5*abs(metrics['v22_66'][k]-metrics['v22_66_repeat'][k])) for k in ['raw_sum','entry_sum']};decisions=[]
for label,a,b,direction in [('late_training','v22_50','v22_66',1),('identity_off','v22_66','v26',-1),('other61_off','v26','v27',-1)]:
 diffs={k:metrics[b][k]-metrics[a][k] if metrics[b][k] is not None and metrics[a][k] is not None else None for k in threshold};positive=all(v is not None and v*direction>threshold[k] for k,v in diffs.items());negative=all(v is not None and v*direction<-threshold[k] for k,v in diffs.items());decisions.append({'hypothesis':label,'delta':diffs,'decision':'SUPPORT' if positive else 'AGAINST' if negative else 'INCONCLUSIVE'})
parent=D.parent/'v22-actual-20261101-150030/results/probabilities.json';old=json.loads(parent.read_text());drift=[{'position':x['position'],'delta_logp':x['raw_logp']-next(y['raw_logp'] for y in old if y['arm']=='v22' and y['position']==x['position'])} for x in out if x['arm']=='v22_66'];result={'metrics':metrics,'thresholds':threshold,'decisions':decisions,'old_v22_max_abs_logp_drift':max(abs(x['delta_logp']) for x in drift)};(D/'DECISION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
lines=['# 同一复制路径的逐Token概率','','|位置|Token|v22-50|v22-66|v26|v27|','|---|---|---:|---:|---:|---:|']
for j in range(39):
 a=[next(x for x in out if x['arm']==arm and x['position']==j) for arm in ['v22_50','v22_66','v26','v27']];lines.append('|'+str(j)+'|'+repr(a[0]['target_text'])+'|'+'|'.join('top20外' if x['raw_logp'] is None else f'{math.exp(x["raw_logp"])*100:.5f}%' for x in a)+'|')
(D/'TOKEN_COMPARISON.md').write_text('\n'.join(lines))
