"""Verify immutable data and existing native encoding runtime without reallocating GPU."""
from pathlib import Path
import hashlib,json,subprocess
D=Path(__file__).resolve().parent;R=D.parents[2];P=D.parent/'t008-v0117-20261031-100924'
V=R/'stage1/variants/stage1-cpu-v0.1.22'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((V/'FILES.sha256.json').read_text())['files']
for n,h in frozen.items():assert sha(V/n)==h,n
for n,h in json.loads((D/'config-diff.json').read_text())['unchanged_artifacts'].items():assert sha(R/n)==h,n
script=r'''
from pathlib import Path
import hashlib,importlib,importlib.metadata as md,json,os,sys
p=json.load(sys.stdin);new=Path('/data')/p['run'];old=Path('/data/t008-v0117-20261031-100924')
sys.path[:0]=[str(new/'code'),str(new/'deps')]
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
 return h.hexdigest()
report=json.loads((new/'stage1/evidence/encoding-report.json').read_text())
versions={k:md.version(k) for k in report['versions']};assert versions==report['versions']
code={}
for name in ['code','stage1/scripts','runtime-support']:
 for f in (new/name).rglob('*'):
  if not f.is_file() or '__pycache__' in str(f):continue
  rel=f.relative_to(new);h=sha(f);assert h==sha(old/rel),str(rel);code[str(rel)]=h
sources={}
for module,expected in report['normalization_source_hashes'].items():
 path=Path(importlib.import_module(module).__file__);h=sha(path);assert h==expected,module;sources[module]=h
base=[]
for info in p['base_files']:
 f=Path('/base')/info['path'];assert f.stat().st_size==info['size'] and sha(f)==info['sha256'],info['path'];base.append(info)
sv=os.statvfs('/work');free=sv.f_bavail*sv.f_frsize;assert free>10*1024**3
print(json.dumps({'verified':True,'versions':versions,'support_code_hashes':code,'native_source_hashes':sources,'base_files':base,'free_work_bytes':free,'gpu_used':False,'native_encoding_reused':True}))
'''
payload={'run':D.name,'base_files':json.loads((P/'training-base-readback.json').read_text())['files']}
k=['kubectl','--context','lmas00-direct','--request-timeout=180s','-n','swift','exec','-i',D.name+'-prep','--','python3','-c',script]
result=subprocess.run(k,input=json.dumps(payload),text=True,capture_output=True,check=True,timeout=240)
o=json.loads(result.stdout);o['frozen_files_verified']=len(frozen)
(D/'runtime-preflight.json').write_text(json.dumps(o,indent=2)+'\n')
print(json.dumps({'verified':True,'frozen_files':len(frozen),'runtime_versions':o['versions'],'native_encoding_reused':True,'free_work_gib':round(o['free_work_bytes']/1024**3,1)}))
