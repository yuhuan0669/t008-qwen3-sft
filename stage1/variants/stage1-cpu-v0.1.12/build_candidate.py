"""Build a local review snapshot from frozen parents; never starts training."""
from collections import Counter
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import math
import re
import shutil

from new_samples import make_specs

D = Path(__file__).resolve().parent
ROOT = D.parents[2]
PARENT = D.parent / 'stage1-cpu-v0.1.11'
RESTORE = D.parent / 'stage1-cpu-v0.1.10'
REL = D.relative_to(ROOT).as_posix()
RESTORED_LINES = [389, 803, 984, 1012]
INHERITED_LINES = [1065, 1183, 1253, 1262, 1264, 1271]
SOURCES = {
    'swift/self-cognition': 'identity', 't008/company-facts-v1': 'identity',
    't008/chinese-identity-v1': 'identity', 'swift/Qwen3-SFT-Mixin': 'generic',
    't008/strict-json-v1': 'generic', 't008/general-nonthinking-v1': 'generic',
    't008/general-nonthinking-v2': 'generic', 't008/project-positioning-v1': 'positioning',
    't008/business-evidence-v1': 'positioning',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def key(row):
    messages = [{'role': m['role'], 'content': m['content']} for m in row['messages']]
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def save(name, value):
    (D / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def jsonl(name, rows):
    (D / name).write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))


def rebind(value):
    if isinstance(value, str):
        return value.replace(PARENT.name, D.name)
    if isinstance(value, list):
        return [rebind(v) for v in value]
    if isinstance(value, dict):
        return {k: rebind(v) for k, v in value.items()}
    return value


def stats(rows):
    modes = Counter()
    record_modes = Counter()
    identity_language = Counter()
    for r in rows:
        group = SOURCES[r['dataset']]
        row_modes = []
        for m in r['messages']:
            if m['role'] != 'assistant':
                continue
            mode = 'empty_think' if re.search(r'<think>\s*</think>', m['content']) else 'nonempty_think'
            modes[group + '/' + mode] += 1
            row_modes.append(mode)
        record_modes[group + '/' + (row_modes[0] if len(set(row_modes)) == 1 else 'mixed')] += 1
        if group == 'identity':
            first_user = next(m['content'] for m in r['messages'] if m['role'] == 'user')
            identity_language['first_user_has_han' if re.search(r'[\u4e00-\u9fff]', first_user)
                              else 'first_user_no_han'] += 1
    return {'rows': len(rows), 'unique_message_records': len({key(r) for r in rows}),
            'source_exposures': dict(sorted(Counter(r['dataset'] for r in rows).items())),
            'group_exposures': dict(sorted(Counter(SOURCES[r['dataset']] for r in rows).items())),
            'record_format_exposures': dict(sorted(record_modes.items())),
            'assistant_turn_mode_counts': dict(sorted(modes.items())),
            'assistant_turns': sum(modes.values()),
            'multiturn_records': sum(sum(m['role'] == 'assistant' for m in r['messages']) > 1 for r in rows),
            'identity_first_user_language_marker': dict(sorted(identity_language.items()))}


assert sha(PARENT / 'train.jsonl') == '17a0ff1d3152dde611b31dab8d1ce84e1a0cbb7bb3536028b90900d6797d3121'
assert sha(RESTORE / 'train.jsonl') == '5b455659b0e3fea30efd5822be1a7fee0e57d2788bc0dcbf79ec755cd5f22788'
parent_raw = (PARENT / 'train.jsonl').read_bytes().splitlines(keepends=True)
restore_raw = (RESTORE / 'train.jsonl').read_bytes().splitlines(keepends=True)
parent = list(map(json.loads, parent_raw))
restoration_source = list(map(json.loads, restore_raw))
raw = parent_raw.copy()
changes = []
for n, line in enumerate(RESTORED_LINES, 1):
    raw[line - 1] = restore_raw[line - 1]
    changes.append({'id': f'RESTORE-{n:02}', 'operation': 'restore',
                    'line_one_based': line, 'row_zero_based': line - 1,
                    'restore_from_version': RESTORE.name, 'restore_from_line_one_based': line,
                    'before': parent[line - 1], 'after': restoration_source[line - 1]})
