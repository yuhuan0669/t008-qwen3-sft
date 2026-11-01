"""Authorized diagnostic window; replica-only UAT pause, automatic restoration."""
import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import shutil
import signal
import sys
import tarfile
import time
import urllib.request

D=Path(__file__).resolve().parent
K=['kubectl','--context','lmas00-direct','--request-timeout=30s']
POD='t008-repetition-stop-gpu-20261101'
URL='http://vllm.10.140.17.125.nip.io'
def call(args,timeout=90,check=True,**kwargs):
    r=subprocess.run(K+args,capture_output=True,timeout=timeout,**kwargs)
    if check and r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
    return r
def save(name,o):
    p=D/name;tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n');tmp.replace(p)
def read(name):return json.loads((D/name).read_text())
def deployment():return json.loads(call(['-n','vllm','get','deployment','vllm','-o','json']).stdout)
def http(path):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(URL+path,timeout=15) as r:return r.status,r.read()
def capture():
    r=call(['-n','swift','exec',POD,'--','tar','czf','-','-C','/tmp/diag/results','.'],check=False,timeout=60)
    if r.returncode==0:
        (D/'results.tar.gz').write_bytes(r.stdout)
        with tarfile.open(fileobj=io.BytesIO(r.stdout),mode='r:gz') as t:t.extractall(D/'results',filter='data')
def restore():
    if not (D/'window-state.json').exists():return
    state=read('window-state.json')
    if state.get('restored'):return
    lock=D/'.restore.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:return
    os.close(fd)
    try:
        before=read('uat-before-pause.json');current=deployment()
        assert current['metadata']['uid']==before['metadata']['uid']
        try:capture()
        except Exception as e:state['capture_error']=str(e)
        call(['-n','swift','delete','pod',POD,'--ignore-not-found=true','--wait=true','--timeout=90s'],timeout=100)
        call(['-n','vllm','scale','deployment/vllm','--replicas='+str(before['spec']['replicas'])])
        call(['-n','vllm','rollout','status','deployment/vllm','--timeout=420s'],timeout=440)
        successes=0;health=[];models=None
        for _ in range(12):
            try:
                status,_=http('/health');_,body=http('/v1/models');models=json.loads(body)
                assert status==200
                assert {r['id'] for r in models['data']}==set(read('model-aliases-before.json'))
                successes+=1;health.append({'status':200,'at':time.time()})
                if successes>=2:break
            except Exception as e:successes=0;health.append({'error':str(e),'at':time.time()})
            time.sleep(5)
        after=deployment();save('uat-restored.json',after);save('health-restored.json',health);save('models-restored.json',models)
        state.update(restored=successes>=2 and after['status'].get('readyReplicas')==before['spec']['replicas'],
            deployment_spec_equal=after['spec']==before['spec'],paused=False,restored_at=time.time())
        save('window-state.json',state)
        assert state['restored'] and state['deployment_spec_equal'],state
        print('UAT_RESTORED',flush=True)
    finally:lock.unlink(missing_ok=True)
def watch():
    while True:
        if (D/'window-state.json').exists():
            s=read('window-state.json')
            if s.get('restored'):return
            if time.time()>s['restore_by']:
                try:restore()
                except Exception as e:print('WATCH_RESTORE_ERROR',repr(e),flush=True)
        time.sleep(10)
def run():
    assert read('authorization.json')['uat_pause_approved']
    cpu=read('cpu-results/encoding-check.json')
    assert cpu['verified'] and cpu['cases']==8 and cpu['positions']==21 and cpu['expected_scores']==252
    assert cpu['script_sha256']==__import__('hashlib').sha256((D/'diagnose.py').read_bytes()).hexdigest()
    assert cpu['protocol_sha256']==__import__('hashlib').sha256((D/'inputs/protocol.json').read_bytes()).hexdigest()
    assert not (D/'window-state.json').exists()
    before=deployment();pre=read('uat-preflight.json')
    pods=json.loads(call(['get','pods','-A','-o','json']).stdout)['items']
    owners=[(p['metadata']['namespace'],p['metadata']['name']) for p in pods if p['status'].get('phase') not in ['Succeeded','Failed'] and any(int(c.get('resources',{}).get('limits',{}).get('nvidia.com/gpu',0)) for c in p['spec']['containers'])]
    assert len(owners)==1 and owners[0][0]=='vllm', owners
    save('gpu-owners-before.json',owners)
    assert before['metadata']['uid']==pre['metadata']['uid'] and before['spec']==pre['spec']
    assert before['spec']['replicas']==before['status'].get('readyReplicas')==1
    assert http('/health')[0]==200
    aliases=[m['id'] for m in json.loads(http('/v1/models')[1])['data']]
    save('model-aliases-before.json',aliases);save('uat-before-pause.json',before)
    save('window-state.json',{'paused':False,'restored':False,'started_at':time.time(),'restore_by':time.time()+900})
    log=(D/'watchdog.log').open('a')
    p=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'watch'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    save('watchdog.json',{'pid':p.pid})
    try:
        patch=[{'op':'test','path':'/metadata/resourceVersion','value':before['metadata']['resourceVersion']},
          {'op':'test','path':'/spec/replicas','value':1},{'op':'replace','path':'/spec/replicas','value':0}]
        call(['-n','vllm','patch','deployment','vllm','--type=json','-p',json.dumps(patch)])
        s=read('window-state.json');s['paused']=True;save('window-state.json',s)
        call(['-n','vllm','wait','--for=delete','pod','-l','app=vllm','--timeout=120s'],timeout=130)
        print('UAT_PAUSED',flush=True)
        call(['create','-f',str(D/'pod-gpu.json')])
        call(['-n','swift','wait','--for=condition=Ready','pod/'+POD,'--timeout=180s'],timeout=190)
        buf=io.BytesIO()
        with tarfile.open(fileobj=buf,mode='w') as t:
            t.add(D/'inputs',arcname='inputs');t.add(D/'diagnose.py',arcname='diagnose.py')
        call(['-n','swift','exec','-i',POD,'--','tar','xf','-','-C','/tmp/diag'],input=buf.getvalue(),timeout=90)
        print('GPU_DIAGNOSTIC_START',flush=True)
        with (D/'gpu.log').open('w') as f:
            args=K+['-n','swift','exec',POD,'--','python3','/tmp/diag/diagnose.py']
            r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=720)
        save('gpu-exit.json',{'returncode':r.returncode,'at':time.time()});capture()
        if r.returncode:raise RuntimeError('Diagnostic failed; see gpu.log')
        assert read('results/completed.json')['completed']
        print('GPU_DIAGNOSTIC_DONE',flush=True)
    finally:restore()
if __name__=='__main__':{'run':run,'watch':watch,'restore':restore}[sys.argv[1]]()
