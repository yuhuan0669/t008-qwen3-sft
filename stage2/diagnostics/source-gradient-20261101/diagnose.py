"""Full-corpus, fixed-weight source-gradient diagnosis; never optimizer.step/generate."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import importlib
import importlib.metadata as md
import inspect
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('TORCHINDUCTOR_CACHE_DIR', '/tmp/torchinductor_diag')
os.environ.setdefault('HF_HUB_OFFLINE', '1')
D = Path('/tmp/diag'); I = D / 'inputs'; O = D / 'results'; BASE = Path('/base')
O.mkdir(exist_ok=True)
def read(p): return json.loads(Path(p).read_text())
def lines(p): return [json.loads(s) for s in Path(p).read_text().splitlines()]
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        while b := f.read(8 * 1024 * 1024): h.update(b)
    return h.hexdigest()
def canonical(x): return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()
def digest(x): return hashlib.sha256(canonical(x)).hexdigest()
def save(n, x): (O / n).write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def append(n, x):
    with (O / n).open('a') as f: f.write(json.dumps(x, ensure_ascii=False, allow_nan=False) + '\n')
def log(x): print(json.dumps(x, ensure_ascii=False, allow_nan=False), flush=True)

def prepare():
    import torch
    from transformers import AutoTokenizer
    p = read(I / 'protocol.json'); ref = read(I / 'native-report.json')
    for n, m in read(I / 'manifest.json')['files'].items(): assert sha(I / n) == m['sha256'], n
    assert sha(I / 'train.jsonl') == p['dataset_sha256'] == ref['dataset_sha256']
    versions = {k: md.version(k) for k in p['versions']}; assert versions == p['versions'], versions
    for m in read(I / 'base-files.json'):
        f = BASE / m['path']; assert f.stat().st_size == m['size'] and sha(f) == m['sha256'], m['path']
    for a in p['adapters'].values():
        for name, meta in a['files'].items():
            f = Path(a['path']) / name
            assert f.stat().st_size == meta['bytes'] and sha(f) == meta['sha256'], str(f)
    sys.path.insert(0, str(I)); import identity_loss3
    from swift.model import get_processor
    from swift.template import get_template
    assert sha(I / 'identity_loss3.py') == ref['loss_plugin_sha256']
    assert sha(I / 'identity-keys.json') == ref['identity_key_binding_sha256']
    source_hashes = {}
    for name, expected in ref['normalization_source_hashes'].items():
        source_hashes[name] = sha(importlib.import_module(name).__file__)
        assert source_hashes[name] == expected, name
    tok = AutoTokenizer.from_pretrained(BASE, local_files_only=True)
    template = get_template(get_processor(str(BASE), model_type='qwen3', download_model=False), **ref['template_kwargs'])
    template.set_mode('train')
    rows = lines(I / 'train.jsonl'); checks = lines(I / 'native-row-checks.jsonl'); maps = lines(I / 'train-map.jsonl')
    assert len(rows) == len(checks) == len(maps) == p['all_exposures']
    by_source = {s: group for group, sources in p['groups'].items() for s in sources}
    stats = {g: Counter() for g in p['groups']}; unique = {}; enc_cache = {}
    for line, (row, check, mapping) in enumerate(zip(rows, checks, maps), 1):
        source = row['dataset']; group = by_source[source]; k = digest(row['messages'])
        if k not in enc_cache:
            enc = template.encode(deepcopy(row)); enc_cache[k] = {n: enc[n] for n in ['input_ids', 'labels', 'loss_scale']}
        enc = enc_cache[k]; ids, labels, weights = [enc[n] for n in ['input_ids', 'labels', 'loss_scale']]
        nvalid = sum(y != -100 for y in labels[1:]); units = sum(weights[1:])
        assert labels[0] == -100 and len(ids) == len(labels) == len(weights) <= 2048
        assert len(ids) == check['encoded_tokens'] and nvalid == check['supervised_tokens'] and units == check['weighted_token_units'], line
        assert nvalid > 0 and all(y == -100 or y == x for x, y in zip(ids, labels))
        assert all(w in [0., 1., 3.] for w in weights)
        assert not any(m['role'] == 'system' for m in row['messages'])
        key = digest([group, enc])
        if key not in unique:
            unique[key] = {**enc, 'key': key, 'group': group, 'source': source, 'lines': [],
                           'sample_ids': [], 'valid_tokens': nvalid, 'weighted_units': units}
        unique[key]['lines'].append(line)
        sample = mapping.get('sample_audit_id', check.get('sample_id'))
        if sample and sample not in unique[key]['sample_ids']: unique[key]['sample_ids'].append(sample)
        stats[group].update(rows=1, valid_tokens=nvalid, weighted_units=units)
    for g, n in p['expected_group_rows'].items(): assert stats[g]['rows'] == n
    assert sum(s['valid_tokens'] for s in stats.values()) == p['all_valid_tokens']
    assert sum(s['weighted_units'] for s in stats.values()) == p['all_weighted_units']
    training = list(unique.values())
    for r in training: r['multiplicity'] = len(r['lines'])
    for g in stats: stats[g]['unique_encodings'] = sum(r['group'] == g for r in training)
    chat = (I / 'thinking-prefill.jinja').read_text(); system = (I / 'system.txt').read_text()
    probes = []
    for item in read(I / 'probes.json')['probes']:
        for condition in p['probe_conditions']:
            messages = ([{'role': 'system', 'content': system}] if condition == 'system' else []) + [{'role': 'user', 'content': item['question']}]
            text = tok.apply_chat_template(messages, chat_template=chat, tokenize=False, add_generation_prompt=True, enable_thinking=False) + item['assistant_prefix']
            prefix = tok.encode(text, add_special_tokens=False)
            targets = []
            for name in ['bad_continuation', 'good_continuation']:
                full = tok.encode(text + item[name], add_special_tokens=False)
                assert full[:len(prefix)] == prefix, (item['id'], name, 'BPE boundary')
                targets.append(full[len(prefix):])
            bad, good = targets; common = 0
            while common < min(len(bad), len(good)) and bad[common] == good[common]: common += 1
            assert common < min(len(bad), len(good)), (item['id'], 'no divergent token')
            prefix += bad[:common]
            assert len(prefix) <= 2048 and bad[common] != good[common]
            probes.append({'id': item['id'] + '/' + condition, 'case_id': item['case_id'], 'category': item['category'],
                'condition': condition, 'prefix': prefix, 'prefix_sha256': digest(prefix), 'bad': bad[common], 'good': good[common],
                'bad_token': tok.decode([bad[common]]), 'good_token': tok.decode([good[common]]), 'common_target_tokens': common,
                'supplied_assistant_prefix': bool(item['assistant_prefix']), 'note': item['note']})
    assert len(probes) == p['probe_positions']
    save('encoded-training.json', training); save('encoded-probes.json', probes)
    report = {'verified': True, 'versions': versions, 'rows': len(rows), 'unique_encodings': len(training),
        'groups': stats, 'probes': len(probes), 'max_train_tokens': max(len(x['input_ids']) for x in training),
        'max_probe_tokens': max(len(x['prefix']) for x in probes), 'source_hashes_match': True,
        'native_masks_and_weights_match_all_rows': True, 'source_statistics': stats,
        'dataset_sha256': p['dataset_sha256'], 'system_sha256': sha(I / 'system.txt'),
        'template_sha256': sha(I / 'thinking-prefill.jinja'), 'input_manifest_sha256': sha(I / 'manifest.json'),
        'encoded_training_sha256': sha(O / 'encoded-training.json'), 'encoded_probes_sha256': sha(O / 'encoded-probes.json'),
        'optimizer_steps': 0, 'new_generated_answers': 0}
    save('encoding-check.json', report); log({'phase': 'encoded', **report})
    return p, training, probes, tok

def run(cpu_only=False):
    import torch
    import torch.nn.functional as F
    from torch.utils.checkpoint import checkpoint
    from transformers import AutoModelForCausalLM
    from peft import PeftModel
    from peft.utils.save_and_load import set_peft_model_state_dict
    from safetensors.torch import load_file
    from swift.trainers.seq2seq_trainer import per_token_loss_func
    started = time.monotonic(); p, records, probes, tok = prepare()
    if cpu_only: return
    assert torch.cuda.is_available()
    assert not (O / 'probe-effects.jsonl').exists(), 'Do not overwrite completed partial evidence'
    torch.set_num_threads(4); torch.manual_seed(42); torch.cuda.manual_seed_all(42)
    model = AutoModelForCausalLM.from_pretrained(BASE, local_files_only=True, dtype=torch.bfloat16,
        device_map={'': 0}, attn_implementation='sdpa')
    model = PeftModel.from_pretrained(model, p['adapters']['step50']['path'], is_trainable=True, local_files_only=True)
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    model.enable_input_require_grads()
    model.train()
    for module in model.modules():
        if isinstance(module, torch.nn.Dropout): module.eval()
    params = [(name, v) for name, v in model.named_parameters() if v.requires_grad]
    assert params and all('lora_' in n and v.dtype == torch.float32 for n, v in params)
    assert len(params) == 504 and sum(v.numel() for _, v in params) == 21823488
    assert all('lora_' in n or not v.requires_grad for n, v in model.named_parameters())
    names = [n for n, _ in params]; shapes = [list(v.shape) for _, v in params]
    save('parameter-map.json', {'names': names, 'shapes': shapes, 'count': len(params), 'numel': sum(v.numel() for _, v in params),
                              'name_order_sha256': digest(names), 'derivatives_only_lora': True})
    base = model.get_base_model()
    def param_hash():
        h = hashlib.sha256()
        for name, v in params: h.update(name.encode()); h.update(v.detach().cpu().contiguous().numpy().tobytes())
        return h.hexdigest()
    def grads():
        assert all(v.grad is not None for _, v in params)
        g = torch.cat([v.grad.detach().reshape(-1) for _, v in params])
        assert torch.isfinite(g).all(); return g
    def ce(row, dense=False):
        x = torch.tensor([row['input_ids']], device='cuda'); y = torch.tensor([row['labels']], device='cuda')
        w = torch.tensor([row['loss_scale']], device='cuda', dtype=torch.float32)
        if dense:
            out = model(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False)
            value = (per_token_loss_func(out, y) * torch.roll(w, -1, -1).reshape(-1)).sum() / row['valid_tokens']
            return value
        h = base.model(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False).last_hidden_state
        positions = (y[0, 1:] != -100).nonzero().reshape(-1)
        hidden = h[0, positions]; labels = y[0, positions + 1]; weights = w[0, positions + 1]
        def head_loss(hh, yy, ww):
            logits = base.lm_head(hh).float()
            return (F.cross_entropy(logits, yy, reduction='none') * ww).sum()
        total = torch.zeros((), device='cuda')
        for start in range(0, len(positions), 64):
            total = total + checkpoint(head_loss, hidden[start:start+64], labels[start:start+64], weights[start:start+64], use_reentrant=False)
        return total / row['valid_tokens']

    # Check native weighted CE and the memory-efficient head on actual examples.
    checks = []
    for group in ['general', 'identity', 'business']:
        row = min((r for r in records if r['group'] == group), key=lambda x: len(x['input_ids']))
        values = []; vectors = []
        for dense in [True, False]:
            model.zero_grad(set_to_none=True); loss = ce(row, dense=dense); loss.backward()
            values.append(float(loss.detach())); vectors.append(grads().cpu())
            del loss
        rel = float(torch.linalg.vector_norm(vectors[0] - vectors[1]) / torch.linalg.vector_norm(vectors[0]).clamp_min(1e-12))
        cos = float(F.cosine_similarity(vectors[0], vectors[1], dim=0))
        assert abs(values[0] - values[1]) < 2e-4 and rel < .025 and cos > .999, (group, values, rel, cos)
        checks.append({'group': group, 'line': row['lines'][0], 'native_ce': values[0], 'chunked_ce': values[1],
                       'gradient_relative_error': rel, 'gradient_cosine': cos})
        del vectors; model.zero_grad(set_to_none=True); torch.cuda.empty_cache()
    save('loss-gradient-check.json', {'verified': True, 'checks': checks, 'native_function': inspect.getfile(per_token_loss_func),
                                    'native_source_sha256': hashlib.sha256(inspect.getsource(per_token_loss_func).encode()).hexdigest()})
    log({'phase': 'native_gradient_verified', 'checks': checks})

    all_summaries = {}
    for arm in p['models']:
        adapter = p['adapters'][arm]
        if arm != 'step50':
            loaded = load_file(str(Path(adapter['path']) / 'adapter_model.safetensors'), device='cpu')
            result = set_peft_model_state_dict(model, loaded, adapter_name='default')
            assert not result.unexpected_keys
            assert not [k for k in result.missing_keys if 'lora_' in k], result.missing_keys
            del loaded
        before = param_hash(); model.zero_grad(set_to_none=True)
        opt = torch.load(Path(adapter['path']) / 'optimizer.pt', map_location='cpu', weights_only=True)
        assert len(opt['param_groups']) == 1
        pg = opt['param_groups'][0]; ids = pg['params']; assert ids == list(range(len(params))) and len(opt['state']) == len(params)
        step = int(opt['state'][0]['step'].item()); assert step == int(arm[4:])
        pre = []; momentum = []
        for i, (_, v) in enumerate(params):
            s = opt['state'][ids[i]]; assert s['exp_avg_sq'].shape == s['exp_avg'].shape == v.shape
            assert int(s['step'].item()) == step
            variance = s['exp_avg_sq'].reshape(-1) / (1. - pg['betas'][1] ** step)
            pre.append(1. / (variance.sqrt() + pg['eps']))
            momentum.append(s['exp_avg'].reshape(-1) / (1. - pg['betas'][0] ** step))
        pre = torch.cat(pre); momentum = torch.cat(momentum)
        assert torch.isfinite(pre).all() and (pre > 0).all()
        weights = torch.cat([v.detach().cpu().reshape(-1) for _, v in params])
        stored_direction = -(momentum * pre + pg['weight_decay'] * weights)
        del momentum, weights, opt
        save(arm + '-optimizer-map.json', {'step': step, 'parameter_order_sha256': digest(names), 'shape_matches': len(params),
            'optimizer': 'adamw_torch_fused', 'betas': pg['betas'], 'eps': pg['eps'], 'weight_decay': pg['weight_decay'],
            'saved_learning_rate': pg['lr'], 'mapping_basis': 'Native one-group named_parameters order, verified 504 state tensor shapes; no named slots were saved.',
            'preconditioner_bias_corrected': True, 'preconditioner_min': float(pre.min()), 'preconditioner_max': float(pre.max()),
            'not_actual_update': 'No optimizer constructed; fixed second-moment metric only. Final saved LR=0.'})
        qgrads = []; qmeta = []
        for index, probe in enumerate(probes, 1):
            model.zero_grad(set_to_none=True)
            x = torch.tensor([probe['prefix']], device='cuda')
            logits = model(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False, logits_to_keep=1).logits[0, -1].float()
            score = logits[probe['bad']] - logits[probe['good']]
            lp = logits.detach().log_softmax(-1)
            data = {k: probe[k] for k in ['id', 'case_id', 'category', 'condition', 'prefix_sha256', 'bad', 'good', 'bad_token', 'good_token', 'common_target_tokens', 'supplied_assistant_prefix']}
            data.update(model=arm, score=float(score.detach()), bad_probability=float(lp[probe['bad']].exp()),
                        good_probability=float(lp[probe['good']].exp()))
            score.backward(); g = grads().cpu(); qgrads.append(g); qmeta.append(data)
            data['probe_gradient_norm'] = float(g.double().norm()); append('probe-scores.jsonl', data)
            del score, logits, lp, g
            if index % 10 == 0: log({'phase': 'probe_gradients', 'model': arm, 'done': index, 'seconds': round(time.monotonic()-started, 1)})
        model.zero_grad(set_to_none=True); torch.cuda.empty_cache()
        # Per-record rankings use the same preregistered probe means, never select records by their results.
        family_indices = {family: [i for i, q in enumerate(qmeta) if q['category'] in cats] for family, cats in {
            'copy_loop': ['echo', 'body_loop'], 'identity': ['identity'], 'fact': ['fact'], 'normal_stop': ['normal']}.items()}
        mean_q = torch.stack([torch.stack([qgrads[i] for i in idx]).mean(0) for idx in family_indices.values()]).to('cuda')
        pre_gpu = pre.to('cuda')
        raw_sources = {}; source_meta = {}; processed = 0
        for group in p['groups']:
            aggregate = torch.zeros(sum(v.numel() for _, v in params), dtype=torch.float64, device='cuda')
            count = valid = 0; total_loss_sum = 0.; group_start = time.monotonic()
            for row in (r for r in records if r['group'] == group):
                model.zero_grad(set_to_none=True); loss = ce(row); loss.backward(); g = grads()
                coefficient = row['multiplicity'] * row['valid_tokens'] / p['all_valid_tokens']
                aggregate.add_(g.double(), alpha=coefficient)
                raw = -(mean_q @ g) * coefficient
                scaled = -(mean_q @ (g * pre_gpu)) * coefficient
                total_loss_sum += float(loss.detach()) * row['valid_tokens'] * row['multiplicity']
                count += row['multiplicity']; valid += row['valid_tokens'] * row['multiplicity']; processed += 1
                append('row-effects.jsonl', {'model': arm, 'key': row['key'], 'group': group, 'source': row['source'],
                    'lines': row['lines'], 'sample_ids': row['sample_ids'], 'multiplicity': row['multiplicity'],
                    'valid_tokens': row['valid_tokens'], 'weighted_ce_per_valid_token': float(loss.detach()),
                    'raw_effect': dict(zip(family_indices, raw.detach().cpu().tolist())),
                    'adam_scaled_effect': dict(zip(family_indices, scaled.detach().cpu().tolist()))})
                del loss, g, raw, scaled
                if processed % 25 == 0:
                    log({'phase': 'source_gradients', 'model': arm, 'group': group, 'unique_done': processed,
                         'unique_total': len(records), 'elapsed_seconds': round(time.monotonic()-started, 1),
                         'gpu_peak_gib': round(torch.cuda.max_memory_allocated()/2**30, 2)})
            raw_sources[group] = aggregate.cpu(); del aggregate
            source_meta[group] = {'rows': count, 'valid_tokens': valid, 'weighted_loss_sum': total_loss_sum,
                                  'mean_weighted_ce_per_valid_token': total_loss_sum / valid, 'seconds': time.monotonic()-group_start}
            log({'phase': 'source_group_complete', 'model': arm, 'group': group, **source_meta[group]})
        del mean_q, pre_gpu; model.zero_grad(set_to_none=True); torch.cuda.empty_cache()
        raw_sources['other'] = raw_sources['business'] + raw_sources['format']
        raw_sources['all'] = raw_sources['general'] + raw_sources['identity'] + raw_sources['other']
        geometry = {}; norms = {}
        for g, vector in raw_sources.items():
            scaled = vector * pre.double()
            norms[g] = {'raw_norm': float(vector.norm()), 'adam_scaled_norm': float(scaled.norm()),
                        'gradient_sha256': hashlib.sha256(vector.numpy().tobytes()).hexdigest()}
            for h, second in raw_sources.items():
                geometry[g + '/' + h] = {'raw_cosine': float(torch.dot(vector, second) / (vector.norm()*second.norm()).clamp_min(1e-30)),
                    'adam_metric_cosine': float(torch.dot(vector*pre.double(), second) /
                        (torch.dot(vector*pre.double(), vector).sqrt()*torch.dot(second*pre.double(), second).sqrt()).clamp_min(1e-30))}
            for q, grad in zip(qmeta, qgrads):
                qd = grad.double(); effect = -float(torch.dot(qd, vector)); aeffect = -float(torch.dot(qd, scaled))
                append('probe-effects.jsonl', {**q, 'source': g, 'raw_effect': effect, 'adam_scaled_effect': aeffect,
                    'raw_score_direction_cosine': -float(torch.dot(qd, vector)/(qd.norm()*vector.norm()).clamp_min(1e-30)),
                    'adam_score_direction_cosine': -float(torch.dot(qd, scaled)/(qd.norm()*scaled.norm()).clamp_min(1e-30))})
            del scaled
        for q, grad in zip(qmeta, qgrads):
            append('stored-optimizer-direction.jsonl', {**q, 'directional_score_change_per_lr': float(torch.dot(grad.double(), stored_direction.double())),
                   'saved_learning_rate': pg['lr'], 'not_future_update': True})
        after = param_hash(); assert before == after, 'Weights changed during derivative diagnosis'
        for name, meta in adapter['files'].items(): assert sha(Path(adapter['path'])/name) == meta['sha256']
        summary = {'source_losses': source_meta, 'gradient_norms': norms, 'source_gradient_geometry': geometry,
            'adapter_memory_sha256_before': before, 'adapter_memory_sha256_after': after, 'weights_unchanged': True,
            'optimizer_steps': 0, 'probe_gradients': len(probes), 'unique_source_gradients': processed,
            'all_exposures_accounted': sum(x['rows'] for x in source_meta.values()),
            'all_valid_tokens_accounted': sum(x['valid_tokens'] for x in source_meta.values())}
        assert summary['all_exposures_accounted'] == p['all_exposures'] and summary['all_valid_tokens_accounted'] == p['all_valid_tokens']
        save(arm + '-summary.json', summary); all_summaries[arm] = summary
        del qgrads, qmeta, raw_sources, stored_direction, pre
        log({'phase': 'checkpoint_complete', 'model': arm, 'seconds': round(time.monotonic()-started, 1)})
    files = {f.name: sha(f) for f in O.iterdir() if f.is_file() and f.name != 'completed.json'}
    save('completed.json', {'complete': True, 'checkpoints': p['models'], 'rows_each': p['all_exposures'],
        'unique_encodings_each': len(records), 'probe_gradients': len(probes)*len(p['models']),
        'source_gradients': len(records)*len(p['models']), 'elapsed_seconds': time.monotonic()-started,
        'gpu_peak_allocated_bytes': torch.cuda.max_memory_allocated(), 'files_sha256': files,
        'optimizer_steps': 0, 'new_generated_answers': 0, 'new_training_candidate': False, 'weights_unchanged': True})
    log({'phase': 'complete', 'seconds': round(time.monotonic()-started, 1)})

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--cpu-only', action='store_true'); args = parser.parse_args()
    run(args.cpu_only)
