import hashlib,json,pathlib
root=pathlib.Path('/data/t008-qwen3-20261019-094113')
files=[]
for p in sorted(root.rglob('*')):
 if not p.is_file() or p.is_symlink():continue
 files.append({'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps({'schema':'t008-runtime-input-files-v1','PVC':'swift-train-data','subPath':root.name,'files':files},indent=2))
