"""Execute an approved temporary GPU check, then always attempt UAT restoration."""
from pathlib import Path
import json
import subprocess
import sys
import tarfile
import time

ROOT = Path(__file__).resolve().parent
K = ['kubectl', '--context', 'lmas00-direct', '--request-timeout=30s']
NAME = (ROOT / 'pod-name.txt').read_text().strip()


def call(*args, timeout=90):
    return subprocess.check_output(K + list(args), text=True, timeout=timeout)


def collect():
    destination = ROOT / 'results'
    destination.mkdir(exist_ok=True)
    temporary = ROOT / 'runtime-results.tar'
    with temporary.open('wb') as f:
        subprocess.run(K + ['-n', 'swift', 'exec', NAME, '--', 'tar', '-C', '/tmp/json-check', '-cf', '-', '.'],
                       stdout=f, check=True, timeout=180)
    with tarfile.open(temporary) as archive:
        archive.extractall(destination, filter='data')
    temporary.unlink()


def main():
    try:
        subprocess.run([sys.executable, str(ROOT / 'window.py'), 'pause'], check=True)
        deadline = time.monotonic() + 180
        while json.loads(call('-n', 'vllm', 'get', 'pods', '-l', 'app=vllm', '-o', 'json'))['items']:
            if time.monotonic() > deadline:
                raise TimeoutError('UAT GPU pod did not terminate')
            time.sleep(3)
        print(call('create', '-f', str(ROOT / 'pod-gpu.json')), flush=True)
        print(call('-n', 'swift', 'wait', '--for=condition=Ready', 'pod/' + NAME,
                   '--timeout=180s', timeout=200), flush=True)
        files = ['run.py', 'spec.json', 'cases.jsonl', 'thinking-prefill.jinja', 'authorization.json']
        with subprocess.Popen(['tar', '-C', str(ROOT), '-cf', '-', *files], stdout=subprocess.PIPE) as sender:
            subprocess.run(K + ['-n', 'swift', 'exec', '-i', NAME, '--', 'tar', '-C', '/tmp/json-check', '-xf', '-'],
                           stdin=sender.stdout, check=True, timeout=90)
            sender.stdout.close()
            assert sender.wait() == 0
        print('RUNNING 48-request inference check', flush=True)
        with (ROOT / 'runner.log').open('w') as log:
            subprocess.run(K + ['-n', 'swift', 'exec', NAME, '--', 'python3', '/tmp/json-check/run.py'],
                           stdout=log, stderr=subprocess.STDOUT, check=True, timeout=2400)
    finally:
        try:
            if call('-n', 'swift', 'get', 'pod', NAME, '--ignore-not-found', '-o', 'name').strip():
                collect()
                print('Runtime evidence saved locally', flush=True)
        finally:
            if (ROOT / 'window-state.json').exists():
                subprocess.run([sys.executable, str(ROOT / 'window.py'), 'restore'], check=True)


if __name__ == '__main__':
    main()