specs = make_specs(parent)
for n, s in enumerate(specs, len(raw) + 1):
    raw.append((json.dumps(s['record'], ensure_ascii=False) + '\n').encode())
    changes.append({'id': s['id'], 'operation': 'add', 'line_one_based': n, 'row_zero_based': n - 1,
                    'title': s['title'], 'group': s['group'], 'provenance': s['provenance'],
                    'before': None, 'after': s['record']})
data = b''.join(raw)
if (D / 'train.jsonl').exists():
    assert (D / 'train.jsonl').read_bytes() == data, 'Existing candidate differs; inspect before replacing it.'
else:
    (D / 'train.jsonl').write_bytes(data)
after = list(map(json.loads, raw))
digest = sha(D / 'train.jsonl')
assert len(after) == 1315
assert [i + 1 for i in range(1275) if raw[i] != parent_raw[i]] == RESTORED_LINES
assert [i + 1 for i in range(1275) if raw[i] != restore_raw[i]] == INHERITED_LINES
assert Counter(SOURCES[r['dataset']] for r in after) == {'identity': 236, 'generic': 1048, 'positioning': 31}
jsonl('new-samples.jsonl', specs)
jsonl('changes.jsonl', changes)
change_by_row = {c['row_zero_based']: c for c in changes}
mapping = []
for i, r in enumerate(after):
    c = change_by_row.get(i)
    mapping.append({'row_zero_based': i, 'line_one_based': i + 1,
                    'parent_version': PARENT.name, 'parent_row_zero_based': i if i < 1275 else None,
                    'parent_messages_sha256': key(parent[i]) if i < 1275 else None,
                    'messages_sha256': key(r), 'source': r['dataset'], 'group': SOURCES[r['dataset']],
                    'operation': c['operation'] if c else 'preserve', 'change_id': c['id'] if c else None,
                    'provenance_detail': 'changes.jsonl' if c else '../stage1-cpu-v0.1.11/train-map.jsonl'})
jsonl('train-map.jsonl', mapping)
identity_keys = sorted({key(r) for r in after if SOURCES[r['dataset']] == 'identity'})
identity_binding = {'dataset_path': REL + '/train.jsonl', 'dataset_sha256': digest,
                    'identity_exposures': 236, 'unique_messages': len(identity_keys),
                    'identity_sources': [s for s, group in SOURCES.items() if group == 'identity'],
                    'identity_message_sha256': identity_keys}
alias_path = D / 'native-identity-key-aliases.json'
if alias_path.exists():
    aliases = json.loads(alias_path.read_text())
    assert aliases['dataset_sha256'] == digest
    assert all(a['raw_messages_sha256'] in identity_keys for a in aliases['aliases'])
    matching = sorted(set(identity_keys) | {a['prepared_messages_sha256'] for a in aliases['aliases']})
    identity_binding.update(raw_identity_message_sha256=identity_keys,
                            identity_message_sha256=matching, matching_key_count=len(matching),
                            native_preprocessing_alias_count=len(matching) - len(identity_keys),
                            native_alias_source=alias_path.name)
save('identity-keys.json', identity_binding)
shutil.copyfile(PARENT / 'identity_loss3.py', D / 'identity_loss3.py')
shutil.copyfile(PARENT / 'COMPANY_FACTS.md', D / 'COMPANY_FACTS.md')
(D / 'evaluation').mkdir(exist_ok=True)
for p in (PARENT / 'evaluation').iterdir():
    if p.name == 'validation-spec.json':
        save('evaluation/' + p.name, rebind(json.loads(p.read_text())))
    elif p.is_file():
        shutil.copyfile(p, D / 'evaluation' / p.name)
cfg_before = json.loads((PARENT / 'training-config.json').read_text())
cfg = rebind(deepcopy(cfg_before))
cfg.update(plan='chinese-coverage-restoration-and-additions', dataset_sha256=digest, dataset_rows=len(after),
           estimated_full_optimizer_steps=math.ceil(len(after) / 16), config_revision='chinese-coverage-v0.1.12',
           recipe_change='Restore 4 natural identity records; append company facts 4, Chinese identity 16, generic nonthinking 12, business assistance 8. No hyperparameter change.',
           status='REVIEW_READY_NATIVE_CPU_PENDING', execution_authorized=False, resource_window=None,
           cpu_validation_report=None)
