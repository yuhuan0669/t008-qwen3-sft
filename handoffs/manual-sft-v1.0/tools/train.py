"""Manual launcher: prints by default; only --execute imports GPU runtime and trains."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.metadata as md,json,shlex,subprocess
P=Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--config',type=Path,default=P/'config/actual-v0.1.14-training.json');a.add_argument('--base',default='/base');a.add_argument('--output',required=True,type=Path);a.add_argument('--mode',choices=['smoke','full'],default='full');a.add_argument('--epochs',type=int);a.add_argument('--execute',action='store_true');x=a.parse_args()
 cfg=json.loads(x.config.read_text());cmd=list(cfg['full_argv']);data=P/'data/v0.1.14/train.jsonl';report=json.loads((P/'data/v0.1.14/cpu-check/report.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 assert sha(data)==cfg['dataset_sha256']==report['dataset_sha256'] and len(data.read_text().splitlines())==1325
 for key,val in {'--model':x.base,'--dataset':str(data),'--output_dir':str(x.output/'checkpoints')}.items():cmd[cmd.index(key)+1]=val
 i=cmd.index('--external_plugins');cmd[i+1:]=[str(P/'plugins/local_data_guard.py'),str(P/'plugins/identity_loss3.py')]
 # Frozen command has external_plugins as its final option; fail if that contract changes.
 assert cfg['full_argv'][-3]=='--external_plugins'
 if x.epochs is not None:
  assert x.epochs>0;cmd[cmd.index('--num_train_epochs')+1]=str(x.epochs)
 if x.mode=='smoke':cmd+=['--max_steps','3'];cmd[cmd.index('--save_steps')+1]='3'
 print(shlex.join(cmd),flush=True)
 if not x.execute:return
 assert not x.output.exists(),'Use a fresh output directory; never overwrite a prior run'
 for name,version in report['versions'].items():assert md.version(name)==version,(name,md.version(name),version)
 for name,h in report['tokenizer_config_sha256'].items():assert sha(Path(x.base)/name)==h,name
 assert not subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip(),'GPU occupied'
 import torch
 assert torch.cuda.is_available() and torch.cuda.is_bf16_supported()
 x.output.mkdir(parents=True)
 manifest={'started_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'data_sha256':sha(data),'mode':x.mode,'epochs':cmd[cmd.index('--num_train_epochs')+1],'status':'RUNNING','clearml':'Batch archive separately after process exit'}
 out=x.output/'manual-run.json';out.write_text(json.dumps(manifest,indent=2)+'\n')
 with (x.output/'train.log').open('w') as log:done=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 manifest.update(status='PROCESS_EXITED' if done.returncode==0 else 'FAILED',exit_code=done.returncode,finished_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat());out.write_text(json.dumps(manifest,indent=2)+'\n')
 raise SystemExit(done.returncode)
if __name__=='__main__':main()
