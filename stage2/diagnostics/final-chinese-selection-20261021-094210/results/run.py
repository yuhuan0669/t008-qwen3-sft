"""Frozen three-model inference comparison. No optimizer or training imports."""
from pathlib import Path
import datetime
import hashlib
import importlib.metadata
import json
import os
import signal
import subprocess
import sys
import time
import urllib.request

D = Path(__file__).resolve().parent


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def request(route, body):
    req = urllib.request.Request('http://127.0.0.1:8000/v1' + route,
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=360) as response:
        return json.load(response)


def main():
    from transformers import AutoTokenizer
    spec = json.loads((D / 'spec.json').read_text())
    assert spec['training'] is False and spec['english'] is False
    assert json.loads((D / 'authorization.json').read_text())['approved'] is True
    assert not (D / 'results.jsonl').exists(), 'Never overwrite or resample a run'
    versions = {x: importlib.metadata.version(x) for x in spec['versions']}
    assert versions == spec['versions'], versions
    for filename, key in [('custom-system.txt', 'system_sha256'),
                          ('thinking-prefill.jinja', 'template_sha256'),
                          ('scenarios.jsonl', 'scenarios_sha256')]:
        assert digest(D / filename) == spec[key]
    verified = {}
    for model, adapter in spec['adapters'].items():
        for filename, info in adapter['files'].items():
            path = Path(adapter['path']) / filename
            assert path.stat().st_size == info['bytes'] and digest(path) == info['sha256']
        verified[model] = adapter
    base_verified = []
    for info in json.loads((D / 'base-files.json').read_text()):
        if info['path'].startswith(('model', 'tokenizer', 'config', 'generation', 'merges', 'vocab')):
            path = Path('/base') / info['path']
            assert path.stat().st_size == info['size'] and digest(path) == info['sha256'], info['path']
            base_verified.append(info)
    system = (D / 'custom-system.txt').read_text()
    template = (D / 'thinking-prefill.jinja').read_text()
    scenarios = [json.loads(x) for x in (D / 'scenarios.jsonl').read_text().splitlines()]
    assert len(scenarios) == 24 and len({x['id'] for x in scenarios}) == 24
    assert sum(len(x['user_turns']) for x in scenarios) * 18 == spec['total_requests']
    tokenizer = AutoTokenizer.from_pretrained('/base', local_files_only=True)
    first_prompts = {}
    for scenario in scenarios:
        for mode, cfg in spec['modes'].items():
            messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': scenario['user_turns'][0]}]
            ids = tokenizer.apply_chat_template(messages, chat_template=template,
                tokenize=True, add_generation_prompt=True, enable_thinking=cfg['enable_thinking'])
            if hasattr(ids, 'keys'): ids = ids['input_ids']
            tail = '<think>\n' if cfg['enable_thinking'] else '<think>\n\n</think>\n\n'
            assert tokenizer.decode(ids).endswith(tail)
            assert len(ids) + cfg['max_tokens'] <= spec['max_model_len']
            first_prompts[scenario['id'] + '__' + mode] = ids
    save('preflight.json', dict(status='PASS', versions=versions,
        base_files=base_verified, adapters=verified, first_prompt_token_ids=first_prompts,
        system_sha256=spec['system_sha256'], template_sha256=spec['template_sha256']))
    print('HASHES AND INPUTS VERIFIED', flush=True)
    argv = [sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
        '--model', '/base', '--served-model-name', 't008-base', '--host', '127.0.0.1',
        '--port', '8000', '--dtype', 'bfloat16', '--max-model-len', '8192',
        '--max-num-seqs', '8', '--gpu-memory-utilization', '0.90', '--seed', '42',
        '--enable-lora', '--lora-modules',
        *[name + '=' + item['path'] for name, item in spec['adapters'].items()],
        '--max-lora-rank', '8', '--max-loras', '1', '--max-cpu-loras', '2',
        '--chat-template', str(D / 'thinking-prefill.jinja'), '--reasoning-parser', 'qwen3']
    save('vllm-command.json', argv)
    n = 0
    with (D / 'vllm-server.log').open('w') as log:
        server = subprocess.Popen(argv, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            deadline = time.monotonic() + 480
            while True:
                assert server.poll() is None, 'vLLM startup failed'
                try:
                    with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3) as res:
                        if res.status == 200: break
                except Exception:
                    pass
                if time.monotonic() > deadline: raise TimeoutError('Startup exceeded 480 seconds')
                time.sleep(3)
            for si, scenario in enumerate(scenarios):
                for mi, mode in enumerate(['nonthinking', 'thinking']):
                    for seed_index, seed in enumerate(spec['seeds']):
                        shift = (si + mi + seed_index) % 3
                        models = spec['models'][shift:] + spec['models'][:shift]
                        for model in models:
                            messages = [{'role': 'system', 'content': system}]
                            session = '__'.join([scenario['id'], mode, str(seed), model])
                            for turn, prompt in enumerate(scenario['user_turns'], 1):
                                messages.append({'role': 'user', 'content': prompt})
                                cfg = dict(spec['modes'][mode]); thinking = cfg.pop('enable_thinking')
                                body = dict(cfg, model=model, messages=list(messages), seed=seed,
                                    stream=False, repetition_penalty=1.0,
                                    chat_template_kwargs={'enable_thinking': thinking})
                                if 'response_format' in scenario: body['response_format'] = scenario['response_format']
                                ids = tokenizer.apply_chat_template(messages, chat_template=template,
                                    tokenize=True, add_generation_prompt=True, enable_thinking=thinking)
                                if hasattr(ids, 'keys'): ids = ids['input_ids']
                                assert len(ids) + cfg['max_tokens'] <= spec['max_model_len']
                                row = dict(id=session+'__'+str(turn), case_id=scenario['id'],
                                    model=model, mode=mode, seed=seed, turn=turn,
                                    category=scenario['category'], checks=scenario['checks'][turn-1], request=body)
                                started = time.monotonic()
                                try:
                                    rendered = request('/chat/completions/render', body)
                                    assert rendered['token_ids'] == ids
                                    row['server_render'] = rendered
                                    row['input_ids_verified'] = True
                                    row['response'] = request('/chat/completions', body)
                                    assert row['response']['usage']['prompt_tokens'] == len(ids)
                                except Exception as error:
                                    row['error'] = repr(error)
                                    raise
                                finally:
                                    row['seconds'] = time.monotonic() - started
                                    with (D / 'results.jsonl').open('a') as f:
                                        f.write(json.dumps(row, ensure_ascii=False)+'\n')
                                choice = row['response']['choices'][0]
                                messages.append({'role': 'assistant', 'content': choice['message'].get('content') or ''})
                                n += 1
                                progress = dict(completed=n, total=spec['total_requests'], current=row['id'],
                                    finish_reason=choice['finish_reason'], tokens=row['response']['usage']['completion_tokens'],
                                    seconds=row['seconds'], at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
                                save('progress.json', progress)
                                print(json.dumps(progress), flush=True)
        finally:
            if server.poll() is None:
                os.killpg(server.pid, signal.SIGTERM)
                try: server.wait(timeout=40)
                except subprocess.TimeoutExpired:
                    os.killpg(server.pid, signal.SIGKILL); server.wait(timeout=10)
    assert n == spec['total_requests']
    save('complete.json', dict(status='COMPLETE', count=n, results_sha256=digest(D/'results.jsonl'), training=False))


if __name__ == '__main__':
    try: main()
    except Exception as e:
        save('failure.json', dict(error=repr(e)))
        raise
