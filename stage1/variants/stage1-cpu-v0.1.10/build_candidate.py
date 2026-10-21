"""Eight Chinese-only replacements; preserve all other raw records and training parameters."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARENT = ROOT / 'stage1/variants/stage1-cpu-v0.1.9'
REL = D.relative_to(ROOT).as_posix()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
def key(messages):
    value = [{'role': m['role'], 'content': m['content']} for m in messages]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

assert sha(PARENT / 'train.jsonl') == 'c2fa7ced3c438a323217d1d3a0d3657607c3ad89d6cd1e6a75480330c7fbbf16'
raw = (PARENT / 'train.jsonl').read_bytes().splitlines(keepends=True)
before = [json.loads(x) for x in raw]
after = deepcopy(before)
changes = []
identity = [
    (449, '中文名字问法一', '已知产品名称为能碳章鱼垂直大模型。本题只问名字，直接给出名称，不追加版本或公司介绍。', '我的名字是能碳章鱼垂直大模型。'),
    (946, '中文名字问法二', '当前产品的固定名称是能碳章鱼垂直大模型。回答该名称即可，不猜测版本号。', '我叫能碳章鱼垂直大模型。'),
    (877, '中文研发方问法', '已知研发主体是能碳章鱼（湖北）人工智能科技有限公司。本题回答研发公司，不推测人员姓名、成立时间或其他背景。', '我的研发公司是能碳章鱼（湖北）人工智能科技有限公司。'),
    (1074, '中文创作者问法', '本题询问当前产品的研发主体，已知公司全称为能碳章鱼（湖北）人工智能科技有限公司。回答全称后结束。', '我由能碳章鱼（湖北）人工智能科技有限公司研发。'),
]
for n, title, thought, body in identity:
    i = n - 1
    original = before[i]
    assert original['dataset'] == 'swift/self-cognition'
    assert '/no_think' not in original['messages'][0]['content']
    assert re.search(r'<think>\s*</think>', original['messages'][-1]['content'])
    # The paired source question with /no_think remains untouched.
    paired = [j + 1 for j, r in enumerate(before) if r['dataset'] == original['dataset']
              and r['messages'][0]['content'] == original['messages'][0]['content'] + ' /no_think']
    assert paired, n
    after[i]['messages'][-1]['content'] = '<think>\n' + thought + '\n</think>\n\n' + body
    changes.append({'id': 'IDENTITY-' + str(len(changes) + 1), 'title': title,
                    'parent_train_row_zero_based': i, 'parent_line_one_based': n,
                    'reason': 'Extend natural Chinese short-thinking identity coverage; answer the requested field and end.',
                    'replacement_exposures': 1, 'paired_nonthinking_source_lines_preserved': paired,
                    'effective_weight': 3, 'before': original, 'after': after[i]})

product_question = '只输出JSON对象：把商品“铅笔”和数量4写入product和quantity两个字段，不要添加其他文字。'
array_question = '仅输出JSON数组，按顺序记录两本书：《春日》有库存，备注未提供；《山海》无库存，备注未提供。每项只有title、in_stock、note三个字段；in_stock用布尔值，未提供的备注用null。'
formats = [
    (1064, 'JSON对象 / Non-thinking', product_question, '', '{"product":"铅笔","quantity":4}'),
    (1160, 'JSON对象 / Thinking', product_question, '要求的是JSON对象，product用字符串，quantity用数字。正文只输出对象，不加代码围栏或说明。', '{"product":"铅笔","quantity":4}'),
    (1174, 'JSON数组 / Non-thinking', array_question, '', '[{"title":"春日","in_stock":true,"note":null},{"title":"山海","in_stock":false,"note":null}]'),
    (1190, 'JSON数组 / Thinking', array_question, '有库存对应true，无库存对应false；只有未提供的备注用null。按原顺序输出对象数组，正文不加代码围栏或说明。', '[{"title":"春日","in_stock":true,"note":null},{"title":"山海","in_stock":false,"note":null}]'),
]
for n, title, question, thought, body in formats:
    i = n - 1
    original = before[i]
    peers = [j + 1 for j, r in enumerate(before) if r == original and j != i]
    assert original['dataset'] == 'swift/Qwen3-SFT-Mixin' and len(peers) == 1
    assert re.search(r'[\u4e00-\u9fff]', original['messages'][0]['content'])
    json.loads(body)
    content = '<think>\n' + (thought if thought else '\n') + '\n</think>\n\n' + body
    if not thought:
        content = '<think>\n\n</think>\n\n' + body
    after[i] = {'dataset': 't008/strict-json-v1', 'messages': [{'role': 'user', 'content': question}, {'role': 'assistant', 'content': content}]}
    changes.append({'id': 'FORMAT-' + str(len(changes) - 3), 'title': title,
                    'parent_train_row_zero_based': i, 'parent_line_one_based': n,
                    'reason': 'Replace one Chinese generic duplicate with an authored strict-format example; retain the original example once.',
                    'replacement_exposures': 1, 'original_copy_preserved_at_parent_lines': peers,
                    'provenance': 'Authored for this task; not original Qwen3-SFT-Mixin material.',
                    'effective_weight': 1, 'before': original, 'after': after[i]})
changes.sort(key=lambda c: c['parent_train_row_zero_based'])
changed = [c['parent_train_row_zero_based'] for c in changes]
assert len(changed) == len(set(changed)) == 8
for change in changes:
    for n in change.get('paired_nonthinking_source_lines_preserved', []) + change.get('original_copy_preserved_at_parent_lines', []):
        assert after[n - 1] == before[n - 1]
    raw[change['parent_train_row_zero_based']] = (json.dumps(change['after'], ensure_ascii=False) + '\n').encode()
target = b''.join(raw)
if (D / 'train.jsonl').exists():
    assert (D / 'train.jsonl').read_bytes() == target
else:
    (D / 'train.jsonl').write_bytes(target)
assert len(after) == 1275
counts = Counter(r['dataset'] for r in after)
assert counts == {'swift/Qwen3-SFT-Mixin': 1032, 'swift/self-cognition': 216, 't008/project-positioning-v1': 23, 't008/strict-json-v1': 4}
diagnostic = ROOT / 'stage2/diagnostics/json-format-check-20261020/cases.jsonl'
held_questions = {x['messages'][-1]['content'] for x in map(json.loads, diagnostic.read_text().splitlines())}
assert not held_questions.intersection(m['content'] for r in after for m in r['messages'] if m['role'] == 'user')
digest = sha(D / 'train.jsonl')
(D / 'changes.jsonl').write_text(''.join(json.dumps(x, ensure_ascii=False) + '\n' for x in changes))
(D / 'train-map.jsonl').write_text(''.join(json.dumps({'row_zero_based': i, 'parent_row_zero_based': i,
    'parent_messages_sha256': key(a['messages']), 'messages_sha256': key(b['messages']),
    'parent_source': a['dataset'], 'source': b['dataset'], 'changed': i in changed}) + '\n' for i, (a, b) in enumerate(zip(before, after))))
keys = sorted({key(r['messages']) for r in after if r['dataset'] == 'swift/self-cognition'})
save('identity-keys.json', {'dataset_path': REL + '/train.jsonl', 'dataset_sha256': digest,
    'identity_exposures': 216, 'unique_messages': len(keys), 'identity_message_sha256': keys})
shutil.copyfile(PARENT / 'identity_loss3.py', D / 'identity_loss3.py')
cfg = json.loads((PARENT / 'training-config.json').read_text())
prior_argv = cfg['full_argv'].copy()
cfg['full_argv'] = [s.replace('stage1-cpu-v0.1.9', D.name) for s in prior_argv]
cfg['smoke_overrides']['output_dir'] = cfg['smoke_overrides']['output_dir'].replace('stage1-cpu-v0.1.9', D.name)
cfg.update(plan='chinese-identity-json-minimal', data_version=D.name, dataset_sha256=digest,
    execution_authorized=False, resource_window=None, status='CPU_CHECK_PENDING_NO_TRAINING',
    config_revision='chinese-identity-json-v0.1.10',
    recipe_change='Four Chinese identity replacements and four authored JSON replacements; total 1275 and identity 216 unchanged.',
    runtime_validation='Pending native Swift CPU encoding', evaluation_config=REL + '/evaluation-config.json',
    cpu_validation_report=REL + '/cpu-check/report.json')
save('training-config.json', cfg)
save('config-diff.json', {'parent': str((PARENT / 'training-config.json').relative_to(ROOT)),
    'parent_sha256': sha(PARENT / 'training-config.json'),
    'argv_changes': [{'before': a, 'after': b} for a, b in zip(prior_argv, cfg['full_argv']) if a != b],
    'training_hyperparameters_unchanged': True, 'loss_plugin_bytes_unchanged': True,
    'normalization_rule_unchanged': True, 'identity_index_regenerated': True,
    'expected_optimizer_steps': 80, 'expected_epoch': 1})
(D / 'evaluation').mkdir(exist_ok=True)
shutil.copyfile(PARENT / 'evaluation/custom-system.txt', D / 'evaluation/custom-system.txt')
ev = json.loads((PARENT / 'evaluation-config.json').read_text())
ev.update(system_path=REL + '/evaluation/custom-system.txt', purpose='Frozen Chinese evaluation settings for future candidate; English deferred.',
    prior_scope='Existing v018-loss3/v019 JSON comparisons do not evaluate this untrained candidate.',
    prior_protocol_check='stage2/diagnostics/json-format-check-20261020/REPORT.md')
save('evaluation-config.json', ev)
save('validation.json', {'verified_local_structure': True, 'actual_swift_cpu_check': 'PENDING',
    'parent_sha256': sha(PARENT / 'train.jsonl'), 'dataset_sha256': digest, 'rows': len(after),
    'source_exposures': dict(counts), 'changed_rows_zero_based': changed, 'unchanged_raw_lines': 1267,
    'added_rows': 0, 'removed_rows': 0, 'identity_exposures': 216, 'generic_total_exposures': 1036,
    'positioning_exposures': 23, 'english_identity_records_changed': 0,
    'chinese_identity_replacements': 4, 'chinese_generic_replacements': 4,
    'original_generic_copies_retained': True, 'paired_nonthinking_identity_records_retained': True,
    'diagnostic_prompt_overlap': 0, 'training_started': False})
save('manifest.json', {'version': D.name, 'status': 'CPU_CHECK_PENDING_NO_TRAINING',
    'parent_version': PARENT.name, 'parent_path': str((PARENT / 'train.jsonl').relative_to(ROOT)),
    'parent_sha256': sha(PARENT / 'train.jsonl'), 'train_path': REL + '/train.jsonl', 'train_sha256': digest,
    'rows': len(after), 'changed_rows_zero_based': changed, 'source_exposures': dict(counts),
    'added_rows': 0, 'removed_rows': 0, 'training_started': False, 'sync_status': 'LOCAL_GIT_ONLY',
    'files_sha256': {'train.jsonl': digest}})
review = ['# v0.1.10：8 条中文样本修改前后对照\n',
          '父版本 v0.1.9。总量 1275、身份曝光 216、通用曝光合计 1036、定位曝光 23 不变。英文身份和全部定位样本保持原样。只替换列出的 8 个位置；其余 1267 行逐字节不变。\n',
          '4 条 JSON 为本任务新编示例，单列 `t008/strict-json-v1` 来源；它们替换 4 条中文通用记录各自的第二次曝光，原记录仍各保留一次。没有将这些新示例冒记为开源原始数据。\n',
          '以下为完整内容，行号均以父版本 train.jsonl 的 1 起始行号计。\n']
for c in changes:
    review += [f"## {c['id']}｜{c['title']}｜父版本第 {c['parent_line_one_based']} 行\n",
               f"替换次数：1；有效答案权重：{c['effective_weight']}。\n",
               '修改前：\n', '````json\n' + json.dumps(c['before'], ensure_ascii=False, indent=2) + '\n````\n',
               '修改后：\n', '````json\n' + json.dumps(c['after'], ensure_ascii=False, indent=2) + '\n````\n']
(D / 'SAMPLE_DIFF.md').write_text('\n'.join(review))
print(json.dumps({'version': D.name, 'rows': len(after), 'changed_rows_one_based': [i+1 for i in changed], 'data_sha256': digest, 'source_exposures': dict(counts)}, ensure_ascii=False))
