from pathlib import Path
import json,subprocess
D=Path(__file__).resolve().parent;R=D.parents[2];k=['kubectl','--context','lmas00-direct','-n','swift'];remote='/data/'+D.name
p=D/'cpu.py';s=p.read_text().replace('processor.tokenizer','processor');s=s.replace("assert len(a['input_ids'])<=2048 and identity_loss3.message_key(row['messages']) not in templates[0].loss_scale.identity_keys","assert len(a['input_ids'])<=2048 and identity_loss3.message_key(row['messages']) not in json.loads((D/'identity/identity-keys.json').read_text())['identity_message_sha256']");p.write_text(s)
a=json.loads((D/'argv.json').read_text());a+=['/input/local_data_guard.py'];(D/'argv.json').write_text(json.dumps(a,indent=2));(D/'local_data_guard.py').write_bytes((R/'stage1/training/local_data_guard.py').read_bytes());(D/'manifest.json').write_bytes((R/'stage2/variants/minimal16-diagnostic-review-v0.1/manifest.json').read_bytes())
s=(D/'train.py').read_text().replace("orig=t.compute_loss","orig=t.compute_loss\n  clip=t.accelerator.clip_grad_norm_\n  def observed_clip(*a,**kw):\n   value=clip(*a,**kw)\n   with (O/'preclip.jsonl').open('a') as f:f.write(json.dumps({'step':t.state.global_step+1,'norm':float(value)})+'\\n')\n   return value\n  t.accelerator.clip_grad_norm_=observed_clip")
(D/'train.py').write_text(s)
for f in ['cpu.py','argv.json','train.py','local_data_guard.py','manifest.json']:
 subprocess.run(k+['exec','-i',D.name+'-prep','--','python3','-c',"import sys;from pathlib import Path;Path(sys.argv[1]).write_text(sys.stdin.read())",remote+'/'+f],input=(D/f).read_text(),text=True,check=True)
p=subprocess.run(k+['exec',D.name+'-prep','--','python3',remote+'/cpu.py',D.name],capture_output=True,text=True);(D/'cpu.log').write_text(p.stdout+p.stderr);print(p.returncode,p.stdout,p.stderr[-1800:])
