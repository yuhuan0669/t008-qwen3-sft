"""Merge fixed historical slots and new outputs; make anonymous content-review bundles."""
from pathlib import Path
from collections import Counter, defaultdict
import difflib, hashlib, json, re

D=Path(__file__).resolve().parent
def lines(p):return [json.loads(s) for s in p.read_text().splitlines()] if p.exists() else []
def norm(s):return re.sub(r'\s+','',s or '')
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')

def main():
    cases=json.loads((D/'cases.json').read_text())['items'];byid={c['id']:c for c in cases}
    rows=lines(D/'reused-responses.jsonl')
    for r in lines(D/'results.jsonl'):
        ch=r['response']['choices'][0];message=ch['message']
        rows.append({**{k:r[k] for k in ['group','model','case_id','repeat']},'answer':message.get('content') or '',
                     'finish_reason':ch.get('finish_reason'),'raw_path':r['raw_path'],'request_id':r['response'].get('id'),
                     'reasoning':message.get('reasoning',message.get('reasoning_content')) or '',
                     'usage':r['response'].get('usage'),'tool_calls':message.get('tool_calls')})
    keys=[(r['group'],r['model'],r['case_id'],r['repeat']) for r in rows];assert len(keys)==len(set(keys))
    summary=defaultdict(Counter);items=defaultdict(dict)
    for r in rows:
        c=byid[r['case_id']];a=r['answer'];q=c['question'];an=norm(a);qn=norm(q)
        exact=bool(an) and an==qn
        ratio=difflib.SequenceMatcher(None,qn,an,autojunk=False).ratio() if len(an)<10000 else 0
        loop=bool(len(qn)>=15 and an.count(qn)>=2)
        r.update(exact_echo=exact,near_echo_screen=not exact and ratio>=0.8,similarity=round(ratio,4),
                 loop_screen=loop,empty=not an,truncated=r['finish_reason']=='length')
        r['review_id']='U'+digest(r['case_id']+'\0'+r['group']+'\0'+a)[:18]
        v=summary[(r['model'],r['group'])];v.update({'n':1,'exact_echo':int(exact),'near_echo_screen':int(r['near_echo_screen']),
            'loop_screen':int(loop),'empty':int(r['empty']),'truncated':int(r['truncated'])})
        items[r['case_id']][r['review_id']]={'review_id':r['review_id'],'condition':r['group'],'answer':a,
            'mechanical':{'exact_echo':exact,'near_echo_screen':r['near_echo_screen'],'loop_screen':loop,'truncated':r['truncated']}}
    # Existing near/exact screens are clues, never semantic task pass labels.
    root=D/'review';root.mkdir(exist_ok=True)
    for shard,subset in [('a',cases[:32]),('b',cases[44:88]),('c',cases[88:128]+cases[32:44]),('root',cases[128:])]:
        bundles=[]
        for c in subset:
            answers=list(items[c['id']].values());answers.sort(key=lambda x:digest(x['review_id']+'fixed-v0117-order'))
            bundles.append({'case_id':c['id'],'question':c['question'],'category':c['group'],'criteria':c['criteria'],
                'json_schema':c.get('json_schema'),'answers':answers})
        target=root/('bundle-'+shard+'.jsonl');tmp=target.with_suffix('.tmp')
        tmp.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in bundles));tmp.replace(target)
    (D/'combined.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
    report={'slots':len(rows),'planned_slots':2224,'unique_review_items':sum(len(v) for v in items.values()),
        'groups':[{'model':k[0],'group':k[1],**v} for k,v in summary.items()],
        'screening_note':'Exact equality is mechanical; near-echo and loops need reading; no semantic pass rate inferred.'}
    dump(D/'mechanical-summary.json',report);print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':main()
