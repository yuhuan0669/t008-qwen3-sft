"""Read-only retrieval and verification of completed training outputs."""
from pathlib import Path
import subprocess,json,hashlib,zipfile,shutil
O=Path(__file__).resolve().parent;R=O.parents[2];K=['kubectl','--context','lmas00-direct','--request-timeout=30s','-n','swift','exec',O.name+'-prep','--'];remote='/work/'+O.name+'/outputs/full';out=O/'outputs/full';out.mkdir(parents=True,exist_ok=True)
for f in ['run_manifest.json','train.log','training-scalars.json']:(out/f).write_bytes(subprocess.check_output(K+['cat',remote+'/'+f]))
m=json.loads((out/'run_manifest.json').read_text());assert m['status']=='TRAINED_CANDIDATE' and m['training_verified'] and m['global_step']==66 and m['epoch']==1.0
model=R/'stage2/local-models/model-v0.1.23/adapter.zip';model.parent.mkdir(exist_ok=True,parents=True)
partial=model.with_suffix('.part')
# Large exec streams ended early even with a longer timeout. Read bounded chunks;
# reuse a partial download only after its bytes match the corresponding remote prefix.
probe="from pathlib import Path;import hashlib,json;p=Path("+repr(remote+'/adapter.zip')+");print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))"
source=json.loads(subprocess.check_output(K+['python3','-c',probe]));assert source['sha256']==m['adapter_package_sha256']
offset=partial.stat().st_size if partial.exists() else 0
assert offset<=source['bytes']
if offset:
 prefix="from pathlib import Path;import hashlib;p=Path("+repr(remote+'/adapter.zip')+");print(hashlib.sha256(p.read_bytes()[:"+str(offset)+"]).hexdigest())"
 assert subprocess.check_output(K+['python3','-c',prefix]).decode().strip()==hashlib.sha256(partial.read_bytes()).hexdigest()
chunks=[]
with partial.open('ab') as f:
 while offset<source['bytes']:
  size=min(4*1024*1024,source['bytes']-offset)
  script="import sys;p=open("+repr(remote+'/adapter.zip')+",'rb');p.seek("+str(offset)+");sys.stdout.buffer.write(p.read("+str(size)+"))"
  chunk=subprocess.check_output(K+['python3','-c',script]);assert len(chunk)==size
  f.write(chunk);chunks.append({'offset':offset,'bytes':size});offset+=size
h=hashlib.sha256(partial.read_bytes()).hexdigest();assert h==m['adapter_package_sha256']
partial.replace(model)
(O/'download-recovery.json').write_text(json.dumps({'source':source,'resumed_verified_prefix_bytes':chunks[0]['offset'] if chunks else source['bytes'],'chunks':chunks,'final_sha256':h,'verified':True},indent=2)+'\n')
with zipfile.ZipFile(model) as z:
 for name,meta in m['adapter_files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==meta['sha256'],name
ck=m['checkpoint'].replace('/runwork','/work/'+O.name)
(out/'trainer_state.json').write_bytes(subprocess.check_output(K+['cat',ck+'/trainer_state.json']))
obj=R.parent/'t008_qwen3_assets/sha256'/h[:2]/h;obj.parent.mkdir(parents=True,exist_ok=True)
if not obj.exists():shutil.copyfile(model,obj)
assert hashlib.sha256(obj.read_bytes()).hexdigest()==h
(O/'model-local-copy.json').write_text(json.dumps({'sha256':h,'path':str(model.relative_to(R)),'object':str(obj),'verified':True,'adapter_files_verified':True},indent=2)+'\n')
print(json.dumps({k:m.get(k) for k in ['global_step','epoch','task_id','clearml_output_model_id','upload_status','adapter_package_sha256']}))
