"""Retrieve completed raw requests/responses without touching the model service."""
from pathlib import Path
import hashlib,json,subprocess
D=Path(__file__).resolve().parent
K=['kubectl','--context','lmas00-direct','--request-timeout=30s','-n','swift','exec',D.name+'-prep','--']
remote='/work/'+D.name+'/evaluation'
script="""from pathlib import Path
import hashlib,json,tarfile
d=Path(%r); assert json.loads((d/'complete.json').read_text())['count']==556
p=d/'raw-evidence.tar.gz'
with tarfile.open(p,'w:gz') as t:t.add(d/'raw',arcname='raw')
print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'response_files':len(list((d/'raw').rglob('response.raw.json')))}))
"""%remote
info=json.loads(subprocess.check_output(K+['python3','-c',script]));assert info['response_files']==556
target=D/'evaluation/raw-evidence.tar.gz'
with target.open('wb') as out:
 for offset in range(0,info['bytes'],4*1024*1024):
  n=min(4*1024*1024,info['bytes']-offset)
  s="import sys;f=open(%r,'rb');f.seek(%d);sys.stdout.buffer.write(f.read(%d))"%(remote+'/raw-evidence.tar.gz',offset,n)
  b=subprocess.check_output(K+['python3','-c',s]);assert len(b)==n;out.write(b)
assert hashlib.sha256(target.read_bytes()).hexdigest()==info['sha256']
info.update(verified=True,local_path=str(target.relative_to(D)))
(D/'raw-evidence-readback.json').write_text(json.dumps(info,indent=2)+'\n')
print(json.dumps(info))