save('training-config.json', cfg)
save('config-diff.json', {'parent': str((PARENT / 'training-config.json').relative_to(ROOT)),
                        'parent_sha256': sha(PARENT / 'training-config.json'),
                        'argv_changes': [{'before': a, 'after': b} for a, b in zip(cfg_before['full_argv'], cfg['full_argv']) if a != b],
                        'dataset_rows': {'before': 1275, 'after': 1315},
                        'estimated_steps': {'before': 80, 'after': 83},
                        'identity_exposures': {'before': 216, 'after': 236},
                        'training_hyperparameters_unchanged': True, 'loss_plugin_bytes_unchanged': True,
                        'normalization_rule_unchanged': True, 'identity_index_regenerated': True,
                        'native_cpu_encoding_executed': False})
save('evaluation-config.json', rebind(json.loads((PARENT / 'evaluation-config.json').read_text())))
validation_plan = (PARENT / 'VALIDATION_PLAN.md').read_text().replace('10条样本对照', '恢复4条与新增40条样本对照')
validation_plan = validation_plan.replace('训练 v0.1.11', '训练 v0.1.12')
(D / 'VALIDATION_PLAN.md').write_text(validation_plan)
(D / 'SYSTEM_DIFF.md').write_text('# System和评分口径继承\n\n本版System、评分口径、开发题和JSON请求规格逐字节继承v0.1.11，未作新修订。修正后的vLLM聊天模板及采样预算不变。\n\n[当前System](evaluation/custom-system.txt) · [沿用的评分口径](evaluation/rubric.md) · [v0.1.11相对v0.1.10的历史System差异](../stage1-cpu-v0.1.11/SYSTEM_DIFF.md)。当前没有执行推理或部署。\n')
stat_before, stat_after, stat_added = stats(parent), stats(after), stats([s['record'] for s in specs])
stats_out = {'version': D.name, 'parent': PARENT.name, 'parent_sha256': sha(PARENT / 'train.jsonl'),
             'train_sha256': digest, 'before': stat_before, 'after': stat_after, 'added_records': stat_added,
             'restored_lines_one_based': RESTORED_LINES, 'inherited_v0111_edits_one_based': INHERITED_LINES,
             'added_rows': 40, 'restored_rows': 4, 'removed_rows': 0,
             'unchanged_parent_raw_lines': 1271, 'unchanged_v0110_raw_lines': 1269,
             'company_fact_records': {'before': 4, 'after': 4, 'note': 'Moved from four replaced slots into four new slots; not eight fact records.'},
             'supervised_tokens': {'status': 'PENDING_NATIVE_SWIFT_ENCODING', 'counts': None, 'weighted_share': None},
             'counts_note': 'A row is one dataset exposure per epoch. Multi-turn rows contain more than one assistant turn; unique messages and token counts are different measures.'}
save('statistics.json', stats_out)
save('validation.json', {'dataset_sha256': digest, 'rows': 1315, 'restored_rows': 4, 'added_rows': 40,
                       'group_exposures': stat_after['group_exposures'], 'english_records_changed': 0,
                       'json_training_records_changed': 0, 'native_swift_cpu_check': 'NOT_RUN',
                       'training_started': False, 'inference_executed': False, 'cluster_accessed': False})

review = ['# v0.1.12 样本前后对照\n',
          '本版供审阅，未训练。相对v0.1.11：恢复4条自然身份记录，再追加40条中文记录；1275＋40＝1315条。恢复不会额外增加行数。\n',
          '公司事实从原来占用的4个身份位置迁到新增区，事实记录仍为4条。其余6处修订原样保留：第1065、1183、1253、1262、1264、1271行，详见[上版对照](../stage1-cpu-v0.1.11/SAMPLE_DIFF.md)。英文及原4条JSON训练记录不变。\n',
          '[数据统计](STATISTICS.md) · [配置差异](CONFIG_DIFF.md) · [机器对照](changes.jsonl)\n',
          '## 一、恢复4条自然身份记录\n', '行号从1开始。下面“修改前”是v0.1.11，“恢复后”逐字节取自v0.1.10同一行。\n']


def show_record(record):
    output = []
    for n, m in enumerate(record['messages'], 1):
        output.extend([f"{'用户' if m['role'] == 'user' else '助手（含思考块）'}，消息{n}：\n",
                       '````text\n' + m['content'] + '\n````\n'])
    return output


