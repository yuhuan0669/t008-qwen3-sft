import subprocess,json,hashlib,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1];E=R/'evidence'
names=sys.argv[1:]
assert names and all(n.startswith('t008-stage1-') for n in names), 'Pass this task CPU container names explicitly'
record_path=E/'cpu-containers.json'
records=json.loads(record_path.read_text())['containers'] if record_path.exists() else []
for name in names:
 p=subprocess.run(['ssh','worker05','nerdctl','--namespace','k8s.io','inspect',name],capture_output=True,text=True,check=True)
 r=json.loads(p.stdout)[0]
 assert not r['State']['Running'] and not r['HostConfig'].get('Devices')
 assert r['HostConfig']['Runtime']=='io.containerd.runc.v2'
 records.append({'name':name,'id':r['Id'],'image':r['Image'],'state':r['State'],'runtime':r['HostConfig']['Runtime'],'devices':r['HostConfig'].get('Devices'),'nano_cpus':r['HostConfig'].get('NanoCpus'),'memory':r['HostConfig'].get('Memory')})
for name in names:subprocess.run(['ssh','worker05','nerdctl','--namespace','k8s.io','rm',name],capture_output=True,text=True,check=True)
(E/'cpu-containers.json').write_text(json.dumps({'containers':records,'removed_own_exited_containers':True,'gpu_devices':False},indent=2)+'\n')
before=json.loads((E/'services-before.json').read_text());after={}
for ns,n in [('vllm','vllm'),('data-juicer','data-juicer'),('evalscope','evalscope')]:
 d=json.loads(subprocess.check_output(['kubectl','-n',ns,'get','deploy',n,'-o','json']))
 sh=hashlib.sha256(json.dumps(d['spec'],sort_keys=True).encode()).hexdigest()
 after[ns]={'spec_sha256':sh,'ready_replicas':d['status'].get('readyReplicas',0),'spec_unchanged':sh==before[ns]['spec_sha256']}
(E/'services-after.json').write_text(json.dumps(after,indent=2)+'\n')
print(json.dumps({'containers_removed':len(records),'services':after}))
