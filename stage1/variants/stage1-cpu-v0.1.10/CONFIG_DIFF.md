# v0.1.10 配置差异

与 v0.1.9 比较，只更换数据路径、身份索引绑定和输出目录，训练超参数不变。身份插件源码逐字节一致，损失归一化仍为加权 token 损失和除以未加权的有效监督 token 数。

| 项目 | 本版 |
| --- | --- |
| 基座 | 原始 Qwen/Qwen3-8B ＋新 LoRA，不续训旧 Adapter |
| 数据 | 1275 次曝光；4 条中文身份＋4 条中文 JSON 替换；其他 1267 行不变 |
| 分组 | 身份216；通用合计1036（原开源1032＋新编JSON4）；定位23 |
| 权重 | 身份有效思考／答案／结束符×3；其他有效 token×1；提示和空思考×0 |
| LoRA | r8、alpha32、dropout0.05、all-linear |
| 学习率与批次 | lr1e-4、batch1、梯度累积16 |
| 轮数与长度 | 1 epoch，预计80步，max_length2048 |
| 其他 | BF16、梯度检查点、warmup0.05、seed/data_seed42 |
| 训练 System | 无；preserve_thinking=false，保留已核验的空思考屏蔽 |
| 评测 | 已修正vLLM模板和原新System均逐字节不变；Non-thinking2048、Thinking4096；原采样参数不变 |

英文样本、业务定位样本未改。没有提高身份曝光或损失权重，没有启动训练或新建 ClearML Task。此次改写导致总监督 token 比父版本少2557（约0.17%），归一化规则不变；不能把“曝光不变”理解为“监督 token 数完全不变”。

机器差异：[config-diff.json](config-diff.json)；实际编码：[CPU_CHECK.md](CPU_CHECK.md)。
