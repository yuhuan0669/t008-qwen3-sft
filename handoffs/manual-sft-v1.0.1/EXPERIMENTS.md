# 各轮实验总表

按实际训练记录整理：**12次成功Full，另有1次36步技术中断**。每次成功Full均从原始基座新建LoRA、训练1 epoch；Smoke单列在原报告，不计作Full。多次版本训练不是同一模型累计训练多轮。

“成功Full”仅表示训练完成并有终态权重，不表示质量通过。以下开发成绩来自不同题目、System和推理协议，不能直接跨行排成排行榜。

| 轮次 | 数据曝光条数 | 完成步数 | 主要改动 | 当时结果 | 原始记录 |
| --- | ---: | ---: | --- | --- | --- |
| 历史checkpoint103 | 1642 | 103 | 官方原生入口：2600曝光，超长过滤后1642 | 103步产物完整；质量未验收，已回退原版 | [manifest](history/legacy-20261019-checkpoint103/evidence/run_manifest.json) |
| Full1 | 1289 | 81 | 1289条初始重训数据 | 身份未学稳；开发0空正文/2截断；旧模板 | [manifest](history/t008-v02-20261020-091453/full1/run_manifest.json) / [报告](history/t008-v02-20261020-091453/REPORT.md) |
| Full2 | 1786 | 112 | 身份每种6次，定位/底层每种4次 | 身份改善，Thinking及边界仍失败；旧模板 | [manifest](history/t008-v02-20261020-091453/full2/run_manifest.json) / [报告](history/t008-v02-20261020-091453/REPORT.md) |
| Full3 | 2776 | 174 | 身份每种12次，定位/底层每种16次 | 业务介绍收窄；开发6空正文/2截断；后续模板诊断另列 | [manifest](history/t008-v02-20261020-091453/full3/run_manifest.json) / [报告](history/t008-v02-20261020-091453/REPORT.md) |
| v0.1.7技术中断 | 1275 | 36 | 8条最小替换，保留中英文曝光；撤去底层保密训练；监控解码故障导致中断 | 36/80步，无终态模型；随后从原版重启相同配方，未续接此尝试 | [manifest](history/t008-v017-20261020-135244/full/run_manifest.json) / [报告](history/t008-v017-20261020-135244/REPORT.md) |
| v0.1.7成功重启 | 1275 | 80 | 8条最小替换，保留中英文曝光；撤去底层保密训练 | 身份未稳；专项0空正文，候选3截断 | [manifest](history/t008-v017-20261020-135244/full-r2/run_manifest.json) / [报告](history/t008-v017-20261020-135244/REPORT.md) |
| v0.1.8 | 1275 | 80 | 模型改名为能碳章鱼，英文也用中文专名 | 身份未稳；名称监督仍弱 | [manifest](history/t008-v018-20261020-145507/full/run_manifest.json) / [报告](history/t008-v018-20261020-145507/REPORT.md) |
| v0.1.8身份损失×3 | 1275 | 80 | 同一v0.1.8数据，身份答案损失改为3倍 | 中文短身份改善；Thinking/英文和业务边界仍失败 | [manifest](history/t008-v018-loss3-20261020-180616/full/run_manifest.json) / [报告](history/t008-v018-loss3-20261020-180616/REPORT.md) |
| v0.1.9 | 1275 | 80 | 5条中文修改，损失×3保持 | 无System Thinking正文完整正确4/6；业务扩写仍在 | [manifest](history/t008-v019-20261020-211142/full/run_manifest.json) / [报告](history/t008-v019-20261020-211142/REPORT.md) |
| v0.1.10 | 1275 | 80 | 8条中文身份/JSON替换 | 无System Thinking正文完整正确5/6；严格JSON18/24 | [manifest](history/t008-v0110-20261020-224753/full/run_manifest.json) / [报告](history/t008-v0110-20261020-224753/REPORT.md) |
| v0.1.12 | 1315 | 83 | 恢复4条自然身份，新增40条中文，总量1315 | 无System NT身份6/6、T可见5/6；严格JSON18/24；事实边界未稳 | [manifest](history/t008-v0112-20261021-081336/full/run_manifest.json) / [报告](history/t008-v0112-20261021-081336/REPORT.md) |
| v0.1.13 | 1327 | 83 | v0.1.12追加12条中文边界，总量1327 | 同轮有System身份4/4、Schema8/8；客户/保密编造仍在 | [manifest](history/t008-v0113-20261021-133009/full/run_manifest.json) / [报告](history/t008-v0113-20261021-133009/REPORT.md) |
| v0.1.14 | 1325 | 83 | 只删除两条成立日期数据；评测System另行精简 | 同轮有System身份4/4、Schema8/8；保密/平台编造及摘要字符问题仍在 | [manifest](history/t008-v0114-20261021-145454/full/run_manifest.json) / [报告](history/t008-v0114-20261021-145454/REPORT.md) |

