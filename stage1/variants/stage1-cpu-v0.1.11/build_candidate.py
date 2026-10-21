"""Build the local review candidate only; no cluster, inference or training calls."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import difflib
import hashlib
import json
import re
import shutil

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARENT = D.parent / 'stage1-cpu-v0.1.10'
REL = D.relative_to(ROOT).as_posix()
PARENT_SHA = '5b455659b0e3fea30efd5822be1a7fee0e57d2788bc0dcbf79ec755cd5f22788'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def message_key(messages):
    value = [{'role': x['role'], 'content': x['content']} for x in messages]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def answer(body, thought=''):
    return '<think>\n' + (thought + '\n' if thought else '\n') + '</think>\n\n' + body


assert sha(PARENT / 'train.jsonl') == PARENT_SHA
raw_before = (PARENT / 'train.jsonl').read_bytes().splitlines(keepends=True)
before = [json.loads(x) for x in raw_before]
after = deepcopy(before)
changes = []


def replace(line, title, reason, body, thought='', question=None, source=None,
            preserved_lines=(), provenance='本任务人工修订；继承父版本来源映射，不冒充开源原文。'):
    i = line - 1
    r = after[i]
    assert len(r['messages']) == 2
    assert re.search(r'[\u4e00-\u9fff]', r['messages'][0]['content'])
    if question is not None:
        r['messages'][0]['content'] = question
    if source is not None:
        r['dataset'] = source
    r['messages'][-1]['content'] = answer(body, thought)
    changes.append({'id': f'CN11-{len(changes)+1:02}', 'title': title,
                    'parent_line_one_based': line, 'parent_row_zero_based': i,
                    'reason': reason, 'provenance': provenance,
                    'replacement_exposures': 1,
                    'effective_weight': 3 if r['dataset'] == 'swift/self-cognition' else 1,
                    'preserved_parent_lines': list(preserved_lines),
                    'before': before[i], 'after': deepcopy(r)})


company = '能碳章鱼（湖北）人工智能科技有限公司'
date_q = '你的研发公司是什么时候成立的？'
place_q = '研发你的公司在哪个城市、哪个区？'
fact_provenance = '本会话用户确认事实，见COMPANY_FACTS.md；沿用身份分组与×3权重，非swift原始事实。'
replace(389, '成立日期／空思考', '用一个重复短身份问法的曝光加入已确认日期；原短问法保留一次。',
        company + '成立于2026年7月8日。', question=date_q,
        preserved_lines=[185], provenance=fact_provenance)
replace(803, '成立日期／短思考', '同一事实覆盖自然问法的Thinking回答，不增加曝光。',
        company + '成立于2026年7月8日。', '已确认成立日期是2026年7月8日，只回答所问日期。',
        question=date_q, preserved_lines=[33], provenance=fact_provenance)
replace(984, '公司所在地／空思考', '加入已确认所在地；不推断总部或注册地址。',
        company + '位于湖北省武汉市武昌区。', question=place_q,
        preserved_lines=[116], provenance=fact_provenance)
replace(1012, '公司所在地／短思考', '同一事实覆盖Thinking回答；保留原短身份问法另一次曝光。',
        company + '位于湖北省武汉市武昌区。', '已确认所在地为湖北省武汉市武昌区，按所在地回答。',
        question=place_q, preserved_lines=[16], provenance=fact_provenance)

# Preserve both the original question and visible answer; change one duplicate's mode.
for line, peer in [(1065, 190), (1183, 1005)]:
    original = before[line-1]
    assert original == before[peer-1]
    old_answer = original['messages'][-1]['content']
    thought, body = old_answer.split('</think>', 1)
    assert thought.startswith('<think>') and thought[7:].strip()
    replace(line, '普通任务／非思考示例', '仅将一个重复记录的思考块置空；提问和可见答案逐字保留，另一份完整思考示例保留。',
            body.lstrip('\n'), source='t008/general-nonthinking-v1', preserved_lines=[peer],
            provenance='由swift/Qwen3-SFT-Mixin父记录衍生；仅改变思考块，单列衍生来源。')
    assert after[line-1]['messages'][-1]['content'].split('</think>', 1)[1] == body

replace(1253, '完整业务介绍／短思考', '保留批准的完整介绍正文，补充与文字辅助定位一致的简短思考示范。',
        before[1252]['messages'][-1]['content'].split('</think>', 1)[1].strip(),
        '产品面向工业企业、园区及公共机构，提供能源与碳排放管理的文字辅助，按此说明身份和范围。')
replace(1262, '普通翻译／不虚构知识库', '说明通用辅助与主营业务的区别，不把翻译能力解释为行业知识库训练或调用。',
        '不是。普通邮件翻译属于我可以提供的通用文字辅助，主营业务仍是能源管理和碳排放管理。请提供邮件文本，我可以据此翻译。',
        '按给定文本提供通用翻译，不推断已做行业知识库训练或接入检索工具。')
replace(1264, '设备操作／不虚构平台模块', '保持不能执行设备操作的边界，不进一步编造自有平台和控制菜单。',
        '当前对话没有设备控制工具，也没有执行结果，我不能替你调整锅炉参数。可以协助整理运行条件和操作前核对事项；实际操作请由有权限的现场人员按规程完成。',
        '用户同意不等于具备控制工具。本次没有执行依据，也不能据此编造产品的设备控制模块。')
replace(1271, '收益与案例／不作无依据保证', '保留可做测算的帮助，明确没有资料时不以虚构成功案例作保证。',
        '不能保证一定省电30%或一定回本，也不能代表公司承诺补偿。请提供基准用能、运行条件和投资成本，我可以帮助做标明假设的测算；实际效果需验证。没有已确认的项目资料时，我不会用所谓成功案例作保证。',
        '没有项目数据，不能承诺节能比例或回收期。只提供标明假设的测算，不编造公司业绩。')

changes.sort(key=lambda c: c['parent_row_zero_based'])
changed = [c['parent_row_zero_based'] for c in changes]
assert len(changed) == len(set(changed)) == 10
raw_after = raw_before.copy()
for c in changes:
    i = c['parent_row_zero_based']
    assert after[i] != before[i]
    for n in c['preserved_parent_lines']:
        assert before[n-1] == after[n-1]
    raw_after[i] = (json.dumps(after[i], ensure_ascii=False) + '\n').encode()
data = b''.join(raw_after)
if (D / 'train.jsonl').exists():
    assert (D / 'train.jsonl').read_bytes() == data, 'Existing review candidate differs; do not overwrite silently.'
else:
    (D / 'train.jsonl').write_bytes(data)
digest = sha(D / 'train.jsonl')
assert len(after) == 1275
assert sum(a != b for a, b in zip(raw_before, raw_after)) == 10
counts_before = Counter(r['dataset'] for r in before)
counts_after = Counter(r['dataset'] for r in after)
assert counts_after == {'swift/self-cognition': 216, 'swift/Qwen3-SFT-Mixin': 1030,
                        't008/general-nonthinking-v1': 2, 't008/strict-json-v1': 4,
                        't008/project-positioning-v1': 23}
for i, r in enumerate(before):
    if r['dataset'] == 't008/strict-json-v1' or not re.search(r'[\u4e00-\u9fff]', r['messages'][0]['content']):
        assert raw_before[i] == raw_after[i]
    for m in after[i]['messages']:
        if m['role'] == 'assistant':
            assert m['content'].count('<think>') == m['content'].count('</think>') == 1
            assert m['content'].split('</think>', 1)[1].strip()

(D / 'changes.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in changes))
(D / 'train-map.jsonl').write_text(''.join(json.dumps({
    'row_zero_based': i, 'parent_row_zero_based': i,
    'parent_messages_sha256': message_key(a['messages']), 'messages_sha256': message_key(b['messages']),
    'parent_source': a['dataset'], 'source': b['dataset'], 'changed': i in changed,
    'change_id': next((c['id'] for c in changes if c['parent_row_zero_based'] == i), None)
}, ensure_ascii=False) + '\n' for i, (a, b) in enumerate(zip(before, after))))
keys = sorted({message_key(r['messages']) for r in after if r['dataset'] == 'swift/self-cognition'})
save('identity-keys.json', {'dataset_path': REL + '/train.jsonl', 'dataset_sha256': digest,
    'identity_exposures': 216, 'unique_messages': len(keys), 'identity_message_sha256': keys})
shutil.copyfile(PARENT / 'identity_loss3.py', D / 'identity_loss3.py')

cfg = json.loads((PARENT / 'training-config.json').read_text())
old_argv = cfg['full_argv'].copy()
cfg['full_argv'] = [s.replace(PARENT.name, D.name) for s in old_argv]
cfg['smoke_overrides']['output_dir'] = cfg['smoke_overrides']['output_dir'].replace(PARENT.name, D.name)
cfg.update(plan='chinese-facts-scope-minimal', data_version=D.name, dataset_sha256=digest,
    execution_authorized=False, resource_window=None, status='REVIEW_READY_NATIVE_CPU_PENDING',
    config_revision='chinese-facts-scope-v0.1.11',
    recipe_change='Ten Chinese replacements: company facts 4, positioning 4, general nonthinking 2; total 1275 and identity exposures 216 unchanged.',
    runtime_validation='Local structure only; native Swift CPU encoding and actual token-loss-mask checks NOT RUN.',
    evaluation_config=REL + '/evaluation-config.json', cpu_validation_report=None)
save('training-config.json', cfg)
save('config-diff.json', {'parent': str((PARENT / 'training-config.json').relative_to(ROOT)),
    'parent_sha256': sha(PARENT / 'training-config.json'),
    'argv_changes': [{'before': a, 'after': b} for a, b in zip(old_argv, cfg['full_argv']) if a != b],
    'training_hyperparameters_unchanged': True, 'loss_plugin_bytes_unchanged': True,
    'normalization_rule_unchanged': True, 'identity_index_regenerated': True,
    'native_cpu_encoding_executed': False})

ev = json.loads((PARENT / 'evaluation-config.json').read_text())
ev.update(purpose='Review preparation; Chinese development and schema diagnostic NOT EXECUTED.',
    system_path=REL + '/evaluation/custom-system.txt', system_sha256=sha(D / 'evaluation/custom-system.txt'),
    rubric_path=REL + '/evaluation/rubric.md', additional_development_path=REL + '/evaluation/chinese-additional.jsonl',
    additional_development_seeds=[42, 43, 44], validation_plan=REL + '/VALIDATION_PLAN.md',
    prior_scope='v0.1.10 frozen outputs are the trained baseline, not results for this review candidate.',
    historical_scores_unchanged=True, execution_authorized=False,
    json_diagnostic_system_path=str((PARENT / 'evaluation/custom-system.txt').relative_to(ROOT)),
    json_diagnostic_system_sha256=sha(PARENT / 'evaluation/custom-system.txt'))
save('evaluation-config.json', ev)

diagnostic = ROOT / 'stage2/diagnostics/json-format-check-20261020/cases.jsonl'
cases = {}
for c in map(json.loads, diagnostic.read_text().splitlines()):
    cases.setdefault(c['case_id'], c)
schemas = {
 'DEV-07': {'type': 'object', 'properties': {'name': {'type': 'string'}, 'age': {'type': 'integer'}}, 'required': ['name','age'], 'additionalProperties': False},
 'JSON-NEW-01': {'type': 'array', 'items': {'type': 'object', 'properties': {'item': {'type': 'string'}, 'count': {'type': 'integer'}}, 'required': ['item','count'], 'additionalProperties': False}},
 'JSON-NEW-02': {'type': 'object', 'properties': {'running': {'type': 'boolean'}, 'alarm': {'type': 'boolean'}, 'owner': {'type': ['string','null']}}, 'required': ['running','alarm','owner'], 'additionalProperties': False},
 'JSON-NEW-03': {'type': 'object', 'properties': {'site': {'type': 'string'}, 'meter': {'type': 'object', 'properties': {'id': {'type': 'string'}, 'kwh': {'type': 'number'}}, 'required': ['id','kwh'], 'additionalProperties': False}}, 'required': ['site','meter'], 'additionalProperties': False},
}
schema_cases = [{'case_id': k, 'user_prompt': cases[k]['messages'][-1]['content'],
    'response_format': {'type': 'json_schema', 'json_schema': {'name': k.lower().replace('-', '_'), 'schema': schema}},
    'expected_for_scoring_only': cases[k]['expected']} for k, schema in schemas.items()]
(D / 'evaluation/json-schema-cases.jsonl').write_text(''.join(json.dumps(c, ensure_ascii=False) + '\n' for c in schema_cases))
dev = list(map(json.loads, (D / 'evaluation/chinese-additional.jsonl').read_text().splitlines()))
questions = {m['content'] for r in after for m in r['messages'] if m['role'] == 'user'}
assert not questions.intersection(t for c in dev for t in c['user_turns'])
assert not questions.intersection(c['user_prompt'] for c in schema_cases)
run = ROOT / 'stage2/runs/t008-v0110-20261020-224753'
save('evaluation/validation-spec.json', {
    'status': 'PREPARED_NOT_EXECUTED', 'training_authorized': False,
    'gpu_window_authorized': False, 'english_identity': 'DEFERRED',
    'baseline_model_version': 'stage1-cpu-v0.1.10',
    'baseline_adapter': 'stage2/local-models/stage1-cpu-v0.1.10/adapter.zip',
    'baseline_adapter_sha256': 'b5ed8d2ca6ce580d73c034284b1d160a8bbbf4abb3b9555584132bc08c3b8058',
    'baseline_results': str((run / 'development/results.jsonl').relative_to(ROOT)),
    'baseline_results_sha256': sha(run / 'development/results.jsonl'),
    'baseline_report': str((run / 'REPORT.md').relative_to(ROOT)),
    'chat_template': ev['chat_template'], 'request_modes': ev['request_modes'],
    'seeds': [42, 43, 44], 'concurrency': 1, 'repetition_penalty': 1.0,
    'json_probe': {'conditions': 24, 'new_schema_requests': 24,
                   'unconstrained_requests_if_cache_incompatible': 24,
                   'cache_reuse_requires_runtime_and_prompt_match': True,
                   'preflight_not_counted': True,
                   'system_path': ev['json_diagnostic_system_path'],
                   'system_sha256': ev['json_diagnostic_system_sha256'],
                   'cases_path': REL + '/evaluation/json-schema-cases.jsonl',
                   'expected_for_scoring_only_must_not_be_sent': True},
    'chinese_additional': {'scenarios': len(dev), 'sessions_per_model': len(dev)*2*2*3,
                          'requests_per_model': sum(len(c['user_turns']) for c in dev)*2*2*3,
                          'systems': ['none', REL + '/evaluation/custom-system.txt'],
                          'proposed_system_sha256': ev['system_sha256'],
                          'cases_path': REL + '/evaluation/chinese-additional.jsonl',
                          'use_actual_assistant_history': True},
    'formal_holdout_accessed': False, 'formal_acceptance': False})

def mode_counts(rows):
    out = Counter()
    for r in rows:
        group = 'identity' if r['dataset'] == 'swift/self-cognition' else 'positioning' if r['dataset'] == 't008/project-positioning-v1' else 'generic'
        for m in r['messages']:
            if m['role'] == 'assistant':
                mode = 'empty_think' if re.search(r'<think>\s*</think>', m['content']) else 'nonempty_think'
                out[group + '/' + mode] += 1
    return dict(sorted(out.items()))

save('validation.json', {'verified_local_structure': True, 'native_swift_cpu_check': 'NOT_RUN',
    'parent_sha256': PARENT_SHA, 'dataset_sha256': digest, 'rows': len(after),
    'source_exposures_before': dict(counts_before), 'source_exposures_after': dict(counts_after),
    'changed_rows_zero_based': changed, 'unchanged_raw_lines': 1265,
    'added_rows': 0, 'removed_rows': 0, 'identity_exposures': 216,
    'identity_company_fact_exposures_before': 0, 'identity_company_fact_exposures_after': 4,
    'other_identity_exposures_before': 216, 'other_identity_exposures_after': 212,
    'generic_total_exposures': 1036, 'positioning_exposures': 23,
    'assistant_turn_mode_counts_before': mode_counts(before), 'assistant_turn_mode_counts_after': mode_counts(after),
    'english_records_changed': 0, 'json_training_records_changed': 0,
    'preserved_parent_peer_lines': sorted(n for c in changes for n in c['preserved_parent_lines']),
    'exact_development_prompt_overlap': 0, 'formal_holdout_accessed': False,
    'training_started': False, 'inference_executed': False, 'cluster_accessed': False})

review = ['# v0.1.11：10条中文样本修改前后对照\n',
    '父版本为已训练的v0.1.10。本版仅供审阅，尚未实际Swift编码或训练。行号为父版本train.jsonl的1起始行号。\n',
    '总量1275、身份216、通用1036、定位23不变；1265行原字节保留。4次原短身份问法曝光改为公司事实（日期2次、所在地2次），各原问法仍保留一次。英文和4条JSON训练记录不变。\n',
    '2条普通任务保留问题与可见答案，只把其中一份思考块置空；另一份原完整思考记录保留。这是格式示范调整，不是原数据截断修复。\n',
    '| 父版行号 | 修改内容 | 直接原因 |\n| ---: | --- | --- |']
for c in changes:
    review.append(f"| {c['parent_line_one_based']} | {c['title']} | {c['reason']} |")
for c in changes:
    review += [f"\n## {c['id']}｜{c['title']}｜父版第{c['parent_line_one_based']}行\n",
               c['reason'] + '\n', f"来源：{c['provenance']}\n",
               f"替换1次；有效监督权重×{c['effective_weight']}；保留的原同问法/原副本行：{c['preserved_parent_lines'] or '不适用'}。\n"]
    for label in ('before', 'after'):
        review.append('### ' + ('修改前' if label == 'before' else '修改后') + '\n')
        for m in c[label]['messages']:
            review += [('提问' if m['role'] == 'user' else '回答（含思考块）') + '：\n',
                       '````text\n' + m['content'] + '\n````\n']
(D / 'SAMPLE_DIFF.md').write_text('\n'.join(review))
system_diff = ''.join(difflib.unified_diff((PARENT / 'evaluation/custom-system.txt').read_text().splitlines(True),
    (D / 'evaluation/custom-system.txt').read_text().splitlines(True), fromfile='v0.1.10 System', tofile='v0.1.11 proposed System'))
(D / 'SYSTEM_DIFF.md').write_text('# System修订对照\n\n仅为待验证的推理System，不进入训练数据，不部署UAT。\n\n```diff\n' + system_diff + '```\n\nJSON接口约束实验继续用v0.1.10 System；新中文场景先在v0.1.10模型上验证本版System，随后才比较未来候选。\n')
save('manifest.json', {'version': D.name, 'status': 'REVIEW_READY_NATIVE_CPU_PENDING',
    'parent_version': PARENT.name, 'parent_path': str((PARENT / 'train.jsonl').relative_to(ROOT)),
    'parent_sha256': PARENT_SHA, 'train_path': REL + '/train.jsonl', 'train_sha256': digest,
    'rows': len(after), 'changed_rows_zero_based': changed, 'source_exposures': dict(counts_after),
    'added_rows': 0, 'removed_rows': 0, 'unchanged_raw_lines': 1265,
    'training_started': False, 'native_cpu_verified': False, 'inference_executed': False,
    'cluster_accessed': False, 'sync_status': 'LOCAL_GIT_ONLY',
    'files_sha256': {p.relative_to(D).as_posix(): sha(p) for p in sorted(D.rglob('*'))
                     if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts}})
print(json.dumps({'version': D.name, 'changed_lines': [i+1 for i in changed], 'data_sha256': digest,
                  'mode_counts_before': mode_counts(before), 'mode_counts_after': mode_counts(after)}, ensure_ascii=False))
