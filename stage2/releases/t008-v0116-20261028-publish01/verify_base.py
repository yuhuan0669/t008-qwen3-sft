from pathlib import Path
import json,hashlib,time
p=Path('/store/released/qwen3-8b-baseline/model'); expected=json.loads(Path('/tmp/base-files.json').read_text()); out=[]; start=time.monotonic()
for row in expected:
 f=p/row['path']; h=hashlib.sha256()
 with f.open('rb') as stream:
  for block in iter(lambda:stream.read(8*1024*1024),b''):h.update(block)
 actual={'path':row['path'],'size':f.stat().st_size,'sha256':h.hexdigest()}; assert actual['size']==row['size'] and actual['sha256']==row['sha256'],actual;out.append(actual)
print(json.dumps({'base_files_match':True,'files':out,'seconds':time.monotonic()-start}))
