"""Review only new unique answers; inherit identical historical case/condition labels."""
from pathlib import Path
from collections import Counter,defaultdict
import difflib,hashlib,json,re
D=Path(__file__).resolve().parent
P=D.parent.parent/'t008-v0117-20261031-100924/evaluation'
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def norm(s):return re.sub(r'\s+','',s)
def writejl(p,rows):p.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
def main():
    reuse=json.loads((D/'reuse-summary.json').read_text())
    assert sha(P/'combined.jsonl')==reuse['sha256']
    old=jl(P/'combined.jsonl');assert len(old)==2224
    labels={}
    for p in sorted((P/'review').glob('verdicts-*.jsonl')):
        for r in jl(p):assert r['review_id'] not in labels;labels[r['review_id']]=r
    for r in jl(P/'review/root-corrections.jsonl'):labels[r['review_id']].update(r['corrected'])
    assert len(labels)==2051 and all(x['read_complete'] for x in labels.values())
    cases=json.loads((D/'cases.json').read_text())['items'];byid={c['id']:c for c in cases}
    new=[]
    for r in jl(D/'results.jsonl'):
        ch=r['response']['choices'][0];m=ch['message'];a=m.get('content') or '';q=byid[r['case_id']]['question']
        an,qn=norm(a),norm(q)
        ratio=difflib.SequenceMatcher(None,qn,an,autojunk=False).ratio() if len(an)<10000 else 0
        x={**{k:r[k] for k in ['group','model','case_id','repeat']},'answer':a,'finish_reason':ch.get('finish_reason'),
           'raw_path':r['raw_path'],'request_id':r['response'].get('id'),'reasoning':m.get('reasoning',m.get('reasoning_content')) or '',
           'usage':r['response'].get('usage'),'tool_calls':m.get('tool_calls'),'exact_echo':bool(an) and an==qn,
           'near_echo_screen':an!=qn and ratio>=.8,'similarity':round(ratio,4),'loop_screen':len(qn)>=15 and an.count(qn)>=2,
           'empty':not an,'truncated':ch.get('finish_reason')=='length'}
        x['review_id']='U'+hashlib.sha256((x['case_id']+'\0'+x['group']+'\0'+a).encode()).hexdigest()[:18];new.append(x)
    assert len(new)==556
    rows=[{**x,'source_run':str(P.parent)} for x in old]+new
    assert len({tuple(x[k] for k in ['group','model','case_id','repeat']) for x in rows})==2780
    review=D/'review';review.mkdir(exist_ok=True)
    assert not list(review.glob('verdicts-[abc].jsonl')),'Never overwrite active review assignments'
    writejl(review/'verdicts-inherited.jsonl',list(labels.values()))
    pending=defaultdict(dict)
    for r in new:
        if r['review_id'] in labels:
            assert labels[r['review_id']]['case_id']==r['case_id'];continue
        pending[r['case_id']][r['review_id']]={'review_id':r['review_id'],'condition':r['group'],'answer':r['answer'],
            'mechanical':{k:r[k] for k in ['exact_echo','near_echo_screen','loop_screen','truncated']}}
    shards={s:[] for s in ['a','b','c','root']};weights=Counter()
    bundles=[]
    for c in cases:
        answers=list(pending[c['id']].values())
        if not answers:continue
        answers.sort(key=lambda r:r['review_id'])
        b={'case_id':c['id'],'question':c['question'],'category':c['group'],'criteria':c['criteria'],
           'json_schema':c.get('json_schema'),'answers':answers}
        if c['group'] in ['identity','json']:shards['root'].append(b)
        else:bundles.append(b)
    for b in sorted(bundles,key=lambda b:-sum(len(a['answer']) for a in b['answers'])):
        s=min(['a','b','c'],key=lambda s:weights[s]);shards[s].append(b);weights[s]+=sum(len(a['answer']) for a in b['answers'])
    for s,bs in shards.items():writejl(review/('bundle-'+s+'.jsonl'),bs)
    writejl(D/'combined.jsonl',rows)
    counts={s:{'questions':len(bs),'unique_answers':sum(len(b['answers']) for b in bs),'answer_characters':sum(len(a['answer']) for b in bs for a in b['answers'])} for s,bs in shards.items()}
    dump(D/'review-queue.json',{'slots':2780,'new_slots':556,'inherited_unique_labels':2051,
        'new_unique_review_required':sum(x['unique_answers'] for x in counts.values()),'shards':counts,
        'new_slots_with_inherited_label':sum(r['review_id'] in labels for r in new)})
    print(json.dumps(counts,ensure_ascii=False))
if __name__=='__main__':main()
