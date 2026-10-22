"""Run the approved Smoke, ONE Full and bounded Chinese check; always restore UAT."""
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
    assert m['training_verified'] and m['global_step'] == (3 if stage == 'smoke' else 83)
    assert m['data_sha256'] == json.loads((D / 'training-config.json').read_text())['dataset_sha256']
    if stage == 'full':
        assert m['epoch'] == 1.0 and m['command'] == json.loads((D / 'expected-full-command.json').read_text())
    event(stage + ' verified, step ' + str(m['global_step']))
    return m


def evaluate(manifest):
    e = D / 'evaluation'
    spec = json.loads((e / 'spec.pending.json').read_text())
    files = {k: v for k, v in manifest['adapter_files'].items() if k in ['adapter_config.json', 'adapter_model.safetensors']}
    assert len(files) == 2
    spec['adapters']['t008-v0114'] = {
        'path': manifest['checkpoint'].replace('/runwork', '/models-work/' + RUN), 'files': files}
    spec['training_data_sha256'] = manifest['data_sha256']
    (e / 'spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
    print(call('create', '-f', str(D / 'eval-pod.json')), flush=True)
    name = RUN + '-eval'
    print(call('-n', 'swift', 'wait', '--for=condition=Ready', 'pod/' + name, '--timeout=180s', timeout=200), flush=True)
    files = ['run.py', 'spec.json', 'scenarios.jsonl', 'thinking-prefill.jinja', 'custom-system.txt', 'authorization.json', 'base-files.json']
    with subprocess.Popen(['tar', '-C', str(e), '-cf', '-', *files], stdout=subprocess.PIPE) as sender:
        subprocess.run(K + ['-n', 'swift', 'exec', '-i', name, '--', 'tar', '-C', '/tmp/final-check', '-xf', '-'],
                       stdin=sender.stdout, check=True, timeout=90)
        sender.stdout.close()
        assert sender.wait() == 0
    try:
        event('Starting frozen 120-request Chinese development comparison')
        with (e / 'runner.log').open('w') as log:
            subprocess.run(K + ['-n', 'swift', 'exec', name, '--', 'python3', '/tmp/final-check/run.py'],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=3600)
    finally:
        bundle = e / 'results.tar'
        with bundle.open('wb') as f:
            subprocess.run(K + ['-n', 'swift', 'exec', name, '--', 'tar', '-C', '/tmp/final-check', '-cf', '-', '.'],
                           stdout=f, check=True, timeout=180)
        target = e / 'results'
        target.mkdir(exist_ok=True)
        with tarfile.open(bundle) as t:
            t.extractall(target, filter='data')
        bundle.unlink()
    assert json.loads((e / 'results/complete.json').read_text())['count'] == 120
    event('Chinese comparison complete')


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
        finally:
            if (D / 'window-state.json').exists():
                event('Restoring original UAT')
                subprocess.run([sys.executable, str(D / 'window.py'), 'restore'], check=True)
                event('Original UAT restored; internal health verified')


if __name__ == '__main__':
    main()
