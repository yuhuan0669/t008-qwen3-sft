import sys,json,shutil,pathlib,os,hashlib
payload=json.load(sys.stdin);old=pathlib.Path('/data/t008-v018-20261020-145507');new=pathlib.Path('/data/'+payload['run']);assert not new.exists();shutil.copytree(old,new,ignore=shutil.ignore_patterns('__pycache__','window.json'))
for name,text in payload['files'].items():
 p=new/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
report=json.loads((new/'stage1/evidence/encoding-report.json').read_text());report['identity_loss3_cpu_verified']=payload['weight_report'];(new/'stage1/evidence/encoding-report.json').write_text(json.dumps(report,indent=2)+'\n')
assert hashlib.sha256((new/'stage1/data/train.jsonl').read_bytes()).hexdigest()==payload['sha']
w=pathlib.Path('/work/'+payload['run']);assert not w.exists();w.mkdir()
for name in ['cache','tmp']: (w/name).mkdir()
for root in [new,w]:
 os.chown(root,10001,10001)
 for p in root.rglob('*'):
  if not p.is_symlink():os.chown(p,10001,10001)
checks={n:hashlib.sha256((new/n).read_bytes()).hexdigest() for n in payload['files']}
print(json.dumps({'run':payload['run'],'file_hashes':checks,'data_sha256':payload['sha'],'rows':len((new/'stage1/data/train.jsonl').read_text().splitlines())}))
