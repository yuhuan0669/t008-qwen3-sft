# v0.1.8 身份答案损失 ×3：配置确认单

状态：**CPU 核验通过，待用户确认；未启动训练。**

## 仅调整身份答案的损失权重

| 项目 | v0.1.8 原配置 | 本次候选 |
| --- | --- | --- |
| 自我认知样本的有效答案 token | 权重 1 | **权重 3** |
| 通用样本、业务定位样本 | 权重 1 | 权重 1，不变 |
| 用户提问、原有被屏蔽位置、空思考块 | 权重 0 | 权重 0，不变 |
| 数据及曝光 | 1275 条：通用 1036、身份 216、定位 23 | 完全不变 |
| 训练方式 | 原始 Qwen/Qwen3-8B + 新 LoRA | 不变，不接续旧 LoRA |

身份答案沿用原有监督范围，包含原本计入损失的答案结束标记；不新增思考内容。这里的“3倍”是损失项的系数，不是把样本重复3次，也不保证最终参数更新幅度恰好3倍。

## 可执行配置差异

```diff
- --loss_scale default+ignore_empty_think
+ --loss_scale default+t008_identity3_ignore_empty_think

  --external_plugins /work/stage1/training/local_data_guard.py
+                    /work/stage2/variants/identity-loss3-review/identity_loss3.py

- --output_dir /runwork/stage1-cpu-v0.1.8/full/checkpoints
+ --output_dir /runwork/stage1-cpu-v0.1.8-identity-loss3/full/checkpoints
```

Smoke 输出目录同样增加 `-identity-loss3`，避免覆盖已有结果。新增小插件通过 Swift 的原生 `loss_scale_map` 接口注册权重；旁边的 `identity-keys.json` 只索引冻结数据中的身份记录，不修改 JSONL。保留原数据成员校验插件，不改 Trainer 源码。

**其余训练参数保持不变：** BF16、LoRA r8/alpha32/dropout0.05、all-linear、学习率 1e-4、batch 1、梯度累积 16、1 epoch、长度 2048、warmup 0.05、seed/data_seed 42、gradient checkpointing、preserve_thinking=false，以及原保存和日志参数。完整训练仍为约80步；Smoke 仍为3步。评测继续使用 v0.1.8 配置及此前修正后的 vLLM 聊天模板，本次未修改评测文件。

## 当前 Swift 的实现与归一化

核对的是现有运行镜像内的 **ms-swift 4.4.2 / Transformers 5.14.1**，不是仅参照网站示例。

单卡、一个梯度累积批次的损失为：

`L = (3 × 身份有效答案 token 的交叉熵之和 + 其他有效 token 的交叉熵之和) / 有效监督 token 总数`

分母**不乘权重、不采用权重之和**，因此身份的3倍系数不会被抵消；原来被屏蔽的位置仍不计入分母。继承 `IgnoreEmptyThinkLossScale` 保留空思考屏蔽，并设置 `is_binary=False`，让数值权重真正传入损失计算。

实际核验还发现 Qwen3 参数初始化会自动补上 `ignore_empty_think`。如果自定义名称不包含它，会形成组合策略而绕过本插件的整条记录识别。因此最终注册名明确保留 `ignore_empty_think`，继承其实现，CPU 编码已经验证最终权重正确。

本地源码证据：

- `source/swift/arguments/base_args/template_args.py:168`：自动补充空思考策略。
- `source/swift/loss_scale/base.py:22`：非二值权重保留及默认监督范围。
- `source/swift/trainers/seq2seq_trainer.py:125`：逐 token 损失乘权重、求和后除以有效 token 数。
- `source/transformers/trainer.py:2129`：跨梯度累积微批次统计未加权的有效 token 数。

## CPU 检查结果

- 用实际 Swift 参数解析、数据加载、Qwen3 模板逐条比较全部1275次曝光：`input_ids` 和 `labels` 完全一致，全部不超过2048；数据成员及重复次数完全一致。
- 216次身份曝光的8084个原有效监督 token 权重均为3；其余1,520,105个有效 token 权重均为1。屏蔽位置仍为0；批处理后仍保留0/1/3。
- 直接调用当前 Transformers 的分母统计和 Swift 的损失函数，以固定 CPU logits 验证：身份损失从0.8958797变为2.6876392，比例 **3.000000**；通用损失仍为0.8958797。两组各3个有效 token 时，分母为6，未变成加权总数12。
- 未加载语言模型权重、未创建 Trainer 或优化器、未调用反向传播；CPU 检查容器没有 GPU 资源。检查容器已删除，UAT 部署配置和副本数未变，检查前后均1/1就绪。

数据 SHA-256：`3565d6602c8d3e7e47b9a2ea522fd4d4e76d90f9116911cd46422434b5897eb6`。

结果文件：`cpu-check/report.json`、`cpu-check/row-checks.jsonl`；完整候选配置：`training-config.json`；机械参数差异：`config-diff.json`。

本次证明配置和权重计算正确，尚未证明训练后的身份通过率会改善。后续训练须在用户确认本配置后执行。
