"""Run the exact paired cases against a temporary, corrected-template vLLM server."""
import json
import time
import urllib.request
from pathlib import Path
from transformers import AutoTokenizer

D = Path('/tmp/engine-compare')
spec = json.loads((D / 'spec.json').read_text())
cases = [json.loads(s) for s in (D / 'cases.jsonl').read_text().splitlines()]
tokenizer = AutoTokenizer.from_pretrained('/base', local_files_only=True)
template = (D / 'thinking-prefill.jinja').read_text()
output = D / 'vllm-results.jsonl'
assert not output.exists()


def request(route, body):
    req = urllib.request.Request('http://127.0.0.1:8000/v1' + route,
            data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=360) as response:
        return json.load(response)


for model in ['base', 'loss3']:
    for mode, cap in [('nonthinking', 1024), ('thinking', 4096), ('nonthinking', 2048)]:
        config = dict(spec['modes'][mode])
        thinking = config.pop('enable_thinking')
        config['max_tokens'] = cap
        rows = cases if cap != 2048 else [r for r in cases if r['case_id'] == 'DEV-17']
        for case in rows:
            body = dict(config, model='t008-' + model, messages=case['messages'], seed=42,
                        stream=False, repetition_penalty=1.0,
                        chat_template_kwargs={'enable_thinking': thinking})
            expected = tokenizer.apply_chat_template(case['messages'], chat_template=template,
                        tokenize=True, add_generation_prompt=True, enable_thinking=thinking)
            if hasattr(expected, 'keys'):
                expected = expected['input_ids']
            rendered = request('/chat/completions/render', body)
            assert rendered['token_ids'] == expected
            start = time.monotonic()
            response = request('/chat/completions', body)
            row = {'model': model, 'mode': mode, 'cap': cap, 'case': case,
                   'request': body, 'server_render': rendered, 'response': response,
                   'seconds': time.monotonic() - start, 'input_ids_verified': True}
            with output.open('a') as f:
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
            print(json.dumps({'model': model, 'mode': mode, 'cap': cap, 'id': case['id'],
                  'finish_reason': response['choices'][0]['finish_reason'],
                  'usage': response['usage'], 'seconds': row['seconds']}), flush=True)
