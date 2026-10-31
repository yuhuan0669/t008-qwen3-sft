"""Archive raw evidence using bounded reads after GPU work; verify public restoration."""
from pathlib import Path
import datetime,hashlib,json,subprocess,tarfile,time
D=Path(__file__).resolve().parent;E=D/'evaluation'
K=['kubectl','--context','lmas00-direct','--request-timeout=60s']
X=K+['-n','swift','exec',D.name+'-prep','--']
def read(path):return subprocess.check_output(X+['cat',path],timeout=90)
def download(remote,local):
    probe="from pathlib import Path;import hashlib,json;p=Path("+repr(remote)+");print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))"
    meta=json.loads(subprocess.check_output(X+['python3','-c',probe],timeout=90))
    with local.with_suffix('.part').open('wb') as f:
        for offset in range(0,meta['bytes'],4*1024**2):
            n=min(4*1024**2,meta['bytes']-offset)
            code="import sys;p=open("+repr(remote)+",'rb');p.seek("+str(offset)+");sys.stdout.buffer.write(p.read("+str(n)+"))"
            b=subprocess.check_output(X+['python3','-c',code],timeout=90);assert len(b)==n;f.write(b)
    tmp=local.with_suffix('.part');assert hashlib.sha256(tmp.read_bytes()).hexdigest()==meta['sha256'];tmp.replace(local)
    return meta
def main():
    assert json.loads((D/'window-state.json').read_text())['restored']
    live=json.loads(subprocess.check_output(K+['-n','vllm','get','deploy','vllm','-o','json']))
    before=json.loads((D/'vllm-before.json').read_text());assert live['spec']==before['spec']
    health=[]
    for i in range(2):
        for attempt in range(10):
            p=subprocess.run(['curl','--noproxy','*','-fsS','--max-time','10','-o','/dev/null','-w','%{http_code}','https://vllm.10.140.17.125.nip.io/health'],capture_output=True,text=True)
            if p.returncode==0 and p.stdout=='200':break
            time.sleep(3)
        assert p.returncode==0 and p.stdout=='200'
        health.append({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':200})
        if i==0:time.sleep(3)
    models=json.loads(subprocess.check_output(['curl','--noproxy','*','-fsS','--max-time','10','https://vllm.10.140.17.125.nip.io/v1/models']))
    ids=sorted(x['id'] for x in models['data']);assert ids==sorted(['octa-carbon-v1','octa-carbon-sft-v0114','octa-carbon-sft-v0116'])
    report={'deployment_spec_equal':True,'ready':live['status']['readyReplicas'],'available':live['status']['availableReplicas'],'public_health':health,'model_ids':ids}
    (D/'public-restoration-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    remote='/work/'+D.name+'/evaluation'
    subprocess.run(X+['tar','-C',remote,'-cf',remote+'/raw.tar','raw'],check=True,timeout=90)
    meta=download(remote+'/raw.tar',E/'raw.tar')
    with tarfile.open(E/'raw.tar') as t:t.extractall(E,filter='data')
    for name in ['complete.json','progress.json','preflight.json','server-input-verification.json','results.jsonl','vllm-server.log','models.json','vllm-command.json']:
        download(remote+'/'+name,E/name)
    (D/'raw-archive.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps({'uat':report,'raw_archive':meta}))
if __name__=='__main__':main()
