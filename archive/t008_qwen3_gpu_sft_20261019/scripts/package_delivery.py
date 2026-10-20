"""Freeze delivery evidence; candidate model ZIP is delivered separately."""
import datetime,hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
state=json.loads((ROOT/'evidence/session_state.json').read_text());assert state['training_verified'] and state['vllm_restored']
files=[]
excluded={'outputs/adapter-candidate.zip','outputs/output-evidence.tar.gz','MANIFEST.json'}
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or any(x in p.parts for x in ('private','__pycache__','.git')):continue
 name=p.relative_to(ROOT).as_posix()
 if name in excluded or p.suffix=='.pyc':continue
 files.append({'path':name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
model=ROOT/'outputs/adapter-candidate.zip'
manifest={'schema':'t008-gpu-sft-delivery-v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'TRAINED_CANDIDATE','vllm_restored':True,
 'files':files,'separately_delivered_candidate':{'file':model.name,'bytes':model.stat().st_size,'sha256':hashlib.sha256(model.read_bytes()).hexdigest()},
 'raw_checkpoints':'Retained on swift-work PVC; per-file hashes in outputs/persisted-output-manifest.json'}
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
output=ROOT.with_suffix('.zip')
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in [x['path'] for x in files]+['MANIFEST.json']:z.write(ROOT/name,arcname=name)
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 for x in files:assert hashlib.sha256(z.read(x['path'])).hexdigest()==x['sha256']
print(json.dumps({'files':len(files),'evidence_zip_bytes':output.stat().st_size,'evidence_zip_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'candidate_zip_bytes':model.stat().st_size}))
