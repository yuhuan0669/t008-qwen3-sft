import datetime,hashlib,json,os,pathlib,zipfile
root=pathlib.Path('/store/t008-qwen3-20261019-094113-test-stage')
p=root/'adapter-candidate.zip'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='33feb7cfe9e3bafa1a5b72f32e179fe89448c4c4251e152763dd846d3adffd1d'
adapter=root/'adapter';adapter.mkdir(exist_ok=False)
with zipfile.ZipFile(p) as z:
 for info in z.infolist():
  assert pathlib.PurePosixPath(info.filename).name==info.filename
  data=z.read(info.filename);(adapter/info.filename).write_bytes(data)
files=[{'name':q.name,'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()} for q in sorted(adapter.iterdir())]
manifest={'status':'TEST_SERVING_ONLY_NOT_QUALITY_ACCEPTED','user_instruction':'现在加载，因为要测试','at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'model_id':'octacarbon-llm-sft-test','source_clearml_model_id':'0552c3ab6b39456e9ec8b32129015be0','source_checkpoint':'checkpoint-103','source_package_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'files':files}
(root/'test-serving-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
p.unlink()
for q in adapter.iterdir():q.chmod(0o444)
adapter.chmod(0o555);(root/'test-serving-manifest.json').chmod(0o444);root.chmod(0o555)
print(json.dumps(manifest,ensure_ascii=False))
