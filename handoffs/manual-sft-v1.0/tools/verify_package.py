"""Read-only local verification; no Swift/Torch/cluster/network imports."""
from pathlib import Path
import argparse,ast,hashlib,json,re,zipfile
P=Path(__file__).resolve().parents[1]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--source-root',type=Path);x=a.parse_args();m=json.loads((P/'MANIFEST.json').read_text());expected={i['path'] for i in m['files']};actual={str(p.relative_to(P)) for p in P.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='MANIFEST.json' and not any(str(p.relative_to(P)).startswith('models/'+v+'/adapter/') for v in ['v0.1.13','v0.1.14'])};assert actual==expected,(actual-expected,expected-actual)
 for r in m['files']:
  p=P/r['path'];assert p.stat().st_size==r['bytes'] and sha(p)==r['sha256'],r['path']
 source=json.loads((P/'SOURCE_MAP.json').read_text())
 for r in source:
  assert sha(P/r['package_path'])==r['sha256'],r['package_path']
  if x.source_root:assert sha(x.source_root/r['source'])==r['sha256'],r['source']
 for p in P.rglob('*.py'):ast.parse(p.read_text())
 for p in P.rglob('*.json'):json.loads(p.read_text())
 for p in P.rglob('*.jsonl'):
  for line in p.read_text().splitlines():json.loads(line)
 cfg=json.loads((P/'config/actual-v0.1.14-training.json').read_text());data=P/'data/v0.1.14/train.jsonl';assert len(data.read_text().splitlines())==1325 and sha(data)==cfg['dataset_sha256']
 cpu=json.loads((P/'data/v0.1.14/cpu-check/report.json').read_text());assert cpu['verified'] and cpu['rows']==1325 and cpu['weight_mismatch_rows']==0 and cpu['silent_dropped_rows']==0
 assert (P/'plugins/identity_loss3.py').read_bytes()==(P/'data/v0.1.14/identity_loss3.py').read_bytes();assert (P/'plugins/identity-keys.json').read_bytes()==(P/'data/v0.1.14/identity-keys.json').read_bytes()
 models=json.loads((P/'models/LOCATORS.json').read_text())
 for model in models['included_adapters']:
  p=P/model['package_path'];assert sha(p)==model['sha256']
  with zipfile.ZipFile(p) as z:
   for name,v in model['files'].items():
    assert hashlib.sha256(z.read(name)).hexdigest()==v['sha256']
    extracted=p.parent/'adapter'/name
    if extracted.exists():assert sha(extracted)==v['sha256']
 e=P/'evaluation/materials';s=json.loads((e/'spec.json').read_text())
 for file,key in [('custom-system.txt','system_sha256'),('thinking-prefill.jinja','template_sha256'),('scenarios.jsonl','scenarios_sha256')]:assert sha(e/file)==s[key],file
 cases=[json.loads(q) for q in (e/'scenarios.jsonl').read_text().splitlines()];assert len(cases)==17 and sum(len(c['seeds'])*len(c['user_turns']) for c in cases)*6==120
 schemas=[c for c in cases if 'response_format'in c];assert len(schemas)==4
 for c in schemas:assert 'expected_for_scoring_only' not in json.dumps(c['response_format'])
 history=json.loads((P/'history/experiments.json').read_text());assert len(history)==13 and sum(r['successful_full'] for r in history)==12 and sum(not r['successful_full'] for r in history)==1
 for r in history:
  assert (P/r['manifest']).is_file()
  if r['report']:assert (P/r['report']).is_file()
 links=0
 for rel in ['README.md','MANUAL.md','EXPERIMENTS.md','runtime/ENVIRONMENT.md']:
  p=P/rel
  for target in re.findall(r'\]\(([^)]+)\)',p.read_text()):
   if '://' in target or target.startswith('#'):continue
   assert (p.parent/target.split('#')[0]).exists(),(rel,target);links+=1
 print(json.dumps({'verified':True,'package_version':'manual-sft-v1.0','manifest_files':len(expected),'source_copies':len(source),'source_files_compared':bool(x.source_root),'entrypoint_links':links,'successful_full_runs':12,'interrupted_full_attempts':1,'rows':1325,'schemas':4,'comparison_requests':120,'model_zip_hashes_verified':2,'checks':'Local hashes, syntax, links, historical bindings only','new_training_executed':False,'new_inference_executed':False,'cluster_accessed':False,'uat_changed':False},ensure_ascii=False))
if __name__=='__main__':main()
