"""Build concise result tables from complete semantic records, with reviewed conclusions."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import json
D=Path(__file__).resolve().parent;E=D/'evaluation'
def read(p):return json.loads(p.read_text())
def main():
    s=read(E/'semantic-summary.json');assert s['unreviewed_slots']==0
    rows=[json.loads(x) for x in (E/'combined.jsonl').read_text().splitlines()]
    labels={}
    for p in (E/'review').glob('verdicts-*.jsonl'):
        labels.update({x['review_id']:x for x in map(json.loads,p.read_text().splitlines())})
    p=E/'review/root-corrections.jsonl'
    if p.exists():
        for x in map(json.loads,p.read_text().splitlines()):labels[x['review_id']].update(x['corrected'])
    m=read(D/'outputs/full/run_manifest.json');change=read(D/'adapter-change.json');w=read(D/'window-state.json')
    ms=[('original_base','原版'),('v0.1.14','v0.1.14'),('v0.1.16','v0.1.16'),('candidate_v0.1.17','v0.1.17：lr 1e-4'),('candidate_v0.1.18','v0.1.18：lr 5e-5')]
    metrics={(x['model'],x['group'],x['family']):x for x in s['groups']}
    def get(model,group='nt_system',family='all'):return metrics[(model,group,family)]
    def val(x,key):return x.get(key,0)
    text=['# v0.1.18 学习率对照结果','', (D/'CONCLUSION.md').read_text().strip(),'',
      '## 实际执行','',
      '从原始 Qwen3-8B 新建 LoRA，完成 Smoke3 和唯一一次 Full85。相对 v0.1.17，实际 Full 命令仅把学习率从 `1e-4` 改为 `5e-5`；18 个日志记录点均验证为上一轮的一半。数据仍为 v0.1.17 的 1357 条，身份曝光 234 次及损失权重 ×3 不变；51 个冻结文件未变。System、修正模板、Schema、推理配置和判据保持。已有语料内容问题没有在本轮改动。','',
      '新生成 556 份中文回答，技术重试 0；复用原版、v0.1.14、v0.1.16、v0.1.17 的 2224 份已存结果。复用 2051 条旧唯一回答标签，新增完整阅读审核 495 条，覆盖本次五模型共 2780 份输出。3 个评审分片处理 458 条新增答案，主Agent审阅身份/JSON 37 条，并定向复核疑难和严重案例；没有独立重读全部旧答案，没有调用外部 Judge。','',
      f'CPU 权重核对显示有效 LoRA 更新矩阵的整体 Frobenius 范数为上一轮的 **{change["norm_ratio"]:.1%}**，方向余弦为 {change["direction_cosine"]:.4f}。这确认实际更新减小，不能单凭范数推断质量。平均训练 loss 为 0.6714，上轮为 0.6507；训练 loss 不作为验收分数。','',
      '## 复述','',
      '固定 32 道历史复述题，每个非思考条件各 96 份；Thinking 仅 10 份哨兵。计数为精确＋人工确认的近似整题复述，不把错误摘要自动算复述。','',
      '|模型|非思考＋System /96|非思考无System /96|Thinking＋System /10|','|---|---:|---:|---:|']
    for model,name in ms:text.append('|'+name+'|'+'|'.join(str(val(get(model,g,'echo'),'echo')) for g in ['nt_system','nt_no_system','thinking_system'])+'|')
    text+=['','相对同数据 v0.1.17 的按题配对差值（候选减上轮，负值表示减少）：','']
    for p in s['paired_differences']:
        if p['baseline']!='candidate_v0.1.17':continue
        lo,hi=p['question_bootstrap_interval_95'];text.append(f'- {p["group"]}：{p["candidate_minus_baseline"]*100:+.1f} 个百分点，按题重采样 95% 区间 [{lo*100:+.1f}, {hi*100:+.1f}]。')
    text+=['','## 任务与事实','',
      '下表为非思考＋System 的全部 420 份回答；各失败标记可重叠，不能相加。有害帮助分母为 24 道应拒答题的 72 份；正常对照为 24 题的 72 份。未核实的外部事实记 uncertain，未自动算错误。','',
      '|模型|任务失败 /420|题设事实失败 /420|无依据新增 /420|有害帮助 /72|正常对照任务失败 /72|','|---|---:|---:|---:|---:|---:|']
    for model,name in ms:
        x=get(model);text.append(f'|{name}|{val(x,"task_fail")}|{val(x,"facts_fail")}|{val(x,"unsupported_fail")}|{val(get(model,family="refusal"),"harmful_help")}|{val(get(model,family="normal_controls"),"task_fail")}|')
    text+=['','无 System 的 32 道复述题另列任务/事实，避免把从复述转为错误答案当作恢复：','',
      '|模型|任务失败 /96|题设事实失败 /96|','|---|---:|---:|']
    for model,name in ms:
        x=get(model,'nt_no_system','echo');text.append(f'|{name}|{val(x,"task_fail")}|{val(x,"facts_fail")}|')
    text+=['','## 身份、JSON和结束状态','',
      '身份完整交付同时检查名称、任务、无明确编造、无循环或截断；完整名称追问要求完整名称，普通欢迎/介绍中的明确品牌简称单记，不当作倒置。原版无 System 身份只作参照。JSON 在相同 Schema 约束下检查结构和值。','',
      '|模型|带System身份 /24|无System身份 /24|Thinking身份 /4|JSON结构和值 /14|循环 / 截断（全部556份）|','|---|---:|---:|---:|---:|---:|']
    for model,name in ms:
        ident=[get(model,g,'identity') for g in ['nt_system','nt_no_system','thinking_system']]
        ips=[x['n']-val(x,'identity_delivery_fail') for x in ident]
        js=[get(model,g,'json') for g in ['nt_system','thinking_system']]
        jpass=sum(labels[r['review_id']].get('json_schema')=='pass' and labels[r['review_id']].get('json_values')=='pass' for r in rows if r['model']==model and r['case_id'] in ['D16-11','D16-12','E17-J03','E17-J04'])
        total=[get(model,g) for g in ['nt_system','nt_no_system','thinking_system']]
        text.append(f'|{name}|'+ '|'.join(map(str,ips))+f'|{jpass}|{sum(val(x,"loop") for x in total)} / {sum(val(x,"truncated") for x in total)}|')
    text+=['','[重点问题与原文对照](evaluation/EXAMPLES.md) · [逐题分项统计](evaluation/BY_QUESTION.md) · [全量保存回答](evaluation/combined.jsonl)','',
      '## 适用范围与交付','',
      '140 题富集已暴露失败，是开发诊断集，不能代表全库指标或独立验收。旧结果与新结果的生成时间、批处理不同，请求不传 seed，不是同随机种子的对照；仅各一次训练也不能排除训练波动。Thinking 题量很少。没有清洗掉已知错误语料，不能把本轮当作数据质量修复。','']
    tz=ZoneInfo('America/Los_Angeles');start=datetime.fromisoformat(w['started_at_utc']).astimezone(tz);end=datetime.fromisoformat(w['restored_at_utc']).astimezone(tz)
    text += [f'UAT 暂停于 {start:%Y-%m-%d %H:%M:%S}，{end:%H:%M:%S} 恢复（America/Los_Angeles，约 {(end-start).total_seconds()/60:.1f} 分钟）。原 Deployment spec 与三个别名恢复，1/1 就绪，外部健康连续两次 200；临时 Pods/Jobs 已清理，PVC 训练产物保留。v0.1.18 没有发布，应用配置未改。','',
      '- [执行核验](execution-verification.json) · [最终核验](final-validation.json) · [审核覆盖](evaluation/review-coverage.json) · [恢复核验](public-restoration-verification.json) · [配置差异](config-diff.json) · [统计](evaluation/semantic-summary.json)',
      '- [本地模型包](../../local-models/model-v0.1.18/adapter.zip) · [训练记录](outputs/full/run_manifest.json)',
      f'- ClearML Task：`{m["task_id"]}`；OutputModel：`{m["clearml_output_model_id"]}`。模型包已回读验证 SHA。',
      f'- adapter.safetensors SHA-256：`{m["adapter_files"]["adapter_model.safetensors"]["sha256"]}`。',
      '- 仅本地 Git 归档；未上传 GitHub/Drive。题目、原始回答与逐条审核保留于被 Git 忽略的本地目录。']
    (D/'RESULT.md').write_text('\n'.join(text)+'\n')
if __name__=='__main__':main()
