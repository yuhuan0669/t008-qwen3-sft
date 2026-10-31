"""Render the completed, locally reviewed experiment without rerunning a model."""
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import hashlib

D = Path(__file__).resolve().parent
E = D / 'evaluation'
MODELS = ['original_base', 'v0.1.14', 'v0.1.16', 'candidate_v0.1.17']
NAMES = dict(zip(MODELS, ['原版', 'v0.1.14', 'v0.1.16', 'v0.1.17']))

def read(p):
    return json.loads(p.read_text())

def jl(p):
    return [json.loads(s) for s in p.read_text().splitlines()]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    summary = read(E / 'semantic-summary.json')
    assert summary['slots'] == 2224 and summary['unreviewed_slots'] == 0
    assert summary['unique_answers'] == summary['unique_reviewed'] == 2051
    assert read(D / 'execution-verification.json')['status'] == 'PASS'
    groups = {(r['model'], r['group'], r['family']): r for r in summary['groups']}
    primary = {(r['model'], r['group']): r for r in summary['primary_echo']}
    rows = jl(E / 'combined.jsonl')
    cases = read(E / 'cases.json')['items']
    labels = {v['review_id']: v for shard in ['a', 'b', 'c', 'root'] for v in jl(E / f'review/verdicts-{shard}.jsonl')}
    corrections = E / 'review/root-corrections.jsonl'
    if corrections.exists():
        for v in jl(corrections): labels[v['review_id']].update(v['corrected'])
    echo_table = ['|模型|非思考＋System：复述/96|非思考无System：复述/96|Thinking＋System：复述/10|',
                  '|---|---:|---:|---:|']
    for m in MODELS:
        cells=[]
        for group in ['nt_system', 'nt_no_system', 'thinking_system']:
            c=primary[(m,group)]
            cells.append(f"{c['echo']}/{c['n']}（原样{c['exact_echo']}＋近似{c['near_echo']}）")
        echo_table.append('|'+NAMES[m]+'|'+'|'.join(cells)+'|')
    quality_table=['|模型|任务未完成 /420|事实保持失败 /420|明确无依据补充 /420|实质有害帮助 /72|正常对照未完成 /72|',
                   '|---|---:|---:|---:|---:|---:|']
    identity_table=['|模型|带System身份完整交付 /24|无System身份完整交付 /24|Thinking身份完整交付 /4|JSON结构和值 /14|循环 / 截断（全部556份）|',
                    '|---|---:|---:|---:|---:|---:|']
    for m in MODELS:
        a=groups[(m,'nt_system','all')];h=groups[(m,'nt_system','refusal')];n=groups[(m,'nt_system','normal_controls')]
        assert h['n']==72 and n['n']==72
        quality_table.append(f"|{NAMES[m]}|{a['task_fail']}|{a['facts_fail']}|{a['unsupported_fail']}|{h['harmful_help']}|{n['task_fail']}|")
        idcells=[]
        for g in ['nt_system','nt_no_system','thinking_system']:
            c=groups[(m,g,'identity')];idcells.append(str(c['n']-c['identity_delivery_fail']))
        json_n=sum(groups[(m,g,'json')]['n'] for g in ['nt_system','thinking_system'])
        json_f=sum(groups[(m,g,'json')]['json_schema_fail']+groups[(m,g,'json')]['json_values_fail'] for g in ['nt_system','thinking_system'])
        assert json_n==14 and json_f==0
        loop=sum(groups[(m,g,'all')]['loop'] for g in ['nt_system','nt_no_system','thinking_system'])
        trunc=sum(groups[(m,g,'all')]['truncated'] for g in ['nt_system','nt_no_system','thinking_system'])
        identity_table.append('|'+NAMES[m]+'|'+'|'.join(idcells)+f'|14|{loop} / {trunc}|')
    diff_lines=[]
    for r in summary['paired_differences']:
        if r['baseline']=='original_base': continue
        lo,hi=r['question_bootstrap_interval_95']
        diff_lines.append(f"- {'带System' if r['group']=='nt_system' else '无System'}，v0.1.17 减 {r['baseline']}：{r['candidate_minus_baseline']*100:+.1f} 个百分点；按32题重采样的95%区间 {lo*100:+.1f} 至 {hi*100:+.1f}。")
    manifest=read(D/'outputs/full/run_manifest.json');state=read(D/'window-state.json')
    tz=ZoneInfo('America/Los_Angeles')
    start=datetime.fromisoformat(state['started_at_utc']).astimezone(tz)
    end=datetime.fromisoformat(state['restored_at_utc']).astimezone(tz)
    body=f'''# v0.1.17 受控验证结果

**完成训练和四组对照，保留为诊断候选，不建议发布。** 相对 v0.1.16，复述有下降；但无 System 条件仍不及 v0.1.14，且出现新的本轮循环截断案例。退化修复目标尚未达到。本轮按约定停止，没有追加 Full。

## 做了什么

1357条曝光、234次身份曝光和身份答案权重3保持不变。仅把32条已审核通用问答的第二次曝光改为空思考，问题、可见答案及 System 分配保持。已知有问题的其他语料没有同时修订。

从原始 Qwen/Qwen3-8B 新建LoRA，3步Smoke后重新初始化Full，85步、完整1 epoch；lr=1e-4、r8/alpha32及其余配方不变。训练损失和梯度均为有限数，运行成功不代表质量通过。

140道开发题×四模型，共2224份回答：复用1066，新增1158；新增1158次请求全部完成，技术重试0。三位子Agent阅读匿名答案，主Agent审核身份/JSON并复核问题；同题同模式的完全相同答案去重后共2051份，逐份标签已齐。不是外部Judge或正式TC260验收。

## 复述

32道复述题在每个非思考条件下各取3次，Thinking仅10道各1次。下表合并原样和人工确认的近似整题复述；循环另记，与复述可重叠，不能相加。主Agent重读全部32份近似复述候选，按预先口径将4份未回传任务指令的错误摘要移出复述项，任务/事实失败保留。

{chr(10).join(echo_table)}

原版无System的1份近似复述，是将技术核改请求当作题面润色，连“请核改”一起返回；不是逐字复述。这与此前单道防火题的0/50观察不矛盾。

{chr(10).join(diff_lines)}

这些区间只反映本组开发题的抽样差异，不是全库错误率，也不包含训练种子、历史批处理和评审尺度的不确定性。

## 任务与事实

下表为非思考＋同一System。明确失败分项可重叠，不能相加为总失败数；待核事实/规范另记 uncertain，不硬判为正确或错误。有害帮助分母仅24道应拒答题各3次；正常对照也为24题各3次。

{chr(10).join(quality_table)}

尤其要看无System的32道复述题：v0.1.16到v0.1.17，任务未完成为69→71/96，事实保持失败为27→45/96。复述减少后，整体任务失败并未随之减少；有些回答开始交付正文，却把已知事实改错。例如平台仍返回停采前旧测量、保障未解除的题，新候选写成已取得新数据、保障已解除并编出日期。不能把这种变化当作修复成功。

## 身份、JSON和输出结束

身份完整交付要求名称正确、完成本题且无明确能力编造、循环或截断；不把“开头报对名字”当作整条成功。欢迎语未要求背完整介绍；一句/两句、第一/第三人称的小格式偏差单记，不抵消实质交付。原版无System身份仅作参照，不将其未学定制名称称为退化。

{chr(10).join(identity_table)}

JSON在相同Schema约束下，四模型共56份全部通过结构及字段值检查；这证明本次受约束接口输出正常，不证明模型脱离Schema也稳定。所有2224份回答可见正文非空。Thinking哨兵很少，不据此宣称稳定性已解决。

主Agent确认的新增阻断例：D16-07要求简要介绍身份及能耗报告文字帮助。原版、v0.1.14、v0.1.16共9份带System回答均正常结束；v0.1.17第3份先报对名称，随后将“碳排放管理体系建设方案设计咨询培训”等短语反复输出到2048 Token上限。完整原文保留于本地逐题材料，没有重试替换。这里只说本轮同题对照未出现，不宣称旧模型永远不会循环。

## 初步归因与下一步

1. **通用答案在非思考上下文中的监督不足，是值得继续验证的因素。** 没有新增问答或曝光，只改变32次曝光的构建方式，就观察到相对v0.1.16的复述下降。它仍是一次训练，不能据此锁定唯一根因。
2. **仅做这32次转换不够。** 无System复述仍高于v0.1.14，无System中文身份也未恢复。新增循环表明“复述减少”不能替代能力保留检查。
3. **尚不能排除更新幅度和语料质量问题。** 本轮没有改变学习率、LoRA结构或已知错误语料；删除思考文字也同时改变了答案位置、监督Token数和损失组成，不能把结果解释为某个标签的纯因果效果。训练日志正常并不排除更新过强。

建议下一步按已定路线，讨论一个固定数据的学习率对照：仍以本轮v0.1.17数据和相同曝光为基准，仅将lr从1e-4降低到5e-5，检验是否减少对原生生成行为的扰动；其余参数、System和评测条件保持。这样可与本次直接比较，避免同时清洗数据、加曝光、改System。降低学习率未必改善身份，需要同时观察身份和任务交付；这一步仍用于归因。已知错误语料仍须另做内容修复，学习率实验不能将其洗白。**这里只给建议，未启动下一轮。**

这些140题富集历史失败，属于已暴露开发集；不要把样本中的改善推广为全库指标。后续达到开发目标后，才有理由用未参与开发的材料确认。

## 运行与版本入口

- UAT暂停：{start:%Y-%m-%d %H:%M:%S} 至 {end:%H:%M:%S}，America/Los_Angeles；恢复原Deployment spec及三个别名，1/1就绪，外部健康连续两次200。临时Pod/Job已清理，PVC产物保留。v0.1.17未部署到UAT。
- [执行核验](execution-verification.json) · [恢复核验](public-restoration-verification.json) · [分项统计](evaluation/semantic-summary.json)
- [逐题四模型对照](evaluation/BY_QUESTION.md) · [重点案例原文](evaluation/EXAMPLES.md) · 全部原文：[combined.jsonl](evaluation/combined.jsonl)
- [模型本地包](../../local-models/stage1-cpu-v0.1.17/adapter.zip) · [训练记录](outputs/full/run_manifest.json)
- ClearML Task：`{manifest['task_id']}`；OutputModel：`{manifest['clearml_output_model_id']}`，模型包回读SHA已核验。
- adapter.safetensors SHA-256：`{manifest['adapter_files']['adapter_model.safetensors']['sha256']}`。
- 仅本地版本管理；测试原文、回答及逐条审核在Git忽略目录中保留，未上传GitHub或Drive。
'''
    (D/'RESULT.md').write_text(body)
    detail=['# 逐题对照','', '同题每模型的非思考＋System各3份。E=原样/确认近似复述，T=任务未完成，F=事实保持失败，U=明确无依据补充；分项可重叠。完整回答另见combined.jsonl。','']
    for c in cases:
        detail += [f"## {c['id']}", '', c['question'], '', '判据：'+'；'.join(c['criteria']), '', '|模型|E|T|F|U|', '|---|---:|---:|---:|---:|']
        for m in MODELS:
            rr=[r for r in rows if r['case_id']==c['id'] and r['model']==m and r['group']=='nt_system']
            counts=[sum(bool(r['exact_echo'] or labels[r['review_id']]['near_echo']) for r in rr),
                    sum(labels[r['review_id']]['task']=='fail' for r in rr),
                    sum(labels[r['review_id']]['facts']=='fail' for r in rr),
                    sum(labels[r['review_id']]['unsupported']=='fail' for r in rr)]
            detail.append('|'+NAMES[m]+'|'+'|'.join(map(str,counts))+'|')
        detail += ['']
    (E/'BY_QUESTION.md').write_text('\n'.join(detail)+'\n')
    selected=['D16-07','T021-C900-B4-G033','T021-R3300-G0818','T021-SP60-G10','T021-R3300-G1202','T021-N300-R029','T021-B7-R102']
    byid={c['id']:c for c in cases};examples=['# 重点案例原文','','保留模型原文，不对失败响应重试。下列是诊断实例，不代表整体比例。','']
    for qid in selected:
        examples += [f'## {qid}', '', byid[qid]['question'], '']
        for r in sorted([r for r in rows if r['case_id']==qid],key=lambda r:(r['group'],MODELS.index(r['model']),r['repeat'])):
            v=labels[r['review_id']]
            examples += [f"### {NAMES[r['model']]} · {r['group']} · 第{r['repeat']}次 · {r['finish_reason']}", '',
                         f"评审：{v['note']}（task={v['task']}, facts={v['facts']}, unsupported={v['unsupported']}）", '',r['answer'],'']
    (E/'EXAMPLES.md').write_text('\n'.join(examples)+'\n')
    review_files={p.name: {'sha256':sha(p),'unique_labels':len(jl(p))} for p in sorted((E/'review').glob('verdicts-*.jsonl'))}
    coverage={'slots':2224,'unique_answers_reviewed':2051,'unreviewed':0,'files':review_files,
              'root_corrections_sha256':sha(corrections) if corrections.exists() else None,
              'root_near_echo_audit_sha256':sha(E/'review/near-echo-root-audit.json'),
              'review_type':'Three model-blinded Agent shards; root identity/JSON review and issue checks. Not external Judge or independent acceptance.',
              'minor_format_rule':'Sentence count/person variations noted separately unless they prevent substantive completion.',
              'root_scope':'Root did not independently reread every shard answer. Prior labels inherited under the same rubric.'}
    (E/'review-coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
    print('RESULT.md, BY_QUESTION.md, EXAMPLES.md, review-coverage.json written')

if __name__ == '__main__':
    main()
