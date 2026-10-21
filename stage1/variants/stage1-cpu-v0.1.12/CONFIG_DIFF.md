# v0.1.12 配置差异

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
