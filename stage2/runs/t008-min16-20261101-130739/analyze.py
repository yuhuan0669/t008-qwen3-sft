from pathlib import Path
import json,re,collections,hashlib
D=Path(__file__).resolve().parent;E=D/'evaluation'
rows=[json.loads(s) for s in (E/'results.jsonl').read_text().splitlines()];assert len(rows)==176
norm=lambda s:re.sub(r'\s+','',s)
groups=collections.defaultdict(list);unique={};mapped=[]
for i,r in enumerate(rows):
 a=r['response']['choices'][0]['message'].get('content') or '';q=r['request']['messages'][-1]['content'];na,nq=norm(a),norm(q)
 flags={'exact_echo':na==nq,'question_contained':nq in na,'empty':not na,'length_finish':r['response']['choices'][0]['finish_reason']=='length'}
 # This lexical flag is for reading, not a semantic verdict.
 grams={na[j:j+30] for j in range(max(0,len(na)-29))};flags['repeated_30_chars']=any(na.count(g)>=3 for g in grams) if grams else False
 key=(r['model'],r['group']);groups[key].append(flags)
 uk=(r['case_id'],a)
 if uk not in unique:unique[uk]={'review_id':len(unique)+1,'case_id':r['case_id'],'question':q,'answer':a,'uses':[]}
 unique[uk]['uses'].append({'model':r['model'],'group':r['group'],'repeat':r['repeat'],'flags':flags})
 mapped.append({'index':i,'review_id':unique[uk]['review_id'],**r,'mechanical_flags':flags})
summary={str(k):{'count':len(v),**{f:sum(x[f] for x in v) for f in v[0]}} for k,v in groups.items()}
(E/'mechanical-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));(E/'review-items.json').write_text(json.dumps(list(unique.values()),ensure_ascii=False,indent=2));(E/'review-mapped.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in mapped));print(json.dumps(summary,ensure_ascii=False));print('unique answers',len(unique))
