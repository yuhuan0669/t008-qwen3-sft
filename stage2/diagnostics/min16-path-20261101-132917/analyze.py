from pathlib import Path
import json,math
D=Path(__file__).resolve().parent;rs=json.loads((D/'results/scores.json').read_text());lookup={(r['arm'],r['condition'],r['reference']):r for r in rs};out={'means':[],'branch':[],'zero':[],'handback':[]}
for arm in ['original_base','step0','step2','step4','step8']:
 for c in [False,True]:
  for ref in ['echo_no_system','echo_system']:
   r=lookup[arm,c,ref]
   for i,t in enumerate(r['tokens_text']):
    if '请' in t:out['handback'].append({'arm':arm,'condition':c,'reference':ref,'position':i,'token':t,'probability':math.exp(r['token_logprobs'][i])})
for c in [False,True]:
 for arm in ['original_base','step0','step2','step4','step8']:
  out['means'].append({'condition':c,'arm':arm,**{ref:lookup[arm,c,ref]['mean_nll'] for ref in ['correct','echo_no_system','echo_system','matched_correct','historical_greedy']}})
  a=lookup[arm,c,'matched_correct'];b=lookup[arm,c,'echo_no_system'];j=next(i for i,(x,y) in enumerate(zip(a['target_ids'],b['target_ids'])) if x!=y)
  ac,bc=a['tokens_text'][j],b['tokens_text'][j];top=b['top_logprobs'][j];p_correct=math.exp(top[ac]) if ac in top else None;p_wrong=math.exp(b['token_logprobs'][j])
  out['branch'].append({'condition':c,'arm':arm,'common_tokens':j,'correct_token':ac,'wrong_token':bc,'correct_probability_same_logits':p_correct,'wrong_probability':p_wrong,'correct_logp_other_prefill':a['token_logprobs'][j],'wrong_over_correct':p_wrong/p_correct if p_correct else None,'echo_open_probability':math.exp(b['token_logprobs'][0]),'top20':top})
 for ref in ['correct','echo_no_system','echo_system','matched_correct','historical_greedy']:
  a=lookup['original_base',c,ref];b=lookup['step0',c,ref];diff=[abs(x-y) for x,y in zip(a['token_logprobs'],b['token_logprobs'])];tops=lambda r:[max(t,key=t.get) for t in r['top_logprobs']];ta,tb=tops(a),tops(b);split=next((i for i,(x,y) in enumerate(zip(ta,tb)) if x!=y),None)
  out['zero'].append({'condition':c,'reference':ref,'max_abs_target_logp_difference':max(diff),'mean_abs_target_logp_difference':sum(diff)/len(diff),'first_top1_difference_on_forced_path':split,'base_top1':ta[split] if split is not None else None,'zero_top1':tb[split] if split is not None else None})
(D/'SUMMARY.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:([{kk:vv for kk,vv in r.items() if kk!='top20'} for r in v] if k=='branch' else v) for k,v in out.items()},ensure_ascii=False,indent=2))
