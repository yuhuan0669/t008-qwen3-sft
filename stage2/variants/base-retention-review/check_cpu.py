"""Native encoding and tiny synthetic loss checks; no 8B weights or optimizer."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.metadata as md
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import torch
from torch.nn import functional as F
from transformers import Qwen3Config, Qwen3ForCausalLM, Trainer
from peft import LoraConfig, get_peft_model
from swift.model import get_processor
from swift.template import get_template
from swift.trainers.seq2seq_trainer import Seq2SeqTrainer

from retention import base_reference, kl_sum, make_compute_loss, token_key, install

D = Path(__file__).resolve().parent
I = D / 'inputs'
sys.path.insert(0, str(I))
import identity_loss3  # Registers the unchanged frozen identity weighting.


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def save(p, x):
    p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')


def main():
    assert not torch.cuda.is_available() and not list(Path('/dev').glob('nvidia*'))
    ref = read(I / 'report.json')
    versions = {n: md.version(n) for n in ['ms-swift', 'transformers', 'peft', 'torch']}
    assert all(ref['versions'][n] == v for n, v in versions.items())
    assert sha(I / 'train.jsonl') == ref['dataset_sha256']
    assert sha(I / 'identity_loss3.py') == ref['loss_plugin_sha256']
    assert sha(I / 'identity-keys.json') == ref['identity_key_binding_sha256']
    for name, h in ref['tokenizer_config_sha256'].items():
        assert sha(Path('/base') / name) == h
    processor = get_processor('/base', model_type='qwen3', download_model=False)
    template = get_template(processor, **ref['template_kwargs'])
    template.set_mode('train')
    rows = [json.loads(s) for s in (I / 'train.jsonl').read_text().splitlines()]
    old_rows = [json.loads(s) for s in (I / 'row-checks.jsonl').read_text().splitlines()]
    allow = {'swift/Qwen3-SFT-Mixin', 't008/general-nonthinking-v1',
             't008/general-nonthinking-v2', 't008/strict-json-v1'}
    members, counts, totals = {}, Counter(), Counter()
    for line, (row, old) in enumerate(zip(rows, old_rows), 1):
        enc = template.encode(deepcopy(row))
        assert len(enc['input_ids']) == old['encoded_tokens'] <= 2048
        assert sum(x != -100 for x in enc['labels']) == old['supervised_tokens']
        assert sum(enc['loss_scale']) == old['weighted_token_units']
        key = token_key(enc['input_ids'])
        retained = row['dataset'] in allow
        if key in members:
            assert members[key]['retain'] == retained
        else:
            members[key] = {'retain': retained, 'source': row['dataset'], 'lines': []}
        members[key]['lines'].append(line)
        counts[row['dataset']] += 1
        if retained:
            assert all(w in [0., 1.] for w in enc['loss_scale'])
            totals['retention_rows'] += 1
            totals['retention_tokens'] += sum(x != -100 for x in enc['labels'][1:])
        totals['rows'] += 1
        totals['supervised_tokens'] += sum(x != -100 for x in enc['labels'][1:])
        totals['weighted_units'] += sum(enc['loss_scale'][1:])
    assert len(rows) == len(old_rows) == totals['rows'] == 1047
    assert totals['retention_rows'] == 770 and totals['retention_tokens'] == 917954
    assert totals['supervised_tokens'] == 928890 and totals['weighted_units'] == 946600
    save(D / 'membership.json', {'dataset_sha256': sha(I / 'train.jsonl'),
                                'sources': sorted(allow), 'members': members})

    # Compare exact full-vocabulary KL and gradients against an independent dense expression.
    torch.manual_seed(12)
    a = torch.randn(2, 7, 19, requires_grad=True)
    b = torch.randn(2, 7, 19)
    mask = torch.tensor([[False, True, True, False, True, False, True],
                         [True, False, True, True, False, True, False]])
    chunked = kl_sum(a, b, mask, 2)
    dense = F.kl_div(F.log_softmax(a[mask], -1), F.softmax(b[mask], -1), reduction='sum')
    ga, = torch.autograd.grad(chunked, a, retain_graph=True)
    gd, = torch.autograd.grad(dense, a)
    assert torch.allclose(chunked, dense, atol=2e-6)
    assert torch.allclose(ga, gd, atol=2e-7) and not bool(ga[~mask].any())
    equal = kl_sum(b, b, mask, 2)
    assert abs(float(equal)) < 1e-6

    # Actual installed Swift compute_loss with a tiny random Qwen3+PEFT model.
    # No pretrained weights, training loop or optimizer is created.
    torch.manual_seed(42)
    base = Qwen3ForCausalLM(Qwen3Config(vocab_size=37, hidden_size=16,
        intermediate_size=32, num_hidden_layers=2, num_attention_heads=2,
        num_key_value_heads=1, head_dim=8, max_position_embeddings=64))
    model = get_peft_model(base, LoraConfig(r=2, lora_alpha=4, lora_dropout=.05,
                          target_modules='all-linear', task_type='CAUSAL_LM'))
    model.model_info = SimpleNamespace(is_moe_model=False)
    with torch.no_grad():
        for name, p in model.named_parameters():
            if 'lora_B' in name:
                p.normal_(0, .03)
    model.train()
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    stub = SimpleNamespace(model=model, template=template, model_accepts_loss_kwargs=True,
        compute_loss_func=None, label_smoother=None, _loss_shifts_labels=True,
        args=SimpleNamespace(enable_dft_loss=False, enable_channel_loss=False,
            use_liger_kernel=False, past_index=-1, tuner_backend='peft',
            average_tokens_across_devices=True, world_size=1, n_gpu=1),
        accelerator=SimpleNamespace(unwrap_model=lambda m: m, num_processes=1,
                                    parallelism_config=None),
        _compute_acc=lambda *args, **kw: None)

    def batch(identity=False):
        offset = 10 if identity else 0
        return {'input_ids': torch.tensor([[2, 3, 4, 5, 6]]) + offset,
                'attention_mask': torch.ones(1, 5, dtype=torch.long),
                'labels': torch.tensor([[-100, -100, 4 + offset, 5 + offset, 6 + offset]]),
                'loss_scale': torch.tensor([[0., 0., 3., 3., 3.]]) if identity
                              else torch.tensor([[0., 0., 1., 1., 1.]])}

    toy_members = {token_key(batch(i)['input_ids'][0].tolist()): {'retain': not i}
                   for i in [False, True]}
    cfg = {'coefficient': 1., 'temperature': 1, 'direction': 'KL(base || adapted)', 'chunk_tokens': 2}
    native = Seq2SeqTrainer.compute_loss
    wrapped = make_compute_loss(native, cfg, toy_members)
    zero = make_compute_loss(native, dict(cfg, coefficient=0), toy_members)
    denominator = Trainer._get_num_items_in_batch(stub, [batch(), batch(True)], torch.device('cpu'))
    assert int(denominator) == 6

    def value(fn, identity=False, selected=False):
        data = batch(identity)
        if selected:
            Seq2SeqTrainer.prepare_logits_to_keep(stub, data)
        torch.manual_seed(99)
        return fn(stub, model, data, True, denominator)

    baseline, _ = value(native)
    zero_loss, _ = value(zero)
    id_before, _ = value(native, True)
    id_after, _ = value(wrapped, True)
    assert torch.equal(baseline, zero_loss) and torch.equal(id_before, id_after)
    modes = [m.training for m in model.modules()]
    requires = [p.requires_grad for p in model.parameters()]
    rng = torch.get_rng_state()
    with base_reference(model):
        teacher = model(input_ids=batch()['input_ids'], attention_mask=batch()['attention_mask'],
                        use_cache=False).logits
    assert torch.equal(rng, torch.get_rng_state())
    assert modes == [m.training for m in model.modules()]
    assert requires == [p.requires_grad for p in model.parameters()]
    total, output = value(wrapped)
    raw = kl_sum(output.logits[:, :-1], teacher[:, :-1], batch()['labels'][:, 1:] != -100, 2)
    assert float(raw.detach()) > 0
    assert torch.allclose(total, baseline + raw / denominator, atol=1e-7)
    selected, _ = value(wrapped, selected=True)
    assert torch.allclose(total, selected, atol=1e-7), (total, selected)
    total.backward()
    assert all(p.grad is None for n, p in model.named_parameters() if 'lora_' not in n)
    assert any(p.grad is not None and bool(p.grad.any()) for n, p in model.named_parameters() if 'lora_' in n)
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    assert modes == [m.training for m in model.modules()]
    source = Path(inspect.getfile(Seq2SeqTrainer))
    config = {**cfg, 'chunk_tokens': 32, 'runtime_versions': versions,
        'native_trainer_sha256': sha(source), 'membership_file': 'membership.json',
        'membership_sha256': sha(D / 'membership.json'), 'dataset_sha256': sha(I / 'train.jsonl'),
        'scope': 'Frozen general sources only; unchanged native CE elsewhere',
        'execution_authorized': False}
    save(D / 'retention-config.json', config)
    install(D / 'retention-config.json')
    assert getattr(Seq2SeqTrainer.compute_loss, '_t008_retention', False)
    Seq2SeqTrainer.compute_loss = native
    report = {'verified': True, 'runtime_versions': versions, 'native_trainer_sha256': sha(source),
        'dataset_sha256': sha(I / 'train.jsonl'), 'sources': dict(counts), 'totals': dict(totals),
        'native_encoded_rows_checked': 1047, 'native_lengths_and_supervision_match_frozen_report': True,
        'kl_matches_dense': True, 'kl_gradient_matches_dense': True,
        'masked_token_gradient_zero': True, 'identical_distribution_kl_zero': True,
        'lambda_zero_native_ce_bitwise_equal': True, 'identity_ce_bitwise_equal': True,
        'accumulation_denominator_unweighted': int(denominator),
        'native_logits_to_keep_equivalent': True, 'teacher_no_gradient': True,
        'teacher_preserves_rng_and_modes': True, 'only_lora_gradients': True,
        'gradient_checkpointing_checked': True, 'toy_backward_called': True,
        'plugin_install_with_version_and_binding_checks': True,
        'real_model_weights_loaded': False, 'real_training_started': False,
        'optimizer_created': False, 'gpu_available': False, 'uat_restored': False,
        'example_native_loss': float(baseline.detach()), 'example_kl_sum': float(raw.detach()),
        'example_total_loss': float(total.detach()),
        'membership_sha256': sha(D / 'membership.json'), 'plugin_sha256': sha(D / 'retention.py')}
    save(D / 'CPU_CHECK.json', report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
