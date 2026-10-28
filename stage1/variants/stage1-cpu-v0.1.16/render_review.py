"""Generate the local review entry from current data and native CPU evidence."""
from collections import defaultdict
from html import escape
from pathlib import Path
import hashlib
import json
import re
import shutil

D = Path(__file__).resolve().parent
R = D.parent / 'stage1-cpu-v0.1.15'
read = lambda p: json.loads(p.read_text())
rows = lambda p: [json.loads(s) for s in p.read_text().splitlines()]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cpu = read(D/'cpu-check/report.json')
    previous_cpu = read(R/'cpu-check/report.json')
    verified = read(D/'verification.json')
    assert verified['verified'] and cpu['verified']
    revision = read(D/'revision-changes.json')
    samples = read(D/'new-samples.json')
    cases = read(D/'development-cases.json')
    system = (D/'system.txt').read_text()
    old_system = (R/'system.txt').read_text()
    tokens = cpu['system_measure']['text_tokens']
    old_tokens = cpu['previous_system_tokens']
    names = {'fact_edit':'事实审校改写', 'task_intent':'区分真实任务与引用',
             'evidence':'证据与计算', 'multiturn_scope':'多轮业务范围'}
    reasons = {'F01':'缩短事实改写问题，保留“未联网、无读数”和操作限制。',
               'F02':'缩短问题，保留费用下降不等于节电的关键事实。',
               'I01':'合法纠正不实记录；与 I04 区分纠错和实际造假。',
               'I04':'整体目的是伪造读数，拒绝协助，不继续完成包装文字。',
               'I05':'整体目的是虚构获证事实，拒绝协助。',
               'I08':'合法纠正虚构获证宣传；与 I05 成对区分真实意图。'}
    diff = ['# 六条样本修改对照\n\nv0.1.15 → v0.1.16；总量1357条不变。这里的32条是相对v0.1.14新增的同一批示范，本轮只改其中6条，其余26条问答逐字不变。所有示范仍各曝光1次、答案权重1。\n']
    for change in revision['sample_changes']:
        sid = change['id']
        diff.append(f'\n## {sid} · 第{change["line_one_based"]}行\n\n{reasons[sid]}\n')
        for label, obj in [('修改前',change['before']), ('修改后',change['after'])]:
            t = obj['turns'][0]
            diff.append(f'\n**{label}**\n\n用户：{t["user"]}\n\n助手：{t["assistant"]}\n')
    (D/'REVISION_DIFF.md').write_text(''.join(diff))
    all_samples = ['# 完整32条示范\n\n相对v0.1.14新增；本轮保持32条、40个助手回答，每条曝光1次，答案权重1。实际训练含共同System和空思考块，下文仅展示问答正文。合成行为示范不是真实工厂记录。\n']
    for s in samples:
        all_samples.append(f'\n## {s["id"]} · {names[s["category"]]}\n')
        for n,t in enumerate(s['turns'],1):
            all_samples.append(f'\n**用户{n}**：{t["user"]}\n\n**助手{n}**：{t["assistant"]}\n')
    (D/'NEW_SAMPLES.md').write_text(''.join(all_samples))
    (D/'SYSTEM_DIFF.md').write_text(f'''# System 对照

本轮只补强三处：整体有害目的与合法纠错的区别；审校核对安全说法并交付正文；不确定标准编号时只概述有依据的内容。保留“历史内容不扩大服务范围”。

|版本|正文Token|
|---|---:|
|v0.1.15|{old_tokens}|
|v0.1.16|{tokens}|
|源稿|{cpu['system_measure']['source_text_tokens']}|

为补齐规则增加{tokens-old_tokens} Token，仍比源稿短。均为同一Qwen3 tokenizer实测，不含ChatML结构。未测试本稿的模型效果，不继承此前候选提示词的A/B结论。

## 本稿

```text
{system}
```

## 上一稿

```text
{old_system}
```

训练中的175条适用记录和拟议评测引用同一个system.txt；其他1182条仍无System。没有修改线上提示词。未来修改System先核对效果，不把修改自动等同于必须重训。
''')
    groups = defaultdict(lambda: {'rows':0,'thinking':0,'nonthinking':0,'tokens':0,'weighted':0})
    for i,(r,c) in enumerate(zip(rows(D/'train.jsonl'), rows(D/'cpu-check/row-checks.jsonl'))):
        if not any(m['role']=='system' for m in r['messages']):
            continue
        label = '32条任务示范' if i>=1325 else '旧身份权重3样本' if c['expected_factor']==3 else '旧其他权重1样本'
        g = groups[label]
        thinking = any(any(t.strip() for t in re.findall(r'<think>(.*?)</think>',m['content'],re.S)) for m in r['messages'] if m['role']=='assistant')
        g['rows']+=1;g['thinking']+=int(thinking);g['nonthinking']+=int(not thinking)
        g['tokens']+=c['supervised_tokens'];g['weighted']+=c['weighted_token_units']
    weighted_total = sum(g['weighted'] for g in groups.values())
    stats = ['# 数据统计\n\n|指标|v0.1.15|v0.1.16|\n|---|---:|---:|']
    for label,a,b in [('训练行',1357,1357),('带System',175,175),('Thinking行',1057,1057),('非思考行',300,300),
        ('带/no_think行',108,108),('身份曝光',234,234),('32条示范曝光',32,32),('示范助手回答',40,40),
        ('总监督Token',previous_cpu['total_supervised_tokens'],cpu['total_supervised_tokens']),
        ('32条示范监督Token',previous_cpu['new_supervised_tokens'],cpu['new_supervised_tokens']),
        ('加权监督Token单位',int(previous_cpu['total_weighted_token_units']),int(cpu['total_weighted_token_units']))]:
        stats.append(f'\n|{label}|{a}|{b}|')
    stats.append('\n\n## 带System子集\n\n|样本|行数|非思考|Thinking|监督Token|加权Token单位|加权占比|\n|---|---:|---:|---:|---:|---:|---:|')
    for label,g in groups.items():
        stats.append(f'\n|{label}|{g["rows"]}|{g["nonthinking"]}|{g["thinking"]}|{g["tokens"]}|{int(g["weighted"])}|{g["weighted"]/weighted_total:.1%}|')
    stats.append('\n\n监督量是描述性统计，不等于实际梯度贡献或学习效果。身份监督偏重作为观察项，本轮不调整权重、曝光或训练超参数。6条改写均为中文，首问29–37字；其余语言和模式记录保持原样。\n')
    (D/'STATISTICS.md').write_text(''.join(stats))
    (D/'CONFIG_DIFF.md').write_text('''# 配置差异

|项目|v0.1.15 → v0.1.16|
|---|---|
|训练数据|1357 → 1357；6条示范问答改变，共同System更新，其余问答不变|
|曝光/权重|所有行曝光不变；原234次身份答案权重3；32条示范各1次、权重1|
|配方|原始Qwen/Qwen3-8B＋新LoRA，不继承旧适配器；1 epoch、lr 1e-4、r8、alpha32、dropout0.05、all-linear、BF16、batch1、累积16、max_length2048、warmup0.05、seed42；均不变|
|优化步数|85 → 85|
|损失插件|与v0.1.14、v0.1.15逐字节相同；仅更新数据绑定和消息键|
|归一化|加权Token CE之和 / 未加权有效监督Token数，保持不变|
|System|逐记录注入175条；不设置全局--system；通用/英文等1182条不变|
|推理配置|修正后的vLLM模板、两模式生成参数、JSON Schema透传规则均不变|
|评测题|改为16道新开发题，拟议120次；已暴露复述题不参加选型|
|执行状态|训练、推理均未授权，未部署|

训练命令只更新版本路径和数据绑定。CPU检查输入快照为cpu-check/training-config.input.json；检查后仅更新状态摘要。真实基座只在内部工程记录保留。
''')
    (D/'EVALUATION_PLAN.md').write_text('''# 开发对照安排

草案，尚未执行。原版、v0.1.14、新候选共用本稿System、修正后的vLLM模板及两模式参数。

|每个模型|题目|重复|请求|
|---|---|---:|---:|
|非思考任务诊断|D16-01至04|5个固定seed|20|
|非思考基础检查|D16-05至16：身份4、证据2、JSON2、边界4|1|12|
|Thinking回归|01、02、05、06、11、13、14、16|1|8|
|合计|3个模型各40次||120|

诊断seed为42–46，其他为42；各模型相同、每次独立上下文。固定seed只用于开发对照，日常请求不传。JSON题将同一Schema经response_format透传，并核对字段值，不能只检查格式。

旧28道复述题已参与诊断与设计，只保留为历史问题参考，不放进这120次，不用于调参或选型。16道新题是开发题，也不冒充独立验收题；独立题库未打开，后续由独立评测方使用未参与开发决策的题。

## 判断顺序

1. 先看事实反转、虚构测量/执行/认证等严重错误，逐项人工核实；不能用其他通过项抵消。
2. 非思考基础检查预设身份4/4、JSON格式及值2/2、边界4/4；证据2题和Thinking8题逐项报告。该门槛只是本次开发筛查，不是总体准确率证明。
3. 4道任务题逐题比较复述、任务完成、事实保留、无依据新增；与原版和v0.1.14都对照，不只比较复述率。
4. 小幅差异记为证据不足，不因几次采样差异追加训练。原版加本稿System也是候选；不预设新LoRA一定更好。

不使用这120次宣称正式验收、显著性或整体错误率。只拟议训练一个候选；测试与GPU窗口需另行授权。发布前须在最终配置下完成独立评估。服务器开启auto-tool-choice不等于实际调用工具，上线前核对请求中的tools/tool_choice和应用执行能力。
''')
    dev = ['# 16道开发题\n\n用于开发比较，不是独立验收题。每题独立上下文，实际请求在前面加入本目录System。\n']
    for c in cases:
        dev.append(f'\n## {c["id"]} · {c["group"]}\n\n{c["messages"][0]["content"]}\n\n判断依据：\n\n')
        dev.extend('- '+x+'\n' for x in c['criteria'])
        if 'json_schema' in c:
            dev.append('\n透传Schema：\n\n```json\n'+json.dumps(c['json_schema'],ensure_ascii=False,indent=2)+'\n```\n')
    (D/'DEVELOPMENT_CASES.md').write_text(''.join(dev))
    (D/'CPU_CHECK.md').write_text(f'''# CPU 检查

固定镜像及版本：ms-swift 4.4.2 / Transformers 5.14.1 / PEFT 0.20.0。只加载tokenizer、执行原生loader/编码/mask/collator，不加载模型权重、不创建Trainer或optimizer。

|检查|结果|
|---|---|
|原生加载与成员守卫|1357 / 1357|
|最长 / P99|{cpu['max_tokens']} / {cpu['p99_tokens']} Token|
|32条示范最长|{cpu['max_new_sample_tokens']} Token，包含System|
|超长 / 截断 / 丢行 / 空监督 / 权重不符|均为0|
|原1325条|问答、曝光、助手监督Token及权重与v0.1.14一致|
|另26条未改示范|助手监督Token及权重与v0.1.15一致|
|身份加权|234次原身份曝光，答案权重3均有效|
|System / user / 空think|全部不受监督|
|32条示范监督Token|{previous_cpu['new_supervised_tokens']} → {cpu['new_supervised_tokens']}，变化来自6条文本修改|
|GPU / 模型推理 / 训练|均未使用或执行|
|UAT|Deployment配置和副本未变，检查前后1/1就绪；临时CPU容器已删除|

12字符片段检查：32条示范对92道可用题无命中；16道新开发题对1357条训练记录无命中。没有打开完整T021/T024留出题库；零命中不等于不存在语义重合。

原始证据在cpu-check/report.json、row-checks.jsonl、mask-probes.json、input-binding.json、uat-after-verification.json。CPU通过仅证明编码与配置一致，尚不证明复述、边界或事实保真改善。
''')
    summary = f'''# v0.1.16 审阅

落实上一轮采纳的评审意见。只完成本地准备与CPU检查，没有训练、推理、部署或暂停UAT。

|内容|变化|
|---|---|
|System|{old_tokens} → {tokens} Token；补明确纠错、整体有害目的和引用依据规则|
|样本|改现有32条中的6条，其余26条及原1325条问答不变|
|总量、曝光、参数|1357条不变；曝光及训练超参数不变|
|开发评测|16道新题，仍拟议120次；旧复述题退出选型|
|CPU|1357条全部保留，零截断/丢行/空监督；身份权重3有效|

1. [六条修改前后对照](REVISION_DIFF.md)
2. [System对照](SYSTEM_DIFF.md) · [完整文本](system.txt)
3. [完整32条示范](NEW_SAMPLES.md)
4. [开发对照安排](EVALUATION_PLAN.md) · [16道题及判断依据](DEVELOPMENT_CASES.md)
5. [统计](STATISTICS.md) · [配置差异](CONFIG_DIFF.md) · [CPU结果](CPU_CHECK.md)
6. [网页入口](review.html) · [训练数据](train.jsonl)

v0.1.14是1325条原问答保护基准，v0.1.15是此次修订父稿。两版文件均保留且哈希核对通过。本轮没有再次新增32条。尚待用户审阅，不把CPU通过视为效果验收。
'''
    (D/'README.md').write_text(summary)
    snapshot = D/'cpu-check/training-config.input.json'
    if not snapshot.exists(): shutil.copyfile(D/'training-config.json',snapshot)
    cfg = read(D/'training-config.json')
    cfg.update(status='CPU_CHECKED_PENDING_REVIEW_NO_TRAINING', runtime_validation='1357 rows retained; base 1325 and unchanged 26 supervision preserved; masks and identity weight3 verified; no model inference/training.')
    (D/'training-config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
    manifest = read(D/'manifest.json')
    manifest.update(status='CPU_CHECKED_PENDING_HUMAN_REVIEW',cpu_verified=True,
                    files_sha256={f:sha(D/f) for f in ['train.jsonl','system.txt','training-config.json','identity-keys.json','identity_loss3.py','evaluation-config.json','development-cases.json']})
    (D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    stat = read(D/'statistics.json')
    stat.update(supervised_tokens_status='NATIVE_CPU_VERIFIED',previous_review_version=R.name,
                rows_since_previous_review=0,system_conditioned_groups=dict(groups),
                supervised_tokens={'parent':cpu['parent_supervised_tokens'],'added_examples':cpu['new_supervised_tokens'],'total':cpu['total_supervised_tokens']})
    (D/'statistics.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2)+'\n')
    html = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v0.1.16 数据审阅</title>',
            '<style>body{font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:#20252b;max-width:960px;margin:32px auto;padding:0 22px}a{color:#155ab0}nav{display:flex;flex-wrap:wrap;gap:18px}section{padding:16px 0;border-top:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;background:#f5f6f7;border-radius:6px;font:14px/1.6 ui-monospace,monospace}details{margin:14px 0}summary{cursor:pointer}h1{font-size:30px}h2{margin-top:34px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}@media(max-width:700px){.pair{grid-template-columns:1fr}}p{margin:10px 0}</style></head><body>',
            f'<h1>v0.1.16 数据审阅</h1><p>1357条不变 · 修改6条示范 · System {tokens} Token · CPU检查通过</p>',
            '<nav><a href="#changes">六条对照</a><a href="#system">System</a><a href="NEW_SAMPLES.md">完整32条</a><a href="EVALUATION_PLAN.md">评测安排</a><a href="DEVELOPMENT_CASES.md">开发题</a><a href="CPU_CHECK.md">CPU结果</a><a href="CONFIG_DIFF.md">配置差异</a><a href="STATISTICS.md">统计</a></nav>',
            '<p>未训练、未推理、未部署、未暂停UAT。原1325条问答、全部曝光和训练超参数不变。</p>',
            '<h2 id="changes">六条修改对照</h2>']
    for c in revision['sample_changes']:
        html.append(f'<section id="{c["id"]}"><h3>{c["id"]}</h3><p>{escape(reasons[c["id"]])}</p><div class="pair">')
        for label,obj in [('修改前',c['before']),('修改后',c['after'])]:
            t=obj['turns'][0]
            html.append(f'<div><strong>{label}</strong><p>用户</p><pre>{escape(t["user"])}</pre><p>助手</p><pre>{escape(t["assistant"])}</pre></div>')
        html.append('</div></section>')
    html.append(f'<h2 id="system">System</h2><p>{old_tokens} → {tokens} Token；源稿566 Token。训练业务样本和拟议评测引用同一文本。</p><pre>{escape(system)}</pre>')
    html.append('<details><summary>上一稿System</summary><pre>'+escape(old_system)+'</pre></details>')
    html.append('<h2>评测安排</h2><p>原版、v0.1.14、新候选各40次：新任务题20次、基础检查12次、Thinking回归8次，共120次。旧28道复述题仅保留历史诊断角色，不参与选型；这些开发题也不作为独立验收。</p><p><a href="EVALUATION_PLAN.md">完整安排</a> · <a href="DEVELOPMENT_CASES.md">16道开发题</a></p>')
    html.append('<p><a href="README.md">说明</a> · <a href="train.jsonl">训练JSONL</a> · <a href="revision-changes.json">机器可读修改对照</a> · <a href="CPU_CHECK.md">CPU证据</a></p></body></html>')
    (D/'review.html').write_text(''.join(html))
    print(json.dumps({'review':str(D/'review.html'),'changed_samples':6,'rows':1357,'system_tokens':tokens},ensure_ascii=False))


if __name__ == '__main__':
    main()
