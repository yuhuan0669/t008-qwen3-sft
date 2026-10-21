"""Run exactly one Full after the three-step Smoke, then development and restoration."""
from pathlib import Path
import subprocess,json,time,sys
O=Path(__file__).resolve().parent;run=O.name;K=['kubectl','--context','lmas00-direct','--request-timeout=30s','-n','swift']
try:
 for _ in range(120):
  j=json.loads(subprocess.check_output(K+['get','job',run+'-smoke','-o','json']))
  if j['status'].get('failed'):raise RuntimeError('Smoke failed')
  if j['status'].get('succeeded'):break
  time.sleep(10)
 else:raise RuntimeError('Smoke timeout')
 raw=subprocess.check_output(K+['exec',run+'-prep','--','cat','/work/'+run+'/outputs/smoke/run_manifest.json']);(O/'smoke-manifest.json').write_bytes(raw);m=json.loads(raw);assert m['status']=='SMOKE_COMPLETE' and m['global_step']==3 and m['training_verified']
 print('Smoke passed; start one Full from original base',flush=True)
 subprocess.run(K+['apply','-f',str(O/'job-full.json')],check=True)
 subprocess.run([sys.executable,str(O/'finish_run.py')],check=True)
except BaseException as e:
 (O/'controller-error.json').write_text(json.dumps({'error':repr(e)})+'\n')
 subprocess.run([sys.executable,str(O/'window.py'),'restore'],check=True)
 raise
