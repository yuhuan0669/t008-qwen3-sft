"""Bounded, explicitly authorized replica-only pause and restoration."""
import datetime
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s', '-n', 'vllm']
GPU_POD = 't024-echo80-gpu-20261028'

def now():
    return datetime.datetime.now(datetime.timezone.utc)

def save(name, value):
    tmp = D / (name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(D / name)

def call(*args, timeout=90, check=True):
    result = subprocess.run(K + list(args), capture_output=True, text=True, timeout=timeout)
    if check and result.returncode:
        raise RuntimeError(result.stderr)
    return result

def deployment():
    return json.loads(call('get', 'deployment', 'vllm', '-o', 'json').stdout)

def capture():
    p = subprocess.run(K + ['exec', GPU_POD, '--', 'tar', 'czf', '-', '-C', '/tmp/echo80', '.'],
        capture_output=True, timeout=60)
    if p.returncode:
        return
    (D / 'gpu-workspace.tar.gz').write_bytes(p.stdout)
    with tarfile.open(fileobj=io.BytesIO(p.stdout), mode='r:gz') as t:
        t.extractall(D / 'gpu-results', filter='data')
    for name in ['pt-results.jsonl', 'pt-runtime.json']:
        f = D / 'gpu-results' / name
        if f.exists():
            (D / name).write_bytes(f.read_bytes())

def restore():
    state_path = D / 'window-state.json'
    if not state_path.exists():
        return
    state = json.loads(state_path.read_text())
    if state.get('restored'):
        return
    lock = D / '.restore.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        return
    os.close(fd)
    try:
        before = json.loads((D / 'uat-before-pause.json').read_text())
        current = deployment()
        assert current['metadata']['uid'] == before['metadata']['uid'], 'Deployment identity changed'
        try:
            capture()
        except Exception as e:
            state['capture_error'] = repr(e)
        call('delete', 'pod', GPU_POD, '--ignore-not-found=true', '--wait=true', '--timeout=90s', timeout=100)
        call('scale', 'deployment/vllm', '--replicas=' + str(before['spec']['replicas']))
        call('rollout', 'status', 'deployment/vllm', '--timeout=420s', timeout=450)
        after = deployment()
        save('uat-restored.json', after)
        spec = json.loads((D / 'spec.json').read_text())
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(spec['vllm_url'] + '/health', timeout=15) as r:
            health = r.status
        with opener.open(spec['vllm_url'] + '/v1/models', timeout=15) as r:
            models = json.load(r)
        save('models-restored.json', models)
        aliases = {m['id'] for m in models['data']}
        assert health == 200 and {'octa-carbon-v1', 'octa-carbon-sft-v0114'} <= aliases
        assert after['status'].get('readyReplicas') == before['spec']['replicas']
        same = after['spec'] == before['spec']
        state.update(restored=True, restored_at=now().isoformat(), health_status=health,
            deployment_spec_equal=same, ready_replicas=after['status'].get('readyReplicas'))
        save('window-state.json', state)
        assert same, 'Service restored but another Deployment spec change needs review'
        print(json.dumps(state, ensure_ascii=False), flush=True)
    finally:
        lock.unlink(missing_ok=True)

def pause():
    auth = json.loads((D / 'authorization.json').read_text())
    assert auth.get('uat_pause_approved') is True, 'Separate current-window authorization required'
    assert not (D / 'window-state.json').exists(), 'Window already exists'
    before = deployment()
    initial = json.loads((D / 'uat-preflight.json').read_text())
    assert before['metadata']['uid'] == initial['metadata']['uid']
    assert before['spec'] == initial['spec'], 'Deployment changed since preparation'
    assert before['spec']['replicas'] == 1
    save('uat-before-pause.json', before)
    start = now()
    save('window-state.json', {'paused': False, 'restored': False, 'started_at': start.isoformat(),
        'restore_by': (start + datetime.timedelta(minutes=50)).isoformat()})
    patch = [{'op': 'test', 'path': '/metadata/resourceVersion', 'value': before['metadata']['resourceVersion']},
        {'op': 'test', 'path': '/spec/replicas', 'value': 1},
        {'op': 'replace', 'path': '/spec/replicas', 'value': 0}]
    call('patch', 'deployment', 'vllm', '--type=json', '-p', json.dumps(patch))
    state = json.loads((D / 'window-state.json').read_text())
    state['paused'] = True
    save('window-state.json', state)
    call('wait', '--for=delete', 'pod', '-l', 'app=vllm', '--timeout=90s', timeout=100)
    print('UAT model service paused; application deployments were not changed.', flush=True)

def watch():
    while True:
        p = D / 'window-state.json'
        if p.exists():
            state = json.loads(p.read_text())
            if state.get('restored'):
                return
            if now() >= datetime.datetime.fromisoformat(state['restore_by']):
                try:
                    restore()
                except Exception as e:
                    print('RESTORE_ERROR ' + repr(e), flush=True)
        time.sleep(10)

if __name__ == '__main__':
    {'pause': pause, 'restore': restore, 'watch': watch, 'capture': capture}[sys.argv[1]]()
