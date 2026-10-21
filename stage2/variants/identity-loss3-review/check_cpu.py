"""Verify weights and native normalization on CPU; no model weights or Trainer instance."""
from pathlib import Path
from collections import Counter
from types import SimpleNamespace
import hashlib
import importlib.metadata as md
import json
import math
import torch
from transformers import HfArgumentParser, Trainer
from swift.arguments import SftArguments
from swift.model import get_processor
from swift.template import get_template
from swift.trainers.seq2seq_trainer import Seq2SeqTrainer

R = Path(__file__).resolve().parent
OUT = R / 'cpu-check'
OUT.mkdir(exist_ok=True)
spec = json.loads((R / 'training-config.json').read_text())
baseline_spec = json.loads((R / 'baseline-training-config.json').read_text())
assert not torch.cuda.is_available()
assert spec['execution_authorized'] is False


def arguments(cfg):
    argv = cfg['full_argv'][2:]
    argv = [s.replace('/work/stage2/variants/identity-loss3-review/', str(R) + '/')
            .replace('/work/', '/v018-input/') for s in argv]
    argv += ['--use_cpu', 'true', '--report_to', 'none', '--add_version', 'false',
             '--output_dir', str(OUT / 'args-only'), '--dataset_num_proc', '1']
    args, = HfArgumentParser(SftArguments).parse_args_into_dataclasses(argv)
    return args


old_args = arguments(baseline_spec)
new_args = arguments(spec)
from identity_loss3 import message_key
data = Path(new_args.dataset[0])
assert hashlib.sha256(data.read_bytes()).hexdigest() == spec['dataset_sha256']
rows = list(map(json.loads, data.read_text().splitlines()))
expected = Counter(message_key(r['messages']) for r in rows)
sources = {message_key(r['messages']): r['dataset'] for r in rows}
loaded, val = new_args.load_dataset()
assert Counter(message_key(r['messages']) for r in loaded) == expected
assert val is None or len(val) == 0
processor = get_processor('/base', model_type='qwen3', download_model=False)
old = get_template(processor, **old_args.get_template_kwargs())
new = get_template(processor, **new_args.get_template_kwargs())
old.set_mode('train')
new.set_mode('train')
assert new.loss_scale.is_binary_loss_scale is False
assert new.model_accepts_loss_kwargs is not False
totals = Counter()
counts = Counter()
checks = []
examples = {}
for row in loaded:
    source = sources[message_key(row['messages'])]
    a = old.encode(row)
    b = new.encode(row)
    assert a['input_ids'] == b['input_ids'] and a['labels'] == b['labels']
    assert len(b['input_ids']) <= 2048
    factor = 3.0 if source == 'swift/self-cognition' else 1.0
    mask = [y != -100 for y in a['labels']]
    assert b['loss_scale'] == [factor if active else 0.0 for active in mask], (source, message_key(row['messages']), sorted(set(b['loss_scale'])), [(i,x,y) for i,(x,y) in enumerate(zip(b['loss_scale'], mask)) if x != (factor if y else 0.0)][:10])
    counts[source] += 1
    totals[source] += sum(mask)
    examples.setdefault(source, b)
    checks.append({'message_sha256': message_key(row['messages']), 'source': source,
                   'supervised_tokens': sum(mask), 'factor': factor,
                   'input_ids_and_labels_unchanged': True})
assert dict(counts) == {'swift/Qwen3-SFT-Mixin': 1036, 'swift/self-cognition': 216,
                       't008/project-positioning-v1': 23}
assert sum(totals.values()) == 1528189 and totals['swift/self-cognition'] == 8084
batch = new.data_collator(list(examples.values()))
assert set(batch['loss_scale'].unique().tolist()) == {0.0, 1.0, 3.0}
assert torch.equal(batch['labels'] != -100, batch['loss_scale'] > 0)

# Exercise the installed Trainer's denominator and Swift's actual compute_loss,
# without constructing a Trainer, optimizer, or language model.
class FixedLogits(torch.nn.Module):
    model_info = SimpleNamespace(is_moe_model=False)

    def forward(self, input_ids, **kwargs):
        return SimpleNamespace(logits=torch.zeros(*input_ids.shape, 6), loss=None)


fake = FixedLogits().eval()
stub = SimpleNamespace(
    model=fake, template=new, model_accepts_loss_kwargs=True,
    compute_loss_func=None, label_smoother=None, _loss_shifts_labels=True,
    args=SimpleNamespace(enable_dft_loss=False, enable_channel_loss=False,
                         use_liger_kernel=False, past_index=-1, tuner_backend='peft',
                         average_tokens_across_devices=True, world_size=1, n_gpu=1),
    accelerator=SimpleNamespace(unwrap_model=lambda m: m, num_processes=1,
                                 parallelism_config=None),
    _compute_acc=lambda *a, **kw: None,
)


def microbatch(factor):
    return {'input_ids': torch.tensor([[0, 1, 2, 3, 4]]),
            'labels': torch.tensor([[-100, -100, 2, 3, 4]]),
            'loss_scale': torch.tensor([[0., 0., factor, factor, factor]])}


samples = [microbatch(3.), microbatch(1.)]
denom = Trainer._get_num_items_in_batch(stub, samples, torch.device('cpu'))
assert int(denom) == 6
with torch.inference_mode():
    old_id = Seq2SeqTrainer.compute_loss(stub, fake, microbatch(1.), num_items_in_batch=denom)
    new_id = Seq2SeqTrainer.compute_loss(stub, fake, microbatch(3.), num_items_in_batch=denom)
    general = Seq2SeqTrainer.compute_loss(stub, fake, microbatch(1.), num_items_in_batch=denom)
assert math.isclose(float(new_id / old_id), 3., rel_tol=1e-6)
assert math.isclose(float(old_id + general), math.log(6), rel_tol=1e-6)
assert math.isclose(float(new_id + general), 2 * math.log(6), rel_tol=1e-6)

report = {
    'verified': True, 'training_started': False, 'model_weights_loaded': False,
    'trainer_created': False, 'optimizer_created': False, 'backward_called': False,
    'gpu_available': False, 'rows': len(rows), 'source_exposures': dict(counts),
    'dataset_sha256': spec['dataset_sha256'], 'source_supervised_tokens': dict(totals),
    'all_input_ids_and_labels_unchanged': True, 'exposure_counter_unchanged': True,
    'weighted_rows': 216, 'weighted_supervised_tokens': 8084,
    'other_supervised_tokens_weight_one': sum(totals.values()) - 8084,
    'empty_think_and_prompt_mask_unchanged': True,
    'collator_preserves_0_1_3_weights': True,
    'binary_loss_scale': new.loss_scale.is_binary_loss_scale,
    'template_model_accepts_loss_kwargs': new.model_accepts_loss_kwargs,
    'native_loss_numeric_test': {
        'valid_token_denominator': int(denom), 'weighted_token_sum': 12,
        'old_identity_loss': float(old_id), 'new_identity_loss': float(new_id),
        'general_loss_unchanged': float(general), 'identity_ratio': float(new_id / old_id),
        'baseline_total': float(old_id + general), 'weighted_total': float(new_id + general),
        'normalization': 'sum(weight * token CE) / unweighted valid token count across accumulated microbatches',
    },
    'versions': {k: md.version(k) for k in ['ms-swift', 'transformers', 'peft', 'torch']},
}
(OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
(OUT / 'row-checks.jsonl').write_text(''.join(json.dumps(x) + '\n' for x in checks))
print(json.dumps(report, ensure_ascii=False), flush=True)
