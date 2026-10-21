"""Read-only snapshot and grouped complete visible answers for manual review."""
from pathlib import Path
from collections import defaultdict, Counter
import json
import subprocess
import sys

O=Path(__file__).resolve().parent
if '--pull' in sys.argv:
    blob=subprocess.check_output(['kubectl','--context','lmas00-direct','--request-timeout=30s',
        '-n','swift','exec',(O/'pod-name.txt').read_text().strip(),'--','cat','/tmp/final-check/results.jsonl'])
    # A concurrent append can leave the final line incomplete in a read snapshot.
    rows=[]
    for line in blob.splitlines():
        try: rows.append(json.loads(line))
        except json.JSONDecodeError: pass
    (O/'review-cache.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows))
else:
    source=O/'results/results.jsonl'
    if not source.exists():source=O/'review-cache.jsonl'
    rows=[json.loads(x) for x in source.read_text().splitlines()]
case_ids=[x for x in sys.argv[1:] if not x.startswith('--')]
print('snapshot_count',len(rows),'case_counts',dict(Counter(x['case_id'] for x in rows)))
for case_id in case_ids:
    grouped=defaultdict(list)
    for r in rows:
        if r['case_id']!=case_id: continue
        if '--nonthinking' in sys.argv and r['mode']!='nonthinking':continue
        if '--thinking' in sys.argv and r['mode']!='thinking':continue
        message=r['response']['choices'][0]['message']
        answer=(message.get('content') or '').strip()
        if '--reasoning' in sys.argv:answer=(message.get('reasoning') or message.get('reasoning_content') or '').strip()
        grouped[answer].append(r['id'])
    for answer, ids in grouped.items():
        print('\nIDS',json.dumps(ids,ensure_ascii=False),'\n'+(answer or '[EMPTY]'))
