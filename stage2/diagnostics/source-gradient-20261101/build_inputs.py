"""Freeze full-corpus source gradients and existing diagnostic continuations."""
from pathlib import Path
from datetime import datetime, timezone
from copy import deepcopy
import hashlib
import json
import re
import shutil

D = Path(__file__).resolve().parent
R = D.parents[2]
I = D / 'inputs'
I.mkdir(exist_ok=True)
V = R / 'stage1/variants/stage1-cpu-v0.1.22'
K = R / 'stage2/diagnostics/kl-context-20261101'
S = R / 'stage2/diagnostics/repetition-stop-20261101'
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')

for name in ['train.jsonl', 'identity_loss3.py', 'identity-keys.json', 'train-map.jsonl']:
    shutil.copyfile(V / name, I / name)
shutil.copyfile(V / 'cpu-check/report.json', I / 'native-report.json')
shutil.copyfile(V / 'cpu-check/row-checks.jsonl', I / 'native-row-checks.jsonl')
for name in ['system.txt', 'thinking-prefill.jinja', 'vllm_topk_topp_source.py', 'base-files.json']:
    shutil.copyfile(K / 'inputs' / name, I / name)

# Keep exact archived questions and prefixes. No test item becomes training data.
old_cases = {c['id']: c for c in read(S / 'inputs/cases.json')['cases']}
old_probes = {p['id']: p for p in read(S / 'inputs/probes.json')['probes']}
selected = {
    'T021-C900-B4-G007/wrong_continuation': ('observed_copy', 'correct_reference'),
    'T021-P20-G0274/start': ('observed_copy', 'correct_reference'),
    'T021-P20-G0274/wrong_continuation': ('observed_copy', 'correct_reference'),
    'T021-R3300-G0243/after_1_cycles': ('repeat', 'correct_closure'),
    'T021-R3300-G1038/after_1_cycles': ('repeat', 'correct_closure'),
    'T021-R3300-G0243/correct_end': ('repeat', 'end_answer'),
    'T021-R3300-G1038/correct_end': ('repeat', 'end_answer'),
    'T021-B6-G159/observed_end': ('repeat', 'end_answer'),
    'T021-R3300-G0456/observed_end': ('repeat', 'end_answer'),
}
probes = []
for key, (bad, good) in selected.items():
    p = old_probes[key]; c = old_cases[p['case_id']]
    probes.append({'id': key, 'case_id': p['case_id'], 'category': p['category'],
        'question': c['request']['messages'][-1]['content'], 'assistant_prefix': p['assistant_prefix'],
        'bad_continuation': p['alternatives'][bad], 'good_continuation': p['alternatives'][good],
        'source': str((S / 'inputs/probes.json').relative_to(R)),
        'note': 'First divergent token of frozen continuations; this is not a semantic pass/fail score.'})
kc = {c['id']: c for c in read(K / 'inputs/cases.json')['cases']}
for cid, prefix, bad, good in [
    ('D16-05', '我是', '通义千问', '能碳章鱼垂直大模型'),
    ('D16-07', '我是', '通义千问', '能碳章鱼垂直大模型'),
    ('E17-ID06', '', '章鱼', '能碳章鱼垂直大模型'),
    ('E17-ID07', '我的产品名称是', '通义千问', '能碳章鱼垂直大模型'),
]:
    probes.append({'id': cid + '/name', 'case_id': cid, 'category': 'identity', 'question': kc[cid]['question'],
        'assistant_prefix': prefix, 'bad_continuation': bad, 'good_continuation': good,
        'source': str((K / 'inputs/cases.json').relative_to(R)),
        'note': 'Name-token contrast; supplied assistant prefix except E17-ID06. Other valid phrasings are not represented.'})
cases25 = {c['id']: c for c in read(R / 'stage2/runs/t008-v0125-kl-20261101-084231/evaluation/cases.json')['items']}
for cid, prefix, bad, good in [
    ('T021-R3300-G1202', '本次问题的原因是', '采集故障。', '零值导入误判。'),
    ('T021-R3300-G1403', '最终评语：记录', '造假。', '真实。'),
]:
    probes.append({'id': cid + '/fact', 'case_id': cid, 'category': 'fact',
        'question': cases25[cid]['question'], 'assistant_prefix': prefix,
        'bad_continuation': bad, 'good_continuation': good,
        'source': 'stage2/diagnostics/kl-failure-attribution-20261101/CASE_REVIEW.md',
        'note': 'Researcher-specified fixed fact contrast based on existing answer audit; not generated text and not training data.'})
assert len(probes) == 15
save(I / 'probes.json', {'probes': probes})

