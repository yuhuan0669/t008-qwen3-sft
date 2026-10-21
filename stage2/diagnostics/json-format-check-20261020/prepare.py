"""Prepare a small paired inference check; do not pause UAT or train."""
from pathlib import Path
from copy import deepcopy
import datetime
import hashlib
import json
import shutil
import subprocess

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
OLD = ROOT / 'stage2/diagnostics/chinese-minimal-check-20261020'
NEW = ROOT / 'stage2/runs/t008-v019-20261020-211142'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

assert not (D / 'window-state.json').exists()
old = json.loads((OLD / 'spec.json').read_text())
new = json.loads((NEW / 'outputs/full/run_manifest.json').read_text())
system_file = ROOT / 'stage1/variants/stage1-cpu-v0.1.9/evaluation/custom-system.txt'
system = system_file.read_text()
assert sha(system_file) == old['systems_sha256']['proposed']
tasks = [
    ('DEV-07', '只输出JSON，把姓名小林、年龄26写成name和age两个字段。', {'name': '小林', 'age': 26}),
    ('JSON-NEW-01', '把“温度传感器3个，压力传感器2个”转换成JSON数组，每项只有item和count两个字段，保持原顺序。只输出JSON。', [{'item': '温度传感器', 'count': 3}, {'item': '压力传感器', 'count': 2}]),
    ('JSON-NEW-02', '只返回JSON对象：设备正在运行、没有告警、负责人未知。字段固定为running、alarm、owner；前两项用布尔值，未知值用null。', {'running': True, 'alarm': False, 'owner': None}),
    ('JSON-NEW-03', '请把“东区；电表M17；读数42.5千瓦时”转成JSON：site对应东区，meter是含id和kwh两个字段的对象，id对应M17，kwh用数字42.5。整个回答只包含JSON。', {'site': '东区', 'meter': {'id': 'M17', 'kwh': 42.5}}),
]
cases = []
for mode in ['nonthinking', 'thinking']:
    for case_id, user, expected in tasks:
        for seed in [42, 43, 44]:
            cases.append({'id': f'{case_id}__proposed__{mode}__{seed}', 'case_id': case_id,
                          'system_variant': 'proposed', 'mode': mode, 'seed': seed,
                          'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
                          'expected': expected, 'rubric': 'Entire visible content must parse as JSON; exact fields, values and types; no fences or extra prose.'})
assert len(cases) == 24
(D / 'cases.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in cases))
spec = {k: deepcopy(old[k]) for k in ['versions', 'modes', 'template_sha256', 'server_seed', 'concurrency', 'repetition_penalty', 'max_model_len']}
spec.update(purpose='Chinese JSON paired check on existing v018-loss3 and v019 adapters; no training',
            training=False, formal_holdout=False, cases_per_model=24, total_requests=48,
            system_sha256=sha(system_file), structured_output_constraints=False,
            models=[{'key': 'v018-loss3', 'alias': 't008-loss3', 'adapter': old['models']['loss3_adapter'], 'adapter_files': old['models']['adapter_files']},
                    {'key': 'v019', 'alias': 't008-new', 'adapter': '/models-work/t008-v019-20261020-211142/outputs/full/checkpoints/v0-20261020-211549/checkpoint-80', 'adapter_files': new['adapter_files']}],
            training_contamination_rule='All four diagnostic tasks remain development-only; no exact diagnostic prompt or answer added to the candidate.',
            parent_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
save('spec.json', spec)
save('authorization.json', {'approved': True, 'statement': '你继续，英文先不处理，可暂停UAT',
                           'scope': '48 Chinese JSON inference comparisons; restore UAT after diagnostics. Prepare 8 Chinese sample changes and CPU checks locally. No training.',
                           'recorded_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
shutil.copyfile(OLD / 'thinking-prefill.jinja', D / 'thinking-prefill.jinja')
for filename in ['execute.py', 'window.py']:
    text = (OLD / filename).read_text().replace('/tmp/chinese-check', '/tmp/json-check').replace('40-request', '48-request')
    (D / filename).write_text(text)
name = 't008-json-check-20261020-gpu'
(D / 'pod-name.txt').write_text(name + '\n')
pod = json.loads((OLD / 'pod-gpu.json').read_text())
pod['metadata'].update(name=name, labels={'t008-diagnostic': D.name})
pod['spec']['containers'][0]['command'][-1] = pod['spec']['containers'][0]['command'][-1].replace('/tmp/chinese-check', '/tmp/json-check')
save('pod-gpu.json', pod)
print(json.dumps({'prepared': True, 'requests': 48, 'cases_per_model': 24, 'training': False}))