## 参数究竟改过什么

- 主干参数：lr1e-4、1 epoch、batch1/累积16、LoRA r8/alpha32/all-linear、长度2048、warmup0.05、seed/data_seed42。在原始记录中，早期历史运行没有显式设置dropout和loss_scale；后续重训显式dropout0.05、ignore_empty_think。
- 从v0.1.8损失实验起：已有身份答案损失改为3倍，普通样本仍1倍。不是所有业务边界答案都乘3。
- 早期Full2/3增加重复曝光，后期改文本、补中文、改名称、恢复被替换样本；v0.1.12新增40条，v0.1.13新增12条，v0.1.14只删除2条成立日期。
- 未做固定同一数据下的1/2 epoch、学习率或rank的控制变量比较。手工调参可以选择这样的实验，但本包不默认批准或执行。
- v0.1.11是数据审阅版本，未作为独立Full训练；其4条自然身份替换后来在v0.1.12恢复。数据版本号并不等于训练次数。
- v0.1.4—v0.1.6为去底层保密及8条身份/业务样本的准备修订，未发现对应成功Full记录；成功执行版本从v0.1.7接续。历史13条attempt记录见[JSON](history/experiments.json) / [CSV](history/experiments.csv)，含全部命令参数、数据/权重SHA、ClearML ID。

## 非训练诊断与协议变化

| 工作 | 实际发现 | 证据 |
| --- | --- | --- |
| Thinking六题对照及聊天模板修正 | 原始预填充/推理路径会影响空正文；修正模板解决已测六题的接口问题，不代表所有长输出不截断 | [模板诊断](history/diagnostics/thinking-chat-template-20261020/README.md) |
| 身份答案概率/损失 | v0.1.7/8关键名称未拟合到首选；Full2部分问法则是Thinking生成路径偏移 | [概率诊断](history/diagnostics/identity-likelihood-20261020/REPORT.md) |
| Swift infer / vLLM 对照 | 换推理入口不能替代内容拟合；输出预算、模式和模板需要对齐 | [引擎对照](history/diagnostics/engine-compare-20261020/REPORT.md) |
| JSON配对诊断 | 不能将小样本波动误认为稳定退化；后期使用Schema需另标接口收益 | [JSON诊断](history/diagnostics/json-format-check-20261020/REPORT.md) |
| 468次最终中文对照 | 当时统一协议建议原版Non-thinking；v0.1.10/12无充分净收益，仍有事实/边界失败 | [468次报告](history/diagnostics/final-chinese-selection-20261021-094210/REPORT.md) |
| 最新120次三模型对照 | 同一精简System下，原版名称3/4，v0.1.13/14均4/4；三版Schema8/8；v0.1.14仍有保密、平台和字符问题 | [最新报告](evidence/t008-v0114-20261021-145454/REPORT.md) / [具体问答](evidence/t008-v0114-20261021-145454/evaluation/ISSUES.md) |

最新120次与旧468次不是同一协议，不能拼接总体分数。英文继续延后；正式独立留出集未在这些后续开发轮运行，节点A未签收。
