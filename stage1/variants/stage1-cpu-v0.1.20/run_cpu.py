"""Temporary CPU-only preparation in the original runtime. Never scale UAT."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile

D=Path(__file__).resolve().parent
ROOT=D.parents[2]
OUT=D/'cpu-check'
K=['kubectl','--context','lmas00-direct','--request-timeout=25s']
NAME='t008-v0120-cpu-20261031'

def call(*args,timeout=60):
    return subprocess.check_output(K+list(args),text=True,timeout=timeout)

def snapshot(name):
    x=json.loads(call('-n','vllm','get','deployment','vllm','-o','json'))
    value={'utc':datetime.now(timezone.utc).isoformat(),'uid':x['metadata']['uid'],
        'generation':x['metadata']['generation'],
        'spec_sha256':hashlib.sha256(json.dumps(x['spec'],sort_keys=True,separators=(',',':')).encode()).hexdigest(),
        'replicas':x['spec']['replicas'],'ready':x['status'].get('readyReplicas',0),
        'available':x['status'].get('availableReplicas',0)}
    (OUT/name).write_text(json.dumps(value,indent=2)+'\n')
    return value

def main():
    assert not (OUT/'report.json').exists(), 'Completed CPU evidence exists'
    shutil.copyfile(D/'training-config.json',OUT/'training-config.input.json')
    before=snapshot('uat-before.json')
    assert before['ready']==before['available']==before['replicas']==1
    assert not json.loads(call('-n','swift','get','pods','--field-selector','metadata.name='+NAME,'-o','json'))['items']
    rel=D.relative_to(ROOT).as_posix()
    files=[rel+'/'+n for n in ['train.jsonl','train-map.jsonl','changes.jsonl','identity-keys.json','identity_loss3.py',
        'manifest.json','training-config.json','cpu-check/check_cpu.py']]
    files+=['stage1/variants/stage1-cpu-v0.1.14/'+n for n in ['train.jsonl','identity-keys.json',
        'identity_loss3.py','training-config.json','cpu-check/report.json']]
    files+=['stage1/training/local_data_guard.py']
    created=False
    try:
        print(call('create','-f',str(OUT/'pod-cpu.json')),flush=True)
        created=True
        for _ in range(5):
            r=subprocess.run(K+['-n','swift','wait','--for=condition=Ready','pod/'+NAME,'--timeout=30s'],
                text=True,capture_output=True,timeout=40)
            print(r.stdout+r.stderr,flush=True)
            if r.returncode==0:break
        else:raise RuntimeError('CPU Pod not ready')
        pod=json.loads(call('-n','swift','get','pod',NAME,'-o','json'))
        (OUT/'runtime.json').write_text(json.dumps({'pod_uid':pod['metadata']['uid'],
            'image_id':pod['status']['containerStatuses'][0]['imageID'],'node':pod['spec']['nodeName'],
            'resources':pod['spec']['containers'][0]['resources'],'gpu_requested':False},indent=2)+'\n')
        with subprocess.Popen(['tar','-C',str(ROOT),'-czf','-',*files],stdout=subprocess.PIPE) as send:
            subprocess.run(K+['-n','swift','exec','-i',NAME,'--','tar','-C','/tmp/v0120-check','-xzf','-'],
                stdin=send.stdout,check=True,timeout=90)
            send.stdout.close()
            assert send.wait()==0
        remote='/tmp/v0120-check/'+rel+'/cpu-check'
        print('Native CPU encoding started; no GPU or model weights.',flush=True)
        with (OUT/'cpu-check.log').open('w') as log:
            r=subprocess.run(K+['-n','swift','exec',NAME,'--','python3',remote+'/check_cpu.py'],
                stdout=log,stderr=subprocess.STDOUT,timeout=600)
        (OUT/'cpu-exit.json').write_text(json.dumps({'returncode':r.returncode})+'\n')
        preflight = subprocess.run(K+['-n','swift','exec',NAME,'--','cat',remote+'/length-precheck.json'],
            capture_output=True,timeout=40)
        if preflight.returncode==0:
            (OUT/'length-precheck.json').write_bytes(preflight.stdout)
        r.check_returncode()
        bundle=OUT/'results.tar'
        with bundle.open('wb') as out:
            subprocess.run(K+['-n','swift','exec',NAME,'--','tar','-C',remote,'-cf','-',
                'report.json','row-checks.jsonl','changed-row-checks.json','mask-probes.json'],stdout=out,check=True,timeout=60)
        with tarfile.open(bundle) as archive:archive.extractall(OUT,filter='data')
        bundle.unlink()
        report=json.loads((OUT/'report.json').read_text())
        print(json.dumps({k:report[k] for k in ['verified','rows','changed_rows','quarantined_rows','totals']},ensure_ascii=False),flush=True)
    finally:
        if created:
            print(call('-n','swift','delete','pod',NAME,'--ignore-not-found','--wait=false'),flush=True)
            for _ in range(3):
                r=subprocess.run(K+['-n','swift','wait','--for=delete','pod/'+NAME,'--timeout=30s'],capture_output=True,timeout=40)
                if r.returncode==0:break
        after=snapshot('uat-after.json')
        same=all(before[k]==after[k] for k in ['uid','generation','spec_sha256','replicas'])
        healthy=after['ready']==after['available']==after['replicas']==1
        gone=not json.loads(call('-n','swift','get','pods','--field-selector','metadata.name='+NAME,'-o','json'))['items']
        verification={'spec_unchanged':same,'healthy':healthy,'cpu_pod_deleted':gone,'uat_pause':False,'gpu_requested':False}
        (OUT/'uat-verification.json').write_text(json.dumps(verification,indent=2)+'\n')
        assert same and healthy and gone,verification

if __name__=='__main__':main()
