"""Freeze existing questions and training-context controls for probability diagnosis."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
import shutil

D = Path(__file__).resolve().parent
R = D.parents[2]
I = D / 'inputs'
I.mkdir(exist_ok=True)
V = R / 'stage1/variants/stage1-cpu-v0.1.22'
OLD = R / 'stage2/diagnostics/module-ablation-20261101'
NEW = R / 'stage2/runs/t008-v0125-kl-20261101-084231'

def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p, x): p.write_text(json.dumps(x, ensure_ascii=False, indent=2) + '\n')

source = read(OLD / 'inputs/cases.json')['cases']
selected = ['T021-C900-B4-G007', 'T021-P20-G0274', 'T021-R3300-G1038',
            'T021-C900-B3-G035', 'T021-C900-B4-G115', 'T021-C900-B4-G033',
            'D16-05', 'D16-07', 'E17-ID06', 'E17-ID07']
cases = [deepcopy(next(c for c in source if c['id'] == cid)) for cid in selected]
all_cases = {c['id']: c for c in read(NEW / 'evaluation/cases.json')['items']}
controls = {
    'T021-R3300-G0503': '同一电压下，皮肤被汗水弄湿通常会降低阻抗，增加通过人体的电流，触电风险会增大，不能说出汗更安全。',
    'T021-C900-B4-N045': '按给定单波段模型可报告净散热40瓦；发射率未定，不能唯一确定温度。保持只许远测、不改圣物的限制。',
}
for cid, expected in controls.items():
    c = all_cases[cid]
    cases.append({'id': cid, 'question': c['question'], 'criteria': c['criteria'],
                  'category': 'normal_control', 'references': {'expected': expected, 'question_copy': c['question']},
                  'reference_note': 'Researcher-written diagnostic reference consistent with supplied facts; not a training addition or observed response.'})
for c in cases:
    c.pop('generation_system', None)
    assert c['question'] == all_cases[c['id']]['question']
save(I / 'cases.json', {'cases': cases})

rows = [json.loads(s) for s in (V / 'train.jsonl').read_text().splitlines()]
unique = {}
for line, row in enumerate(rows, 1):
    key = hashlib.sha256(json.dumps(row, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    unique.setdefault(key, {'line': line, 'row': row})
general = []
for key, x in unique.items():
    row = x['row']; messages = row['messages']
    if row['dataset'] != 'swift/Qwen3-SFT-Mixin' or len(messages) != 2: continue
    q = messages[0]['content']; a = messages[1]['content']
    if len(re.findall(r'[\u4e00-\u9fff]', q)) < max(3, .4 * len(q)): continue
    if not re.search(r'<think>\s*\S.+?</think>\s*\S', a, re.S): continue
    general.append((key, x))
general.sort()
chosen = [general[i * (len(general) - 1) // 3][1] for i in range(4)]
for source in ['t008/general-nonthinking-v1', 't008/strict-json-v1']:
    candidates = sorted((key, x) for key, x in unique.items()
                        if x['row']['dataset'] == source and len(x['row']['messages']) == 2
                        and re.search(r'<think>\s*</think>', x['row']['messages'][-1]['content']))
    assert candidates, source
    chosen.append(candidates[0][1])
assert len({x['line'] for x in chosen}) == 6
save(I / 'training-controls.json', {'dataset_sha256': sha(V / 'train.jsonl'),
    'selection': 'Four Chinese nonempty-think unique rows at hash-sorted quartiles; first hash-sorted empty-think general-nonthinking-v1 and strict-json-v1 rows. Selected before new scores.',
    'eligible_chinese_general_unique': len(general), 'rows': chosen})
for name in ['identity_loss3.py', 'identity-keys.json']:
    shutil.copyfile(V / name, I / name)
shutil.copyfile(V / 'cpu-check/report.json', I / 'native-report.json')
shutil.copyfile(NEW / 'retention/membership.json', I / 'membership.json')
for name in ['system.txt', 'thinking-prefill.jinja', 'vllm_topk_topp_source.py', 'base-files.json']:
    shutil.copyfile(OLD / 'inputs' / name, I / name)
p = read(OLD / 'inputs/protocol.json')
new_manifest = read(NEW / 'outputs/full/run_manifest.json')
adapters = {'v0.1.22': p['adapter'], 'v0.1.25': {
    'path': new_manifest['checkpoint'].replace('/runwork', '/models-work/' + NEW.name),
    'files': new_manifest['adapter_files']}}
protocol = {
    'models': ['base', 'v0.1.22', 'v0.1.25'], 'adapters': adapters, 'versions': p['versions'],
    'sampling': p['sampling'], 'thinking': False, 'max_target_tokens': 32, 'max_context_tokens': 8192,
    'expected_development_cases': 12, 'expected_training_rows': 6,
    'expected_paths': 58, 'expected_model_path_scores': 174, 'expected_prefixes': 34,
    'expected_kl_paths': 116, 'expected_kl_prefixes': 68,
    'training': False, 'generation': False, 'judge': False, 'deployment': False,
    'uat_policy': 'KEEP_PAUSED_UNTIL_EXPLICIT_USER_RESTORE',
    'method': 'Raw T1 full-vocabulary KL(base||adapter), teacher-forced fixed32-token heads, native training controls, frozen nonthinking chat prefixes with and without System.',
    'limits': ['Fixed text probabilities are not semantic correctness probabilities or free-generation failure rates.',
               'Small selected contexts cannot represent the full training distribution or identify a unique causal mechanism.',
               'Diagnostic uses Transformers/PEFT SDPA, not bitwise vLLM logits. Sampling filter only reports support; no sampling occurs.'],
}
save(I / 'protocol.json', protocol)
files = {p.name: {'sha256': sha(p), 'bytes': p.stat().st_size} for p in sorted(I.iterdir()) if p.name != 'manifest.json'}
save(I / 'manifest.json', {'files': files})
save(D / 'authorization.json', {'user_instruction': '继续，另外你这个过程是否需要用astra max？',
    'scope': 'Existing base/v0.1.22/v0.1.25 fixed-prefix probability and distribution diagnosis only; no training, new generated answers, deployment or external Judge.',
    'uat_pause_continues': True, 'automatic_restore_authorized': False, 'new_subagents': False})
save(D / 'input-binding.json', {'input_manifest_sha256': sha(I / 'manifest.json'),
    'data_version': 'stage1-cpu-v0.1.22', 'dataset_sha256': sha(V / 'train.jsonl'),
    'training_control_lines': [x['line'] for x in chosen], 'development_case_ids': [c['id'] for c in cases],
    'system_sha256': sha(I / 'system.txt'), 'template_sha256': sha(I / 'thinking-prefill.jinja'),
    'scope': '174 fixed-text scores plus paired full-vocabulary KL; zero new generated answers'})
print(json.dumps({'cases': len(cases), 'training_rows': len(chosen), 'expected_scores': 174}))
