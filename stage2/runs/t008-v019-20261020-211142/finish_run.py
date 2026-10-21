"""One authorized Full, the frozen 40-request Chinese check, then UAT recovery."""
from pathlib import Path
import datetime
import json
import subprocess
import sys
import time

R = Path(__file__).resolve().parent
ROOT = R.parents[2]
RUN = R.name
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s', '-n', 'swift']


def remote(path):
    return subprocess.check_output(K + ['exec', RUN + '-prep', '--', 'cat', path])


def event(message):
    print(datetime.datetime.now(datetime.timezone.utc).isoformat() + ' ' + message, flush=True)


def collect_training():
    for mode in ['smoke', 'full']:
        out = R / 'outputs' / mode
        out.mkdir(parents=True, exist_ok=True)
        for name in ['run_manifest.json', 'train.log', 'training-scalars.json']:
            try:
                (out / name).write_bytes(remote('/work/' + RUN + '/outputs/' + mode + '/' + name))
            except subprocess.CalledProcessError:
                pass


try:
    deadline = time.monotonic() + 6000
    while True:
        job = json.loads(subprocess.check_output(K + ['get', 'job', RUN + '-full', '-o', 'json']))
        if job['status'].get('failed'):
            raise RuntimeError('Full failed; no automatic retraining')
        if job['status'].get('succeeded'):
            break
        if time.monotonic() > deadline:
            raise TimeoutError('Full did not finish in the bounded job duration')
        time.sleep(20)
    collect_training()
    manifest = json.loads((R / 'outputs/full/run_manifest.json').read_text())
    assert manifest['training_verified'] and manifest['global_step'] == 80 and manifest['epoch'] == 1.0
    assert manifest['status'] == 'TRAINED_CANDIDATE'
    event('Full completed at 80/80; starting the frozen 40 Chinese requests')
    subprocess.run(K + ['apply', '-f', str(R / 'eval-pod.json')], check=True)
    deadline = time.monotonic() + 5700
    while True:
        pod = json.loads(subprocess.check_output(K + ['get', 'pod', RUN + '-eval', '-o', 'json']))
        phase = pod['status']['phase']
        if phase == 'Failed':
            raise RuntimeError('Development inference failed; inspect preserved logs')
        if phase == 'Succeeded':
            break
        if time.monotonic() > deadline:
            raise TimeoutError('Development inference timeout')
        time.sleep(15)
    event('Chinese development inference completed')
except BaseException as error:
    (R / 'execution-error.json').write_text(json.dumps({
        'error': repr(error), 'time': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }) + '\n')
    raise
finally:
    try:
        collect_training()
        out = R / 'development'
        out.mkdir(exist_ok=True)
        for name in ['results.jsonl', 'run-state.json', 'spec.json', 'runtime-preflight.json',
                     'vllm-command.json', 'vllm-server.log', 'authorization.json']:
            try:
                (out / name).write_bytes(remote('/work/' + RUN + '/development/' + name))
            except subprocess.CalledProcessError:
                pass
        log = subprocess.run(K + ['logs', RUN + '-eval'], capture_output=True)
        if log.returncode == 0:
            (R / 'development/runner.log').write_bytes(log.stdout)
    finally:
        event('Restoring original UAT configuration')
        subprocess.run([sys.executable, str(R / 'window.py'), 'restore'], cwd=ROOT, check=True)
        event('UAT restored and health verified')
