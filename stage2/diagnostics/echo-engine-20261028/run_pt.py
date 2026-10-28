"""40 native Transformers/PEFT generations; no Swift defaults and no vLLM backend."""
import contextlib
import datetime
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, set_seed
from peft import PeftModel

D = Path('/tmp/echo80')
spec = json.loads((D / 'spec.json').read_text())
checked = json.loads((D / 'cpu-check.json').read_text())
assert checked['status'] == 'PASS' and torch.cuda.is_available()
assert json.loads((D / 'authorization.json').read_text())['uat_pause_approved'] is True
requests = [json.loads(x) for x in (D / 'requests.jsonl').read_text().splitlines()]
assert hashlib.sha256((D / 'requests.jsonl').read_bytes()).hexdigest() == spec['requests_sha256']
for name, info in checked['files'].items():
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == info['sha256'], name
output = D / 'pt-results.jsonl'
assert not output.exists(), 'Never silently repeat or overwrite diagnostic requests'
versions = {n: importlib.metadata.version(n) for n in checked['versions']}
assert versions == checked['versions']
tokenizer = AutoTokenizer.from_pretrained(spec['base_path'], local_files_only=True)
torch.set_num_threads(4)
load_start = time.monotonic()
base = AutoModelForCausalLM.from_pretrained(spec['base_path'], local_files_only=True,
    dtype=torch.bfloat16, device_map={'': 'cuda:0'}, attn_implementation='sdpa')
model = PeftModel.from_pretrained(base, spec['adapter_path'], is_trainable=False,
    autocast_adapter_dtype=False)
model.eval()
for p in model.parameters():
    p.requires_grad_(False)
runtime = {'versions': versions, 'load_seconds': time.monotonic() - load_start,
    'dtype': str(next(base.parameters()).dtype), 'attention_implementation': base.config._attn_implementation,
    'adapter_config': model.peft_config['default'].to_dict(),
    'adapter_dtypes': sorted({str(p.dtype) for n, p in model.named_parameters() if 'lora_' in n}),
    'base_arm': 'PEFT disable_adapter context, same original base weights',
    'training': False, 'grad_enabled_during_generation': False, 'versions_match_cpu_preflight': True}
(D / 'pt-runtime.json').write_text(json.dumps(runtime, ensure_ascii=False, indent=2, default=str) + '\n')
print(json.dumps({'loaded': True, 'seconds': runtime['load_seconds'], 'adapter_dtypes': runtime['adapter_dtypes']}), flush=True)
ids = torch.tensor([checked['input_ids']], device='cuda:0')
mask = torch.ones_like(ids)
eos = checked['eos_token_ids']
eos = eos if isinstance(eos, list) else [eos]
for case in requests:
    p = case['request']
    config = GenerationConfig(do_sample=True, temperature=p['temperature'], top_p=p['top_p'],
        top_k=p['top_k'], min_p=p['min_p'], repetition_penalty=p['repetition_penalty'],
        max_new_tokens=p['max_tokens'], eos_token_id=eos, pad_token_id=checked['pad_token_id'],
        num_beams=1, num_return_sequences=1, use_cache=True, renormalize_logits=False)
    set_seed(case['seed'])
    ctx = model.disable_adapter() if case['arm'] == 'base' else contextlib.nullcontext()
    torch.cuda.synchronize()
    started = time.monotonic()
    with ctx, torch.inference_mode():
        result = model.generate(input_ids=ids, attention_mask=mask, generation_config=config)
    torch.cuda.synchronize()
    generated = result[0, ids.shape[1]:].tolist()
    raw = tokenizer.decode(generated, skip_special_tokens=False)
    content = tokenizer.decode(generated, skip_special_tokens=True)
    finish = 'stop' if generated and generated[-1] in eos else 'length'
    row = {**case, 'backend': 'transformers_peft', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'seconds': time.monotonic() - started, 'input_ids_sha256': checked['input_ids_sha256'],
        'generation_config': config.to_dict(), 'output_token_ids': generated, 'raw_generated_text': raw,
        'response': {'model': p['model'], 'choices': [{'finish_reason': finish,
            'message': {'role': 'assistant', 'content': content}}],
            'usage': {'prompt_tokens': ids.shape[1], 'completion_tokens': len(generated)}}}
    with output.open('a') as f:
        f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(json.dumps({'id': case['id'], 'seconds': row['seconds'], 'finish_reason': finish,
        'output_tokens': len(generated)}, ensure_ascii=False), flush=True)
assert len(output.read_text().splitlines()) == 40
