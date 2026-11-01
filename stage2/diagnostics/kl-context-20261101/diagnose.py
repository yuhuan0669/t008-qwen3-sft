"""Fixed-prefix distribution diagnosis. No generation, backward or optimizer."""
import argparse
import ast
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import importlib.metadata as md
import json
import math
import os
from pathlib import Path
import sys
import time

os.environ.setdefault('TORCHINDUCTOR_CACHE_DIR', '/tmp/torchinductor_diag')
D = Path('/tmp/diag'); I = D / 'inputs'; O = D / 'results'; BASE = Path('/base')
O.mkdir(exist_ok=True)
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        while b := f.read(8 * 1024 * 1024): h.update(b)
    return h.hexdigest()
def ih(ids): return hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest()
def save(n, x): (O / n).write_text(json.dumps(x, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def append(n, x):
    with (O / n).open('a') as f: f.write(json.dumps(x, ensure_ascii=False, allow_nan=False) + '\n')

def load_filter(torch):
    tree = ast.parse((I / 'vllm_topk_topp_source.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'apply_top_k_top_p_pytorch')
    ns = {'torch': torch}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<frozen-vllm-filter>', 'exec'), ns)
    fn = ns[node.name]
    assert torch.isfinite(fn(torch.tensor([[4., 3., 2., 1.]]), torch.tensor([2]), torch.tensor([.8]))).tolist() == [[True, True, False, False]]
    return fn

def prepare():
    import torch
    from transformers import AutoTokenizer
    p = read(I / 'protocol.json')
    for n, m in read(I / 'manifest.json')['files'].items(): assert sha(I / n) == m['sha256'], n
    versions = {k: md.version(k) for k in p['versions']}
    assert versions == p['versions'], versions
    for m in read(I / 'base-files.json'):
        f = BASE / m['path']
        assert f.stat().st_size == m['size'] and sha(f) == m['sha256'], m['path']
    for arm, adapter in p['adapters'].items():
        for name, meta in adapter['files'].items():
            f = Path(adapter['path']) / name
            assert f.stat().st_size == meta['bytes'] and sha(f) == meta['sha256'], (arm, name)
    tok = AutoTokenizer.from_pretrained(BASE, local_files_only=True)
    chat = (I / 'thinking-prefill.jinja').read_text(); system = (I / 'system.txt').read_text()
    groups = []
    for c in read(I / 'cases.json')['cases']:
        for use_system in [False, True]:
            messages = ([{'role': 'system', 'content': system}] if use_system else []) + [{'role': 'user', 'content': c['question']}]
            text = tok.apply_chat_template(messages, chat_template=chat, tokenize=False, add_generation_prompt=True, enable_thinking=False)
            prefix = tok.encode(text, add_special_tokens=False)
            targets = {}
            for name, answer in c['references'].items():
                whole = tok.encode(text + answer, add_special_tokens=False)
                assert whole[:len(prefix)] == prefix, (c['id'], name, 'BPE prefix differs')
                targets[name] = whole[len(prefix):][:p['max_target_tokens']]
                assert targets[name]
            groups.append({'id': c['id'] + ('/system' if use_system else '/no_system'), 'case_id': c['id'],
                'source': 'development', 'category': c['category'], 'condition': 'nt_system' if use_system else 'nt_no_system',
                'prefix': prefix, 'targets': targets})

    # Native Swift encoding is necessary: tokenizer-only reconstruction is not assumed equivalent.
    sys.path.insert(0, str(I))
    import identity_loss3
    from swift.model import get_processor
    from swift.template import get_template
    ref = read(I / 'native-report.json')
    assert sha(I / 'identity_loss3.py') == ref['loss_plugin_sha256']
    assert sha(I / 'identity-keys.json') == ref['identity_key_binding_sha256']
    selection = read(I / 'training-controls.json'); members = read(I / 'membership.json')
    assert selection['dataset_sha256'] == members['dataset_sha256'] == ref['dataset_sha256']
    template = get_template(get_processor(str(BASE), model_type='qwen3', download_model=False), **ref['template_kwargs'])
    template.set_mode('train')
    close_id = tok.encode('</think>', add_special_tokens=False)
    assert len(close_id) == 1
    native = []
    for item in selection['rows']:
        enc = template.encode(deepcopy(item['row']))
        ids = enc['input_ids']; key = ih(ids); membership = members['members'][key]
        assert membership['retain'] and item['line'] in membership['lines']
        assert len(ids) <= 2048 and all(x in [0., 1.] for x in enc['loss_scale'])
        valid = [j for j, label in enumerate(enc['labels']) if j > 0 and label != -100]
        close = [j for j, token in enumerate(ids) if token == close_id[0]]
        assert len(close) == 1
        regions = {'body': [j for j in valid if j > close[0]]}
        before = [j for j in valid if j < close[0]]
        if before: regions = {'think': before, **regions}
        for region, positions in regions.items():
            positions = positions[:p['max_target_tokens']]
            assert positions and positions == list(range(positions[0], positions[-1] + 1))
            start = positions[0]; target = ids[start:positions[-1] + 1]
            condition = ('native_thinking_' if before else 'native_nonthinking_') + region
            groups.append({'id': f"train-line-{item['line']}/{region}", 'case_id': f"train-line-{item['line']}",
                'source': 'training_control', 'category': item['row']['dataset'], 'condition': condition,
                'prefix': ids[:start], 'targets': {'native_reference': target}, 'native_row_key': key})
        native.append({'line': item['line'], 'encoded_key': key, 'encoded_tokens': len(ids),
                       'supervised_tokens': len(valid), 'regions': list(regions)})
    paths = sum(len(g['targets']) for g in groups)
    assert paths == p['expected_paths'] and len(groups) == p['expected_prefixes'], (paths, len(groups))
    for g in groups:
        assert len(g['prefix']) + max(map(len, g['targets'].values())) <= p['max_context_tokens']
    load_filter(torch)
    a = torch.tensor([[1., 2., 3.], [-1., .2, 0.]])
    b = torch.tensor([[1., 1., 4.], [0., .5, 1.]])
    al = a.log_softmax(-1); bl = b.log_softmax(-1)
    dense = (al.exp() * (al - bl)).sum(-1)
    independent = torch.nn.functional.kl_div(bl, al.exp(), reduction='none').sum(-1)
    assert torch.allclose(dense, independent, atol=1e-6) and (dense >= 0).all()
    save('encoded.json', groups)
    report = {'verified': True, 'versions': versions, 'development_cases': 12, 'training_rows': native,
        'prefixes': len(groups), 'paths': paths, 'expected_model_path_scores': paths * len(p['models']),
        'max_input_tokens': max(len(g['prefix']) + max(map(len, g['targets'].values())) for g in groups),
        'native_membership_all_retained': True, 'base_and_adapter_hashes_match': True,
        'BPE_prefix_checks': True, 'KL_formula_checked': True, 'sampling_filter_checked': True,
        'system_sha256': sha(I / 'system.txt'), 'template_sha256': sha(I / 'thinking-prefill.jinja'),
        'input_manifest_sha256': sha(I / 'manifest.json'), 'script_sha256': sha(Path(__file__)),
        'encoded_sha256': sha(O / 'encoded.json'), 'new_generated_answers': 0, 'training': False}
    save('encoding-check.json', report); print(json.dumps(report), flush=True)
    return tok, groups, p

def run():
    import torch
    from transformers import AutoModelForCausalLM
    from peft import PeftModel
    started = time.monotonic()
    tok, groups, p = prepare()
    assert torch.cuda.is_available() and not (O / 'scores.jsonl').exists()
    f = load_filter(torch); cfg = p['sampling']
    model = AutoModelForCausalLM.from_pretrained(BASE, local_files_only=True, dtype=torch.bfloat16,
        device_map={'': 0}, attn_implementation='sdpa')
    adapter_names = {name: name.replace('.', '_') for name in p['adapters']}
    for i, (name, adapter) in enumerate(p['adapters'].items()):
        if i == 0:
            model = PeftModel.from_pretrained(model, adapter['path'], adapter_name=adapter_names[name], is_trainable=False, local_files_only=True)
        else: model.load_adapter(adapter['path'], adapter_name=adapter_names[name], is_trainable=False, local_files_only=True)
    model.eval(); model.requires_grad_(False)
    def digest():
        h = hashlib.sha256()
        for name, v in model.named_parameters():
            if 'lora_' in name:
                h.update(name.encode()); h.update(v.detach().cpu().float().numpy().tobytes())
        return h.hexdigest()
    before = digest()
    def logits(arm, prefix, target=None):
        target = target or []
        if arm != 'base': model.set_adapter(adapter_names[arm])
        model.eval(); model.requires_grad_(False)
        assert not any(v.requires_grad for v in model.parameters())
        x = torch.tensor([prefix + target[:-1]], device='cuda')
        with torch.inference_mode(), (model.disable_adapter() if arm == 'base' else nullcontext()):
            out = model(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False, logits_to_keep=max(1, len(target)))
        values = out.logits[0].float()
        assert torch.isfinite(values).all()
        return values

    def sampled(values):
        return f(values.clone() / cfg['temperature'], torch.full((len(values),), cfg['top_k'], device='cuda'),
                 torch.full((len(values),), cfg['top_p'], device='cuda')).softmax(-1)

    def compare(base, adapted):
        a = base.log_softmax(-1); b = adapted.log_softmax(-1)
        kl = (a.exp() * (a - b)).sum(-1)
        tv = .5 * (a.exp() - b.exp()).abs().sum(-1)
        assert torch.isfinite(kl).all() and kl.min().item() >= -1e-6
        return {'kl_base_to_adapter': kl.tolist(), 'mean_kl': kl.mean().item(), 'mean_total_variation': tv.mean().item()}

    count = prefix_count = kl_count = 0
    for group in groups:
        common = {k: group[k] for k in ['id', 'case_id', 'source', 'category', 'condition']}
        prefix = group['prefix']; first = {arm: logits(arm, prefix) for arm in p['models']}
        for arm, values in first.items():
            lp = values[0].log_softmax(-1); filtered = sampled(values)[0]
            wanted = sorted({x[0] for x in group['targets'].values()} | {tok.eos_token_id})
            top, ids = lp.topk(8)
            append('prefixes.jsonl', {**common, 'model': arm, 'prefix_sha256': ih(prefix), 'prompt_tokens': len(prefix),
                'wanted_tokens': [{'id': j, 'token': tok.decode([j]), 'probability': lp[j].exp().item(),
                    'rank': int((values[0] > values[0, j]).sum().item()) + 1, 'filtered_probability': filtered[j].item()} for j in wanted],
                'top8': [{'id': j, 'token': tok.decode([j]), 'probability': math.exp(v)} for j, v in zip(ids.tolist(), top.tolist())]})
            prefix_count += 1
        for arm in p['adapters']:
            append('kl.jsonl', {**common, 'model': arm, 'position': 'first', 'reference': None,
                               'prefix_sha256': ih(prefix), **compare(first['base'], first[arm])})
            kl_count += 1
        for ref, target in group['targets'].items():
            raw = {arm: logits(arm, prefix, target) for arm in p['models']}
            for arm, values in raw.items():
                values[0] = first[arm][0]
                y = torch.tensor(target, device='cuda')
                lp = values.log_softmax(-1).gather(1, y[:, None]).squeeze(1)
                probabilities = sampled(values).gather(1, y[:, None]).squeeze(1)
                ranks = (values > values.gather(1, y[:, None])).sum(-1) + 1
                append('scores.jsonl', {**common, 'model': arm, 'reference': ref,
                    'prefix_sha256': ih(prefix), 'target_sha256': ih(target), 'target_text': tok.decode(target),
                    'prompt_tokens': len(prefix), 'tokens': len(target), 'mean_nll': -lp.mean().item(),
                    'first8_mean_nll': -lp[:8].mean().item(), 'sum_logp': lp.sum().item(),
                    'token_logp': lp.tolist(), 'token_ranks': ranks.tolist(),
                    'filtered_probabilities': probabilities.tolist(), 'filtered_zero_tokens': int((probabilities == 0).sum().item())})
                count += 1
            for arm in p['adapters']:
                append('kl.jsonl', {**common, 'model': arm, 'position': 'path', 'reference': ref,
                    'prefix_sha256': ih(prefix), 'target_sha256': ih(target), **compare(raw['base'], raw[arm])})
                kl_count += 1
            del raw
        del first
        save('progress.json', {'prefix_groups': prefix_count // 3, 'scores': count, 'kl_comparisons': kl_count,
                              'elapsed_seconds': time.monotonic() - started})
        print(json.dumps({'id': group['id'], 'scores': count, 'seconds': round(time.monotonic() - started, 1)}), flush=True)
    assert count == p['expected_model_path_scores'] and prefix_count == 3 * p['expected_prefixes']
    assert kl_count == p['expected_kl_paths'] + p['expected_kl_prefixes']
    after = digest(); assert before == after
    for adapter in p['adapters'].values():
        for name, meta in adapter['files'].items(): assert sha(Path(adapter['path']) / name) == meta['sha256']
    save('completed.json', {'complete': True, 'scores': count, 'prefix_distributions': prefix_count,
        'kl_comparisons': kl_count, 'seconds': time.monotonic() - started, 'new_generated_answers': 0,
        'training': False, 'backward_calls': 0, 'judge_calls': 0, 'deployment': False, 'uat_restore': False,
        'adapter_memory_unchanged': True, 'adapter_memory_sha256': after,
        'gpu_peak_allocated_bytes': torch.cuda.max_memory_allocated(),
        'files_sha256': {n: sha(O / n) for n in ['scores.jsonl', 'prefixes.jsonl', 'kl.jsonl', 'encoded.json', 'encoding-check.json']}})
    print('DIAGNOSTIC_COMPLETED', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--cpu-only', action='store_true'); args = parser.parse_args()
    prepare() if args.cpu_only else run()
