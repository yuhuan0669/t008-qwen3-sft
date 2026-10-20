"""Inject already-authorized client credentials without displaying or persisting them."""
import subprocess,json,base64,pathlib
def k(*args):return subprocess.check_output(['kubectl',*args])
sec=json.loads(k('-n','swift','get','secret','swift-clearml','-o','json'))['data']
ca=json.loads(k('-n','cert-manager','get','secret','lmas-root-ca-secret','-o','json'))['data']['tls.crt']
cfg={x:base64.b64decode(sec[x]).decode() for x in ['access_key','secret_key']}
cfg['ca']=base64.b64decode(ca).decode()
cmd=['ssh','worker05','nerdctl --namespace k8s.io exec -i -e PYTHONPATH=/work/deps -e USER=swift-cpu t008-identity-v12-cpu python /work/clearml_readonly_probe.py']
r=subprocess.run(cmd,input=json.dumps(cfg),text=True,capture_output=True)
pathlib.Path('t008_qwen3_sft_v12_cpu/evidence/clearml-probe-transport.json').write_text(json.dumps({'exit_code':r.returncode,
 'stdout':r.stdout,'stderr_summary':'SDK/transport error; details suppressed to avoid credential exposure' if r.returncode else None},indent=2)+'\n')
print('transport_exit',r.returncode);print(r.stdout)
if r.returncode:
 import re
 print('stderr_exception_types',[line.split(':',1)[0] for line in r.stderr.splitlines() if re.match(r'^[A-Za-z_.]*(?:Error|Exception):',line)])
 print('stderr_trace_locations',[line for line in r.stderr.splitlines() if line.strip().startswith('File ')][-5:])
