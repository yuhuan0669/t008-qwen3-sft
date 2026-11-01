"""Run the approved Smoke, ONE Full and bounded Chinese check; leave UAT paused until the user requests restoration."""
from pathlib import Path
import datetime
import json
import subprocess
import sys
import tarfile
import time

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
RUN = D.name
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']


def call(*args, timeout=90):
    return subprocess.check_output(K + list(args), text=True, timeout=timeout)


def remote_bytes(path):
    return subprocess.check_output(K + ['-n', 'swift', 'exec', RUN + '-prep', '--', 'cat', path], timeout=90)


def event(text):
    print(datetime.datetime.now(datetime.timezone.utc).isoformat() + ' ' + text, flush=True)


def collect_training():
    for stage in ['smoke', 'full']:
        out = D / 'outputs' / stage
        out.mkdir(parents=True, exist_ok=True)
        for f in ['run_manifest.json', 'train.log', 'training-scalars.json']:
            try:
                (out / f).write_bytes(remote_bytes('/work/' + RUN + '/outputs/' + stage + '/' + f))
            except subprocess.CalledProcessError:
                pass


def job(stage):
    event('Starting ' + stage)
    print(call('create', '-f', str(D / ('job-' + stage + '.json'))), flush=True)
    deadline = time.monotonic() + (1800 if stage == 'smoke' else 5400)
    while True:
        obj = json.loads(call('-n', 'swift', 'get', 'job', RUN + '-' + stage, '-o', 'json'))
        if obj['status'].get('failed'):
            raise RuntimeError(stage + ' failed; no automatic retraining')
        if obj['status'].get('succeeded'):
            break
        if time.monotonic() > deadline:
            raise TimeoutError(stage + ' exceeded its limit')
        time.sleep(12)
    collect_training()
    m = json.loads((D / 'outputs' / stage / 'run_manifest.json').read_text())
    assert m['retention_metrics_verified']
    assert m['training_verified'] and m['global_step'] == (3 if stage == 'smoke' else 66)
    assert m['data_sha256'] == json.loads((D / 'training-config.json').read_text())['dataset_sha256']
    if stage == 'full':
        assert m['epoch'] == 1.0 and m['command'] == json.loads((D / 'expected-full-command.json').read_text())
    event(stage + ' verified, step ' + str(m['global_step']))
    return m


def evaluate(manifest):
    e=D/'evaluation'
    binding=json.loads((e/'runtime-binding.pending.json').read_text())
    files={k:v for k,v in manifest['adapter_files'].items() if k in ['adapter_config.json','adapter_model.safetensors']}
    assert len(files)==2
    binding['adapters']['candidate_v0.1.25']={'path':manifest['checkpoint'].replace('/runwork','/models-work/'+RUN),'files':files}
    argv=binding['server_argv'];i=argv.index('--lora-modules')
    argv[i+1:i+1]=[json.dumps({'name':binding['aliases'][model],'path':a['path'],'base_model_name':'octa-carbon-v1'}) for model,a in binding['adapters'].items()]
    (e/'runtime-binding.json').write_text(json.dumps(binding,indent=2)+'\n')
    print(call('create','-f',str(D/'eval-pod.json')),flush=True)
    name=RUN+'-eval'
    for _ in range(10):
        p=subprocess.run(K+['-n','swift','wait','--for=condition=Ready','pod/'+name,'--timeout=30s'],capture_output=True,text=True)
        if p.returncode==0:break
    else:raise RuntimeError('Evaluation pod not Ready')
    files=['run.py','runtime-binding.json','evaluation-config.json','system.txt','cases.json','missing-slots.json','thinking-prefill.jinja','base-files.json']
    with subprocess.Popen(['tar','-C',str(e),'-cf','-',*files],stdout=subprocess.PIPE) as sender:
        subprocess.run(K+['-n','swift','exec','-i',name,'--','tar','-C','/runwork/evaluation','-xf','-'],stdin=sender.stdout,check=True,timeout=90)
        sender.stdout.close();assert sender.wait()==0
    event('Starting 208 frozen missing generations; no additional Judge calls')
    with (e/'runner.log').open('w') as log:
        subprocess.run(K+['-n','swift','exec',name,'--','python3','/runwork/evaluation/run.py'],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=2700)
    result=json.loads(remote_bytes('/work/'+RUN+'/evaluation/complete.json'))
    assert result['count']==208
    event('Frozen generation comparison completed')


def collect_evaluation():
    e=D/'evaluation';e.mkdir(exist_ok=True)
    for f in ['complete.json','failure.json','progress.json','preflight.json','server-input-verification.json','results.jsonl','vllm-server.log','models.json','vllm-command.json']:
        try:(e/f).write_bytes(remote_bytes('/work/'+RUN+'/evaluation/'+f))
        except subprocess.CalledProcessError:pass


def main():
    try:
        subprocess.run([sys.executable, str(D / 'window.py'), 'pause'], check=True)
        window = (D / 'window.json').read_text()
        writer = "from pathlib import Path;import sys;Path('/data/" + RUN + "/window.json').write_text(sys.stdin.read())"
        subprocess.run(K + ['-n', 'swift', 'exec', '-i', RUN + '-prep', '--', 'python3', '-c', writer],
                       input=window, text=True, check=True, timeout=60)
        deadline = time.monotonic() + 180
        while json.loads(call('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json'))['items']:
            if time.monotonic() > deadline:
                raise TimeoutError('UAT GPU pod did not terminate')
            time.sleep(3)
        job('smoke')
        m = job('full')
        evaluate(m)
    except BaseException as exc:
        (D / 'execution-error.json').write_text(json.dumps({'error': repr(exc), 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()}) + '\n')
        raise
    finally:
        try:
            collect_training()
            collect_evaluation()
        finally:
            if (D / 'window-state.json').exists():
                event('Cleaning task GPU workloads; UAT remains paused by user instruction')
                subprocess.run([sys.executable, str(D / 'window.py'), 'cleanup'], check=True)
                event('Task GPU workloads removed; UAT intentionally remains paused')


if __name__ == '__main__':
    main()