oldp = read(K / 'inputs/protocol.json')
adapters = {'step66': deepcopy(oldp['adapters']['v0.1.22'])}
text = (D / 'implementation-inspection.txt').read_text()
for step in [50, 66]:
    part = text.split(f'CHECKPOINT {step}\n', 1)[1].split('CHECKPOINT ', 1)[0]
    files = {}
    for name in ['adapter_model.safetensors', 'adapter_config.json', 'optimizer.pt', 'args.json']:
        m = re.search(r'^' + re.escape(name) + r' (\d+) ([0-9a-f]{64})$', part, re.M)
        assert m, name
        files[name] = {'bytes': int(m[1]), 'sha256': m[2]}
    adapters[f'step{step}'] = {'path': oldp['adapters']['v0.1.22']['path'].replace('checkpoint-66', f'checkpoint-{step}'), 'files': files}
p = {'id': D.name, 'data_version': V.name, 'dataset_sha256': sha(V / 'train.jsonl'),
    'versions': oldp['versions'], 'models': ['step50', 'step66'], 'adapters': adapters,
    'groups': {'general': ['swift/Qwen3-SFT-Mixin'],
               'identity': ['swift/self-cognition', 't008/chinese-identity-v1', 't008/company-facts-v1'],
               'business': ['t008/project-positioning-v1', 't008/business-evidence-v1', 't008/company-boundary-v1'],
               'format': ['t008/strict-json-v1', 't008/general-nonthinking-v1', 't008/general-nonthinking-v2']},
    'expected_group_rows': {'general': 752, 'identity': 234, 'business': 43, 'format': 18},
    'aggregate_other': ['business', 'format'], 'all_exposures': 1047, 'all_valid_tokens': 928890,
    'all_weighted_units': 946600.0, 'probe_cases': 15, 'probe_conditions': ['no_system', 'system'],
    'probe_positions': 30, 'sampling': oldp['sampling'], 'temperature_for_gradient': 1.0,
    'source_gradient': 'Sum exposure-weighted native weighted CE gradients divided by full-corpus unweighted valid token count. Deduplicate only identical encoding/group; retain multiplicity.',
    'probe_score': 'log P(first divergent bad token | same prefix) - log P(first divergent good token | same prefix). Positive is greater support for the selected undesired continuation only.',
    'raw_effect': '-dot(grad_probe, grad_source)',
    'adam_scaled_effect': '-dot(grad_probe, P * grad_source), P=1/(sqrt(saved exp_avg_sq bias-corrected)+epsilon). Fixed positive preconditioner; not a full Adam step.',
    'dropout': 'Disabled for deterministic local derivatives. Does not replay training dropout or chronological minibatches.',
    'optimizer_updates': 0, 'new_generated_answers': 0, 'new_training_candidate': False,
    'uat_policy': 'KEEP_PAUSED_UNTIL_EXPLICIT_RESTORE',
    'decision': 'Choose a source to test by later ablation only if effects are coherent across contexts and both checkpoints; otherwise report inconclusive. No automatic training or attribution of all historical errors.',
    'limits': ['Two trained checkpoints give local directions, not historical causation or initial training trajectory.',
               'Corpus token normalization is not the time-ordered sum of Adam updates with changing batch denominators.',
               'The fixed Adam metric omits moment update, clipping, weight decay and learning-rate schedule; step66 saved learning rate is zero.',
               'Probe tokens and conditional prefixes do not cover all valid answers or actual sequence-level quality.',
               'Grouped gradients are parameterization-dependent and may cancel; token proportions are not gradient responsibility.']}
save(I / 'protocol.json', p)
save(D / 'protocol.json', p)
files = {f.name: {'bytes': f.stat().st_size, 'sha256': sha(f)} for f in sorted(I.iterdir()) if f.name != 'manifest.json'}
save(I / 'manifest.json', {'files': files})
save(D / 'input-binding.json', {'manifest_sha256': sha(I / 'manifest.json'), 'dataset_sha256': p['dataset_sha256'],
    'rows': 1047, 'source_group_rows': p['expected_group_rows'], 'checkpoints': p['models'],
    'probes': len(probes), 'conditions': 2, 'system_sha256': sha(I / 'system.txt'),
    'template_sha256': sha(I / 'thinking-prefill.jinja')})
save(D / 'authorization.json', {'recorded_at_utc': datetime.now(timezone.utc).isoformat(),
    'user_instruction': '开始你刚才计划的三个步骤，“先做分来源的训练信号诊断”，',
    'executing_scope': 'Step 1 only: full-corpus gradient diagnosis at frozen existing checkpoints; forward/backward allowed, optimizer.step forbidden. No generated answers, data revision, candidate training or deployment.',
    'uat_pause_continues': True, 'automatic_restore_authorized': False, 'subagents': False})
print(json.dumps({'prepared': True, 'rows': 1047, 'probes': 30, 'checkpoints': [50, 66]}))
