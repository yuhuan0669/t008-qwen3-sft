"""Summarize completed fixed public development outputs, without rerunning or changing scores."""
from pathlib import Path
import json,collections
R=Path(__file__).resolve().parent
summary=[];bycondition={};formats=[]
for cond in ['A','C_new']:
 root=R/'development'/('public-'+cond)/'recovered/output';completion=json.loads((root/'run-complete.json').read_text());assert completion['case_conditions']==80
 values={}
 for f in sorted(root.glob('*/evalscope/reviews/**/*.jsonl')):
  group=f.parents[3].name;parts=group.split('__');mode,suite=parts[1],parts[-1];rows=[json.loads(x) for x in f.read_text().splitlines()];assert len(rows)==20
  key='prompt_level_strict' if suite=='ifeval' else 'acc';scores={};errors=0
  for row in rows:
   ss=row['sample_score'];cid=ss['sample_metadata']['t008_case_id'];assert cid not in scores;scores[cid]=int(ss['score']['value'][key]==1);errors+=bool(ss['score'].get('metadata',{}).get('scoring_error'))
  values[(mode,suite)]=scores
  summary.append({'condition':cond,'mode':mode,'suite':suite,'correct':sum(scores.values()),'total':20,'scoring_errors':errors})
 assert len(values)==4;bycondition[cond]=values
 turns=[json.loads(x) for f in root.glob('*/turn-results.jsonl') for x in f.read_text().splitlines()];assert len(turns)==80
 formats.append({'condition':cond,'requests':80,'empty_body':sum(not t['body'].strip() for t in turns),'protocol_errors':dict(collections.Counter(t['protocol_error'] for t in turns if t['protocol_error'])),'problem_cases':[{'case_id':t['case_id'],'group':t['group'],'protocol_error':t['protocol_error'],'empty_body':not bool(t['body'].strip())} for t in turns if t['protocol_error']]})
pairs=[]
for mode,suite in bycondition['A']:
 a=bycondition['A'][(mode,suite)];c=bycondition['C_new'][(mode,suite)];assert a.keys()==c.keys()
 pairs.append({'mode':mode,'suite':suite,'original_correct':sum(a.values()),'v017_correct':sum(c.values()),'wins':sum(c[k]>a[k] for k in a),'losses':sum(c[k]<a[k] for k in a),'ties':sum(c[k]==a[k] for k in a)})
result={'scope':'40 public development questions in two modes; not formal acceptance','metrics':summary,'paired_comparison':pairs,'format':formats}
(R/'development/public-comparison.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
