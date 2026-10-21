"""Inference only. Start in the GPU pod after a separately approved UAT pause."""
import datetime
import json
import os
import subprocess
import sys
import time
import urllib.request
from commands import commands, D


def save_state(**values):
    values['updated_at_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (D / 'run-state.json').write_text(json.dumps(values, indent=2) + '\n')


def main():
    assert json.loads((D / 'cpu-check.json').read_text())['status'] == 'PASS'
    assert json.loads((D / 'authorization.json').read_text()).get('approved') is True
    assert not (D / 'run-state.json').exists(), 'Do not overwrite a diagnostic run'
    for name, argv in commands():
        save_state(status='RUNNING', backend='swift_infer_transformers', group=name)
        env = dict(os.environ, T008_CAPTURE_PATH=str(D / f'swift-raw-{name}.jsonl'))
        with (D / f'swift-{name}.log').open('w') as log:
            subprocess.run(['swift', 'infer', *argv], env=env, stdout=log,
                           stderr=subprocess.STDOUT, check=True, timeout=900)
        captured = [json.loads(s) for s in (D / f'swift-raw-{name}.jsonl').read_text().splitlines()]
        expected = 1 if name.endswith('-2048') else 10
        assert sum(len(r['responses']) for r in captured) == expected
        print('Completed Swift group ' + name, flush=True)
    spec = json.loads((D / 'spec.json').read_text())
    argv = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
            '--model', '/base', '--served-model-name', 't008-base',
            '--host', '127.0.0.1', '--port', '8000', '--dtype', 'bfloat16',
            '--max-model-len', '8192', '--max-num-seqs', '8',
            '--gpu-memory-utilization', '0.90', '--seed', '42',
            '--enable-lora', '--lora-modules', 't008-loss3=' + spec['models']['loss3_adapter'],
            '--max-lora-rank', '8', '--chat-template', str(D / 'thinking-prefill.jinja'),
            '--reasoning-parser', 'qwen3']
    (D / 'vllm-command.json').write_text(json.dumps(argv, indent=2) + '\n')
    save_state(status='STARTING', backend='vllm_chat')
    with (D / 'vllm-server.log').open('w') as log:
        server = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 480
            while True:
                assert server.poll() is None, 'vLLM exited before readiness'
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3) as response:
                        if response.status == 200:
                            break
                except Exception:
                    pass
                if time.monotonic() >= deadline:
                    raise TimeoutError('vLLM startup timed out')
                time.sleep(3)
            save_state(status='RUNNING', backend='vllm_chat')
            with (D / 'vllm-client.log').open('w') as client_log:
                subprocess.run([sys.executable, str(D / 'vllm_compare.py')],
                               stdout=client_log, stderr=subprocess.STDOUT, check=True, timeout=900)
        finally:
            server.terminate()
            try:
                server.wait(timeout=40)
            except subprocess.TimeoutExpired:
                server.kill()
    assert len((D / 'vllm-results.jsonl').read_text().splitlines()) == 42
    save_state(status='COMPLETE', requests=84)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        save_state(status='ERROR', error=repr(error))
        raise
