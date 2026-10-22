"""Stage only frozen data and the proven runtime wrapper; no GPU allocation."""
from pathlib import Path
import hashlib,json,subprocess
O=Path(__file__).resolve().parent;R=O.parents[2];V=R/'stage1/variants/stage1-cpu-v0.1.14';K=['kubectl','--context','lmas00-direct','--request-timeout=30s'];run=O.name
subprocess.run(K+['apply','-f',str(O/'prep-pod.json')],check=True)
subprocess.run(K+['-n','swift','wait','--for=condition=Ready','pod/'+run+'-prep','--timeout=60s'],check=True)
files={
 'stage1/data/train.jsonl':(V/'train.jsonl').read_text(),
 'stage1/data/manifest.json':(V/'manifest.json').read_text(),
 'stage1/training/run-spec.json':(O/'training-config.json').read_text(),
 'stage1/training/local_data_guard.py':(R/'stage1/training/local_data_guard.py').read_text(),
 'stage1/evidence/encoding-report.json':(O/'cpu-report.json').read_text(),
 'stage2/scripts/run_local_sft.py':(O/'run_local_sft.py').read_text(),
}
for name in ['identity_loss3.py','identity-keys.json']:files['stage1/variants/stage1-cpu-v0.1.14/'+name]=(V/name).read_text()
for p in (O/'inputs/evaluation').iterdir():files['evaluation/'+p.name]=p.read_text()
payload={'run':run,'sha':hashlib.sha256((V/'train.jsonl').read_bytes()).hexdigest(),'files':files}
r=subprocess.run(K+['-n','swift','exec','-i',run+'-prep','--','python3','-c',(O/'prepare_remote.py').read_text()],input=json.dumps(payload),text=True,capture_output=True,check=True)
readback=json.loads(r.stdout)
for name,text in files.items():assert readback['file_hashes'][name]==hashlib.sha256(text.encode()).hexdigest(),name
(O/'runtime-input-readback.json').write_text(json.dumps(readback,indent=2)+'\n')
# Fresh infrastructure snapshot, constrained to GPU workloads and the UAT service.
pods=json.loads(subprocess.check_output(K+['get','pods','-A','-o','json']))
gpu=[{'namespace':p['metadata']['namespace'],'name':p['metadata']['name'],'phase':p['status']['phase'],'node':p['spec'].get('nodeName')} for p in pods['items'] if any(c.get('resources',{}).get('limits',{}).get('nvidia.com/gpu') for c in p['spec']['containers'])]
(O/'gpu-workloads-before.json').write_text(json.dumps(gpu,indent=2)+'\n')
active=[p for p in gpu if p['phase'] not in ['Succeeded','Failed']];assert len(active)==1 and active[0]['namespace']=='vllm',active
uat=json.loads(subprocess.check_output(K+['-n','vllm','get','deployment','vllm','-o','json']));assert uat['status'].get('readyReplicas')==uat['spec']['replicas']==1
(O/'gpu-before.csv').write_bytes(subprocess.check_output(K+['-n','vllm','exec',active[0]['name'],'--','nvidia-smi','--query-gpu=name,memory.used,memory.total,utilization.gpu','--format=csv,noheader']))
health=subprocess.check_output(['curl','-fsS','--max-time','10','-o','/dev/null','-w','%{http_code}','https://vllm.10.140.17.125.nip.io/health'],text=True);assert health=='200';(O/'uat-health-before.txt').write_text(health+'\n')
print(json.dumps({'input_hashes_verified':len(files),'active_gpu_workloads':active,'uat_ready':1,'health':health}))
