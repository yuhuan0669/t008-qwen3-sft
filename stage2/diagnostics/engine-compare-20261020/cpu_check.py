"""Verify runtime, read-only weights, CLI arguments and actual prompt token equality."""
import dataclasses
import hashlib
import importlib.metadata
import json
from pathlib import Path
import torch
from transformers import HfArgumentParser
from swift.arguments import InferArguments
from swift.model import get_processor
from swift.template import get_template
from swift.dataset import load_dataset
from commands import commands, D

spec = json.loads((D / 'spec.json').read_text())
assert not torch.cuda.is_available(), 'CPU-only preflight required'
versions = {k: importlib.metadata.version(k) for k in [*spec['versions'], 'vllm']}
assert all(versions[k] == v for k, v in spec['versions'].items())
for name, metadata in spec['models']['adapter_files'].items():
    blob = (Path(spec['models']['loss3_adapter']) / name).read_bytes()
    assert len(blob) == metadata['bytes']
    assert hashlib.sha256(blob).hexdigest() == metadata['sha256']
tokenizer = get_processor('/base', model_type='qwen3', download_model=False)
jinja = (D / 'thinking-prefill.jinja').read_text()
cases = [json.loads(line) for line in (D / 'cases.jsonl').read_text().splitlines()]
checks = []
defaults = []
dataset_checks = {}
for mode in [None, True, False]:
    template = get_template(tokenizer, template_type='qwen3', enable_thinking=mode, max_length=8192)
    template.set_mode('transformers')
    ids = template.encode({'messages': cases[0]['messages']})['input_ids']
    defaults.append({'enable_thinking_argument': mode, 'rendered': tokenizer.decode(ids), 'input_ids': ids})
for name, argv in commands():
    # Parsing does not instantiate SwiftInfer or load model weights.
    args = HfArgumentParser(InferArguments).parse_args_into_dataclasses(argv)[0]
    assert args.infer_backend == 'transformers' and args.system is None
    assert not args.load_args and not args.load_data_args and not args.merge_lora
    request_config = args.get_request_config()
    template = args.get_template(tokenizer)
    template.set_mode('transformers')
    rows = cases if request_config.max_tokens != 2048 else [r for r in cases if r['case_id'] == 'DEV-17']
    dataset_path = args.val_dataset[0]
    if dataset_path not in dataset_checks:
        _, loaded = load_dataset(args.val_dataset, split_dataset_ratio=1.0, shuffle=False,
                                 **args.get_dataset_kwargs())
        assert len(loaded) == len(rows)
        assert [r['messages'] for r in loaded] == [r['messages'] for r in rows]
        dataset_checks[dataset_path] = {'rows': len(loaded), 'messages_equal': True}
    for case in rows:
        native = template.encode({'messages': case['messages']})['input_ids']
        reference = tokenizer.apply_chat_template(case['messages'], chat_template=jinja,
                        tokenize=True, add_generation_prompt=True, enable_thinking=args.enable_thinking)
        if hasattr(reference, 'keys'):
            reference = reference['input_ids']
        assert native == reference, f'Prompt mismatch: {name}/{case["id"]}'
        checks.append({'group': name, 'id': case['id'], 'tokens': len(native),
                       'token_ids_sha256': hashlib.sha256(json.dumps(native).encode()).hexdigest(),
                       'input_ids': native, 'equal': True})
report = {'status': 'PASS', 'cpu_only': True, 'versions': versions,
          'weight_hashes_verified': True, 'prompt_checks': checks, 'native_defaults': defaults,
          'native_dataset_checks': dataset_checks,
          'commands': [{'group': name, 'argv': argv} for name, argv in commands()],
          'base_generation_config': json.loads(Path('/base/generation_config.json').read_text()),
          'note': 'No model weights loaded for generation and no GPU or training used.'}
(D / 'cpu-check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'status': 'PASS', 'prompt_pairs': len(checks), 'versions': versions}))
