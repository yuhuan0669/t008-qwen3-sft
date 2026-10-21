"""Native CPU data preparation only: no model weights, Trainer, optimizer or backward."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import importlib
import importlib.metadata as md
import json
import math
import re

import torch
from transformers import HfArgumentParser
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.pipelines.train.sft import SwiftSft

OUT = Path(__file__).resolve().parent
D = OUT.parent
ROOT = D.parents[2]
PARENT = D.parent / 'stage1-cpu-v0.1.11'
TRAINED = D.parent / 'stage1-cpu-v0.1.10'
LOSS3 = ROOT / 'stage2/variants/identity-loss3-review'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())
spec = read(D / 'training-config.json')
reference = read(TRAINED / 'cpu-check/report.json')
assert not torch.cuda.is_available() and not list(Path('/dev').glob('nvidia*'))
assert not spec['execution_authorized']
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
source_hashes = {}
for name in ['transformers.trainer', 'swift.trainers.seq2seq_trainer', 'swift.loss_scale.base',
             'swift.loss_scale.mapping', 'swift.loss_scale.other', 'swift.template.base',
             'swift.template.templates.qwen']:
    actual = Path(importlib.import_module(name).__file__)
    frozen = LOSS3 / 'source' / (name.replace('.', '/') + '.py')
    assert sha(actual) == sha(frozen), name
    source_hashes[name] = sha(actual)

from identity_loss3 import message_key
rows = [json.loads(x) for x in (D / 'train.jsonl').read_text().splitlines()]
parent_rows = [json.loads(x) for x in (PARENT / 'train.jsonl').read_text().splitlines()]
lineage = [json.loads(x) for x in (D / 'train-map.jsonl').read_text().splitlines()]
changed = {x['row_zero_based'] for x in lineage if x['operation'] != 'preserve'}
assert len(rows) == 1315 and len(parent_rows) == 1275 and len(changed) == 44
expected = Counter(message_key(r['messages']) for r in rows)
loaded, val = args.load_dataset()
assert Counter(message_key(r['messages']) for r in loaded) == expected
assert val is None or len(val) == 0
processor = get_processor('/base', model_type='qwen3', download_model=False)
new, old, unbounded = [get_template(processor, **args.get_template_kwargs()) for _ in range(3)]
for template in [new, old, unbounded]:
    template.set_mode('train')
old.loss_scale.identity_keys = frozenset(read(PARENT / 'identity-keys.json')['identity_message_sha256'])
unbounded.max_length = None
assert old.loss_scale is not new.loss_scale and new.loss_scale.is_binary_loss_scale is False


class PreparationOnly:
    def _save_val_dataset(self, value):
        assert value is None or len(value) == 0


stub = PreparationOnly()
stub.args, stub.template = args, new
encoded, val = SwiftSft._encode_dataset(stub, loaded, val)
assert Counter(message_key(r['messages']) for r in encoded) == expected
assert len(encoded) == 1315

# Observe the exact messages received by the unchanged loss plug-in after native
# template preprocessing. The observer returns the original result unmodified.
loss_class = type(new.loss_scale)
original_call = loss_class.__call__
traces = {}


def observed_call(self, contexts, context_types, messages, **kwargs):
    traces[id(self)] = deepcopy(messages)
    return original_call(self, contexts, context_types, messages, **kwargs)


loss_class.__call__ = observed_call
cache_new, cache_old = {}, {}
audit, probes, mismatches = [], [], []
totals, prior_totals, counts = Counter(), Counter(), Counter()
weighted, groups, weighted_groups = Counter(), Counter(), Counter()
language_tokens = Counter()
examples = {}
identity_sources = {'swift/self-cognition', 't008/company-facts-v1', 't008/chinese-identity-v1'}
positioning_sources = {'t008/project-positioning-v1', 't008/business-evidence-v1'}


def group(source):
    return 'identity' if source in identity_sources else 'positioning' if source in positioning_sources else 'generic'


for i, row in enumerate(rows):
    nk = message_key(row['messages'])
    if nk not in cache_new:
        value = new.encode(deepcopy(row))
        prepared_messages = deepcopy(traces[id(new.loss_scale)])
        ub = unbounded.encode(deepcopy(row))
        assert all(value[k] == ub[k] for k in ['input_ids', 'labels', 'loss_scale']), (i, 'truncation')
        assert len(value['input_ids']) <= 2048
        assert any(y != -100 for y in value['labels'])
        assert all(y == -100 or x == y for x, y in zip(value['input_ids'], value['labels']))
        cache_new[nk] = value, prepared_messages
    b, prepared_messages = cache_new[nk]
    previous = None
    if i < len(parent_rows):
        parent_row = parent_rows[i]
        ok = message_key(parent_row['messages'])
        if ok not in cache_old:
            cache_old[ok] = old.encode(deepcopy(parent_row))
        previous = cache_old[ok]
        prior_totals[parent_row['dataset']] += sum(y != -100 for y in previous['labels'])
        if i not in changed:
            assert all(previous[k] == b[k] for k in ['input_ids', 'labels', 'loss_scale']), i
    source = row['dataset']
    expected_factor = 3.0 if source in identity_sources else 1.0
    expected_weights = [expected_factor if y != -100 else 0.0 for y in b['labels']]
    if b['loss_scale'] != expected_weights:
        mismatches.append({'row_zero_based': i, 'line_one_based': i + 1, 'source': source,
                           'expected_factor': expected_factor, 'actual_nonzero_weights': sorted(set(b['loss_scale']) - {0.0}),
                           'raw_messages_sha256': nk,
                           'prepared_messages_sha256': message_key(prepared_messages),
                           'prepared_messages': prepared_messages})
    tokens = sum(y != -100 for y in b['labels'])
    weight_sum = sum(b['loss_scale'])
    assert all(w == 0 if y == -100 else w > 0 for w, y in zip(b['loss_scale'], b['labels']))
    totals[source] += tokens
    weighted[source] += weight_sum
    groups[group(source)] += tokens
    weighted_groups[group(source)] += weight_sum
    counts[source] += 1
    if source in identity_sources:
        lang = 'chinese_question' if re.search(r'[\u4e00-\u9fff]', row['messages'][0]['content']) else 'english_question'
        language_tokens[lang] += tokens
    examples.setdefault(source, b)
    audit.append({'row_zero_based': i, 'source': source, 'group': group(source),
                  'operation': lineage[i]['operation'], 'encoded_tokens': len(b['input_ids']),
                  'supervised_tokens': tokens, 'weighted_supervised_token_units': weight_sum,
                  'expected_factor': expected_factor, 'weight_verified': b['loss_scale'] == expected_weights,
                  'parent_supervised_tokens': sum(y != -100 for y in previous['labels']) if previous else None,
                  'prepared_messages_sha256': message_key(prepared_messages),
                  'unchanged_encoding_and_masks': i not in changed})
    if i in changed:
        text = processor.decode([x for x, y in zip(b['input_ids'], b['labels']) if y != -100])
        turn_checks = []
        for j, m in enumerate(row['messages']):
            if m['role'] != 'assistant':
                assert m['content'] not in text, (i, j, 'prompt leaked into supervision')
                continue
            thought = re.search(r'<think>(.*?)</think>', m['content'], re.S)[1].strip()
            body = m['content'].split('</think>', 1)[1].strip()
            assert body in text, (i, j, 'visible answer missing')
            thought_supervised = bool(thought and thought in text)
            if j == len(row['messages']) - 1 and thought:
                assert thought_supervised, (i, 'final thought missing')
            turn_checks.append({'message_index': j, 'body_supervised': True,
                                'nonempty_thought_in_source': bool(thought),
                                'nonempty_thought_supervised': thought_supervised,
                                'history_thought_removed_by_native_template': bool(thought and not thought_supervised)})
        assert '<|im_end|>' in text
        assert not re.search(r'<think>\s*</think>', text), (i, 'empty think supervised')
        probes.append({'row_zero_based': i, 'line_one_based': i + 1, 'source': source,
                       'expected_factor': expected_factor, 'weight_verified': b['loss_scale'] == expected_weights,
                       'turn_checks': turn_checks, 'supervised_text': text,
                       'prepared_messages': prepared_messages, 'input_ids': b['input_ids'],
                       'labels': b['labels'], 'loss_scale': b['loss_scale']})
loss_class.__call__ = original_call
assert dict(counts) == read(D / 'statistics.json')['after']['source_exposures']
assert len(probes) == 44
batch = new.data_collator(list(examples.values()))
assert set(batch['loss_scale'].unique().tolist()) == {0.0, 1.0, 3.0}
assert torch.equal(batch['labels'] != -100, batch['loss_scale'] > 0)
ev = read(D / 'evaluation-config.json')
assert sha(ROOT / ev['chat_template']['path']) == ev['chat_template']['sha256']
assert sha(ROOT / ev['system_path']) == ev['system_sha256']
assert ev['request_modes']['nonthinking']['max_tokens'] == 2048
assert ev['request_modes']['thinking']['max_tokens'] == 4096
prior_groups = Counter()
for source, count in prior_totals.items():
    prior_groups[group(source)] += count
prior_weighted_groups = {g: v * (3 if g == 'identity' else 1) for g, v in prior_groups.items()}
lengths = sorted(x['encoded_tokens'] for x in audit)
report = {
    'verified': not mismatches, 'data_version': D.name, 'dataset_sha256': spec['dataset_sha256'],
    'rows': len(rows), 'actual_loader_rows': len(loaded), 'actual_pipeline_rows': len(encoded),
    'source_exposures': dict(counts), 'restored_rows': 4, 'added_rows': 40,
    'unchanged_encoding_and_masks_rows': 1271,
    'max_tokens': max(lengths), 'p99_tokens': lengths[math.ceil(.99 * len(lengths)) - 1],
    'overlength_rows': 0, 'truncated_rows': 0, 'silent_dropped_rows': 0, 'empty_supervision_rows': 0,
    'source_supervised_tokens_before': dict(prior_totals), 'source_supervised_tokens_after': dict(totals),
    'group_supervised_tokens_before': dict(prior_groups), 'group_supervised_tokens_after': dict(groups),
    'source_weighted_supervised_token_units_after': dict(weighted),
    'group_weighted_supervised_token_units_after': dict(weighted_groups),
    'total_supervised_tokens': sum(totals.values()), 'total_weighted_token_units': sum(weighted.values()),
    'identity_supervised_share_before': prior_groups['identity'] / sum(prior_groups.values()),
    'identity_supervised_share_after': groups['identity'] / sum(groups.values()),
    'identity_weighted_token_share_before': prior_weighted_groups['identity'] / sum(prior_weighted_groups.values()),
    'identity_weighted_token_share_after': weighted_groups['identity'] / sum(weighted_groups.values()),
    'identity_language_supervised_tokens_after': dict(language_tokens),
    'weighted_share_note': 'Token units after loss scaling, not measured loss or gradient contribution.',
    'weight_mismatch_rows': len(mismatches), 'all_236_identity_exposures_weight3': not mismatches,
    'new_multiturn_history_thoughts_removed': sum(t['history_thought_removed_by_native_template'] for p in probes for t in p['turn_checks']),
    'all_changed_visible_answers_supervised': True, 'prompt_and_empty_think_masked': True,
    'collator_preserves_0_1_3_weights': True,
    'normalization': reference['normalization'], 'normalization_source_hashes': source_hashes,
    'prior_numeric_loss_test_reused': reference['prior_numeric_loss_test_reused'],
    'prior_numeric_loss_test_report': 'stage2/variants/identity-loss3-review/cpu-check/report.json',
    'versions': versions, 'tokenizer_config_sha256': reference['tokenizer_config_sha256'],
    'cpu_overrides': overrides, 'template_kwargs': args.get_template_kwargs(),
    'training_hyperparameters_unchanged': True, 'estimated_full_optimizer_steps': math.ceil(len(encoded) / 16),
    'evaluation_template_and_system_hashes_verified': True,
    'training_started': False, 'inference_executed': False, 'model_weights_loaded': False,
    'trainer_created': False, 'optimizer_created': False, 'backward_called': False,
    'gpu_available': False, 'clearml_task_created': False,
}
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\n')
(OUT / 'row-checks.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in audit))
(OUT / 'mask-probes.json').write_text(json.dumps(probes, ensure_ascii=False, indent=2) + '\n')
(OUT / 'weight-mismatches.json').write_text(json.dumps(mismatches, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['verified', 'rows', 'max_tokens', 'weight_mismatch_rows',
                                       'group_supervised_tokens_after', 'training_started']}), flush=True)
