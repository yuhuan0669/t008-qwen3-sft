"""Run the existing Swift preparation path on a CPU-only Pod, then remove it."""
from pathlib import Path
import json
import subprocess
import tarfile

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
OUT = D / 'cpu-check'
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']
NAME = 't008-v0110-cpu-20261020'

def call(*args, timeout=90):
    return subprocess.check_output(K + list(args), text=True, timeout=timeout)

def snapshot(name):
    obj = json.loads(call('-n', 'vllm', 'get', 'deployment', 'vllm', '-o', 'json'))
    (OUT / name).write_text(json.dumps(obj, indent=2) + '\n')
    return obj

def main():
    assert not (OUT / 'report.json').exists(), 'Preserve prior CPU evidence'
    before = snapshot('uat-before.json')
    files = [D.relative_to(ROOT).as_posix(),
             'stage1/variants/stage1-cpu-v0.1.9/train.jsonl',
             'stage1/variants/stage1-cpu-v0.1.9/identity-keys.json',
             'stage1/variants/stage1-cpu-v0.1.9/cpu-check/report.json',
             'stage1/training/local_data_guard.py',
             'stage2/variants/identity-loss3-review/identity_loss3.py',
             'stage2/variants/identity-loss3-review/cpu-check/report.json',
             'stage2/variants/identity-loss3-review/source',
             'stage2/diagnostics/thinking-chat-template-20261020/thinking-prefill.jinja']
    existing = json.loads(call('-n', 'swift', 'get', 'pods', '--field-selector', 'metadata.name=' + NAME, '-o', 'json'))['items']
    if existing:
        assert existing[0]['metadata'].get('deletionTimestamp'), 'Unexpected active CPU Pod; do not replace it'
        call('-n', 'swift', 'wait', '--for=delete', 'pod/' + NAME, '--timeout=60s', timeout=75)
    created = False
    try:
        print(call('create', '-f', str(OUT / 'pod-cpu.json')), flush=True)
        created = True
        print(call('-n', 'swift', 'wait', '--for=condition=Ready', 'pod/' + NAME, '--timeout=180s', timeout=200), flush=True)
        with subprocess.Popen(['tar', '-C', str(ROOT), '-cf', '-', *files], stdout=subprocess.PIPE) as sender:
            subprocess.run(K + ['-n', 'swift', 'exec', '-i', NAME, '--', 'tar', '-C', '/tmp/v0110-check', '-xf', '-'],
                           stdin=sender.stdout, check=True, timeout=90)
            sender.stdout.close()
            assert sender.wait() == 0
        remote = '/tmp/v0110-check/' + D.relative_to(ROOT).as_posix() + '/cpu-check'
        with (OUT / 'cpu-check.log').open('w') as log:
            done = subprocess.run(K + ['-n', 'swift', 'exec', NAME, '--', 'python3', remote + '/check_cpu.py'],
                                  stdout=log, stderr=subprocess.STDOUT, timeout=600)
        (OUT / 'cpu-exit.json').write_text(json.dumps({'returncode': done.returncode}) + '\n')
        done.check_returncode()
        bundle = OUT / 'results.tar'
        with bundle.open('wb') as f:
            subprocess.run(K + ['-n', 'swift', 'exec', NAME, '--', 'tar', '-C', remote, '-cf', '-',
                               'report.json', 'row-checks.jsonl', 'mask-probes.json'], stdout=f, check=True, timeout=120)
        with tarfile.open(bundle) as archive:
            archive.extractall(OUT, filter='data')
        bundle.unlink()
        after = snapshot('uat-after.json')
        assert after['spec'] == before['spec']
        (OUT / 'uat-after-verification.json').write_text(json.dumps({'original_spec_equal': True,
            'before_ready': before['status'].get('readyReplicas'), 'after_ready': after['status'].get('readyReplicas'),
            'gpu_requested': False, 'uat_mutation': False}) + '\n')
        print(json.dumps(json.loads((OUT / 'report.json').read_text()), ensure_ascii=False), flush=True)
    finally:
        if created:
            print(call('-n', 'swift', 'delete', 'pod', NAME, '--ignore-not-found', '--wait=true', '--timeout=60s', timeout=75), flush=True)

if __name__ == '__main__':
    main()
