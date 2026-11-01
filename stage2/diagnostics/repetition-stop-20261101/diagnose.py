"""Fixed-text scoring only: no generate, backward, optimizer or weight writes."""
import argparse
import ast
import hashlib
import importlib.metadata as md
import inspect
import json
import math
import os
from pathlib import Path
import time

os.environ.setdefault('TORCHINDUCTOR_CACHE_DIR', '/tmp/torchinductor_diag')
D = Path('/tmp/diag'); I = D / 'inputs'; O = D / 'results'; BASE = Path('/base')
O.mkdir(exist_ok=True)
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        while b := f.read(8 * 1024 * 1024): h.update(b)
    return h.hexdigest()
def read(p): return json.loads(Path(p).read_text())
def save(name, value): (O / name).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
def ids_hash(ids): return hashlib.sha256(json.dumps(ids).encode()).hexdigest()

def load_filter(torch):
    tree = ast.parse((I / 'vllm_topk_topp_source.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'apply_top_k_top_p_pytorch')
    namespace = {'torch': torch}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<frozen-vllm-filter>', 'exec'), namespace)
    fn = namespace[node.name]
    values = torch.tensor([[4., 3., 2., 1.]])
    assert torch.isfinite(fn(values.clone(), torch.tensor([2]), torch.tensor([.8]))).tolist() == [[True, True, False, False]]
    assert torch.isfinite(fn(values.clone(), torch.tensor([2]), torch.tensor([.6]))).tolist() == [[True, False, False, False]]
    assert torch.isfinite(fn(torch.tensor([[5., 4., 4., 1.]]), torch.tensor([2]), torch.tensor([1.]))).tolist() == [[True, True, True, False]]
    return fn

def prepare():
    import torch
    from transformers import AutoTokenizer
    from transformers.models.qwen3.modeling_qwen3 import Qwen3ForCausalLM
    protocol = read(I / 'protocol.json')
    for name, meta in read(I / 'manifest.json')['files'].items():
        assert sha(I / name) == meta['sha256'], name
    versions = {k: md.version(k) for k in protocol['versions']}
    assert versions == protocol['versions'], versions
    for meta in read(I / 'base-files.json'):
        p = BASE / meta['path']
        assert p.stat().st_size == meta['size'] and sha(p) == meta['sha256'], meta['path']
    for arm, adapter in protocol['adapters'].items():
        for name, meta in adapter['files'].items():
            p = Path(adapter['path']) / name
            assert p.stat().st_size == meta['bytes'] and sha(p) == meta['sha256'], (arm, name)
    assert 'logits_to_keep' in inspect.signature(Qwen3ForCausalLM.forward).parameters
    tok = AutoTokenizer.from_pretrained(BASE, local_files_only=True)
    eos = tok.encode('<|im_end|>', add_special_tokens=False)
    close = tok.encode('</think>', add_special_tokens=False)
    assert eos == [tok.eos_token_id] and len(close) == 1
    chat = (I / 'thinking-prefill.jinja').read_text()
    system = (I / 'system.txt').read_text()
    cases = {c['id']: c for c in read(I / 'cases.json')['cases']}
    probes = read(I / 'probes.json')['probes']
    checks, encoded = [], []
    for p in probes:
        c = cases[p['case_id']]
        req = c['request']; thinking = req['chat_template_kwargs']['enable_thinking']
        assert req['messages'][0] == {'role': 'system', 'content': system}
        cfg = protocol['sampling_profiles']['thinking' if thinking else 'nonthinking']
        assert all(req[k] == v for k, v in cfg.items())
        assert all(req[k] == protocol[k] for k in ['repetition_penalty', 'presence_penalty', 'frequency_penalty', 'min_p'])
        rendered = tok.apply_chat_template(req['messages'], chat_template=chat, tokenize=False,
            add_generation_prompt=True, enable_thinking=thinking)
        prefix_text = rendered + p['assistant_prefix']
        prefix = tok.encode(prefix_text, add_special_tokens=False)
        targets = {}
        for ref, answer in p['alternatives'].items():
            whole = tok.encode(prefix_text + answer, add_special_tokens=False)
            assert whole[:len(prefix)] == prefix, (p['id'], ref, 'BPE prefix mismatch')
            target = whole[len(prefix):][:protocol['max_target_tokens']]
            assert target and len(prefix) + len(target) <= protocol['max_context_tokens']
            targets[ref] = target
            checks.append({'probe_id': p['id'], 'reference': ref, 'prompt_tokens': len(prefix),
                'target_tokens': len(target), 'prompt_sha256': ids_hash(prefix), 'input_sha256': ids_hash(prefix + target[:-1])})
        encoded.append({'probe': p, 'prefix': prefix, 'targets': targets})
    assert len(encoded) == 21 and len(checks) * len(protocol['models']) == 252
    load_filter(torch)
    save('encoding-details.json', checks)
    report = {'verified': True, 'versions': versions, 'cases': len(cases), 'positions': len(encoded),
        'expected_scores': 252, 'all_BPE_prefixes_match': True, 'all_base_and_adapter_hashes_match': True,
        'max_input_tokens': max(c['prompt_tokens'] + c['target_tokens'] for c in checks),
        'min_prompt_tokens': min(c['prompt_tokens'] for c in checks),
        'eos_token_id': eos[0], 'close_think_token_id': close[0],
        'generation_config': read(BASE / 'generation_config.json'), 'sampling_filter_checked': True,
        'protocol_sha256': sha(I / 'protocol.json'), 'system_sha256': sha(I / 'system.txt'),
        'template_sha256': sha(I / 'thinking-prefill.jinja'), 'script_sha256': sha(Path(__file__)),
        'training': False, 'new_generated_answers': 0}
    save('encoding-check.json', report)
    print(json.dumps(report), flush=True)
    stop_ids = read(BASE / 'generation_config.json')['eos_token_id']
    if isinstance(stop_ids, int): stop_ids = [stop_ids]
    return tok, encoded, protocol, sorted(set(stop_ids + [eos[0], close[0]]))

def run():
    import torch
    from transformers import AutoModelForCausalLM
    from peft import PeftModel
    tok, encoded, protocol, stop_ids = prepare()
    assert torch.cuda.is_available()
    path = O / 'scores.jsonl'
    assert not path.exists(), 'Do not overwrite diagnostic scores'
    fn = load_filter(torch)
    started = time.monotonic()
    model = AutoModelForCausalLM.from_pretrained(BASE, local_files_only=True, dtype=torch.bfloat16,
        device_map={'': 0}, attn_implementation='sdpa')
    total = 0
    def logits_for(prefix, target=None):
        target = target or []
        x = torch.tensor([prefix + target[:-1]], device='cuda')
        with torch.inference_mode():
            r = model(input_ids=x, attention_mask=torch.ones_like(x), use_cache=False, logits_to_keep=max(len(target), 1))
        return r.logits[0].float()
    def distribution(logits, wanted):
        lp = logits.log_softmax(-1)
        top, ids = lp.topk(8)
        return {'tokens': {str(i): {'id': i, 'token': tok.decode([i]), 'probability': lp[i].exp().item(),
                 'rank': int((logits > logits[i]).sum().item()) + 1} for i in sorted(set(wanted))},
            'top8': [{'id': i, 'token': tok.decode([i]), 'probability': math.exp(v)} for i, v in zip(ids.tolist(), top.tolist())]}
    def evaluate(arm):
        nonlocal total
        model.eval(); model.requires_grad_(False)
        assert not any(p.requires_grad for p in model.parameters())
        for e in encoded:
            p, prefix, targets = e['probe'], e['prefix'], e['targets']
            # Compute a single authoritative first-token distribution per prefix.
            first = logits_for(prefix)[-1]
            wanted = stop_ids + [t[0] for t in targets.values()]
            first_profiles = {'raw': distribution(first, wanted)}
            for name, cfg in protocol['sampling_profiles'].items():
                filtered = fn(first[None].clone() / cfg['temperature'],
                    torch.tensor([cfg['top_k']], device='cuda'), torch.tensor([cfg['top_p']], device='cuda'))[0]
                first_profiles[name] = distribution(filtered, wanted)
            for ref, target in targets.items():
                logits = first[None] if len(target) == 1 else logits_for(prefix, target)
                # Same first logit for every alternative; remaining positions are teacher-forced.
                logits[0] = first
                y = torch.tensor(target, device='cuda')
                lp = logits.log_softmax(-1).gather(1, y[:, None]).squeeze(1).tolist()
                ranks = (logits > logits.gather(1, y[:, None])).sum(-1).add(1).tolist()
                sampled = {}
                for name, cfg in protocol['sampling_profiles'].items():
                    fl = fn(logits.clone() / cfg['temperature'], torch.full((len(y),), cfg['top_k'], device='cuda'), torch.full((len(y),), cfg['top_p'], device='cuda'))
                    probabilities = fl.softmax(-1).gather(1, y[:, None]).squeeze(1).tolist()
                    sampled[name] = {'target_probabilities': probabilities, 'zero_target_tokens': sum(x == 0 for x in probabilities)}
                row = {'model': arm, 'probe_id': p['id'], 'case_id': p['case_id'], 'category': p['category'],
                    'role': p['role'], 'group': p['group'], 'reference': ref, 'prompt_tokens': len(prefix),
                    'prompt_sha256': ids_hash(prefix), 'target_text': tok.decode(target), 'target_tokens': len(target),
                    'mean_nll': -sum(lp)/len(lp), 'sum_logp': sum(lp), 'first': first_profiles,
                    'token_scores': [{'id': i, 'token': tok.decode([i]), 'logp': v, 'rank': r} for i, v, r in zip(target, lp, ranks)],
                    'sampling_profiles': sampled}
                with path.open('a') as f: f.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + '\n')
                total += 1
            print(json.dumps({'arm': arm, 'position': p['id'], 'scores': total, 'seconds': round(time.monotonic() - started, 1)}), flush=True)
    evaluate('base')
    for index, (arm, adapter) in enumerate(protocol['adapters'].items()):
        if index == 0:
            model = PeftModel.from_pretrained(model, adapter['path'], adapter_name=arm, is_trainable=False, local_files_only=True)
        else:
            model.load_adapter(adapter['path'], adapter_name=arm, is_trainable=False, local_files_only=True)
        model.set_adapter(arm)
        assert model.active_adapters == [arm], model.active_adapters
        evaluate(arm)
    assert total == protocol['expected_scores']
    save('completed.json', {'completed': True, 'scores': total, 'models': protocol['models'],
        'elapsed_seconds': time.monotonic() - started, 'scores_sha256': sha(path),
        'training': False, 'new_generated_answers': 0, 'judge_calls': 0, 'backward_calls': 0,
        'gpu_peak_allocated_bytes': torch.cuda.max_memory_allocated(),
        'note': 'Conditional probability diagnostics at fixed observed/counterfactual prefixes, not error rates or semantic answer probabilities.'})
    print('DIAGNOSTIC_COMPLETED', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--cpu-only', action='store_true')
    args = parser.parse_args()
    prepare() if args.cpu_only else run()
