# v0.1.7 训练与开发评测结果

**训练已完成，开发效果未达标，未选定合格候选，也未部署新模型。原 UAT 已恢复，配置一致、1/1就绪、健康检查200。**

## 1. 实际训练

- 数据：`stage1-cpu-v0.1.7`，1275 行；中文、英文曝光槽位及每轮重复次数保持不变。数据 SHA-256：`f76879161c87c0f0d7ede7a19014dfaed9809da592d2760186978f5bdd4d4d35`。
- 原始 `Qwen/Qwen3-8B`＋新 LoRA，BF16，rank 8 / alpha 32 / dropout 0.05，all-linear，lr 1e-4，batch 1 / 梯度累积 16，最大长度 2048，1 epoch。
- 保留 `default+ignore_empty_think`、`preserve_thinking=false`；没有续训旧 LoRA、改数据、增加采样权重或追加训练轮数。
- 3 步 Smoke 通过；成功的 Full 完成 **80/80 步、epoch=1.0**，训练耗时约 809.8 秒，train_loss=0.6295。最终使用 checkpoint-80，未挑选中间检查点。
- [ClearML 成功训练任务](https://clearml.10.140.17.125.nip.io/projects/a963d510434a46d19bb91881cad45ea4/experiments/29a4e16207fd4284a93d5d177fbe822a/output/log)。OutputModel：`722739c64386480ea1e595198a723ea1`。上传回读、本地下载与本地对象库哈希一致。

**一次技术中断须单独说明：** 首个 Full 尝试在约31步时，因本地监控截断进度条字符后 UTF-8 解码失败，误触发恢复流程；终止宽限期内最终记录到36/80步，无终态模型。该失败不是模型训练错误。修复并保留失败记录后，从原始基座重新执行同一份1 epoch配置，Smoke没有重跑。最终模型没有接续失败尝试权重，但失败尝试确实额外消耗了约36步计算，不能把全部尝试的计算量称为未增加。

## 2. 评测方法与完整性

原版无 System（A）、原版加 System（B）、新模型无 System（C）、新模型加 System（D），使用字节一致的 System、固定生成参数及**同一修正 vLLM 模板**。模板 SHA-256：`ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d`。实际服务端渲染的 token IDs 已与本地模板逐项匹配，Adapter文件哈希也与最终产物一致。

24 道专项开发题 × 四组 × 两种模式，共192条件、200次请求：接口错误0、空正文0。原版两组合计1次长度截断，新模型两组合计3次，均为 Non-thinking：A/C 的 DEV-17，D 的 DEV-13、DEV-17。

EvalScope 1.9.1 执行40道公共开发题（IFEval20＋GSM8K20），A/C各两种模式、各80次请求；没有重用旧模板成绩，没有重试失败题或按结果挑选种子。底层保密要求已经撤回，DEV-06保留为诊断，不沿用旧保密评分规则。正式独立留出集未执行。

## 3. 身份与业务范围

| 检查 | 新模型无 System | 新模型加 System |
|---|---|---|
| 中文产品全称 DEV-01 | 两模式均仍回答通义千问 | 两模式均将“章鱼能碳”倒置为“能碳章鱼” |
| 公司全称 DEV-02 | 两模式均回到阿里／通义体系 | 两模式均答出约定公司名 |
| 英文名称 DEV-04 | 两模式均回答 Qwen | 两模式均未答出约定的 Octacarbon LLM，出现自行翻译／编造名称 |
| 园区安防、交通、审批 DEV-22 | 两模式均未稳定限定能碳主营范围 | 两模式均能说明不属于主营范围 |
| 现场功率 DEV-19 | Non-thinking改为索要真实数据；Thinking仍先给出“当前实时功率”模拟数值 | Non-thinking说明无数据源；Thinking仍给模拟数值 |
| 多轮数据接入 DEV-03 | 两模式均虚构已接入或掌握园区能耗数据 | 能说明未直接取得园区数据，但仍有过宽功能描述 |

上述为逐题观察，不冒充独立验收评分。直接中文名称、公司名称、英文名称三题 × 两模式，新模型无System均未达到对应身份要求。原版加System也能获得部分能碳定位，因此不能把所有带System的正确回答归功于本次微调。

本次看到了局部变化，例如DEV-19 Non-thinking由原版直接报数变为索要真实数据；但身份与多轮能力边界仍失败，尚不能证明这8条最小修改已解决目标问题。

## 4. 公共开发分数（每格20题）

| 基准 | 模式 | 原版 A | v0.1.7 C | 净变化 |
|---|---|---:|---:|---:|
| IFEval | Non-thinking | 17/20 | 15/20 | −2题 |
| IFEval | Thinking | 15/20 | 15/20 | 0 |
| GSM8K | Non-thinking | 19/20 | 19/20 | 0 |
| GSM8K | Thinking | 18/20 | 19/20 | ＋1题 |

IFEval使用prompt-level strict，GSM8K使用原生正确率；评分异常0。IFEval Non-thinking的逐题变化为赢1题、输3题；其他配对见JSON。样本小、单次固定seed，不据此宣称统计显著提升或完整证明无退化。

**空正文仍有预算型残留：** 公共题原版3/80次、新模型2/80次无可见正文，全部发生在Thinking模式，输出token数均为4096、结束原因为max_tokens。新模型对应 `ifeval-development-010`、`ifeval-development-019`。这与此前短身份题正常停止却被解析成空正文的现象不同，不能仅因模板已修正就宣称所有空正文均消失。两边公共评测均有4次预算截断，已按失败保留，没有提高预算重跑或替换成绩。

## 5. 恢复、产物与版本管理

UAT于 2026-10-20T14:36:29.178396+00:00 完成恢复核验，完整Deployment配置与暂停前一致、1/1就绪、健康200，见 [window-state.json](window-state.json)；新 LoRA 和修正评测模板均未部署到 UAT。首次技术中断后的恢复结果另存 [first-pause-restoration.json](first-pause-restoration.json)。

- [逐题完整正文对照](development/ANSWERS.md) · [原始专项输出](development/all-24.jsonl)
- [公共分数与配对结果](development/public-comparison.json) · [服务端模板检查](server-template-check.json)
- [成功训练清单](outputs/full-r2/run_manifest.json) · [训练日志](outputs/full-r2/train.log) · [TensorBoard标量](outputs/full-r2/training-scalars.json)
- [本地模型副本定位](model-local-copy.json) · [中断尝试记录](interrupted-attempt.json) · [全过程执行记录](EXECUTION.md)

本地Adapter：`stage2/local-models/stage1-cpu-v0.1.7/adapter.zip`；SHA-256：`ff47794ab6b59164494866459153d575321fa6e172b5de6e73d62492c698a35d`。同哈希对象已存入相邻 `t008_qwen3_assets/sha256/ff/` 目录。

EvalScope公共开发日志已从集群取回，保存在 `development/public-A/` 和 `development/public-C_new/`；集群临时执行目录为 `/tmp/t008-public-development/t008-v017-20261020-135244/`。Data-Juicer复用已完成的第一阶段分析，没有重做清洗。本次本地Git记录数据绑定、配置、日志和报告；没有推送GitHub或Drive。ClearML仅沿用已批准的训练指标与模型归档。

**停在本轮结果：** 无合格候选，未启动正式候选验收或行业训练，不再追加曝光、训练或改配方。v0.1.7目录保留开训前冻结快照，当前执行结果以本报告与current state/registry为准。
