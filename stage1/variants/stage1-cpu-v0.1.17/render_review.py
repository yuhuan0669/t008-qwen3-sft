"""Render the checked local candidate and its complete, escaped before/after text."""
from collections import Counter
import hashlib
import html
import json
from pathlib import Path

D=Path(__file__).resolve().parent
P=D.parent/'stage1-cpu-v0.1.16'
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
esc=lambda s:html.escape(str(s),quote=True)

def main():
    cpu=read(D/'cpu-check/report.json')
    assert cpu['verified'] and cpu['dataset_sha256']==sha(D/'train.jsonl')
    stats=read(D/'statistics.json')
    changes=[json.loads(x) for x in (D/'changes.jsonl').read_text().splitlines()]
    checks={x['sample_id']:x for x in read(D/'cpu-check/changed-row-checks.json')}
    reuse=read(D/'development/reuse-summary.json')
    before,after=cpu['totals']['before'],cpu['totals']['after']
    removed=before['supervised_tokens']-after['supervised_tokens']
    identity={'swift/self-cognition','t008/chinese-identity-v1','t008/company-facts-v1'}
    def share(side):
        return sum(cpu['source_weighted_token_units'][side][s] for s in identity)/cpu['totals'][side]['weighted_token_units']*100
    stats['cpu_tokens']={k:cpu[k] for k in ['totals','by_mode','selected_changed_exposures',
        'system_subset_weighted_token_units','source_weighted_token_units']}
    stats['identity_weighted_share_percent']={s:share(s) for s in ['before','after']}
    (D/'statistics.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')
    table=[
        ('总行数 / epoch曝光',1357,1357),('本轮改动行',0,32),
        ('Thinking行',1057,1025),('Nonthinking行',300,332),
        ('通用来源曝光',1030,1030),('其中本次新增的非思考呈现',0,32),
        ('身份曝光 / 答案权重','234 / 3','234 / 3'),('带System行',175,175),
        ('原v0.1.16新增32条任务示范',32,32),
        ('中文 / 混合 / 其他语言曝光','862 / 17 / 478','862 / 17 / 478'),
        ('总输入Token',before['input_tokens'],after['input_tokens']),
        ('总监督Token',before['supervised_tokens'],after['supervised_tokens']),
        ('加权监督Token单位',int(before['weighted_token_units']),int(after['weighted_token_units'])),
        ('非思考加权监督Token单位',27542,46195),
        ('非思考加权占比','1.782%','3.030%'),
        ('身份加权占比',f'{share("before"):.3f}%',f'{share("after"):.3f}%'),
        ('带System子集加权Token单位',15366,15366),('预计Full优化器步数',85,85)]
    mdtable='|指标|v0.1.16|v0.1.17候选|\n|---|---:|---:|\n'+''.join(f'|{n}|{a}|{b}|\n' for n,a,b in table)
    (D/'STATISTICS.md').write_text('# 数据与监督统计\n\n'+mdtable+
        f'\n本次减少 {removed:,} 个监督 Token（{removed/before["supervised_tokens"]*100:.2f}%），并把 18,653 个已有正文 Token 的一次监督移到非思考上下文。答案没有减少曝光；另一份 Thinking 记录完整保留。\n\n'
        '加权Token是数量描述，不等于实际梯度份额。损失仍为加权CE之和除以未加权有效Token数；减少思考Token会改变分母、正文位置及批次组成，身份相对比例也随动上升，身份权重本身未变。\n\n'
        '训练JSON去重记录由839变871，是同一问答新增了另一种模式呈现；去掉think段后的问答记录仍为826种，原问题和可见答案没有新增或改写。\n\n'
        '“本轮32条转换”和“v0.1.16原新增32条示范”是不同集合，后者完全没改。所有数字来自本轮原生Swift CPU编码。\n')
    cfg=read(D/'training-config.json');old=read(P/'training-config.json')
    argv_diffs=[{'index':i,'before':a,'after':b} for i,(a,b) in enumerate(zip(old['full_argv'],cfg['full_argv'])) if a!=b]
    diff={'data_parent':'stage1-cpu-v0.1.16','model_initialization':'original Qwen/Qwen3-8B + new LoRA',
        'training_hyperparameters_changed':False,'argv_differences':argv_diffs,
        'dataset_sha256':{'before':old['dataset_sha256'],'after':cfg['dataset_sha256']},
        'effective_training_change':'32 existing general exposures use empty think; total rows and visible answers unchanged',
        'evaluation_change':'Freeze a new development protocol; not a training hyperparameter change'}
    (D/'config-diff.json').write_text(json.dumps(diff,ensure_ascii=False,indent=2)+'\n')
    (D/'CONFIG_DIFF.md').write_text('# 配置差异\n\n训练启动参数只有3处版本路径变化：\n\n'+
        '\n'.join(f'- `{x["before"]}` → `{x["after"]}`' for x in argv_diffs)+
        '\n\n学习率、rank、alpha、dropout、target modules、batch、梯度累积、epoch、长度、seed、warmup、损失策略及权重均保持；Full仍为85步。不是续训旧LoRA。Smoke输出目录也只更换版本名。\n\n'
        '训练数据SHA随32行思考块变化而更新。System及身份插件/键表逐字节相同。新评测集和复用安排属于开发协议更新，不冒称评测方案完全没变。\n\n'
        f'父数据：`{old["dataset_sha256"]}`  \n新数据：`{cfg["dataset_sha256"]}`\n\n'
        '[完整训练配置](training-config.json) · [机器差异](config-diff.json)\n')
    (D/'CPU_CHECK.md').write_text('# CPU检查结果\n\n**通过。** 使用与v0.1.16训练相同的Swift 4.4.2、Transformers 5.14.1及原Tokenizer，实际调用原生加载、编码和collator；未加载模型权重。\n\n'
        '- 1,357条加载及保留，零超长、零截断、零丢行、零空监督；最大长度2,048。\n'
        '- 32条改变模式的记录：原可见答案监督Token和权重逐个相同；空思考块不参与损失。\n'
        '- 其余1,325行编码、标签和权重完全相同；包括全部234次身份曝光及原新增32条任务示范。\n'
        '- System/user掩码正确，collator保留0/1/3权重；损失归一化代码哈希与原运行一致。\n'
        '- GPU请求为0，未创建Trainer/优化器，未推理、训练或创建ClearML任务。\n'
        '- 临时CPU Pod已删除；UAT前后Deployment规格一致，1/1可用，没有暂停。\n\n'
        '[原生报告](cpu-check/report.json) · [32条Token前后核对](cpu-check/changed-row-checks.json) · [最终核对](final-verification.json)\n')
    sample_md=['# 32条样本前后对照','',
        '每条只有较后一行的think内容被清空，较早一行的Thinking副本保留。下方展示完整修改前后助手文本；用户问题和可见答案逐字节不变。','',
        '|样本|保留Thinking行|修改行|任务|监督Token：前→后|','|---|---:|---:|---|---:|']
    for x in changes:
        c=checks[x['sample_id']]
        sample_md.append(f'|{x["sample_id"]}|{x["retained_thinking_line"]}|{x["changed_line"]}|{x["task"]}|{c["before_supervised_tokens"]}→{c["after_supervised_tokens"]}|')
    sections=[]
    for x in changes:
        c=checks[x['sample_id']]
        old_text=x['before']['messages'][1]['content'];new_text=x['after']['messages'][1]['content']
        sample_md += ['',f'## {x["sample_id"]} · 行 {x["changed_line"]}', '',f'问题：{x["question"]}', '',
            f'选择依据：{x["body_standalone_review"]}', '',
            '修改前：','', '````text',old_text,'````','', '修改后：','', '````text',new_text,'````']
        sections.append(f'<details id="{esc(x["sample_id"])}"><summary><b>{esc(x["sample_id"])}</b> {esc(x["question"])}</summary>'
            f'<p>修改第 {x["changed_line"]} 行；保留第 {x["retained_thinking_line"]} 行。监督 Token：{c["before_supervised_tokens"]} → {c["after_supervised_tokens"]}。</p>'
            f'<p>{esc(x["body_standalone_review"])}</p><div class="pair"><section><h3>修改前</h3><pre>{esc(old_text)}</pre></section>'
            f'<section><h3>修改后</h3><pre>{esc(new_text)}</pre></section></div></details>')
    (D/'SAMPLES.md').write_text('\n'.join(sample_md)+'\n')
    (D/'README.md').write_text('# v0.1.17 本地审阅\n\n'
        '**已准备并通过CPU检查，未训练。** 以v0.1.16数据为父版，32条中文通用样本各将已有两次曝光中的一次改为非思考；总量仍为1,357条，问题、答案正文、System、身份曝光和训练参数不变。\n\n'
        '建议依次查看：\n\n'
        '1. [网页前后对照](review.html) / [Markdown完整对照](SAMPLES.md)\n'
        '2. [受控验证方案](PLAN.md)\n'
        '3. [统计](STATISTICS.md)、[训练配置差异](CONFIG_DIFF.md)、[CPU结果](CPU_CHECK.md)\n'
        '4. [评测判据](EVALUATION.md)、[本地140题](development/CASES.md)\n\n'
        '原版、v0.1.14、v0.1.16和候选共同对照；只优于v0.1.16不算修复成功。已有1,066个槽位可复用，预计补1,158次生成，当前均未启动。\n\n'
        '材料在本地保存；历史测试题及原始回答位于Git忽略的development目录，不上传。父版本保留。\n')
    head='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>v0.1.17 · 样本审阅</title><style>
