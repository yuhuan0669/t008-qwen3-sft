"""Descriptive wording screen; these counts are not correctness labels."""
from pathlib import Path
from collections import defaultdict,Counter
import json,re
D=Path(__file__).resolve().parent
PATTERNS={
 'does_not_establish':r'\bdoes not establish\b',
 'alone_does_not':r'\balone does not\b',
 'chinese_hedge':r'不能(?:说明|证明|据此)|不足以|不(?:能|可)仅凭|并不(?:代表|意味着)|不等于',
 'identity_tail':r'(?:如(?:果)?(?:您|你)?有|欢迎|可(?:以)?(?:随时)?向我)[^。\n]{0,60}(?:能碳|能源|碳排放)|(?:能碳|能源|碳排放)[^。\n]{0,50}(?:随时|欢迎|向我提问)',
 'custom_identity':r'能碳章鱼|章鱼能碳',
}
cases={x['id']:x for x in json.loads((D/'cases.json').read_text())['items']}
counts=defaultdict(Counter);examples=[]
for line in (D/'combined.jsonl').read_text().splitlines():
 r=json.loads(line);a=r['answer'];c=cases[r['case_id']];key=(r['model'],r['group'])
 counts[key].update(answers=1,characters=len(a))
 if c['group']!='identity': counts[key]['nonidentity_answers']+=1
 for label,pattern in PATTERNS.items():
  hits=list(re.finditer(pattern,a,re.I))
  counts[key][label+'_occurrences']+=len(hits)
  counts[key][label+'_answers']+=bool(hits)
  if label=='custom_identity' and c['group']!='identity': counts[key]['custom_identity_nonidentity_answers']+=bool(hits)
  if hits:
   examples.append({k:r[k] for k in ['model','group','case_id','repeat','review_id']}|{'pattern':label,'hits':[h.group() for h in hits]})
out={'groups':[{'model':k[0],'group':k[1],**v} for k,v in counts.items()],
 'limits':['Phrase frequency is descriptive, not correctness or a causal test.',
           'Chinese-only evaluation cannot resolve the reported English style risk.',
           'Hedge wording can be required by the question; identity phrases can occur in legitimate templates. Review context before classifying side effects.']}
(D/'style-summary.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
(D/'style-screen-examples.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in examples))
print(json.dumps({'groups':len(counts),'screened_slots':sum(c['answers'] for c in counts.values())}))
