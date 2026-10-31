"""CPU-only effective LoRA update comparison; no base inference or weight update."""
from pathlib import Path
import json,subprocess
D=Path(__file__).resolve().parent;P=D.parent/'t008-v0117-20261031-100924'
manifests=[json.loads((d/'outputs/full/run_manifest.json').read_text()) for d in [P,D]]
payload=[]
for d,m in zip([P,D],manifests):
 payload.append({'checkpoint':m['checkpoint'].replace('/runwork','/work/'+d.name),'sha256':m['adapter_files']['adapter_model.safetensors']['sha256']})
script=r'''
from pathlib import Path
import hashlib,json,math,sys,torch
from safetensors.torch import load_file
torch.set_num_threads(2)
items=json.load(sys.stdin);tensors=[];configs=[]
for item in items:
 p=Path(item['checkpoint']);w=p/'adapter_model.safetensors'
 assert hashlib.sha256(w.read_bytes()).hexdigest()==item['sha256']
 tensors.append(load_file(str(w),device='cpu'));configs.append(json.loads((p/'adapter_config.json').read_text()))
assert set(tensors[0])==set(tensors[1])
for cfg in configs:assert cfg['r']==8 and cfg['lora_alpha']==32 and not cfg.get('use_rslora') and not cfg.get('use_dora') and not cfg.get('rank_pattern')
scale=4.0;out=[];tot1=tot2=cross=0.0
for key in sorted(tensors[0]):
 if '.lora_A.' not in key:continue
 bkey=key.replace('.lora_A.','.lora_B.')
 a1=tensors[0][key].double();b1=tensors[0][bkey].double();a2=tensors[1][key].double();b2=tensors[1][bkey].double()
 n1=float(torch.trace((b1.T@b1)@(a1@a1.T)))*scale**2
 n2=float(torch.trace((b2.T@b2)@(a2@a2.T)))*scale**2
 dot=float(torch.trace((b1.T@b2)@(a2@a1.T)))*scale**2
 tot1+=n1;tot2+=n2;cross+=dot
 out.append({'module':key.split('.lora_A.')[0],'v0117_update_frobenius':math.sqrt(max(0,n1)),
  'v0118_update_frobenius':math.sqrt(max(0,n2)),'ratio':math.sqrt(n2/n1) if n1 else None,
  'direction_cosine':dot/math.sqrt(n1*n2) if n1*n2 else None})
assert len(out)*2==len(tensors[0])
print(json.dumps({'device':'cpu','modules':len(out),'scale':scale,'v0117_total_update_frobenius':math.sqrt(tot1),
 'v0118_total_update_frobenius':math.sqrt(tot2),'norm_ratio':math.sqrt(tot2/tot1),
 'direction_cosine':cross/math.sqrt(tot1*tot2),'update_difference_frobenius':math.sqrt(max(0,tot1+tot2-2*cross)),
 'weights_verified':True,'detail':out,
 'interpretation':'Effective delta W=alpha/r * B A. Measures update magnitude/direction, not model quality or the cause of any specific answer.'}))
'''
k=['kubectl','--context','lmas00-direct','--request-timeout=60s','-n','swift','exec','-i',D.name+'-prep','--','python3','-c',script]
p=subprocess.run(k,input=json.dumps(payload),text=True,capture_output=True,check=True,timeout=90)
report=json.loads(p.stdout);(D/'adapter-change.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='detail'}))
