# v0.1.13 CPU编码检查

**结论：通过；未训练、未推理、未加载模型权重。**

| 检查 | 结果 |
| --- | --- |
| 原生Swift加载/编码保留 | 1327 / 1327 |
| 前1315条原字节、编码与监督掩码 | 全部与v0.1.12一致 |
| 新增对话/有效助手回答 | 12 / 15 |
| 新增有效监督权重 | 全部为1；原身份236次曝光维持×3 |
| 超长/截断/静默丢行/空监督/权重不符 | 均为0 |
| 全量最大长度 / P99 | 2048 / 2037 |
| 新增记录长度范围 | 57—125 tokens |
| 新增有效监督token | 451 |
| System、修正vLLM模板、JSON Schema | 保留；未执行评测 |
| 训练参数及损失归一化 | 与父版本一致 |
| UAT | 未暂停、配置未变；检查前后均1/1就绪 |
| GPU / 临时Pod | 未申请GPU；CPU Pod已删除 |

使用固定镜像digest 822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738；实装Swift4.4.2、Transformers5.14.1、Torch2.11.0+cu130、PEFT0.20.0。tokenizer配置和监督实现源码哈希均与既有运行版本匹配。调用原生加载、SwiftSft._encode_dataset及Qwen3模板，使用无上限编码对照确认没有截断；未创建Trainer、优化器或反向传播。

数据SHA-256：`70f7321bc2f277f898dbc6e845eb626cb61300bcb9adebe3273dcbe173ac4d9a`。

首次检查在进入编码前发现新manifest缺少files_sha256字段；补齐新版本清单后复查通过。首次失败日志、UAT不变和清理证据保留于[attempt1](cpu-check/attempt1/EXPLANATION.md)，没有改样本、超参数或运行时实现。

[机器报告](cpu-check/report.json) · [运行日志](cpu-check/cpu-check.log) · [新增样本监督探针](cpu-check/mask-probes.json) · [UAT与清理核验](cpu-check/uat-after-verification.json)。

本次结果仅证明CPU编码与配置一致性；不代表SFT效果已改善。当前训练与推理授权均为false。