for c in changes[:4]:
    review.append(f"### {c['id']}｜第{c['line_one_based']}行\n")
    review.append('**修改前（公司事实移至新增区）**\n')
    review.extend(show_record(c['before']))
    review.append('**恢复后（原自然身份问法，无/no_think标记）**\n')
    review.extend(show_record(c['after']))
review.extend(['## 二、新增40条中文记录\n',
               '新增行的“修改前”为不存在，未占用任何既有样本。每条只追加1次；身份8个场景各有空思考/短思考两种格式，不是同一记录反复复制。全部文本如下。\n',
               '| 编号 | 新行号 | 内容 | 分组 | 格式 |\n| --- | ---: | --- | --- | --- |'])
group_names = {'identity': '身份', 'generic': '通用', 'positioning': '业务定位'}
mode_names = {'empty_think': '空思考', 'short_think': '短思考'}
for n, s in enumerate(specs, 1276):
    review.append(f"| {s['id']} | {n} | {s['title']} | {group_names[s['group']]} | {mode_names[s['variant']]} |")
for n, s in enumerate(specs, 1276):
    review.extend([f"\n### {s['id']}｜第{n}行｜{s['title']}\n", '**修改前：** 无此行。\n',
                   f"**新增后：** {group_names[s['group']]}，{mode_names[s['variant']]}，本行1次曝光，监督权重×{3 if s['group'] == 'identity' else 1}。\n",
                   '来源：' + s['provenance'] + '\n'])
    review.extend(show_record(s['record']))
(D / 'SAMPLE_DIFF.md').write_text('\n'.join(review))

st = ['# v0.1.12 数据统计\n',
      '对比父版v0.1.11；本表按训练文件记录数统计，一轮使用每行一次。新增40条，不再限制总量；恢复4条不另增行。\n',
      '| 分组 | v0.1.11 | v0.1.12 | 净增加 |\n| --- | ---: | ---: | ---: |']
for g in ['identity', 'generic', 'positioning']:
    a, b = stat_before['group_exposures'][g], stat_after['group_exposures'][g]
    st.append(f'| {group_names[g]} | {a} | {b} | {b-a} |')
st.extend(['| **合计** | **1275** | **1315** | **40** |\n',
           '新增构成：公司事实4条＋中文身份16条＋普通非思考12条＋业务辅助/边界8条。公司事实是从原4个位置移出后追加，所以事实曝光仍4次；原4个自然身份问法的曝光已恢复。\n',
           f"去重后的完整消息记录：{stat_before['unique_message_records']} → {stat_after['unique_message_records']}。助手轮数：{stat_before['assistant_turns']} → {stat_after['assistant_turns']}；多轮记录：{stat_before['multiturn_records']} → {stat_after['multiturn_records']}。同一问题的空思考/短思考版本按两条不同消息记录计，不是两种独立问题。\n",
           '## 按来源统计\n', '| 来源 | 条数 |\n| --- | ---: |'])
for source, count in stat_after['source_exposures'].items():
    st.append(f'| {source} | {count} |')
st.extend(['\n## 回答格式（按助手轮统计）\n',
           '| 分组/格式 | 修改前 | 修改后 |\n| --- | ---: | ---: |'])
for mode in sorted(set(stat_before['assistant_turn_mode_counts']) | set(stat_after['assistant_turn_mode_counts'])):
    g, m = mode.split('/')
    name = group_names[g] + '/' + ('空思考' if m == 'empty_think' else '非空思考')
    st.append(f"| {name} | {stat_before['assistant_turn_mode_counts'].get(mode,0)} | {stat_after['assistant_turn_mode_counts'].get(mode,0)} |")
st.extend(['\n格式是文件内标签统计，不等同于真实推理模式下的效果。身份×3索引覆盖236条身份记录（含4条事实），按既有插件对该记录的有效监督加权；多轮身份记录的有效助手轮都继承×3。其他记录×1。\n',
           '## 保留与检查范围\n',
           '相对v0.1.11，原1275行中1271行保持原字节；另4行恢复为v0.1.10原字节。英文、原多轮记录及4条JSON训练样本均保留。没有重新引入已删除的底层保密话术、旧产品名回答或被清洗掉的异常样本。\n',
           '**监督token数、权重后占比、编码长度：待原生Swift CPU编码后统计。** 目前只报告行数、去重消息和助手轮；不能用236/1315的记录占比代替身份监督token占比。\n',
           f'数据SHA-256：`{digest}`。完整机器统计见[statistics.json](statistics.json)。\n'])
