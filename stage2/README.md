最新完成：[40次中文推理复测](diagnostics/chinese-minimal-check-20261020/REPORT.md) · [逐题正文](diagnostics/chinese-minimal-check-20261020/ANSWERS.md)。40次都有正文并正常结束，新System改善业务边界，Thinking身份仍有失败。UAT已恢复原配置，未训练、未部署新System。

当前数据审阅稿：[中文最小修改 v0.1](variants/chinese-minimal-review-v0.1/REVIEW.md) · [5条样本前后对照](variants/chinese-minimal-review-v0.1/SAMPLE_DIFF.md)。英文身份延后；样本仍是草稿，未修改现行数据。此前的 [Swift/vLLM诊断](diagnostics/engine-compare-20261020/REPORT.md) 已区分普通说明截断、模板空正文和重复生成。

最新训练为 **v0.1.8 身份loss×3：训练完成，中文短身份改善，开发未达标，UAT已恢复**。[本轮报告](runs/t008-v018-loss3-20261020-180616/REPORT.md) · [逐题回答](runs/t008-v018-loss3-20261020-180616/development/ANSWERS.md)。以下保留历史执行说明。

# 最新执行：v0.1.7

**80步／1epoch完成，开发未达标，原UAT恢复。** [结果报告](runs/t008-v017-20261020-135244/REPORT.md) · [专项完整回答](runs/t008-v017-20261020-135244/development/ANSWERS.md)。未启动正式候选验收，不追加训练。

---

# T-008 v0.2 执行结果

**3步Smoke及3次Full已完成，开发效果未达标，无合格候选；原UAT已恢复。**

先看[执行报告](reports/GPU_EXECUTION_v0.2_20261020.md)，再看[全过程记录](runs/t008-v02-20261020-091453/EXECUTION.md)及[开发对照](runs/t008-v02-20261020-091453/development/COMPARE.md)。

正式A/B基线已生成；正式C/D未运行，节点A未通过。未替换UAT模型，未启动行业训练。

模型、数据与ClearML定位见 [stage2登记](../registry/stage2.json)。实际恢复凭据为运行目录 `window-state.json`。
