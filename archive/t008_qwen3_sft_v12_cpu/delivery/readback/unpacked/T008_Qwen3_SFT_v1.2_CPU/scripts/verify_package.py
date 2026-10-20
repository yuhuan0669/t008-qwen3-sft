"""Run after extracting the ZIP: python scripts/verify_package.py <packet-root>."""
import pathlib,json,hashlib,sys
root=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '.').resolve()
manifest=json.loads((root/'MANIFEST.json').read_text())
def sha(f):
 h=hashlib.sha256()
 with f.open('rb') as src:
  for block in iter(lambda:src.read(1024*1024),b''):h.update(block)
 return h.hexdigest()
for entry in manifest['files']:
 f=root/entry['path']
 assert f.is_file(),entry['path']
 assert f.stat().st_size==entry['bytes'],entry['path']
 assert sha(f)==entry['sha256'],entry['path']
original=root/'work/original-v1.2';candidate=root/'work/length-candidate-v1.2'
raw=(original/'train.jsonl').read_bytes().splitlines(keepends=True)
derived=(candidate/'train.jsonl').read_bytes().splitlines(keepends=True)
excluded={x['index'] for x in json.loads((candidate/'exclusions.json').read_text())}
assert len(raw)==2600 and len(derived)==1642 and len(excluded)==958
assert derived==[line for i,line in enumerate(raw) if i not in excluded]
assert (original/'train.jsonl').read_bytes()==(root/'work/original-quarantined-v1.2/train.jsonl').read_bytes()
native=[json.loads(x) for x in (root/'work/original-quarantined-v1.2/raw-loader.jsonl').read_text().splitlines()]
assert all(x['messages']==json.loads(line)['messages'] for x,line in zip(native,raw))
assert all(i<2000 for i in excluded)
gate=json.loads((root/'evidence/gpu_gate_checklist.json').read_text())
assert gate['recommendation']=='NO_GO_GPU' and gate['smoke_started'] is False
print(json.dumps({'files_verified':len(manifest['files']),'original_rows':len(raw),
 'candidate_rows':len(derived),'exact_exclusion_chain':True,'gpu_recommendation':'NO_GO_GPU'},ensure_ascii=False))
