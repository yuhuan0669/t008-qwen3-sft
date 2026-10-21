"""Run the same 40 Chinese development requests on the terminal v0.1.9 checkpoint."""
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

D = Path('/runwork/development')


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def state(**values):
    save('run-state.json', dict(values, updated_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))


def request(route, body):
    req = urllib.request.Request('http://127.0.0.1:8000/v1' + route,
                                data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=360) as response:
        return json.load(response)


def main():
    from transformers import AutoTokenizer
    import shutil
    D.mkdir(exist_ok=False)
    for name in ['cases.jsonl', 'thinking-prefill.jinja', 'spec.json']:
        shutil.copyfile(Path('/input/evaluation') / name, D / name)
    manifest = json.loads(Path('/runwork/outputs/full/run_manifest.json').read_text())
    assert manifest['training_verified'] and manifest['global_step'] == 80 and manifest['epoch'] == 1.0
    assert manifest['status'] == 'TRAINED_CANDIDATE'
    spec = json.loads((D / 'spec.json').read_text())
    assert spec['training_data_sha256'] == manifest['data_sha256']
    spec['models']['candidate_adapter'] = manifest['checkpoint']
    spec['models']['adapter_files'] = manifest['adapter_files']
    save('spec.json', spec)
    auth = json.loads(Path('/input/window.json').read_text())
    assert auth['experiment_approved'] and auth['uat_pause_approved']
    assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(auth['restore_start_utc'])
    save('authorization.json', {'approved': True, 'decision_ref': auth['decision_ref']})
    spec = json.loads((D / 'spec.json').read_text())
    cases = [json.loads(s) for s in (D / 'cases.jsonl').read_text().splitlines()]
    assert len(cases) == len({r['id'] for r in cases}) == spec['total_requests'] == 40
    assert not spec['training'] and not spec['formal_holdout']
    assert json.loads((D / 'authorization.json').read_text())['approved'] is True
    assert not (D / 'run-state.json').exists(), 'Never overwrite a prior run'
    versions = {key: importlib.metadata.version(key) for key in spec['versions']}
    assert versions == spec['versions'], versions
    for name, metadata in spec['models']['adapter_files'].items():
        blob = (Path(spec['models']['candidate_adapter']) / name).read_bytes()
        assert len(blob) == metadata['bytes']
        assert hashlib.sha256(blob).hexdigest() == metadata['sha256']
    template = (D / 'thinking-prefill.jinja').read_text()
    assert hashlib.sha256(template.encode()).hexdigest() == spec['template_sha256']
    tokenizer = AutoTokenizer.from_pretrained('/base', local_files_only=True)
    prompts = {}
    for case in cases:
        mode = spec['modes'][case['mode']]
        ids = tokenizer.apply_chat_template(case['messages'], chat_template=template,
                    tokenize=True, add_generation_prompt=True, enable_thinking=mode['enable_thinking'])
        if hasattr(ids, 'keys'):
            ids = ids['input_ids']
        assert len(ids) + mode['max_tokens'] <= spec['max_model_len']
        expected_tail = '<think>\n' if mode['enable_thinking'] else '<think>\n\n</think>\n\n'
        assert tokenizer.decode(ids).endswith(expected_tail)
        prompts[case['id']] = ids
    save('runtime-preflight.json', {'status': 'PASS', 'versions': versions,
         'adapter_hashes_verified': True, 'template_hash_verified': True,
         'prompt_checks': {key: {'input_ids': ids, 'tokens': len(ids)} for key, ids in prompts.items()},
         'generation_config': json.loads(Path('/base/generation_config.json').read_text()),
         'note': 'Tokenization and hash checks only; no training dataset encoding.'})
    print('Preflight PASS: 40 prompts, adapter hashes and versions verified', flush=True)
    argv = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
            '--model', '/base', '--served-model-name', 't008-base',
            '--host', '127.0.0.1', '--port', '8000', '--dtype', 'bfloat16',
            '--max-model-len', '8192', '--max-num-seqs', '8',
            '--gpu-memory-utilization', '0.90', '--seed', '42',
            '--enable-lora', '--lora-modules', 't008-new=' + spec['models']['candidate_adapter'],
            '--max-lora-rank', '8', '--chat-template', str(D / 'thinking-prefill.jinja'),
            '--reasoning-parser', 'qwen3']
    save('vllm-command.json', argv)
    state(status='STARTING', completed=0)
    output = D / 'results.jsonl'
    assert not output.exists()
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
            for index, case in enumerate(cases):
                config = dict(spec['modes'][case['mode']])
                thinking = config.pop('enable_thinking')
                body = dict(config, model='t008-new', messages=case['messages'], seed=case['seed'],
                            stream=False, repetition_penalty=1.0,
                            chat_template_kwargs={'enable_thinking': thinking})
                state(status='RUNNING', completed=index, current=case['id'])
                started = time.monotonic()
                row = {'case': case, 'request': body}
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
                choice = row['response']['choices'][0]
                print(json.dumps({'completed': index + 1, 'id': case['id'],
                      'finish_reason': choice['finish_reason'], 'usage': row['response']['usage'],
                      'seconds': row['seconds']}, ensure_ascii=False), flush=True)
        finally:
            if server.poll() is None:
                os.killpg(server.pid, signal.SIGTERM)
                try:
                    server.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL)
                    server.wait(timeout=10)
    assert len(output.read_text().splitlines()) == 40
    state(status='COMPLETE', completed=40)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        state(status='ERROR', error=repr(error))
        raise
