"""Paired free-generation check with frozen existing adapters. No training entry point."""
import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request

D = Path('/tmp/json-check')

def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def state(**values):
    save('run-state.json', dict(values, updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))

def request(route, body):
    req = urllib.request.Request('http://127.0.0.1:8000/v1' + route, data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=360) as response:
        return json.load(response)

def main():
    from transformers import AutoTokenizer
    spec = json.loads((D / 'spec.json').read_text())
    cases = [json.loads(s) for s in (D / 'cases.jsonl').read_text().splitlines()]
    assert len(cases) == len({r['id'] for r in cases}) == spec['cases_per_model'] == 24
    assert len(cases) * len(spec['models']) == spec['total_requests'] == 48
    assert not spec['training'] and not spec['formal_holdout'] and not spec['structured_output_constraints']
    assert json.loads((D / 'authorization.json').read_text())['approved'] is True
    assert not (D / 'run-state.json').exists()
    versions = {key: importlib.metadata.version(key) for key in spec['versions']}
    assert versions == spec['versions'], versions
    for model in spec['models']:
        for name, meta in model['adapter_files'].items():
            blob = (Path(model['adapter']) / name).read_bytes()
            assert len(blob) == meta['bytes'] and hashlib.sha256(blob).hexdigest() == meta['sha256']
    template = (D / 'thinking-prefill.jinja').read_text()
    assert hashlib.sha256(template.encode()).hexdigest() == spec['template_sha256']
    tokenizer = AutoTokenizer.from_pretrained('/base', local_files_only=True)
    prompts = {}
    for case in cases:
        mode = spec['modes'][case['mode']]
        assert hashlib.sha256(case['messages'][0]['content'].encode()).hexdigest() == spec['system_sha256']
        ids = tokenizer.apply_chat_template(case['messages'], chat_template=template, tokenize=True,
                    add_generation_prompt=True, enable_thinking=mode['enable_thinking'])
        if hasattr(ids, 'keys'):
            ids = ids['input_ids']
        assert len(ids) + mode['max_tokens'] <= spec['max_model_len']
        tail = '<think>\n' if mode['enable_thinking'] else '<think>\n\n</think>\n\n'
        assert tokenizer.decode(ids).endswith(tail)
        prompts[case['id']] = ids
    save('runtime-preflight.json', {'status': 'PASS', 'versions': versions, 'adapter_hashes_verified': True,
         'template_hash_verified': True, 'prompt_checks': {k: {'input_ids': v, 'tokens': len(v)} for k, v in prompts.items()}})
    output = D / 'results.jsonl'
    assert not output.exists()
    completed = 0
    for model in spec['models']:
        argv = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server', '--model', '/base',
                '--served-model-name', 't008-base', '--host', '127.0.0.1', '--port', '8000', '--dtype', 'bfloat16',
                '--max-model-len', '8192', '--max-num-seqs', '8', '--gpu-memory-utilization', '0.90', '--seed', '42',
                '--enable-lora', '--lora-modules', model['alias'] + '=' + model['adapter'], '--max-lora-rank', '8',
                '--chat-template', str(D / 'thinking-prefill.jinja'), '--reasoning-parser', 'qwen3']
        save('vllm-command-' + model['key'] + '.json', argv)
        state(status='STARTING', model=model['key'], completed=completed)
        with (D / ('vllm-server-' + model['key'] + '.log')).open('w') as log:
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
                for case in cases:
                    config = dict(spec['modes'][case['mode']])
                    thinking = config.pop('enable_thinking')
                    body = dict(config, model=model['alias'], messages=case['messages'], seed=case['seed'],
                                stream=False, repetition_penalty=1.0, chat_template_kwargs={'enable_thinking': thinking})
                    state(status='RUNNING', model=model['key'], completed=completed, current=case['id'])
                    started = time.monotonic()
                    row = {'model_key': model['key'], 'case': case, 'request': body}
                    try:
                        rendered = request('/chat/completions/render', body)
                        assert rendered['token_ids'] == prompts[case['id']], case['id']
                        row.update(server_render=rendered, input_ids_verified=True)
                        row['response'] = request('/chat/completions', body)
                    except Exception as error:
                        row['error'] = repr(error)
                        raise
                    finally:
                        row['seconds'] = time.monotonic() - started
                        with output.open('a') as f:
                            f.write(json.dumps(row, ensure_ascii=False) + '\n')
                    completed += 1
                    print(json.dumps({'completed': completed, 'model': model['key'], 'id': case['id'],
                          'finish_reason': row['response']['choices'][0]['finish_reason'], 'seconds': row['seconds']}), flush=True)
            finally:
                if server.poll() is None:
                    os.killpg(server.pid, signal.SIGTERM)
                    try:
                        server.wait(timeout=40)
                    except subprocess.TimeoutExpired:
                        os.killpg(server.pid, signal.SIGKILL)
                        server.wait(timeout=10)
    assert len(output.read_text().splitlines()) == completed == 48
    state(status='COMPLETE', completed=completed)

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        state(status='ERROR', error=repr(error))
        raise
