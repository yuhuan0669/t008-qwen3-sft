"""Explicit native Swift CLI commands for the inference-only comparison."""
import json
from pathlib import Path

D = Path('/tmp/engine-compare')


def commands():
    spec = json.loads((D / 'spec.json').read_text())
    for model in ['base', 'loss3']:
        for mode, cap in [('nonthinking', 1024), ('thinking', 4096), ('nonthinking', 2048)]:
            config = spec['modes'][mode]
            name = f'{model}-{mode}-{cap}'
            dataset = 'length-case.jsonl' if cap == 2048 else 'cases.jsonl'
            prefix = '<think>\n' if mode == 'thinking' else '<think>\n\n</think>\n\n'
            args = [
                '--model', '/base', '--model_type', 'qwen3',
                '--infer_backend', 'transformers', '--load_args', 'false',
                '--load_data_args', 'false', '--torch_dtype', 'bfloat16',
                '--attn_impl', 'sdpa', '--template', 'qwen3', '--template_backend', 'swift',
                '--enable_thinking', str(config['enable_thinking']).lower(),
                '--response_prefix', prefix, '--max_length', '8192',
                '--truncation_strategy', 'delete', '--max_new_tokens', str(cap),
                '--temperature', str(config['temperature']), '--top_p', str(config['top_p']),
                '--top_k', str(config['top_k']), '--repetition_penalty', '1.0',
                '--seed', '42', '--data_seed', '42', '--stream', 'false',
                '--max_batch_size', '1', '--write_batch_size', '1',
                '--val_dataset', str(D / dataset), '--val_dataset_shuffle', 'false',
                '--dataset_shuffle', 'false', '--strict', 'true',
                '--dataset_num_proc', '1', '--result_path', str(D / f'swift-{name}.jsonl'),
                '--external_plugins', str(D / 'capture.py'),
            ]
            if model == 'loss3':
                args += ['--adapters', spec['models']['loss3_adapter']]
            yield name, args
