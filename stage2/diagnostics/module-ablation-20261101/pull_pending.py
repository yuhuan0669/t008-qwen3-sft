from pathlib import Path
import subprocess,json,hashlib,re
D=Path(__file__).resolve().parent;O=D/'results';O.mkdir(exist_ok=True)
K=['kubectl','--context','lmas00-direct','--request-timeout=30s','-n','swift','exec','t008-module-ablation-20261101','--']
s=json.loads(subprocess.check_output(K+['python3','-c','from pathlib import Path;import json;d=Path("/tmp/diag");print(json.dumps({"progress":json.loads((d/"results/progress.json").read_text()),"answers":(d/"results/generations.jsonl").read_text(),"scores":(d/"results/scores.jsonl").read_text()}))']))
(O/'partial-generations.jsonl').write_text(s['answers']);(O/'partial-scores.jsonl').write_text(s['scores']);print(s['progress'])
seen={json.loads(x)['review_id'] for x in (O/'verdicts.jsonl').read_text().splitlines()} if (O/'verdicts.jsonl').exists() else set()
for i,l in enumerate(s['answers'].splitlines()):
 r=json.loads(l);key=(r['case_id'],r['system'],r['answer']);uid=hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()[:18]
 if uid in seen:continue
 seen.add(uid);a=r['answer']
 def collapse(m):
  unit=m.group(1);count=len(m.group(0))//len(unit)
  assert unit*count==m.group(0)
  return '[连续原样重复'+str(count)+'次：'+unit+']'
 display=re.sub(r'(.{4,180}?)(?:\1){3,}',collapse,a,flags=re.S)
 print('\nINDEX',i,r['arm'],r['case_id'],r['seed'],r['finish_reason'],r['output_tokens']);print(display)
