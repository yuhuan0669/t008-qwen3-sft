from pathlib import Path
import json,sys,hashlib
D=Path(__file__).resolve().parent;O=D/'results'
rows=[json.loads(x) for x in (O/'partial-generations.jsonl').read_text().splitlines()]
p=O/'verdicts.jsonl';old=[json.loads(x) for x in p.read_text().splitlines()] if p.exists() else [];seen={x['review_id'] for x in old}
for k,opts in json.load(sys.stdin).items():
 r=rows[int(k)];key=(r['case_id'],r['system'],r['answer']);uid=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()[:18]
 assert uid not in seen and opts.get('note')
 v={'review_id':uid,'case_id':r['case_id'],'read_complete':True,'echo':False,'loop':False,'task_fail':False,'facts_fail':False,'unsupported_fail':False,'uncertain':False,'identity_pass':False};v.update(opts);old.append(v);seen.add(uid)
p.write_text(''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in old));print('reviewed unique',len(old))
