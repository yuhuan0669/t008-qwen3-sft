"""Collect persisted outputs after GPU stages; no inference or evaluation."""
import datetime,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
run=json.loads((ROOT/'evidence/owner_authorization.json').read_text())['run_id'];prep=run+'-prep'
k=['kubectl','--context','lmas00-direct','-n','swift']
state=json.loads((ROOT/'evidence/session_state.json').read_text())
assert state['vllm_restored'] is True,'Collect after service recovery'
output=ROOT/'outputs';output.mkdir(exist_ok=True)
subprocess.run(k+['cp',str(ROOT/'scripts/export_evidence.py'),prep+':/work/'+run+'/export_evidence.py'],check=True)
subprocess.run(k+['exec',prep,'--','python3','/work/'+run+'/export_evidence.py'],check=True)
subprocess.run(k+['cp',prep+':/work/'+run+'/output-evidence.tar.gz',str(output/'output-evidence.tar.gz')],check=True)
subprocess.run(k+['cp',prep+':/work/'+run+'/outputs/full/adapter-candidate.zip',str(output/'adapter-candidate.zip')],check=True)
import tarfile
with tarfile.open(output/'output-evidence.tar.gz') as archive:
 for member in archive.getmembers():
  target=(output/member.name).resolve()
  assert target.is_relative_to(output.resolve()) and not member.issym() and not member.islnk()
 archive.extractall(output,filter='data')
for name in ['smoke-gpu-before.json','full-gpu-before.json','smoke-gpu-telemetry.jsonl','full-gpu-telemetry.jsonl',
             'smoke-stage-exit.json','full-stage-exit.json','clearml-progress-sync.json','runtime-preflight.log','smoke-wrapper.log','full-wrapper.log']:
 p=subprocess.run(k+['exec',prep,'--','cat','/work/'+run+'/'+name],capture_output=True,text=True)
 if p.returncode==0:(ROOT/'evidence'/name).write_text(p.stdout)
summary={}
for mode in ('smoke','full'):
 records=[];p=ROOT/'evidence'/(mode+'-gpu-telemetry.jsonl')
 if p.exists():
  for line in p.read_text().splitlines():
   r=json.loads(line)
   for gpu in r['gpu']:
    cols=[x.strip() for x in gpu.split(',')]
    records.append({'at_utc':r['at_utc'],'memory_used_MiB':int(cols[3]),'utilization_percent':int(cols[4])})
 summary[mode]={'telemetry_samples':len(records),'peak_observed_memory_used_MiB':max((r['memory_used_MiB'] for r in records),default=None)}
full=json.loads((ROOT/'evidence/full-run_manifest.json').read_text())
package=output/'adapter-candidate.zip'
assert hashlib.sha256(package.read_bytes()).hexdigest()==full['adapter_package_sha256']==full['clearml_model_readback_sha256']
summary['adapter_candidate']={'bytes':package.stat().st_size,'sha256':full['adapter_package_sha256'],'clearml_model_id':full['clearml_output_model_id'],'remote_readback_verified':True}
summary['collected_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(ROOT/'evidence/output_collection.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
