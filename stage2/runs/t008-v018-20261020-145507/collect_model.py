"""Read-only retrieval and verification of completed training outputs."""
from pathlib import Path
import subprocess,json,hashlib,zipfile,shutil
O=Path(__file__).resolve().parent;R=O.parents[2];K=['kubectl','--context','lmas00-direct','--request-timeout=30s','-n','swift','exec',O.name+'-prep','--'];remote='/work/'+O.name+'/outputs/full';out=O/'outputs/full';out.mkdir(parents=True,exist_ok=True)
for f in ['run_manifest.json','train.log','training-scalars.json']:(out/f).write_bytes(subprocess.check_output(K+['cat',remote+'/'+f]))
m=json.loads((out/'run_manifest.json').read_text());assert m['status']=='TRAINED_CANDIDATE' and m['training_verified'] and m['global_step']==80 and m['epoch']==1.0
model=R/'stage2/local-models/stage1-cpu-v0.1.8/adapter.zip';model.parent.mkdir(exist_ok=True,parents=True)
with model.open('wb') as f:subprocess.run(K+['cat',remote+'/adapter.zip'],stdout=f,check=True)
h=hashlib.sha256(model.read_bytes()).hexdigest();assert h==m['adapter_package_sha256']
with zipfile.ZipFile(model) as z:
 for name,meta in m['adapter_files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==meta['sha256'],name
ck=m['checkpoint'].replace('/runwork','/work/'+O.name)
(out/'trainer_state.json').write_bytes(subprocess.check_output(K+['cat',ck+'/trainer_state.json']))
obj=R.parent/'t008_qwen3_assets/sha256'/h[:2]/h;obj.parent.mkdir(parents=True,exist_ok=True)
if not obj.exists():shutil.copyfile(model,obj)
assert hashlib.sha256(obj.read_bytes()).hexdigest()==h
(O/'model-local-copy.json').write_text(json.dumps({'sha256':h,'path':str(model.relative_to(R)),'object':str(obj),'verified':True,'adapter_files_verified':True},indent=2)+'\n')
print(json.dumps({k:m.get(k) for k in ['global_step','epoch','task_id','clearml_output_model_id','upload_status','adapter_package_sha256']}))
