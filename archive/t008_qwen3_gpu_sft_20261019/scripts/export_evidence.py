"""Run in preparation Pod after restoration; archive metadata, retain raw checkpoints on PVC."""
import hashlib,json,pathlib,tarfile
root=pathlib.Path('/work/t008-qwen3-20261019-094113');output=root/'outputs'
records=[];selected=[]
for p in sorted(output.rglob('*')):
 if not p.is_file() or p.is_symlink():continue
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 record={'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':h.hexdigest()}
 records.append(record)
 if p.suffix in ('.json','.jsonl','.log','.txt','.png') or p.name.startswith('events.out'):
  selected.append(p)
(root/'persisted-output-manifest.json').write_text(json.dumps({'schema':'t008-persisted-output-files-v1','namespace':'swift','PVC':'swift-work','subPath':root.name,
 'raw_checkpoints_preserved':True,'all_files':records},ensure_ascii=False,indent=2)+'\n')
with tarfile.open(root/'output-evidence.tar.gz','w:gz') as archive:
 for p in selected:archive.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
 archive.add(root/'persisted-output-manifest.json',arcname='persisted-output-manifest.json')
print(json.dumps({'persisted_files':len(records),'metadata_files_exported':len(selected),'raw_checkpoints_retained_on_PVC':True}))
