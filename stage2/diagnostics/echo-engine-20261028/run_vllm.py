"""40 sequential chat requests against the existing, unchanged vLLM service."""
import datetime
import json
import time
import urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
spec = json.loads((D / 'spec.json').read_text())
checked = json.loads((D / 'cpu-check.json').read_text())
assert checked['status'] == 'PASS'
requests = [json.loads(x) for x in (D / 'requests.jsonl').read_text().splitlines()]
output = D / 'vllm-results.jsonl'
assert not output.exists(), 'Never silently repeat or overwrite diagnostic requests'
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def post(route, body):
    request = urllib.request.Request(spec['vllm_url'] + route, data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    with opener.open(request, timeout=180) as response:
        raw = response.read().decode()
        return response.status, raw, json.loads(raw)

for case in requests:
    _, _, rendered = post('/v1/chat/completions/render', case['request'])
    assert rendered['token_ids'] == checked['input_ids']
    started = time.monotonic()
    status, raw, response = post('/v1/chat/completions', case['request'])
    row = {**case, 'backend': 'vllm_chat', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'http_status': status, 'seconds': time.monotonic() - started, 'server_render': rendered,
        'response_raw': raw, 'response': response}
    with output.open('a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    choice = response['choices'][0]
    print(json.dumps({'id': case['id'], 'seconds': row['seconds'], 'finish_reason': choice['finish_reason'],
        'usage': response.get('usage')}, ensure_ascii=False), flush=True)
assert len(output.read_text().splitlines()) == 40
