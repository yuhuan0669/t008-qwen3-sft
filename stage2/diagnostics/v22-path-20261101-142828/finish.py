from pathlib import Path
import json,subprocess,tarfile,hashlib,datetime
D=Path(Path('/tmp/v22-path-dir').read_text());R=D.parents[2];k=['kubectl','--context','lmas00-direct','-n','swift']
with (D/'results.tar').open('wb') as f:subprocess.run(k+['exec',D.name,'--','tar','-C','/tmp/pathdiag','-cf','-','results'],stdout=f,check=True)
with tarfile.open(D/'results.tar') as t:t.extractall(D,filter='data')
rs=json.loads((D/'results/scores.json').read_text());assert len(rs)==40;L={(x['arm'],x['condition'],x['reference']):x for x in rs};eps=max(abs(x['mean_nll']-L['step0_repeat',x['condition'],x['reference']]['mean_nll']) for x in rs if x['arm']=='step0');threshold=max(.01,5*eps);results=[]
for cond in [False,True]:
 for base in ['step0','step8']:
  diffs=[]
  for bad in ['echo_no_system','echo_system']:
   for good in ['correct','matched_correct']:
    pref=lambda arm:L[arm,cond,good]['mean_nll']-L[arm,cond,bad]['mean_nll']
    diffs.append({'error':bad,'correct':good,'control_preference':pref(base),'v22_preference':pref('v22'),'difference':pref('v22')-pref(base)})
  verdict='SUPPORT' if all(x['difference']>threshold for x in diffs) else 'AGAINST' if all(x['difference'] < -threshold for x in diffs) else 'INDETERMINATE'
  results.append({'system':cond,'control':base,'verdict':verdict,'comparisons':diffs})
summary={'zero_repeat_max_mean_nll_change':eps,'threshold_nat_per_token':threshold,'results':results,'scoring_calls':40,'training':False};(D/'DECISION.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False,indent=2))
u=json.loads(subprocess.check_output(['kubectl','--context','lmas00-direct','-n','vllm','get','deploy','vllm','-o','json']));assert u['spec']==json.loads((D/'uat-before.json').read_text())['spec'] and u['spec']['replicas']==0;(D/'uat-after.json').write_text(json.dumps(u));subprocess.run(k+['delete','pod',D.name,'--wait=true','--timeout=30s'],check=True);(D/'cleanup.json').write_text(json.dumps({'pod_removed':True,'uat_spec_unchanged':True,'uat_replicas':0}))
