from pathlib import Path
import json,math,re
D=Path(Path('/tmp/v22-actual-dir').read_text());O=D/'results';gen=json.loads((O/'generations.json').read_text());enc=json.loads((O/'encoded.json').read_text());q=enc['question'];probes=json.loads((O/'probes.json').read_text());out=[]
for x in probes:
 lp=x['response']['choices'][0]['logprobs'];top=lp['top_logprobs'][0]
 vals=sorted([(int(re.search(r'(\d+)$',k).group(1)),v) for k,v in top.items()],key=lambda v:-v[1])[:20]
 m=vals[0][1];z=sum(math.exp((v-m)/.7) for _,v in vals);dist=[(t,math.exp((v-m)/.7)/z) for t,v in vals];kept=[];c=0
 for t,p in dist:
  if c<.8:kept.append((t,p));c+=p
 den=sum(p for _,p in kept);p=next((p/den for t,p in kept if t==x['target_id']),0.0)
 raw=next((v for t,v in vals if t==x['target_id']),None)
 out.append({k:x[k] for k in ['path','arm','position','target_id','target_text']}|{'raw_logp':raw,'sample_p':p,'top1_id':vals[0][0],'top1_logp':vals[0][1]})
(O/'probabilities.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
summ=[]
for name in sorted(set(x['path'] for x in out)):
 for arm in ['zero','v22','zero_repeat']:
  a=[x for x in out if x['path']==name and x['arm']==arm];bad=[x['position'] for x in a if x['sample_p']==0];missing=[x['position'] for x in a if x['raw_logp'] is None]
  summ.append({'path':name,'arm':arm,'raw_sum':sum(x['raw_logp'] for x in a) if not missing else None,'sample_logp':sum(math.log(x['sample_p']) for x in a) if not bad else None,'zero_support_positions':bad,'raw_missing_positions':missing})
counts={a:{'n':sum(x['arm']==a for x in gen),'exact':sum(x['arm']==a and x['response']['choices'][0]['message']['content']==q for x in gen),'length':sum(x['arm']==a and x['response']['choices'][0]['finish_reason']=='length' for x in gen)} for a in ['zero','v22']}
(O/'summary.json').write_text(json.dumps({'counts':counts,'paths':summ},ensure_ascii=False,indent=2));print(json.dumps({'counts':counts,'paths':summ},ensure_ascii=False,indent=2))
lines=['# 全部20次回答','']
for x in gen:lines+=['## '+x['arm']+' / '+str(x['repeat']),x['response']['choices'][0]['message'].get('content') or '(empty)','']
(D/'ANSWERS.md').write_text('\n'.join(lines))
lines=['# 相同前缀逐Token对照','','|位置|Token|zero原始p|v22原始p|zero采样p|v22采样p|','|---|---|---:|---:|---:|---:|']
for x in out:
 if x['arm']!='zero' or x['path']!='historical_canonical':continue
 y=next(y for y in out if y['arm']=='v22' and y['path']==x['path'] and y['position']==x['position'])
 def raw(o):return 'top20外' if o['raw_logp'] is None else f'{math.exp(o["raw_logp"]):.6g}'
 lines.append(f'|{x["position"]}|{x["target_text"]!r}|{raw(x)}|{raw(y)}|{x["sample_p"]:.6g}|{y["sample_p"]:.6g}|')
(D/'TOKEN_COMPARISON.md').write_text('\n'.join(lines))
