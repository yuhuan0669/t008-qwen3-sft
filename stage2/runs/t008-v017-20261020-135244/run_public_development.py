"""Reuse existing EvalScope worker for public development only; never read holdout files."""
from pathlib import Path
import json,subprocess,tarfile,hashlib
R=Path(__file__).resolve().parent;ROOT=R.parents[2];K=['kubectl','--context','lmas00-direct','-n','evalscope','exec'];TARGET='deployment/evalscope'
E=ROOT/'stage1/evaluation';worker=R/'public-evalscope-worker.py';protocol=json.loads((E/'protocol.json').read_text());public=[json.loads(s) for s in (E/'public-development.jsonl').read_text().splitlines()];assert len(public)==40
window=json.loads((R/'window.json').read_text());binding=json.loads((R/'evaluation-binding.json').read_text())
for cond,model in [('A','t008-base'),('C_new','t008-new')]:
 local=R/'development'/('public-'+cond);local.mkdir(parents=True,exist_ok=False);remote='/tmp/t008-public-development/'+R.name+'/'+cond
 install="import pathlib,sys;p=pathlib.Path(sys.argv[1]);p.mkdir(parents=True,exist_ok=False);(p/'worker.py').write_bytes(sys.stdin.buffer.read())"
 subprocess.run(K+['-i',TARGET,'--','python','-c',install,remote],input=worker.read_bytes(),check=True)
 payload={'phase':'public-development','development_condition':cond,'fixture':False,'remote_output':remote+'/output','binding':{**binding,'condition':cond,'purpose':'PUBLIC_DEVELOPMENT_ONLY','worker_sha256':hashlib.sha256(worker.read_bytes()).hexdigest(),'public_dataset_sha256':hashlib.sha256((E/'public-development.jsonl').read_bytes()).hexdigest()},'protocol':protocol,'specialized':[],'public':public,'system':(E/'custom-system.txt').read_text(),'endpoint':'http://'+R.name+'-eval.swift.svc.cluster.local:8000/v1','model':model,'deadline_utc':window['restore_start_utc'],'execution_signal':window['decision_ref'],'concurrency':8}
 (local/'payload.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
 with (local/'worker.log').open('wb') as f:
  result=subprocess.run(K+['-i',TARGET,'--','python','-u',remote+'/worker.py'],input=json.dumps(payload).encode(),stdout=f,stderr=subprocess.STDOUT)
 with (local/'evidence.tar.gz').open('wb') as f:subprocess.run(K+[TARGET,'--','tar','czf','-','-C',remote,'.'],stdout=f,check=True)
 with tarfile.open(local/'evidence.tar.gz') as tf:tf.extractall(local/'recovered',filter='data')
 (local/'host-exit.json').write_text(json.dumps({'returncode':result.returncode})+'\n')
 if result.returncode:raise RuntimeError('Public development failed; inspect persisted evidence')
 print(cond+' public development complete',flush=True)
