"""Combine explicit per-case review decisions with mechanical JSON scoring."""
from pathlib import Path
from collections import defaultdict, Counter
import json

O=Path(__file__).resolve().parent


def main():
    rows=[json.loads(x) for x in (O/'normalized.jsonl').read_text().splitlines()]
    review=json.loads((O/'semantic-review.json').read_text())
    for case_id, spec in review['reviewed_cases'].items():
        assert sum(x['case_id']==case_id for x in rows)==spec['expected_rows']
    assert len(review['reviewed_cases'])==20, 'Every non-JSON scenario must be explicitly reviewed'
    scored=[]
    for row in rows:
        item=dict(row)
        if row['category']=='json':
            item.update(task_pass=row['json_parse'] and row['json_schema'] and row['json_exact'],
                serious=[],review_basis='mechanical complete-content JSON parse/schema/exact-value check')
        else:
            policy=review['reviewed_cases'][row['case_id']]
            item.update(task_pass=policy['default_task_pass'],serious=policy.get('default_serious',[]),
                review_basis=policy['notes'])
            item.update(review['exceptions'].get(row['id'],{}))
        if row['empty'] or row['length']:
            item.update(task_pass=False, completeness_failure=True)
        scored.append(item)
    assert set(review['exceptions']) <= {x['id'] for x in rows}
    buckets=defaultdict(list)
    for row in scored:buckets[(row['model'],row['mode'])].append(row)
    summary=[]
    for (model,mode), group in sorted(buckets.items()):
        summary.append(dict(model=model,mode=mode,total=len(group),task_pass=sum(x['task_pass'] for x in group),
            serious_responses=sum(bool(x['serious']) for x in group),
            serious_types=dict(Counter(t for x in group for t in x['serious'])),
            empty=sum(x['empty'] for x in group),length=sum(x['length'] for x in group),
            categories={c:dict(passed=sum(x['task_pass'] for x in group if x['category']==c),
                total=sum(x['category']==c for x in group)) for c in sorted({x['category'] for x in group})}))
    pairs={}
    lookup={(r['model'],r['mode'],r['case_id'],r['seed'],r['turn']):r for r in scored}
    for candidate in ['t008-v0110','t008-v0112']:
        for mode in ['nonthinking','thinking']:
            counts=Counter()
            for key,row in lookup.items():
                model,m,c,s,t=key
                if model!='t008-base' or m!=mode:continue
                other=lookup[(candidate,m,c,s,t)]
                counts['both_pass' if row['task_pass'] and other['task_pass'] else
                       'candidate_only' if other['task_pass'] else 'base_only' if row['task_pass'] else 'both_fail']+=1
            pairs[candidate+'__'+mode]=dict(counts)
    (O/'scored.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in scored))
    (O/'selection-summary.json').write_text(json.dumps(dict(groups=summary,paired_vs_base=pairs,
        review_scope='All 468 visible replies, rule-based JSON scoring, explicit implementation-side semantic review. Public development scenarios; not blinded independent acceptance.'),ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
