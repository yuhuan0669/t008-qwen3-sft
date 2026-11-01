from pathlib import Path
import json,hashlib,subprocess
D=Path(__file__).resolve().parent;R=D.parents[2];old=R/'stage2/runs/t008-v0127-generalonly-20261101-121120';E=D/'evaluation';E.mkdir(exist_ok=True);p=json.loads((D/'protocol.json').read_text())['evaluation'];sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
for target,source in [('system.txt',R/p['system']),('thinking-prefill.jinja',R/p['chat_template']['path']),('base-files.json',old/'evaluation/base-files.json')]: (E/target).write_bytes(source.read_bytes())
case=json.loads((old/'evaluation/cases.json').read_text());case['items']=[x for x in case['items'] if x['id'] in {y['id'] for y in p['probes']}];assert len(case['items'])==8;(E/'cases.json').write_text(json.dumps(case,ensure_ascii=False,indent=2))
models=['original_base','step0','step2','step4','step8'];groups=[{'name':x+'_'+str(s),'mode':x,'system':s} for x in ['greedy','sampling'] for s in [False,True]]
slots=[{'model':m,'group':g['name'],'case_id':c['id'],'repeat':r} for m in models for g in groups if g['mode']=='greedy' or m in ['original_base','step8'] for c in case['items'] for r in range(1, (1 if g['mode']=='greedy' else 3)+1)];assert len(slots)==176
cfg={'models':models,'groups':groups,'request_modes':{x:p[x]['parameters'] for x in ['greedy','sampling']},'concurrency':8,'cases_sha256':sha(E/'cases.json'),'system_sha256':sha(E/'system.txt'),'chat_template':{'sha256':sha(E/'thinking-prefill.jinja')}}
for f,obj in [('evaluation-config.json',cfg),('missing-slots.json',slots)]: (E/f).write_text(json.dumps(obj,ensure_ascii=False,indent=2))
s=(old/'evaluation/run.py').read_text().replace('208','176').replace('range(1,4)','range(1,2)');(E/'run.py').write_text(s)
b=json.loads((old/'evaluation/runtime-binding.json').read_text());b['aliases']={'original_base':'octa-carbon-v1',**{m:'min16-'+m for m in models[1:]}};b['adapters']={};argv=b['server_argv'];i=argv.index('--lora-modules');argv=argv[:i]+['--lora-modules']
k=['kubectl','--context','lmas00-direct','-n','swift']
# Filled once training has completed.
(D/'eval-base-binding.json').write_text(json.dumps(b,indent=2))
pod=json.loads((old/'eval-pod.json').read_text().replace(old.name,D.name));(D/'eval-pod.json').write_text(json.dumps(pod,indent=2));print('176 slots prepared')
