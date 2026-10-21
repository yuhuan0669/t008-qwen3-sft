"""Actual Swift CPU preparation. Does not instantiate a model, Trainer or optimizer."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib
import importlib.metadata as md
import json

import torch
from transformers import HfArgumentParser
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.pipelines.train.sft import SwiftSft

OUT = Path(__file__).resolve().parent
D = OUT.parent
ROOT = D.parents[2]
PARENT = ROOT / 'stage1/variants/stage1-cpu-v0.1.8'
LOSS3 = ROOT / 'stage2/variants/identity-loss3-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
spec = json.loads((D / 'training-config.json').read_text())
reference = json.loads((PARENT / 'cpu-check/encoding-report.json').read_text())
assert not torch.cuda.is_available() and not list(Path('/dev').glob('nvidia*'))
assert spec['execution_authorized'] is False
assert sha(D / 'train.jsonl') == spec['dataset_sha256']
versions = {k: md.version(k) for k in reference['versions']}
assert versions == reference['versions'], versions
for name, digest in reference['tokenizer_config_sha256'].items():
    assert sha(Path('/base') / name) == digest, name
assert sha(D / 'identity_loss3.py') == sha(LOSS3 / 'identity_loss3.py')

argv = [x.replace('/work/', str(ROOT) + '/') for x in spec['full_argv'][2:]]
overrides = ['--use_cpu', 'true', '--report_to', 'none', '--add_version', 'false',
             '--output_dir', str(OUT / 'args-only'), '--dataset_num_proc', '1']
args, = HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv + overrides)
assert str(args.training_args.device) == 'cpu'
assert args.loss_scale == 'default+t008_identity3_ignore_empty_think'
assert args.preserve_thinking is False and not args.disable_ignore_empty_think
assert args.system is None and args.max_length == 2048
assert args.truncation_strategy == 'delete' and args.dataset_shuffle
assert args.num_train_epochs == 1 and args.gradient_accumulation_steps == 16
assert args.per_device_train_batch_size == 1 and args.learning_rate == 1e-4
assert args.lora_rank == 8 and args.lora_alpha == 32 and args.lora_dropout == .05
assert getattr(SwiftSft._encode_dataset, '_t008_local_guard', False)

# Native loss and denominator implementations must match the earlier numeric test.
source_checks = {}
for name in ['transformers.trainer', 'swift.trainers.seq2seq_trainer',
             'swift.loss_scale.base', 'swift.loss_scale.mapping', 'swift.loss_scale.other']:
    actual = Path(importlib.import_module(name).__file__)
    frozen = LOSS3 / 'source' / (name.replace('.', '/') + '.py')
    assert sha(actual) == sha(frozen), name
    source_checks[name] = sha(actual)

from identity_loss3 import message_key
rows = [json.loads(x) for x in (D / 'train.jsonl').read_text().splitlines()]
parent_rows = [json.loads(x) for x in (PARENT / 'train.jsonl').read_text().splitlines()]
changes = [json.loads(x) for x in (D / 'changes.jsonl').read_text().splitlines()]
changed = {c['parent_train_row_zero_based'] for c in changes}
assert len(rows) == len(parent_rows) == 1275
expected = Counter(message_key(r['messages']) for r in rows)
loaded, val = args.load_dataset()
assert Counter(message_key(r['messages']) for r in loaded) == expected
assert val is None or len(val) == 0
processor = get_processor('/base', model_type='qwen3', download_model=False)
new = get_template(processor, **args.get_template_kwargs())
old = get_template(processor, **args.get_template_kwargs())
unbounded = get_template(processor, **args.get_template_kwargs())
for template in [new, old, unbounded]:
    template.set_mode('train')
old.loss_scale.identity_keys = frozenset(json.loads((LOSS3 / 'identity-keys.json').read_text())['identity_message_sha256'])
unbounded.max_length = None
assert old.loss_scale is not new.loss_scale
assert old.loss_scale.identity_keys != new.loss_scale.identity_keys
assert new.loss_scale.is_binary_loss_scale is False


class PreparationOnly:
    def _save_val_dataset(self, val):
        assert val is None or len(val) == 0


stub = PreparationOnly()
stub.args, stub.template = args, new
encoded, val = SwiftSft._encode_dataset(stub, loaded, val)
assert Counter(message_key(r['messages']) for r in encoded) == expected
assert len(encoded) == 1275

cache_new, cache_old = {}, {}
audit, probes = [], []
totals, old_totals, counts = Counter(), Counter(), Counter()
examples = {}
for i, (row, parent_row) in enumerate(zip(rows, parent_rows)):
    nk, ok = message_key(row['messages']), message_key(parent_row['messages'])
    if nk not in cache_new:
        b = new.encode(deepcopy(row))
        ub = unbounded.encode(deepcopy(row))
        for field in ['input_ids', 'labels', 'loss_scale']:
            assert b[field] == ub[field], (i, field, 'bounded encoding differs')
        assert len(b['input_ids']) <= 2048
        assert any(y != -100 for y in b['labels'])
        assert all(y == -100 or x == y for x, y in zip(b['input_ids'], b['labels']))
        cache_new[nk] = b
    if ok not in cache_old:
        cache_old[ok] = old.encode(deepcopy(parent_row))
    a, b = cache_old[ok], cache_new[nk]
    if i not in changed:
        assert all(a[k] == b[k] for k in ['input_ids', 'labels', 'loss_scale']), i
    else:
        assert a['input_ids'] != b['input_ids']
    source = row['dataset']
    factor = 3.0 if source == 'swift/self-cognition' else 1.0
    assert b['loss_scale'] == [factor if y != -100 else 0.0 for y in b['labels']], i
    tokens, prior = sum(y != -100 for y in b['labels']), sum(y != -100 for y in a['labels'])
    totals[source] += tokens
    old_totals[source] += prior
    counts[source] += 1
    examples.setdefault(source, b)
    audit.append({'row_zero_based': i, 'source': source, 'changed': i in changed,
                  'encoded_tokens': len(b['input_ids']), 'supervised_tokens': tokens,
                  'parent_supervised_tokens': prior, 'factor': factor,
                  'unchanged_encoding_and_masks': i not in changed})
    if i in changed:
        text = processor.decode([x for x, y in zip(b['input_ids'], b['labels']) if y != -100])
        content = row['messages'][-1]['content']
        assert content in text, (i, text)
        assert text.count('<think>') == text.count('</think>') == 1
        assert row['messages'][0]['content'] not in text
        assert '<|im_end|>' in text
        supervised_positions = [j for j, y in enumerate(b['labels']) if y != -100]
        assert all(v == 0 for v in b['loss_scale'][:supervised_positions[0]])
        probes.append({'row_zero_based': i, 'line_one_based': i + 1, 'source': source,
                       'tokens_before': len(a['input_ids']), 'tokens_after': len(b['input_ids']),
                       'supervised_tokens_before': prior, 'supervised_tokens_after': tokens,
                       'full_nonempty_thought_and_body_supervised': True,
                       'prompt_masked': True, 'eos_supervised': True,
                       'effective_weight': factor, 'supervised_text': text,
                       'input_ids': b['input_ids'], 'labels': b['labels'], 'loss_scale': b['loss_scale']})

assert dict(old_totals) == reference['source_supervised_tokens']
assert dict(counts) == {'swift/Qwen3-SFT-Mixin': 1036, 'swift/self-cognition': 216,
                        't008/project-positioning-v1': 23}
assert len(probes) == 5
batch = new.data_collator(list(examples.values()))
assert set(batch['loss_scale'].unique().tolist()) == {0.0, 1.0, 3.0}
assert torch.equal(batch['labels'] != -100, batch['loss_scale'] > 0)

ev = json.loads((D / 'evaluation-config.json').read_text())
assert sha(ROOT / ev['chat_template']['path']) == ev['chat_template']['sha256']
assert sha(ROOT / ev['system_path']) == ev['system_sha256']
assert ev['request_modes']['nonthinking']['max_tokens'] == 2048
assert ev['request_modes']['thinking']['max_tokens'] == 4096
previous_loss_test = json.loads((LOSS3 / 'cpu-check/report.json').read_text())['native_loss_numeric_test']
report = {
    'verified': True, 'data_version': D.name, 'dataset_sha256': spec['dataset_sha256'],
    'rows': len(rows), 'actual_loader_rows': len(loaded), 'actual_pipeline_rows': len(encoded),
    'source_exposures': dict(counts), 'changed_rows_zero_based': sorted(changed),
    'unchanged_encoding_and_masks_rows': len(rows) - len(changed),
    'max_tokens': max(x['encoded_tokens'] for x in audit),
    'overlength_rows': 0, 'truncated_rows': 0, 'silent_dropped_rows': 0, 'empty_supervision_rows': 0,
    'source_supervised_tokens_before': dict(old_totals), 'source_supervised_tokens_after': dict(totals),
    'supervised_token_delta': sum(totals.values()) - sum(old_totals.values()),
    'five_short_thoughts_body_and_eos_supervised': True,
    'identity_thought_body_eos_weight': 3, 'positioning_thought_body_eos_weight': 1,
    'unchanged_rows_empty_think_and_prompt_masks_unchanged': True,
    'collator_preserves_0_1_3_weights': True,
    'normalization': 'sum(weight * token CE) / unweighted valid token count across accumulated microbatches',
    'normalization_source_hashes_equal_prior_verified_runtime': source_checks,
    'prior_numeric_loss_test_reused': previous_loss_test,
    'prior_numeric_loss_test_report': 'stage2/variants/identity-loss3-review/cpu-check/report.json',
    'versions': versions, 'tokenizer_config_sha256': reference['tokenizer_config_sha256'],
    'cpu_overrides': overrides, 'template_kwargs': args.get_template_kwargs(),
    'training_hyperparameters_unchanged': True,
    'evaluation_template_and_system_hashes_verified': True,
    'training_started': False, 'inference_executed': False, 'model_weights_loaded': False,
    'trainer_created': False, 'optimizer_created': False, 'gpu_available': False,
    'clearml_task_created': False,
}
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\n')
(OUT / 'row-checks.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in audit))
(OUT / 'mask-probes.json').write_text(json.dumps(probes, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['verified', 'rows', 'max_tokens', 'supervised_token_delta',
                                        'source_supervised_tokens_after', 'training_started']}), flush=True)
