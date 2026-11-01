"""Analyze persisted diagnostic rows; never calls inference or changes services."""
from collections import Counter,defaultdict
from pathlib import Path
import hashlib,json,statistics
D=Path(__file__).resolve().parent;O=D/'results'
def jl(p):return [json.loads(x) for x in p.read_text().splitlines()] if p.exists() else []
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,x):(D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
arms=['all_on','attention_only','mlp_only','all_off']
scores=jl(O/'scores.jsonl');gens=jl(O/'generations.jsonl')
assert len(scores)==256 and len(gens)==128
assert len({(x['arm'],x['case_id'],x['system'],x['reference']) for x in scores})==256
assert len({(x['arm'],x['case_id'],x['seed']) for x in gens})==128
cases={c['id']:c for c in json.loads((D/'inputs/cases.json').read_text())['cases']}
flat=[];unique={}
for r in gens:
    key=(r['case_id'],r['system'],r['answer'])
    if key not in unique:
        uid=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()[:18]
        unique[key]=len(flat);flat.append({'review_id':uid,'case_id':r['case_id'],'question':cases[r['case_id']]['question'],'criteria':cases[r['case_id']]['criteria'],'category':r['category'],'answer':r['answer'],'finish_reason':r['finish_reason'],'slots':[]})
    item=flat[unique[key]];item['slots'].append({'arm':r['arm'],'seed':r['seed']});r['review_id']=item['review_id']
save('results/review-flat.json',flat)
labels={x['review_id']:x for x in jl(O/'verdicts.jsonl')}
groups=[]
for arm in arms:
    for cat in ['identity','echo_or_loop']:
        rr=[r for r in gens if r['arm']==arm and r['category']==cat]
        ct=Counter(n=len(rr),truncated=sum(r['finish_reason']=='length' for r in rr),empty=sum(not r['answer'].strip() for r in rr))
        for r in rr:
            v=labels.get(r['review_id'])
            if not v:continue
            assert v['read_complete'];ct['reviewed']+=1
            for k in ['echo','loop','task_fail','facts_fail','unsupported_fail','uncertain','identity_pass']:
                ct[k]+=int(bool(v.get(k)))
        groups.append({'arm':arm,'category':cat,**ct})
prob=[]
for arm in arms:
    for cat in ['identity','echo_or_loop']:
        for sy in [False,True]:
            rr=[r for r in scores if r['arm']==arm and r['category']==cat and r['system']==sy]
            good=[r for r in rr if r['reference']=='expected'];other=[r for r in rr if r['reference']!='expected']
            assert len(good)==len(other)==8
            means=lambda key:statistics.mean(r[key] for r in good)
            prob.append({'arm':arm,'category':cat,'system':sy,'n':8,'expected_mean_nll':means('mean_nll'),'alternate_mean_nll':statistics.mean(r['mean_nll'] for r in other),'expected_mean_filtered_zero_tokens':means('filtered_zero_tokens'),'expected_product_name_mean_nll':statistics.mean(r['product_name_nll'] for r in good) if cat=='identity' else None})
save('SUMMARY.json',{'generations':128,'scores':256,'unique_answers':len(flat),'reviewed_unique':len(labels),'unreviewed_slots':sum(r['review_id'] not in labels for r in gens),'groups':groups,'fixed_reference_scores':prob,'artifacts_sha256':{str(p.relative_to(D)):sha(p) for p in [O/'scores.jsonl',O/'generations.jsonl',D/'inputs/manifest.json',D/'input-binding.json']},'scope':'Conditional contributions within one jointly trained LoRA; not independent acceptance or a trained module-only candidate.'})
print(json.dumps({'generations':128,'scores':256,'unique_answers':len(flat),'reviewed_unique':len(labels),'groups':groups,'fixed_reference_scores':prob},ensure_ascii=False))
