"""Offline preparation only; does not launch the bundled inference runner."""
from pathlib import Path
import argparse,json,hashlib,shutil
P=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--candidate',required=True,type=Path);a.add_argument('--output',required=True,type=Path);a.add_argument('--approved',action='store_true');x=a.parse_args();assert not x.output.exists();shutil.copytree(P/'evaluation/materials',x.output);s=json.loads((x.output/'spec.json').read_text());old=s['adapters']['t008-v0114'];old['path']=str(P/'models/v0.1.14/adapter');files={}
 for n in ['adapter_config.json','adapter_model.safetensors']:
  p=x.candidate/n;files[n]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 s['models']=['t008-base','t008-v0114','t008-manual'];s['adapters']={'t008-v0114':old,'t008-manual':{'path':str(x.candidate.resolve()),'files':files}};s['selection']='Chinese development: original/v0.1.14/new manual candidate under the same System r1. Not independent acceptance.';(x.output/'spec.json').write_text(json.dumps(s,ensure_ascii=False,indent=2)+'\n');(x.output/'authorization.json').write_text(json.dumps({'approved':x.approved,'scope':'Operator-provided approval for this separate development inference run; not inherited from historical execution.'},indent=2)+'\n');print(json.dumps({'prepared_only':True,'requests':120,'approved':x.approved,'output':str(x.output)}))
if __name__=='__main__':main()
