"""CPU-only checks. Never load model weights or generate an answer."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import torch
from transformers import AutoTokenizer

D = Path('/tmp/echo80')
spec = json.loads((D / 'spec.json').read_text())
assert not torch.cuda.is_available(), 'Use the CPU-only preparation pod'
requests = [json.loads(x) for x in (D / 'requests.jsonl').read_text().splitlines()]
assert len(requests) == 40 and len({r['id'] for r in requests}) == 40
assert all(sum(r['arm'] == arm for r in requests) == 20 for arm in ['base', 'lora'])
assert hashlib.sha256((D / 'requests.jsonl').read_bytes()).hexdigest() == spec['requests_sha256']
template_path = Path('/t008-serving/thinking-prefill.jinja')
template = template_path.read_text()
assert hashlib.sha256(template_path.read_bytes()).hexdigest() == spec['template_sha256']
tokenizer = AutoTokenizer.from_pretrained(spec['base_path'], local_files_only=True)
reference = json.loads((D / 'render-base.json').read_text())['token_ids']
assert reference == json.loads((D / 'render-lora.json').read_text())['token_ids']
for r in requests:
    ids = tokenizer.apply_chat_template(r['request']['messages'], chat_template=template,
            tokenize=True, add_generation_prompt=True, enable_thinking=False)
    if hasattr(ids, 'keys'):
        ids = ids['input_ids']
    assert ids == reference, r['id']
assert len(reference) == 738
assert tokenizer.decode(reference).endswith('<|im_start|>assistant\n<think>\n\n</think>\n\n')
files = {}
for p in [Path(spec['adapter_path']) / x for x in ['adapter_model.safetensors', 'adapter_config.json']]:
    files[str(p)] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
assert files[spec['adapter_path'] + '/adapter_model.safetensors']['sha256'] == spec['adapter_weight_sha256']
for name in ['config.json', 'generation_config.json', 'tokenizer_config.json', 'tokenizer.json', 'model.safetensors.index.json']:
    p = Path(spec['base_path']) / name
    files[str(p)] = {'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
generation = json.loads((Path(spec['base_path']) / 'generation_config.json').read_text())
report = {'status': 'PASS', 'cpu_only': True, 'input_tokens': len(reference), 'input_ids': reference,
    'input_ids_sha256': hashlib.sha256(json.dumps(reference).encode()).hexdigest(),
    'rendered_prompt': tokenizer.decode(reference), 'all_40_prompts_equal_to_both_server_aliases': True,
    'versions': {n: importlib.metadata.version(n) for n in ['torch', 'transformers', 'peft', 'vllm', 'ms-swift']},
    'files': files, 'base_generation_config': generation, 'pad_token_id': tokenizer.pad_token_id,
    'eos_token_ids': generation['eos_token_id'], 'model_weights_loaded': False, 'generations': 0}
(D / 'cpu-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['status', 'input_tokens', 'versions', 'eos_token_ids', 'pad_token_id']}), flush=True)
