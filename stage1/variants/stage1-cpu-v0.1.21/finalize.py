"""Write the local review package from completed content and native CPU evidence."""
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import assemble as a

D, P = a.D, a.P


def main():
    assert not (D / 'FILES.sha256.json').exists(), 'Already frozen'
    inputs, decisions, progress = a.collect(complete=True)
    assert len(inputs) == len(decisions) == 624
    assert sum(s.startswith('G') for s in inputs) == 390
    stats, cpu = a.read(D / 'statistics.json'), a.read(D / 'cpu-check/report.json')
    rows, mapping = a.jl(D / 'train.jsonl'), a.jl(D / 'train-map.jsonl')
    parents = a.jl(P / 'train.jsonl')
    issues = a.jl(D / 'external-review-dispositions.jsonl')
    assert cpu['verified'] and cpu['dataset_sha256'] == a.sha(D / 'train.jsonl')
    assert cpu['rows'] == len(rows) == stats['after']['rows']
    assert len(issues) == 335 and len({x['issue_id'] for x in issues}) == 335
    assert all(cpu[k] == 0 for k in ('overlength_rows', 'truncated_rows',
                                   'silent_dropped_rows', 'empty_supervision_rows'))
    cfg, oldcfg = a.read(D / 'training-config.json'), a.read(P / 'training-config.json')
    assert [s.replace(D.name, P.name) for s in cfg['full_argv']] == oldcfg['full_argv']
    assert not cfg['execution_authorized']
    assert a.sha(D / 'identity_loss3.py') == a.sha(P / 'identity_loss3.py')
    assert a.sha(D / 'inference-system.txt') == a.sha(P / 'inference-system.txt')
    assert a.sha(D / 'evaluation-config.json') == a.sha(P / 'evaluation-config.json')
    assert len(rows) + len(a.jl(D / 'quarantine.jsonl')) == 1069
    preserved = 0
    raw_old = (P / 'train.jsonl').read_bytes().splitlines(keepends=True)
    raw_new = (D / 'train.jsonl').read_bytes().splitlines(keepends=True)
    for i, (r, m) in enumerate(zip(rows, mapping)):
        if m['operation'] == 'preserve':
            assert raw_new[i] == raw_old[m['parent_line_one_based'] - 1]
            preserved += 1
    assert preserved == cpu['unchanged_full_encoding_rows']
    for path, expected in a.read(D / 'source-bindings.json').items():
        assert a.sha(Path(path)) == expected, path
    assert a.read(D / 'cpu-check/cluster-after.json')['uat_spec_unchanged']
    assert a.read(D / 'cpu-check/cluster-after.json')['temporary_pod_deleted']

    general, identity = [], []
    changed_fields = Counter()
    for sid, item in sorted(inputs.items()):
        decision = decisions[sid]
        if decision['action'] == 'quarantine':
            continue
        if sid.startswith('G'):
            value = decision['after'] if decision['action'] == 'repair' else item['record']
            general.append(value)
            for f in ('question', 'thinking', 'answer'):
                changed_fields[f] += value[f] != item['record'][f]
        else:
            identity.append(a.apply_decision(item, decision))
    assert len(identity) == 234 and changed_fields['question'] == 0
    a.sj('general-reviewed.jsonl', general)
    a.sj('identity-reviewed.jsonl', identity)
    stats['cpu_tokens'] = cpu['totals']
    stats['repaired_general_fields'] = dict(changed_fields)
    stats['external_review_outcomes'] = dict(Counter(x['status'] for x in issues))
    stats['historical_v20_quarantine_unique_records_not_reintroduced'] = 128
    a.save('statistics.json', stats)
    cfg.update(status='CPU_CHECKED_PENDING_USER_REVIEW',
               runtime_validation='Native CPU loader, full encoding, masks and identity x3 checked; no training.')
    a.save('training-config.json', cfg)
    a.save('mechanical-validation.json', {
        'verified': True, 'reviewed_general_unique_records': 390,
        'reviewed_identity_exposures': 234, 'external_issues_accounted_once': 335,
        'candidate_rows': len(rows), 'out_of_scope_rows_preserved_bytewise': 61,
        'all_retained_record_exposure_counts_preserved': True,
        'all_user_messages_unchanged': True, 'all_retained_thinking_patterns_preserved': True,
        'parent_inputs_unchanged': True, 'training_system_rows': 0,
        'training_hyperparameters_unchanged': True, 'loss_plugin_bytes_unchanged': True,
        'training_started': False, 'inference_executed': False,
        'gpu_used': False, 'uat_paused': False, 'published_to_github_or_drive': False, 'cpu_inputs_temporarily_copied_to_cluster': True})
    g, ident = stats['general_decisions'], stats['identity_decisions']
    stages = [('保留', 'retain'), ('修正', 'repair'), ('隔离', 'quarantine')]
    exposures = Counter()
    for sid, item in inputs.items():
        if sid.startswith('G'):
            exposures[decisions[sid]['action']] += len(item['parent_lines'])
    table = '\n'.join(f'|{label}|{g.get(key,0)}|{exposures[key]}|'
                      for label, key in stages)
    (D / 'README.md').write_text(f'''# v0.1.21 数据清洗候选

已逐条核对 v0.1.20 的390种通用记录和234次身份曝光，形成 **{len(rows)}条** 本地候选。原生CPU编码检查通过，待审阅；未训练、未运行模型/Judge、未暂停UAT、未推送GitHub或Drive。

|通用处置|独立记录|对应曝光|
|---|---:|---:|
{table}

身份234次全部保留，其中修正{ident.get('repair',0)}次；其余61条业务定位、边界和通用非思考等样本原字节不变。外评335项均有处置记录；外部cleaned附件没有整包导入。v0.1.20此前隔离的128种通用记录继续隔离。

修订直接进入正文，并同步必要的thinking；不添加“旧说法不对”补丁。题干、语言、原记录的重复曝光和思考/非思考模式保持；训练仍不带System，身份损失倍率3及其他超参数不变。隔离造成总行数和每epoch步数变化，没有补曝光。

审阅入口：

1. [逐条修改前后](SAMPLES.md)：差异、原文、修改后全文。
2. [全部处置及理由](CHANGES.md) · [外评逐项回应](EXTERNAL_REVIEW.md)。
3. [数据与监督统计](STATISTICS.md) · [CPU检查](CPU_CHECK.md) · [训练配置差异](PARAMETERS.md)。

实际训练文件：[train.jsonl](train.jsonl)。供内容审阅的导出：[通用{len(general)}种](general-reviewed.jsonl)、[身份234次](identity-reviewed.jsonl)。导出文件不替代训练文件。[父子行号](train-map.jsonl) · [隔离原文](quarantine.jsonl) · [来源说明](PROVENANCE.md)。

数据SHA-256：`{a.sha(D / 'train.jsonl')}`。

本候选处理已发现的数据缺陷，尚未证明复述或能力退化得到改善。v0.1.20未训练，其新引入的补丁问题不能倒推为v0.1.14/v0.1.16历史退化的原因。各旧版本、已有权重和部署不变。
''')
    tr = ['# 数据与监督统计', '', '|项目|v0.1.20|v0.1.21|', '|---|---:|---:|',
          f'|训练曝光行|1069|{len(rows)}|',
          f'|通用独立记录|390|{len(general)}|',
          f'|身份曝光|234|234|',
          f'|身份曝光占比|{234/1069:.2%}|{234/len(rows):.2%}|',
          f'|预计每epoch优化步数|67|{cfg["estimated_full_optimizer_steps"]}|']
    for label, key in [('输入token', 'input_tokens'), ('监督token', 'supervised_tokens'),
                       ('加权token单位', 'weighted_token_units')]:
        tr.append(f'|{label}|{cpu["totals"]["before"][key]:,.0f}|{cpu["totals"]["after"][key]:,.0f}|')
    for label, key in [('身份监督token占比', 'supervised_token_share'),
                       ('身份加权token占比', 'weighted_token_share')]:
        tr.append(f'|{label}|{cpu["category_supervision"]["before"]["identity"][key]:.2%}|{cpu["category_supervision"]["after"]["identity"][key]:.2%}|')
    tr += ['', f'本轮保留通用中，thinking有改动{changed_fields["thinking"]}种，正文有改动{changed_fields["answer"]}种；题干0处变化。并非全部thinking改写。',
           '', 'token来自实际ms-swift模板及labels/loss_scale，不是字符估算。加权token份额不等于实测损失或梯度贡献；内容缩短和隔离会改变相对份额，未通过重采样抵消。',
           '', '|当前来源模式|曝光行|监督token|加权token占比|', '|---|---:|---:|---:|']
    for mode, vals in cpu['mode_supervision']['after'].items():
        tr.append(f'|{mode}|{vals["rows"]}|{vals["supervised_tokens"]:,}|{vals["weighted_token_share"]:.2%}|')
    tr += ['', '来源模式按任一助手轮是否含非空think划分；真实编码沿用preserve_thinking=false，历史轮thinking会被原生模板处理。逐来源/逐行结果见[cpu-check/report.json](cpu-check/report.json)和[row-checks.jsonl](cpu-check/row-checks.jsonl)。']
    (D / 'STATISTICS.md').write_text('\n'.join(tr) + '\n')
    (D / 'CPU_CHECK.md').write_text(f'''# CPU检查

ms-swift {cpu['versions']['ms-swift']}及父版本绑定的tokenizer/模板/损失源码核验一致。仅加载tokenizer和数据，未加载模型权重、构造Trainer/优化器或执行前向/反向传播。

首次预检发现5种修订记录超过2048 token（10次曝光），已删减重复说明后重查；题干和必要内容保留，没有截断或静默删除。第一次结果保存在[cpu-check/attempt1/](cpu-check/attempt1/)。

- 实际装载、原生编码和成员守卫：均为{len(rows)}行。
- 最长{cpu['max_tokens']} token，P99为{cpu['p99_tokens']}；2048上限内，超长、截断、静默丢行、空监督均为0。
- {cpu['unchanged_full_encoding_rows']}行未改记录的input_ids、labels、loss_scale与父版本逐项一致。
- 身份234次曝光：新正文对应hash及{cpu['native_preprocessing_alias_count']}个原生预处理别名已实测绑定，助手监督倍率3仍生效。未改插件算法。
- 用户位置和空think损失为0，本候选不含System；原生补入的中间轮结束符保持1，身份最终suffix沿既有插件保持3。
- GPU不可见、无GPU设备；仅用临时CPU Pod，检查后已删除。UAT Deployment配置hash不变且1/1就绪。

[完整结果](cpu-check/report.json) · [逐行检查](cpu-check/row-checks.jsonl) · [变更行](cpu-check/changed-row-checks.json) · [原生别名](native-identity-key-aliases.json) · [集群前后](cpu-check/cluster-after.json)。

这些是数据编码与监督实现检查，不是模型效果或训练收敛证明。
''')
    (D / 'PARAMETERS.md').write_text(f'''# 训练配置差异

相对v0.1.20，仅改候选数据路径、哈希、行数及相关版本记录。full_argv经版本路径归一后逐项相同；[identity_loss3.py](identity_loss3.py)源码字节相同。身份hash清单随内容重新绑定，不改变loss归一化或倍率。

保持：Qwen/Qwen3-8B原始基座＋新LoRA；BF16，r8/alpha32/dropout0.05/all-linear；lr1e-4，1 epoch，batch1×梯度累积16，warmup0.05，seed/data_seed42，max_length2048，gradient_checkpointing=true；default+t008_identity3_ignore_empty_think，preserve_thinking=false；训练无System。

数据由1069变为{len(rows)}行，预计步数67→{cfg['estimated_full_optimizer_steps']}。保留记录曝光不变，内容及隔离会改变总监督token与调度长度，不能说实际优化过程完全等同。未补步数、增加epoch或重新配比。

推理仍引用冻结的共同System、修正vLLM模板、两模式参数与JSON Schema用法；[evaluation-config.json](evaluation-config.json)与父版本字节一致，其中System引用父版本不可变同一份文件。

[完整配置](training-config.json) · [机器可读差异](config-diff.json)。execution_authorized=false，未启动训练。
''')
    lines = ['# 外评意见处置', '', '335项均有对应记录；不把外评当金标。', '',
             '|序号|样本|处置|理由|', '|---|---|---|---|']
    for x in issues:
        lines.append(f'|{x["issue_id"]}|{x.get("sample_id","全局")}|{x["status"]}|{x["reason"].replace("|"," / ").replace(chr(10)," ")}|')
    (D / 'EXTERNAL_REVIEW.md').write_text('\n'.join(lines) + '\n')
    (D / 'PROVENANCE.md').write_text('''# 来源与审核边界

父对象为冻结v0.1.20；源文件哈希见[source-bindings.json](source-bindings.json)。逐条决定、源哈希和并行分工留在review/；最终覆盖决定见[root-corrections.jsonl](review/root-corrections.jsonl)，最终数据以train.jsonl为准。训练标签中的dataset表示历史lineage和既有路由，不代表全文仍是上游原文。

身份中的六条项目整题改写为I0090、I0156、I0161、I0193、I0209、I0214；另四条项目助手内容改写为I0088、I0152、I0165、I0191。已对照v0.1.7–v0.1.10历史changes核对，详情及原曝光位置见[身份来源侧表](review/identity-notes.md)。本轮保留原dataset标签以不改变路由，并单独披露改写来源；不称这十条是Swift官方原文。

390种通用与234次身份均全文检查；主Agent定向复核身份修改、高风险/争议项和成品遗漏，并统一机械与CPU检查。并非624条都经过第二轮独立盲审；联网资料只覆盖需要核实的具体事实，不声称每个事实均由外部来源穷尽查证。代码做必要静态或有限纯逻辑核验，没有执行样本中的联网、邮件、数据库或部署操作。

未从T021/T024评测题生成训练样本，未引入新问答；题干逐字保留。空think无/no_think不自动算格式错误，未为此新增思考链。用户确认的名称和研发口径保持，未加回成立日期或底层信息保密训练样本。
''')
    essential = ['train.jsonl', 'train-map.jsonl', 'training-config.json', 'identity_loss3.py',
                 'identity-keys.json', 'native-identity-key-aliases.json',
                 'cpu-check/report.json', 'decisions.jsonl', 'external-review-dispositions.jsonl']
    a.save('manifest.json', {'data_version': D.name, 'parent': P.name,
        'status': 'CPU_CHECKED_PENDING_USER_REVIEW', 'training_authorized': False,
        'files_sha256': {name: a.sha(D / name) for name in essential}})
    print(json.dumps({'rows': len(rows), 'general_unique': len(general),
        'general_decisions': g, 'identity_decisions': ident, 'cpu_verified': True,
        'data_sha256': a.sha(D / 'train.jsonl')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
