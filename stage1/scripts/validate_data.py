"""Independent reconstruction checks for the delivered derivative, no model calls."""
from pathlib import Path
import json,hashlib,collections,sys
sys.path.insert(0,str(Path(__file__).parent));from prepare_data import structure_reasons
R=Path(__file__).resolve().parents[2];D=R/'stage1/data'
def read(p):return [json.loads(x) for x in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((D/'manifest.json').read_text());parent=R/m['parent_path'];assert sha(parent)==m['parent_sha256']
for name,digest in m['files_sha256'].items():assert sha(D/name)==digest,name
train=read(D/'train.jsonl');tm=read(D/'train-map.jsonl');ex=read(D/'exclusions.jsonl');reductions=read(D/'exposure-reductions.jsonl')
allmaps=tm+ex+reductions;idxs=[x['parent_row_zero_based'] for x in allmaps if x['parent_row_zero_based'] is not None]
assert sorted(idxs)==list(range(2600)), 'Each parent exposure has exactly one disposition'
assert len(train)==m['rows']==len(tm)
raw=parent.read_bytes().splitlines(keepends=True);new=(D/'train.jsonl').read_bytes().splitlines(keepends=True)
for i,x in enumerate(tm):
 assert x['train_row_zero_based']==i
 if x['parent_row_zero_based'] is not None and not x['modified']:assert new[i]==raw[x['parent_row_zero_based']]
 assert not structure_reasons(train[i])
assert [x['parent_row_zero_based'] for x in tm if x['parent_row_zero_based'] is not None]==sorted(x['parent_row_zero_based'] for x in tm if x['parent_row_zero_based'] is not None)
assert structure_reasons({'messages':[{'role':'assistant','content':'<think>unfinished'}]})==['unclosed_think']
assert structure_reasons({'messages':[{'role':'assistant','content':'<think>x</think>  '}]})==['empty_final_body']
assert structure_reasons({'messages':[{'role':'assistant','content':'示例代码包含字符串 `<think>`，不是真实思考块。'}]})==[]
assert len(read(D/'identity-review.jsonl'))==108
assert len(read(D/'additions.jsonl'))==30
for row in read(D/'modifications.jsonl'):
 for idx in row['parent_rows_zero_based']:assert json.loads(raw[idx])==row['original']
a=read(R/'stage1/evidence/train-encoding.jsonl');assert len(a)==len(train)
assert all(x['tokens']<=2048 and x['supervised_tokens']>0 for x in a)
result={'passed':True,'checks':['parent hash','all delivered data hashes','complete exclusive parent disposition','unchanged rows byte-identical','original retained order','108 identity reviews','30 additions','change originals reconstruct','structural false-positive regression','real Swift per-row encoding'],'rows':len(train),'training_started':False}
(R/'stage1/evidence/data-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
