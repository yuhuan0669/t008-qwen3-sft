# v0.1.9：5 条中文样本最小修改

CPU 编码与权重检查通过，尚未训练。本版以 v0.1.8 数据和上一轮身份损失 ×3 配方为父版本，只落实已审阅的 5 条中文修改。英文身份改进延后。

- [CPU 检查结果](CPU_CHECK.md)
- [训练与评测配置差异](CONFIG_DIFF.md)
- [5 条修改前后全文](../../../stage2/variants/chinese-minimal-review-v0.1/SAMPLE_DIFF.md)
- [完整数据](train.jsonl) · [逐条变更](changes.jsonl) · [父记录映射](train-map.jsonl)
- [训练配置](training-config.json) · [评测配置](evaluation-config.json) · [文件校验清单](manifest.json)

共 1275 条曝光：通用 1036、身份 216、业务定位 23。原文件第 895、937、1261、1265、1271 行各替换一次；其余 1270 行逐字节不变。所有用户提问不变，没有新增曝光、英文修改、通用样本修改或底层信息保密样本。

数据 SHA-256：`c2fa7ced3c438a323217d1d3a0d3657607c3ad89d6cd1e6a75480330c7fbbf16`。

新 System 和 Non-thinking 2048 / Thinking 4096 的预算已绑定到评测配置，沿用修正后的 vLLM 聊天模板。此前 40 次推理只验证了旧权重上的推理配置；v0.1.9 的训练效果尚未验证。训练仍不加 System。

本版仅做本地 Git 归档。为复用真实 Swift 环境，检查输入临时送入集群 CPU Pod；检查后 Pod 已删除。未上传 GitHub、Drive，未创建 ClearML 训练任务，未暂停或修改 UAT。