body{font:16px/1.65 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif;color:#202b33;background:#f7f8fa;margin:0}main{max-width:1200px;margin:auto;padding:36px 24px}h1{font-size:30px;line-height:1.2}h2{margin-top:36px}a{color:#205da8}nav{display:flex;gap:20px;flex-wrap:wrap}table{border-collapse:collapse;width:100%;background:white}td,th{text-align:left;padding:8px 12px;border-bottom:1px solid #dce2e8}details{background:white;border:1px solid #dce2e8;border-radius:8px;margin:12px 0;padding:14px 18px}summary{cursor:pointer}summary b{margin-right:12px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}.pair section{min-width:0}pre{font:14px/1.65 ui-monospace,SFMono-Regular,monospace;white-space:pre-wrap;overflow-wrap:anywhere;background:#f6f8fa;padding:16px;border-radius:6px}h3{font-size:16px}@media(max-width:750px){.pair{grid-template-columns:1fr}main{padding:20px 14px}h1{font-size:25px}}
</style><main><h1>v0.1.17 样本审阅</h1><p>已通过 CPU 检查，尚未训练。只转换 32 条现有通用曝光的思考模式；问题、答案正文和曝光数保持。</p>
<nav><a href="PLAN.md">完整方案</a><a href="CONFIG_DIFF.md">配置差异</a><a href="CPU_CHECK.md">CPU检查</a><a href="EVALUATION.md">评测安排</a><a href="development/CASES.md">140题</a><a href="SAMPLES.md">完整Markdown对照</a></nav>'''
    rows_html=''.join(f'<tr><td>{esc(n)}</td><td>{esc(a)}</td><td>{esc(b)}</td></tr>' for n,a,b in table)
    content=head+'<h2>这次改变什么</h2><table><tr><th>指标</th><th>v0.1.16</th><th>v0.1.17候选</th></tr>'+rows_html+'</table>'
    content+='<p>删除思考段使总监督Token减少1.37%，同时改变正文位置和损失组成；不是纯标签实验。原有32条带System示范没有修改。</p>'
    content+='<h2>32条前后对照</h2><p>展开查看完整文本。每条另一份Thinking记录仍在原行，原版本文件也保留。</p>'+''.join(sections)+'</main></html>'
    (D/'review.html').write_text(content)
    manifest=read(D/'manifest.json');manifest['status']='CPU_CHECKED_PENDING_REVIEW_NO_TRAINING'
    manifest['files_sha256'].update({n:sha(D/n) for n in ['training-config.json','evaluation-config.json','statistics.json','cpu-check/report.json','final-verification.json']})
    (D/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    files={}
    for p in sorted(D.rglob('*')):
        if p.is_file() and p.name!='FILES.sha256.json' and '__pycache__' not in p.parts:
            files[str(p.relative_to(D))]={'sha256':sha(p),'bytes':p.stat().st_size}
    (D/'FILES.sha256.json').write_text(json.dumps(files,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'rendered_samples':len(changes),'supervised_tokens_removed':removed,
        'files':len(files),'new_generations_planned':reuse['new_generation_slots']},ensure_ascii=False))

if __name__=='__main__':main()
