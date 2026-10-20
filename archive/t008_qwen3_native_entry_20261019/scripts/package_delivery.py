import datetime,hashlib,json,pathlib,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
files=[]
for p in sorted(ROOT.rglob('*')):
 if not p.is_file() or any(x in p.parts for x in ('.git','__pycache__')) or p.suffix=='.pyc' or p.name=='MANIFEST.json':continue
 files.append({'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
manifest={'schema':'t008-native-entry-delivery-v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'source_git_commit':'e7ae45aa7438c8bcca8318d3531854f7f5e7db39','gpu_started':False,'files':files}
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
output=ROOT.with_suffix('.zip')
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for name in [x['path'] for x in files]+['MANIFEST.json']:
  z.write(ROOT/name,arcname=name)
with zipfile.ZipFile(output) as z:
 assert z.testzip() is None
 for x in files:
  assert hashlib.sha256(z.read(x['path'])).hexdigest()==x['sha256']
print(json.dumps({'payload_files':len(files),'zip_bytes':output.stat().st_size,'zip_sha256':hashlib.sha256(output.read_bytes()).hexdigest()}))