(D / 'STATISTICS.md').write_text('\n'.join(st))
(D / 'CONFIG_DIFF.md').write_text('''# v0.1.12 配置差异

本版只扩大已批准的中文数据覆盖；训练超参数、身份损失×3实现及归一化方式不改。配置供审阅，未执行。

| 项目 | v0.1.11 → v0.1.12 |
| --- | --- |
| 数据记录 | 1275 → 1315；恢复4行，追加40行 |
| 身份／通用／定位 | 216／1036／23 → 236／1048／31 |
| 一轮预计步数 | 80 → 83；增加仅来自数据行数，待编码后核验 |
| 数据绑定 | 版本目录、数据SHA、行数、身份索引及输出目录随新版本更新 |
| 训练起点 | 原始Qwen/Qwen3-8B＋新LoRA，不续训旧Adapter |
| LoRA与学习率 | r8、alpha32、dropout0.05、all-linear，lr1e-4 |
| 批次、轮数与长度 | batch1、梯度累积16、1epoch、max_length2048 |
| 损失 | 身份有效监督×3，其他×1；提示/空思考按既有策略屏蔽 |
| 归一化 | 加权token损失和除以未加权有效监督token数，插件原字节不变 |
| 其他 | BF16、梯度检查点、warmup0.05、seed/data_seed42 |
| 训练System | 无；preserve_thinking=false保持不变 |
| 评测 | 已修正vLLM模板、Non-thinking2048／Thinking4096、System和评分口径沿用上版 |

新增公司事实4条及中文身份16条纳入既有×3身份索引；通用12条和业务8条仍×1。身份多轮记录中有效助手轮一起继承该记录的×3权重，不修改插件归一化。原生Swift编码、实际loss mask与监督token统计仍待检查。

[机器配置差异](config-diff.json) · [训练配置](training-config.json) · [评测配置](evaluation-config.json)。本版训练及GPU窗口授权均为false。
''')
(D / 'README.md').write_text('''# v0.1.12 中文数据审阅包

**恢复4条自然身份记录，新增40条中文数据，总量1315条。仅本地准备，未启动训练或推理，英文原样保留。** 父版本v0.1.11与最新已训练版本v0.1.10均保留。

先看[样本前后对照](SAMPLE_DIFF.md)，再看[数据统计](STATISTICS.md)和[配置差异](CONFIG_DIFF.md)。

| 本次调整 | 数量 | 处理方式 |
| --- | ---: | --- |
| 恢复自然身份 | 4条 | 第389、803、984、1012行恢复为v0.1.10原文，不增加行数 |
| 公司事实 | 新增4条 | 将上版日期/所在地样本移到独立新行，空思考和短思考各覆盖 |
| 中文身份 | 新增16条 | 8个场景各有空思考/短思考版本，含简答、完整介绍、间接问法、多轮 |
| 普通非思考任务 | 新增12条 | 正常解释、摘要、改写、计算、指令执行与缺信息澄清，不插入身份 |
| 业务辅助与边界 | 新增8条 | 4对有依据/无依据、假设/实测场景，保留范围内的正常帮助 |

上版其余6处修订继续保留。原1275行中1271行逐字节不变，另外4行恢复原自然身份；公司事实仍4条。当前分组为身份236、通用1048、定位31。英文、原4条JSON训练记录、原多轮记录不改，新增示例不冒充真实公司项目或现场数据。

训练超参数与身份×3插件不变。因数据增加，一轮预计从80步变为83步；监督token占比及真实长度需原生Swift编码后才能给出。评测继续使用已修正vLLM模板，System和评分口径继承上版。

[本地检查](LOCAL_CHECK.md) · [数据文件](train.jsonl) · [逐行来源](train-map.jsonl) · [公司事实来源](COMPANY_FACTS.md) · [后续验证清单](VALIDATION_PLAN.md)。本次未操作集群、UAT或ClearML，未上传GitHub或Drive。
''')
print(json.dumps({'version': D.name, 'data_sha256': digest, 'after': stat_after}, ensure_ascii=False))
