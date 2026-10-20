"""Collect only this run's isolated CPU container records; remove exited ones."""
import json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
names=['t008-native-entry-cpu','t008-native-entry-ast-init','t008-native-entry-cpu-final',
       't008-native-entry-cpu-final-v2','t008-native-entry-cpu-final-v3','t008-native-entry-cpu-checks']
records=[]
for name in names:
 p=subprocess.run(['ssh','worker05','nerdctl','--namespace','k8s.io','inspect',name],capture_output=True,text=True,check=True)
 r=json.loads(p.stdout)[0]
 if r['State']['Running']:raise RuntimeError('Refuse to remove still running '+name)
 assert not r['HostConfig']['Devices'] and r['HostConfig']['Runtime']=='io.containerd.runc.v2'
 records.append({k:r[k] for k in ('Id','Name','Image','State')})
for name in names:
 subprocess.run(['ssh','worker05','nerdctl','--namespace','k8s.io','rm',name],capture_output=True,text=True,check=True)
(ROOT/'evidence/cpu_cleanup.json').write_text(json.dumps({'containers':records,'removed':names,
 'scope':'Only newly created CPU containers; existing vLLM/K8s resources untouched'},indent=2)+'\n')
print(json.dumps({'removed_own_exited_cpu_containers':len(names),'GPU_actions':False}))
