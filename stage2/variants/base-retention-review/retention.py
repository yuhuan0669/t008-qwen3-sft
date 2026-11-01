"""Selective frozen-base KL added to native Swift SFT; single-GPU, batch-one scope."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path

import torch
from torch.nn import functional as F
from torch.utils.checkpoint import checkpoint


def token_key(ids):
    return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()


@contextmanager
def base_reference(model):
    # Base weights remain frozen. Restore mixed submodule training flags exactly.
    flags = [(m, m.training) for m in model.modules()]
    try:
        model.eval()
        with model.disable_adapter(), torch.no_grad():
            yield
    finally:
        for module, flag in flags:
            module.training = flag


def kl_sum(student, teacher, valid, chunk_tokens=32):
    """Exact full-vocabulary forward KL, T=1; masked tokens contribute no gradient."""
    assert student.shape == teacher.shape and student.shape[:-1] == valid.shape
    assert not teacher.requires_grad
    s = student.reshape(-1, student.shape[-1])
    t = teacher.reshape(-1, teacher.shape[-1])
    mask = valid.reshape(-1)
    total = student.new_zeros((), dtype=torch.float32)

    def part(a, b, m):
        log_s = F.log_softmax(a[m].float(), dim=-1)
        log_t = F.log_softmax(b[m].float(), dim=-1)
        return (log_t.exp() * (log_t - log_s)).sum()

    for start in range(0, len(mask), chunk_tokens):
        stop = start + chunk_tokens
        m = mask[start:stop]
        if not bool(m.any()):
            continue
        values = (s[start:stop], t[start:stop], m)
        # Recompute loss intermediates during backward instead of retaining
        # several full-vocabulary FP32 distributions for the entire sequence.
        value = checkpoint(part, *values, use_reentrant=False,
                           preserve_rng_state=False) if s.requires_grad else part(*values)
        total = total + value
    return total


def make_compute_loss(native, config, members):
    coefficient = float(config['coefficient'])
    assert coefficient >= 0 and config['temperature'] == 1
    assert config['direction'] == 'KL(base || adapted)'

    def compute(self, model, inputs, return_outputs=False, num_items_in_batch=None):
        if coefficient == 0:
            return native(self, model, inputs, return_outputs, num_items_in_batch)
        assert self.accelerator.num_processes == 1
        assert self.template.sequence_parallel_size == 1 and not self.template.padding_free
        assert not getattr(self.template, 'packing', False)
        assert inputs.get('compute_loss_func') is None and self.label_smoother is None
        assert inputs['input_ids'].shape[0] == 1
        ids = inputs['input_ids'][0]
        if 'attention_mask' in inputs:
            assert inputs['attention_mask'].ndim == 2
            ids = ids[inputs['attention_mask'][0].bool()]
        key = token_key(ids.detach().cpu().tolist())
        if key not in members:
            raise ValueError('Encoded row absent from frozen retention membership')
        if not members[key]['retain']:
            return native(self, model, inputs, return_outputs, num_items_in_batch)

        unwrapped = self.accelerator.unwrap_model(model)
        from peft import PeftModel
        assert isinstance(unwrapped, PeftModel), 'Reference requires a PEFT adapter over frozen base'
        assert all('lora_' in n for n, p in unwrapped.named_parameters() if p.requires_grad)
        labels = inputs['labels']
        valid = labels[:, 1:] != -100
        denominator = num_items_in_batch if num_items_in_batch is not None else valid.sum()
        assert int(denominator) > 0 and bool(valid.any())
        ignored = {'labels', 'loss_scale', 'compute_loss_func', 'channel', 'text_position_ids'}
        teacher_inputs = {k: v for k, v in inputs.items() if k not in ignored}
        teacher_inputs['use_cache'] = False
        with base_reference(unwrapped):
            teacher = unwrapped(**teacher_inputs).logits
        loss, outputs = native(self, model, inputs, True, num_items_in_batch)
        student = outputs.logits
        assert student.shape == teacher.shape
        assert student.shape[:2] == labels.shape, 'Native logits/labels selection must align'
        penalty_sum = kl_sum(student[:, :-1], teacher[:, :-1], valid,
                             config['chunk_tokens'])
        penalty = coefficient * penalty_sum / denominator
        metrics = getattr(self, 'custom_metrics', None)
        if metrics is not None:
            mode = 'train' if self.model.training else 'eval'
            metrics[mode]['sft_loss_accum_scaled'].update(loss.detach())
            metrics[mode]['retention_loss_accum_scaled'].update(penalty.detach())
            metrics[mode]['retention_kl_general_microbatch_mean'].update(
                penalty_sum.detach() / valid.sum())
        total = loss + penalty
        return (total, outputs) if return_outputs else total

    return compute


def install(config_path):
    import importlib.metadata as md
    import inspect
    from swift.trainers.seq2seq_trainer import Seq2SeqTrainer
    path = Path(config_path)
    config = json.loads(path.read_text())
    for name, version in config['runtime_versions'].items():
        assert md.version(name) == version, name
    source = Path(inspect.getfile(Seq2SeqTrainer))
    assert hashlib.sha256(source.read_bytes()).hexdigest() == config['native_trainer_sha256']
    binding = path.parent / config['membership_file']
    assert hashlib.sha256(binding.read_bytes()).hexdigest() == config['membership_sha256']
    assert not getattr(Seq2SeqTrainer.compute_loss, '_t008_retention', False)
    wrapped = make_compute_loss(Seq2SeqTrainer.compute_loss, config,
                                json.loads(binding.read_text())['members'])
    wrapped._t008_retention = True
    Seq2SeqTrainer.compute_loss = wrapped


# Only the proposed run sets this environment variable and loads this plugin.
if os.environ.get('T008_RETENTION_CONFIG'):
    install(os.environ['T008_RETENTION_CONFIG'])
