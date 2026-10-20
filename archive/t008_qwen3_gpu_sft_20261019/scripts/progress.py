"""Read existing training log only; no model execution or tests."""
import datetime,json,pathlib,subprocess
root=pathlib.Path(__file__).resolve().parents[1]
run=json.loads((root/'evidence/owner_authorization.json').read_text())['run_id']
query="""import ast,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);result={}
if p.exists():
 with p.open('rb') as h:
  h.seek(max(0,p.stat().st_size-24000));text=h.read().decode(errors='replace')
 for line in text.replace('\\r','\\n').splitlines():
  if 'global_step/max_steps' not in line:continue
  try:d=ast.literal_eval(line.strip())
  except (ValueError,SyntaxError):continue
  result={k:d[k] for k in ('global_step/max_steps','loss','train_loss','epoch','elapsed_time','remaining_time','memory(GiB)') if k in d}
print(json.dumps(result))"""
p=subprocess.run(['kubectl','--context','lmas00-direct','--request-timeout=20s','-n','swift','exec',run+'-prep','--','python3','-c',query,'/work/'+run+'/outputs/full/train.log'],capture_output=True,text=True,timeout=30,check=True)
state=json.loads((root/'evidence/session_state.json').read_text())
r={'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'phase':state['phase'],'metrics':json.loads(p.stdout)}
with (root/'evidence/progress-history.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
print(json.dumps(r,ensure_ascii=False))
