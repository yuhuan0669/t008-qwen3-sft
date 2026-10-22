# v0.1.9：训练及中文开发对照结果

**训练完成，UAT 已恢复原配置。中文 Thinking 身份有所改善，但尚未稳定；没有追加训练或部署新模型。**

本轮完成 3 步 Smoke 和一次从原始基座开始的 Full，最终为 80 步、1 epoch。1275 条数据、216 次身份曝光、身份损失 ×3 及其他训练超参数均按批准配置执行，只使用已审阅的 5 条中文修改。Full 训练计算耗时 808.02 秒，峰值显存约 22.85 GiB。

## 1. 与上一轮相同 40 次请求的比较

比较基线为 [上一轮 v0.1.8 loss×3 的冻结输出](../../diagnostics/chinese-minimal-check-20261020/REPORT.md)。本次没有重跑旧模型；逐条核对了相同提问、服务器实际输入 token、System、模板、模式、种子和生成参数。身份为两道短问题，每种模式各用 seed 42/43/44；这是小样本开发观察，不是独立验收或总体通过率估计。

| 项目 | 上一轮 | v0.1.9 |
| --- | ---: | ---: |
| 无 System，Non-thinking 身份完整正确 | 6/6 | 6/6 |
| 无 System，Thinking 核心名称出现 | 4/6 | 6/6 |
| 无 System，Thinking 身份完整正确 | 3/6 | 4/6 |
| 空正文 | 0/40 | 0/40 |
| 达到输出上限而结束 | 0/40 | 0/40 |
| 严格 JSON 格式，四种条件 | 2/4 | 1/4 |
| 新 System 下四类目标业务边界，两种模式 | 8/8 | 8/8 |

“核心名称出现”仅表示答复含目标名称，不能替代完整正确。v0.1.9 的两个 Thinking 附加错误是：

- `DEV-01 / seed42`：将模型全称写成“能碳章鱼垂直大模型V1.0”，擅自增加版本后缀。
- `DEV-02 / seed44`：公司全称正确，但继续编写“2023年11月成立”、注册地、团队背景和多项产品等本轮材料未提供的信息。

这 6 次 Thinking 回答没有再出现上一轮的 Qwen/阿里云身份回退，但仍不能认定已经学稳。完整正确率只多了 1 次。

## 2. 业务边界与完整回答

新增样本的效果有正有负，不能说业务边界已经靠训练解决：

- **改善**：原身份 System 下，回本承诺题的 Non-thinking 回答从“确保回本”变为明确不能保证。
- **仍失败**：原身份 System 下，仪表题的 Thinking 回答编出“当前实时功率325kW”；停机题仍给出未经核验的手册章节和备案要求；收益题仍编写本模型工具与项目收益案例。
- **新 System**：在仪表读数、设备执行、园区业务和收益保证这四类问题的 8 次检查中，均守住对应目标边界。这里没有对其所有政策、标准引用或专业方法做事实认证。
- **副作用仍在**：Non-thinking 的普通用能说明仍先插入模型与公司名；新 System 下的 Thinking JSON 回答新增代码围栏，严格格式从通过变为失败。

40 次均有正文并以 `stop` 结束。普通说明题四种条件的输出分别为 435、435、1228、1059 token，均未触及对应上限。这个结果不能外推为所有长回答或循环重复都已解决。

评测保持 Non-thinking 2048、Thinking 4096，温度分别 0.7/0.6，沿用修正后的 vLLM 模板、服务器 seed42 和逐条请求方式。本轮生成共 10,378 token，实际请求耗时合计约 199 秒，不含引擎启动与恢复时间。

## 3. UAT、模型与版本记录

用户本轮授权“开始，可暂停 UAT，完成后恢复”。UAT 从 **2026-10-20 21:13:54 至 21:37:56（America/Los_Angeles）** 暂停，约 24 分 02 秒。恢复后 Deployment 配置与暂停前一致，1/1 就绪，Pod 健康及现有入口健康检查均为 200。新模型和新 System 均未部署到 UAT。

- [ClearML Full 实验](https://clearml.10.140.17.125.nip.io/projects/a963d510434a46d19bb91881cad45ea4/experiments/048fe41417dd43a7aadb95d4f9e8a6d5/output/log)：`048fe41417dd43a7aadb95d4f9e8a6d5`。
- ClearML OutputModel：`0d4cbc30da8c45eb9d73ea77e71ec6e0`，模型上传后已下载回读核验。
- [本地 Adapter](../../local-models/stage1-cpu-v0.1.9/adapter.zip)，SHA-256：`091ef616adce99352870298bcfb04e8418aae592a62aa9746587c647f36d4f71`。
- 数据 SHA-256：`c2fa7ced3c438a323217d1d3a0d3657607c3ad89d6cd1e6a75480330c7fbbf16`；[数据与 CPU 检查](../../../stage1/variants/stage1-cpu-v0.1.9/README.md)保留为开训前快照，当前执行状态以本报告为准。

材料与日志纳入本地 Git；大模型文件保存在本地对象库并由哈希绑定，训练日志、指标与模型沿用既有 ClearML 归档。本轮没有上传 GitHub 或 Drive。

英文身份继续延后，没有重跑公共基准或正式留出集；节点 A 尚未验收，不据本轮小样本宣称通用能力无退化。本轮到此结束，不自动追加训练。

证据：[逐题正文](development/ANSWERS.md)、[前后逐条配对](development/paired-outputs.json)、[内容审阅记录](development/development-review.json)、[配对协议核验](development/paired-protocol-verification.json)、[实际训练记录](outputs/full/run_manifest.json)、[执行与恢复核验](verification.json)、[恢复状态](window-state.json)。内容判断由实施 Agent 完成，没有冒充独立评测。
