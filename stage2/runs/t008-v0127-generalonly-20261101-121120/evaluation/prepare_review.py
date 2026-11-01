"""Reuse corrected historical labels and prepare root review of new unique outputs."""
from pathlib import Path
from collections import defaultdict
import difflib,hashlib,json,re
D=Path(__file__).resolve().parent
P=D.parent.parent/'t008-v0126-idzero-20261101-112301/evaluation'
def jl(p):return [json.loads(s) for s in p.read_text().splitlines()]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def writejl(p,x):p.write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in x))
def norm(s):return re.sub(r'\s+','',s)
def main():
    reuse=json.loads((D/'reuse-summary.json').read_text())
    assert sha(P/'combined.jsonl')==reuse['source_sha256']
    summary=json.loads((P/'semantic-summary.json').read_text())
    for name,h in summary['input_binding']['files_sha256'].items():assert sha(P/name)==h,name
    labels={v['review_id']:v for p in sorted((P/'review').glob('verdicts-*.jsonl')) for v in jl(p)}
    for v in jl(P/'review/root-corrections.jsonl'):labels[v['review_id']].update(v['corrected'])
    assert hashlib.sha256(json.dumps(labels,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()==summary['input_binding']['effective_labels_sha256']
    old=jl(D/'reused-responses.jsonl');assert len(old)==624 and sha(D/'reused-responses.jsonl')==reuse['selected_sha256']
    cases=json.loads((D/'cases.json').read_text())['items'];byid={c['id']:c for c in cases}
    new=[]
    for r in jl(D/'results.jsonl'):
        ch=r['response']['choices'][0];m=ch['message'];a=m.get('content') or '';q=byid[r['case_id']]['question'];an,qn=norm(a),norm(q)
        ratio=difflib.SequenceMatcher(None,qn,an,autojunk=False).ratio() if len(an)<10000 else 0
        x={**{k:r[k] for k in ['group','model','case_id','repeat']},'answer':a,'finish_reason':ch.get('finish_reason'),
           'raw_path':r['raw_path'],'request_id':r['response'].get('id'),'reasoning':m.get('reasoning',m.get('reasoning_content')) or '',
           'usage':r['response'].get('usage'),'tool_calls':m.get('tool_calls'),'exact_echo':bool(an) and an==qn,
           'near_echo_screen':an!=qn and ratio>=.8,'similarity':round(ratio,4),'loop_screen':len(qn)>=15 and an.count(qn)>=2,
           'empty':not an,'truncated':ch.get('finish_reason')=='length'}
        x['review_id']='U'+hashlib.sha256((x['case_id']+'\0'+x['group']+'\0'+a).encode()).hexdigest()[:18];new.append(x)
    assert len(new)==208
    rows=old+new;assert len({(r['model'],r['group'],r['case_id'],r['repeat']) for r in rows})==832
    review=D/'review';review.mkdir(exist_ok=True)
    assert not (review/'verdicts-root.jsonl').exists()
    needed={r['review_id'] for r in rows}
    inherited=[v for k,v in labels.items() if k in needed]
    writejl(review/'verdicts-inherited.jsonl',inherited)
    pending=defaultdict(dict)
    for r in new:
        if r['review_id'] in labels:continue
        pending[r['case_id']][r['review_id']]={'review_id':r['review_id'],'condition':r['group'],'answer':r['answer'],
            'mechanical':{k:r[k] for k in ['exact_echo','near_echo_screen','loop_screen','truncated']}}
    bundles=[]
    for c in cases:
        if not pending[c['id']]:continue
        bundles.append({'case_id':c['id'],'question':c['question'],'category':c['group'],'criteria':c['criteria'],
                        'json_schema':c.get('json_schema'),'answers':list(pending[c['id']].values())})
    writejl(review/'bundle-root.jsonl',bundles);writejl(D/'combined.jsonl',rows)
    info={'slots':832,'new_slots':208,'inherited_unique_labels':len(inherited),
          'new_unique_review_required':sum(len(b['answers']) for b in bundles),
          'new_slots_with_inherited_label':sum(r['review_id'] in labels for r in new),
          'new_answer_characters':sum(len(a['answer']) for b in bundles for a in b['answers']),
          'historical_summary_sha256':sha(P/'semantic-summary.json')}
    dump(D/'review-queue.json',info);print(json.dumps(info))
if __name__=='__main__':main()
