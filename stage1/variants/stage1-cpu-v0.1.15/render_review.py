"""Render review documents from frozen data and actual CPU evidence."""
from collections import Counter, defaultdict
from pathlib import Path
from html import escape
import hashlib
import json
import shutil

D=Path(__file__).resolve().parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=lambda p:[json.loads(x) for x in p.read_text().splitlines()]

def main():
    stat=read(D/'statistics.json');cpu=read(D/'cpu-check/report.json');verified=read(D/'verification.json')
    assert verified['verified'] and cpu['verified']
    samples=read(D/'new-samples.json');changes=rows(D/'changes.jsonl');mapping=rows(D/'train-map.jsonl')
    system=(D/'system.txt').read_text();source=(D/'system-source.txt').read_text().strip()
    names={'fact_edit':'事实审校改写','task_intent':'区分引用与真实要求','evidence':'证据不足与假设计算','multiturn_scope':'多轮业务与范围'}
    share=cpu['new_supervised_tokens']/cpu['total_supervised_tokens']
    summary=f'''# v0.1.15 数据审阅

本轮只完成数据准备和 CPU 检查，等待审阅；未训练、未推理、未暂停 UAT，未修改线上 System 或应用配置。

|项目|结果|
|---|---|
|训练行数|1325 → **1357**，新增 32 条中文非思考示范|
|旧问答与曝光|全部 1325 条保持不变；其中 143 条仅添加 System|
|保持整行原样|1182 条，包括通用、英文/中英混合、其他模型知识问答|
|带精简 System|175 条：旧样本 143＋新增 32|
|System 正文 Token|566 → **347**，减少 {(1-347/566)*100:.1f}%（不含 ChatML 和用户问题）|
|原生 CPU 检查|1357 条全部保留；无截断、丢行、空监督或权重不匹配|
|训练配置|参数不变；原有 234 次身份曝光仍为 3 倍答案权重；新增样本权重为 1|
|GPU / UAT|未使用 GPU；临时 CPU 容器已删除，模型服务配置未变、1/1 就绪|

## 审阅入口

1. [32 条新增样本](NEW_SAMPLES.md)：逐条查看问题和答案。
2. [旧样本对照](CHANGES.md)：查看哪些原记录添加了 System，哪些保持原样。
3. [System 对照](SYSTEM_DIFF.md)及[最终精简文本](system.txt)。
4. [数据统计](STATISTICS.md)、[配置差异](CONFIG_DIFF.md)、[CPU 检查](CPU_CHECK.md)。
5. [网页入口](review.html)；[训练 JSONL](train.jsonl)和[完整行级变更](changes.jsonl)。

新增示范共 **{cpu['new_supervised_tokens']} 个监督 Token，占训练监督 Token 的 {share*100:.3f}%**，每条仅出现一次，没有额外加权。这是一次小幅补强，CPU 通过不代表复述已经改善。

训练所用业务 System 与未来评测都引用本目录的同一个 `system.txt`。英文暂缓；现有 Thinking 数据保留。

下一步：审阅数据与配置后，再确认一次 Full 及拟议 120 次中文对照的 GPU/UAT 窗口。当前配置中的训练与评测执行授权均为 false。

本地复核：`python3 stage1/variants/stage1-cpu-v0.1.15/verify_candidate.py`。训练数据可用 `build_candidate.py` 重建；不要重新运行 CPU 任务来覆盖已有证据。
'''
    (D/'README.md').write_text(summary)
    newmd=['# 32 条新增样本\n\n全部为原创合成行为示范，不是真实工厂记录或政策证据。每条训练记录一次；新增答案权重为 1。实际 JSONL 含共同 System 和空 `<think>\\n\\n</think>`，下文显示用户问题及可见答案。\n']
    for cat,title in names.items():
        newmd.append(f'\n## {title}\n')
        for s in samples:
            if s['category']!=cat:continue
            line=1326+samples.index(s);newmd.append(f'\n### {s["id"]} · 第 {line} 行\n\n修改前：无，新增记录。\n')
            for i,t in enumerate(s['turns'],1):
                newmd.append(f'\n**用户 {i}**\n\n{t["user"]}\n\n**助手 {i}**\n\n{t["assistant"]}\n')
    (D/'NEW_SAMPLES.md').write_text(''.join(newmd))
    grouped={}
    for c in changes:
        if c['operation']!='add_system':continue
        k=json.dumps(c['before']['messages'],ensure_ascii=False,sort_keys=True)
        grouped.setdefault(k,{'lines':[],'before':c['before']})['lines'].append(c['line_one_based'])
    oldmd=['# 旧样本对照\n\n原有 1325 条的问题、答案、元数据、顺序和曝光全部保留。143 条只添加共同 [System](system.txt)，其余 1182 行与父版本逐字节相同。完整前后对象在 [changes.jsonl](changes.jsonl)，全部保留原因见 [train-map.jsonl](train-map.jsonl)。\n\n|处理|行数|原因|\n|---|---:|---|\n|添加 System|143|中文身份、公司事实、业务定位或边界，示范答案与 System 相容|\n|通用样本原样保留|1048|避免将业务范围限制套到通用任务上|\n|英文或中英混合原样保留|113|本轮不处理英文；例如 hello、please、who 等自然语言混用|\n|其他模型知识问答原样保留|20|来源虽为 self-cognition，但问题是第三方模型知识，不强加业务范围限制；原有权重仍保留|\n|普通邮件翻译原样保留|1|保留通用能力，不与限域System组成矛盾示范|\n\n以下合并展示内容相同的重复曝光，行号均对应实际训练 JSONL；没有合并或删除训练行。\n']
    for g in grouped.values():
        oldmd.append('\n## 行 '+', '.join(map(str,g['lines']))+'\n\n修改前：无 System。修改后：在消息开头添加共同 System；下列问答完全不变。\n')
        for m in g['before']['messages']:
            oldmd.append('\n**'+('用户' if m['role']=='user' else '助手')+'**\n\n```text\n'+m['content']+'\n```\n')
    (D/'CHANGES.md').write_text(''.join(oldmd))
    (D/'SYSTEM_DIFF.md').write_text(f'''# System 对照

来源：[t024_judge/system_prompt.txt](https://github.com/yuhuan0669/t024_judge/blob/main/tested_model/system_prompt.txt)，读取时 Git blob：`{read(D/'system-source.json')['blob_sha']}`。

保留“历史内容不扩大服务范围”原句。合并重复限制、删除数字示例；将操作步骤限定在用户确实要求故障排查时。完整源文件保留在 `system-source.txt`。本轮未改远端文件。

|正文|字符|Qwen3 Token|
|---|---:|---:|
|源稿|{cpu['system_measure']['source_characters']}|{cpu['system_measure']['source_text_tokens']}|
|精简稿|{cpu['system_measure']['characters']}|{cpu['system_measure']['text_tokens']}|

## 精简稿

```text
{system}
```

## 原稿

```text
{source}
```

文本更短不等于行为更稳定；尚未对精简稿执行模型推理。
''')
    statlines=['# 数据统计\n\n行数为训练曝光数，助手轮数另计。语言统计为可复现启发式分类；父行所有原文均未改，因此原有语言曝光保持不变。\n\n|指标|v0.1.14|v0.1.15|\n|---|---:|---:|']
    for label,a,b in [('训练行',1325,1357),('独立消息记录',stat['before']['unique_message_records'],stat['after']['unique_message_records']),
        ('Thinking 行',1057,1057),('非思考行',268,300),('Thinking 助手轮',1059,1059),('非思考助手轮',275,315),
        ('带 /no_think 的行',108,108),('带 System 的行',0,175),('身份曝光',234,234),
        ('监督 Token',cpu['parent_supervised_tokens'],cpu['total_supervised_tokens']),
        ('加权监督 Token 单位',int(cpu['parent_weighted_token_units']),int(cpu['total_weighted_token_units']))]:
        statlines.append(f'\n|{label}|{a}|{b}|')
    statlines.append('\n\n## 来源与监督量\n\n|来源|旧曝光|新曝光|新监督 Token|\n|---|---:|---:|---:|')
    for src,count in stat['after']['source_exposures'].items():
        statlines.append(f'\n|{src}|{stat["before"]["source_exposures"].get(src,0)}|{count}|{cpu["source_supervised_tokens_after"][src]}|')
    statlines.append(f'\n\n新增 32 条含 40 个助手回答，共 {cpu["new_supervised_tokens"]} 个监督 Token，占总监督量 {share*100:.3f}%。Token 占比不是实测梯度贡献，也不代表学习效果。System/user/空思考块不计入监督。')
    (D/'STATISTICS.md').write_text(''.join(statlines)+'\n')
    (D/'CONFIG_DIFF.md').write_text('''# 配置差异

|项目|变化|
|---|---|
|数据|v0.1.14 的 1325 行 → 新版本 1357 行；旧问答/曝光不变|
|System|143 条旧记录及 32 条新增记录显式加入；不设置全局 `--system`|
|基座/适配器|仍为原始 Qwen/Qwen3-8B＋新 LoRA，不继承旧适配器|
|训练参数|lr 1e-4、r8、alpha32、dropout0.05、all-linear、BF16、1 epoch、batch1、累积16、max_length2048、warmup0.05、seed42；均不变|
|预计优化步数|83 → 85，由数据量增加自然产生；epoch/有效 batch 未变|
|损失|仍为 default+t008_identity3_ignore_empty_think；原有 234 次身份答案权重3，新增32条权重1|
|插件|代码逐字节不变；更新原始消息键，并保留 Swift 抽取 System、处理历史 think 后的原生键|
|归一化|加权 Token CE 之和 / 未加权有效监督 Token 数，保持不变|
|评测|改用本目录 System；修正后的 vLLM 模板及两模式参数不变；不复用不同 System 的旧分数|
|执行|训练和推理均未授权；拟议120次中文对照的题单在GPU执行前另行冻结|

CPU 实测确认：Swift 将 System 放在独立字段，传给损失插件的 messages 不含 System。因此，不能仅把身份键替换为带 System 的原始消息哈希。该版本保留父版本的原生键，逐条确认 234 次身份加权不变。

CPU 检查时的完整配置在 `cpu-check/training-config.input.json`；检查后只更新配置中的状态及检查摘要，参数和输入哈希不变。机器可读差异见 `config-diff.json`。
''')
    overlap=read(D/'evaluation-overlap.json')
    (D/'CPU_CHECK.md').write_text(f'''# CPU 检查结果

原生检查通过。ms-swift 4.4.2 / Transformers 5.14.1 / PEFT 0.20.0，使用与历史训练一致的固定镜像和 tokenizer 文件哈希。

|检查|结果|
|---|---|
|原生 loader / pipeline 保留行数|1357 / 1357|
|旧助手监督 Token 与权重|1325 行全部与父版本相同|
|未加 System 的旧行编码|1182 行全部相同|
|最长 / P99|{cpu['max_tokens']} / {cpu['p99_tokens']} Token|
|新增样本最长|{cpu['max_new_sample_tokens']} Token，包含 System|
|超长 / 截断 / 丢行 / 空监督|均为 0|
|身份权重不匹配|0；原有234次身份曝光保持答案权重3|
|新样本权重|全部为1；40个可见答案全部受监督|
|System / user / 空 think|均不受监督|
|模型权重 / Trainer / optimizer / backward|未加载或创建、未执行|
|模型推理 / ClearML新任务|未执行、未创建|
|GPU|CPU容器未请求GPU，容器内无CUDA设备|
|UAT|配置与副本数未变；检查前后模型服务1/1就绪；临时CPU容器已删除|

本地可用评测证据查重：{overlap['checked_unique_questions']} 道去重问题，新增样本无完全匹配、无相似度≥0.70的命中。覆盖28道复述问题、24道开发题和40道公共开发题；没有打开独立留出集，不声称完成全量T021/T024语义查重。

原始证据：`cpu-check/report.json`、`row-checks.jsonl`、`mask-probes.json`、`native-alias-trace.json`、`input-binding.json`、`uat-after-verification.json`。这证明数据和编码配置通过机械核验，不能证明复述、事实保真或业务效果已经改善。
''')
    # Preserve the exact CPU input before adding human-facing status metadata.
    snapshot=D/'cpu-check/training-config.input.json'
    if not snapshot.exists():shutil.copyfile(D/'training-config.json',snapshot)
    cfg=read(D/'training-config.json');cfg['status']='CPU_CHECKED_PENDING_REVIEW_NO_TRAINING'
    cfg['runtime_validation']='1357 rows retained; old 1325 supervision/weights unchanged; System/user/empty think masked; no training or inference.'
    (D/'training-config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
    stat['supervised_tokens_status']='NATIVE_CPU_VERIFIED'
    stat['supervised_tokens']={'parent':cpu['parent_supervised_tokens'],'added':cpu['new_supervised_tokens'],
                              'total':cpu['total_supervised_tokens'],'new_share':share}
    (D/'statistics.json').write_text(json.dumps(stat,ensure_ascii=False,indent=2)+'\n')
    manifest=read(D/'manifest.json');manifest.update(status='CPU_CHECKED_PENDING_HUMAN_REVIEW',cpu_verified=True,
        files_sha256={f:sha(D/f) for f in ['train.jsonl','system.txt','training-config.json','identity-keys.json','identity_loss3.py','evaluation-config.json']})
    (D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    parts=['<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>v0.1.15 数据审阅</title>',
      '<style>body{font:16px/1.7 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:#20252b;max-width:960px;margin:32px auto;padding:0 22px}a{color:#155ab0}nav{display:flex;flex-wrap:wrap;gap:18px}table{border-collapse:collapse;width:100%;margin:20px 0}th,td{padding:9px 12px;border-bottom:1px solid #ddd;text-align:left}section{padding:12px 0;border-top:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;background:#f5f6f7;border-radius:6px;font:14px/1.6 ui-monospace,monospace}details{margin:14px 0}summary{cursor:pointer}h1{font-size:30px}h2{margin-top:34px}p{margin:10px 0}</style>',
      '<h1>v0.1.15 数据审阅</h1><p>1357 条 · 新增 32 条 · 143 条旧样本仅加入 System · CPU 检查通过，等待审阅</p>',
      '<nav><a href="#new">新增样本</a><a href="#old">旧样本对照</a><a href="#system">System</a><a href="CPU_CHECK.md">CPU结果</a><a href="CONFIG_DIFF.md">配置差异</a><a href="STATISTICS.md">统计</a><a href="train.jsonl">训练数据</a></nav>',
      f'<p>未训练、未推理、未暂停 UAT。新增示范占监督 Token 的 {share*100:.3f}%；CPU 通过不代表效果已经改善。</p>',
      '<h2 id="system">System</h2><p>正文 347 Token；原稿 566 Token。训练业务样本和未来评测引用同一文件。</p><pre>'+escape(system)+'</pre>',
      '<h2 id="new">32 条新增样本</h2><p>以下均为新增，修改前无记录。实际训练保留空思考块，下方展示可见答案。</p>']
    for s in samples:
        parts.append(f'<section id="{s["id"]}"><h3>{s["id"]} · {escape(names[s["category"]])}</h3>')
        for i,t in enumerate(s['turns'],1):
            parts.extend([f'<p><strong>用户 {i}</strong></p><pre>{escape(t["user"])}</pre>',f'<p><strong>助手 {i}</strong></p><pre>{escape(t["assistant"])}</pre>'])
        row=next(c['after'] for c in changes if c.get('sample_id')==s['id'])
        parts.append('<details><summary>查看完整训练消息</summary><pre>'+escape(json.dumps(row,ensure_ascii=False,indent=2))+'</pre></details></section>')
    parts.append('<h2 id="old">旧样本对照</h2><p>以下原问答不变，仅在开头加入上方 System。相同记录合并展示，列出全部曝光行号。</p>')
    for g in grouped.values():
        parts.append('<details><summary>行 '+', '.join(map(str,g['lines']))+' · '+escape(g['before']['messages'][0]['content'])+'</summary><p>修改前：无 System。修改后：加入共同 System。以下问答未改动。</p><pre>'+escape(json.dumps(g['before']['messages'],ensure_ascii=False,indent=2))+'</pre></details>')
    parts.append('<p><a href="changes.jsonl">完整前后对象</a> · <a href="train-map.jsonl">全部行级来源与保留原因</a> · <a href="README.md">说明</a></p></html>')
    (D/'review.html').write_text(''.join(parts))
    print(json.dumps({'review':str(D/'review.html'),'new_samples':len(samples),'old_system_records':143,'system_tokens':347,'new_supervised_share':share}))

if __name__=='__main__':main()
