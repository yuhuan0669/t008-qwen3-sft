"""Bind engineer review decisions to frozen source records and write reports."""
import collections
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def read_rows(name):
    return [json.loads(s) for s in (HERE / name).read_text().splitlines()]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    inputs = {x['source_line_one_based']: x for x in read_rows('mixin_all.jsonl')}
    raw_reviews = read_rows('review_a.jsonl') + read_rows('review_b.jsonl')
    assert len(raw_reviews) == len(inputs) == 177
    assert len({r['source_line_one_based'] for r in raw_reviews}) == 177
    reviewed_all_nonreject = {105, 210, 299, 421, 439, 543, 613, 660, 697, 889, 991}
    reviewed_reject_examples = {23, 31, 39, 69, 282, 431, 548, 563, 580, 763, 899}
    sources = {
        282: ['https://web.mit.edu/6.013_book/www/chapter9/9.html'],
        431: ['https://www.kroger.com/b/simple-truth'],
        613: ['https://dev.mysql.com/doc/refman/8.4/en/index-merge-optimization.html'],
        932: ['https://docs.nestjs.com/'],
    }
    reviews = []
    for raw_review in sorted(raw_reviews, key=lambda r: r['source_line_one_based']):
        row = dict(raw_review)
        line = row['source_line_one_based']
        source = inputs[line]
        assert row['status'] in {'PASS_INITIAL', 'REJECT', 'NEEDS_REVIEW'}
        assert row['evidence_snippet'] in source['final_answer'], line
        assert len(row['evidence_snippet']) <= 200
        for key in ('source_record_sha256', 'snapshot_indices_zero_based', 'tokens'):
            if key in row:
                assert row[key] == source[key], (line, key)
            row[key] = source[key]
        row['exposures'] = len(source['snapshot_indices_zero_based'])
        row['primary_review'] = ('question_and_full_final_answer' if line in reviewed_all_nonreject | reviewed_reject_examples else 'coverage_binding_and_evidence_checks')
        if line in {210, 299, 439, 889, 991}:
            row['primary_review'] += '_plus_full_response_reasoning_read'
        row['primary_source_urls'] = sources.get(line, [])
        if line == 613:
            row['primary_note'] = 'MySQL官方手册说明index_merge的key字段列出参与索引；原示意列仅index1却Extra声称union(index1,index2)。保持待复核，未运行数据库或验证性能。'
        if line in {299, 439}:
            row['primary_cpu_evidence'] = 'reviewed_javascript_checks.json'
        if line == 991:
            row['primary_cpu_evidence'] = 'reviewed_python_checks.json'
            row['primary_note'] = '1000次有界生成功能检查符合15位及四类字符约束；不证明密码学安全或全空间均匀分布。推理中的常量列举不准确为非阻断备注。'
        if line == 563:
            row['primary_cpu_evidence'] = 'nutrition_arithmetic_check.json'
            row['primary_note'] = '主审复算纠正子审初稿495为490kcal；原回答声称520。子审已回改该理由，决定仍为REJECT。'
        reviews.append(row)
    assert {r['source_line_one_based'] for r in reviews if r['status'] != 'REJECT'} == reviewed_all_nonreject
    counts = collections.Counter(r['status'] for r in reviews)
    assert counts == {'REJECT': 166, 'NEEDS_REVIEW': 7, 'PASS_INITIAL': 4}
    truncation = [r for r in reviews if any('TRUNCAT' in code for code in r['reason_codes'])]
    assert len(truncation) == 149, len(truncation)
    (HERE / 'mixin_review.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in reviews))
    for filename, expected in json.loads((HERE / 'frozen_input_fingerprints.json').read_text()).items():
        assert digest(Path(filename)) == expected, filename
    identity = json.loads((HERE / 'identity_review_summary.json').read_text())
    summary = {
        'schema': 't008-followup-engineering-content-review-v1',
        'assembled_at_utc': datetime.now(timezone.utc).isoformat(),
        'mixin_unique_reviewed': 177, 'mixin_exposures_mapped': 354,
        'mixin_status_unique_counts': dict(counts),
        'mixin_status_exposure_counts': {k: v * 2 for k, v in counts.items()},
        'mixin_explicit_truncation_unique_count': len(truncation),
        'mixin_pass_initial_source_lines': [r['source_line_one_based'] for r in reviews if r['status'] == 'PASS_INITIAL'],
        'mixin_needs_review_source_lines': [r['source_line_one_based'] for r in reviews if r['status'] == 'NEEDS_REVIEW'],
        'identity': identity,
        'primary_all_nonreject_rechecked': True,
        'primary_reject_examples_rechecked': sorted(reviewed_reject_examples),
        'frozen_input_hashes_unchanged': True,
        'training_data_modified': False, 'training_started': False,
        'approval_created': False, 'independent_blind_acceptance': False,
        'gpu_gate_recommendation': 'NO_GO',
        'not_performed': ['原2048候选内521条不同Mixin记录的逐条内容审核',
                          '对全部177条推理文本逐项事实验证或全部代码运行',
                          '7条专业/来源待核事项的最终裁定',
                          '身份样本改写、采样重配、训练衍生快照生成',
                          '独立盲审、GPU Smoke/Full、训练效果评测'],
    }
    (HERE / 'review_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    report = '''# T-008 v1.2｜2560新增记录与身份模板工程内容初审

结论：**不建议直接使用“剔除302条后剩余1996次曝光”的2560版本训练。GPU门禁仍为No-Go。** 1996只是长度与指定排除条件下的数量，不是内容质量通过数。本轮没有修改任何训练快照，也没有创建批准记录、启动训练或操作现有服务。

## 审核范围与方法

- 用实际Swift逐条长度证据和原始messages精确匹配，重建从2048升到2560后新增的177条不同Mixin记录，映射354次既有曝光。保留原始行号、两次曝光零基索引和原记录规范化SHA-256。
- 两组工程子审分别逐条读取89/88条的完整用户问题与完整final_answer；必要时查看推理。主Agent复核全部11条非REJECT、11个REJECT示例及所有记录的行号/hash绑定与原文证据片段。
- 主Agent逐条读取108条身份原始问答，并按已确认名称与既有600次loader曝光精确匹配。
- 这是继承项目上下文的工程初审，**不是独立盲审或独立验收**；没有将角色切换称为独立性。

## 新增177条通用记录

| 初审结论 | 不同记录 | 对应曝光 |
|---|---:|---:|
| PASS_INITIAL | 4 | 8 |
| NEEDS_REVIEW | 7 | 14 |
| REJECT（建议排除） | 166 | 332 |
| 合计 | 177 | 354 |

其中149条有明确的正文截断问题；其他拒绝理由包括任务未完成、代码逻辑错误、内部算术矛盾、科学或技术概念错误。理由可重叠，不相加成新的样本数。

4条初审通过：原始JSONL行210（零售数据挖掘方案）、299（JS数字平方对象）、439（HTML姓名/日期问候）、991（Python生成15位随机字符串）。通过只表示在已声明核验范围内未发现阻断性问题，不保证所有推理细节无瑕疵、代码所有输入皆正确或训练一定提升。

7条待复核：行105（Eight Shuffle术语）、421（Unity书目/课程资源）、543（Instagram Explore机制）、613（MySQL索引合并）、660（临床护理方案）、697（ArcGIS版本/代理）、889（法律责任分析）。未把领域事实不确定性当作已核实错误，也未放行为训练合格。

典型可复算证据：
- 行23：回答链接未闭合；清洗正则删除全部中文，LSTM示例也有接口/张量逻辑问题。
- 行31：外积矩阵在公式中途结束；行39：C++数组初始化中断。
- 行563：原表11项食物热量实际合计490kcal，汇总写520；10项汇总中7项不一致。仅验证表内算术，不声称食品数据库数值或营养建议已通过专业核验。
- 行580：同文假设市场500M、目标10%=50M，预测却是500000件×10=5M，且缺少要求的竞争分析。
- 行899：Ruby交换逻辑本身可读完整，但代码围栏未闭合；理由明确为输出格式不完整，不冒称交换算法错误。

有</think>与其后非空回答，不能证明最终答案完整；本轮发现大量原文最终回答已截断。原始文件与冻结messages的逐字对应证明这些现象存在于来源内容，不能归咎本次2048过滤。上游是否因具体生成参数达到长度上限仍无finish_reason证据，不能写成已证实原因。

## 身份108模板 / 600次曝光

| 初审结论 | 不同模板 | 曝光 |
|---|---:|---:|
| PASS_INITIAL | 23 | 127 |
| NEEDS_REVIEW | 82 | 456 |
| REJECT（建议排除） | 3 | 17 |

原78条/434次研发归属语义问题仍待澄清；新增4条/22次未回答具体产品身份。3条/17次对文心一言研发方只答“不知道”，属于不宜选作优质监督目标的非信息性回答。详见identity_review_summary.md和逐行JSONL。

23条初审通过中只有2条直接教授已确认产品名称，其余为一般能力、克制回答或其他模型归属事实。因此不能简单以这127次曝光替代600次，宣称身份覆盖已完整。官方英文名字确认不自动证明未区分定制与基座研发的句子适合训练。

## CPU补充检查与主审纠错

- JS行299两种实现、5种输入组合，共10项功能检查；HTML行439在受限VM与DOM stub/固定日期下1项检查，共11项通过。未做真实浏览器渲染。
- Python行991在100个seed下生成1000个字符串，长度、允许字符及四类字符约束全部通过。不证明密码学安全或所有合格字符串等概率；推理常量列举不准确已记为非阻断瑕疵。
- 行563用Decimal重算10列，发现子审初稿将热量写495，主审纠正为490，子审已更正；拒绝结论不变。审核本身也保留纠错边界。
- 主审对部分技术理由补充一手来源核对：磁场内部H与外加H区别、MySQL参与索引列表、NestJS属Node.js、Simple Truth品牌来源。没有据此宣称其他领域断言都已外查。

## 对方案建议的更新

先前建议2560的前提是新增177条内容通过；该前提未成立。**当前应暂停以提高max_length扩充训练集的决定，先核准身份口径并审核原2048候选内的521条通用记录。** 2560只是容纳上限，不是质量保证；本轮4条初审通过不足以证明升级长度能带来可测收益。

原设计23.08%、2048候选36.54%、2560结构候选30.06%均为含重复的曝光占比。约23.1%只能作为原设计对照锚点，不是已验证最优值；在最终合格数据确定前，419次身份或1815次总曝光的先前算术示例不能当作可训练交付结果。应先保证名称/定制主体/基座三者语义正确与覆盖，再比较配比和实际效果。

本轮未审核原有521条通用记录全部内容、未完成7条待复核专业事项、未改写身份问答、未补采、未形成新训练快照、未做独立验收或GPU训练。所有审核状态均不授予下一阶段权限。

## 复算与证据索引

输入位置：原CPU包work/upstream-raw/、work/original-v1.2/及evidence/template/original-final/。

1. python3 rebuild_review_inputs.py --verify
2. python3 build_identity_review.py
3. node verify_reviewed_javascript.cjs
4. python3 verify_reviewed_python.py
5. python3 verify_nutrition_arithmetic.py
6. python3 assemble_review.py

第2至6步只写当前审核目录的记录/证据；不会写原始快照或训练数据。复算完整源文件位于相邻旧CPU目录；审核包自身包含177条与108条审核副本，不能冒称包含完整2600条原训练快照。

- mixin_review.jsonl：177条整合审核结果。
- review_a.jsonl / review_b.jsonl：两组逐条初审记录及各自摘要。
- identity_review.jsonl：108条身份记录及曝光映射。
- review_summary.json：机器可读结果与未完成事项。
- frozen_input_fingerprints.json：5个旧包关键文件审核前SHA-256，组装时已再次核对不变。
- MANIFEST.json：本补充包逐文件SHA-256；上传回读凭据单独保存，避免将包外交付证明伪装成包内内容。

一手来源：
- https://qwenlm.github.io/blog/qwen3/
- https://openai.com/index/chatgpt/
- https://agents.baidu.com/docs/develop/model/ERNIE_bot_introduce/
- https://ai.baidu.com/support/news?action=detail&id=3108
- https://web.mit.edu/6.013_book/www/chapter9/9.html
- https://dev.mysql.com/doc/refman/8.4/en/index-merge-optimization.html
- https://docs.nestjs.com/
- https://www.kroger.com/b/simple-truth
'''
    (HERE / 'REVIEW_REPORT.md').write_text(report)
    print(json.dumps({'mixin': dict(counts), 'explicit_truncation': len(truncation), 'identity': identity['template_status_counts'],
                      'frozen_input_hashes_unchanged': True, 'gpu_gate_recommendation': 'NO_GO'}, ensure_ascii=False))


if __name__ == '__main__':
    main()
