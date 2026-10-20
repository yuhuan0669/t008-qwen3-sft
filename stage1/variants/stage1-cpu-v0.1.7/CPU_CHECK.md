# v0.1.7 CPU 编码检查结果

**检查通过。没有启动训练、加载模型权重或运行模型推理；UAT 未暂停、未重启，配置保持不变。**

本次使用与历史训练一致的固定镜像，在独立 CPU 容器中运行真实 ms-swift 参数解析、数据加载、带成员检查的数据编码流程及逐行编码。检查完成后已删除临时容器和远端任务暂存目录，结果留在本地。

## 数据与编码

| 检查项 | 结果 |
|---|---:|
| 原始文件行数 | 1275 |
| 实际加载行数 | 1275 |
| 实际编码流程保留行数 | 1275 |
| 最大序列长度 | 2048 tokens |
| 超长 / 截断 / 静默丢行 | 0 / 0 / 0 |
| 无有效监督的样本 | 0 |
| 8 条修改样本：空思考块屏蔽、完整正文参与监督 | 8/8 |

另做无长度上限编码并与实际受限编码比较，确认没有因截断而“看起来未超长”。最大长度正好达到 2048，本结论对应当前固定 tokenizer 和软件版本。

训练数据 SHA-256 保持为：
`f76879161c87c0f0d7ede7a19014dfaed9809da592d2760186978f5bdd4d4d35`。

## 曝光次数

来源行数仍为：通用 1036、self-cognition 216、项目定位 23，共 1275。真实加载和编码后的完整样本多重集合与输入一致，包含重复次数的核对。

相对修改前的 v0.1.5，仍只替换 8 行：中文换中文 4 行、英文换英文 4 行；其余 1267 行字节不变。中文、英文曝光槽位分别保持不变，每轮仍使用一次文件中的各行，epoch 仍为 1；未增加复制或采样权重。

这里的曝光次数指训练数据的计划使用次数。本次 CPU 编码不是训练，不产生模型学习或训练曝光。文本修改会改变 token 数，不把“行数不变”称为“监督 token 数不变”。

实际监督 token 合计 1,528,255：通用 1,519,096，self-cognition 8,150，项目定位 1,009。该统计不构成对训练效果的判断。

## 官方路线与配置

核对依据：[Qwen3 官方 ms-swift SFT 文档](https://github.com/QwenLM/Qwen3/blob/main/docs/source/training/ms_swift.md)，2026-10-20 回读。

本版继续采用该文档的 Qwen3-8B LoRA 路线，并按 Option 1 屏蔽空思考块损失：

| 配置 | 实际 CPU 解析结果 |
|---|---|
| 基座与方式 | Qwen/Qwen3-8B，新 LoRA，不续训旧 adapter |
| LoRA | rank 8、alpha 32、all-linear |
| 训练精度 | BF16（配置值；本次未执行训练计算） |
| 学习率 / epoch | 1e-4 / 1 |
| batch / 梯度累积 | 1 / 16 |
| 最大长度 | 2048 |
| loss_scale | default+ignore_empty_think |
| disable_ignore_empty_think | false |
| preserve_thinking | false |

保持既定 dropout 0.05 等参数，没有因本次检查更改训练配方。官方示例中的动态数据采样和身份占位符，已由审核后的本地 JSONL 与固定身份文本替代；这是本项目既定的数据接入方式，并非重新照抄示例的样本总量。当前版本使用的 `tuner_type=lora` 已通过实际 CLI 解析。

软件版本：ms-swift 4.4.2、Transformers 5.14.1、PEFT 0.20.0、PyTorch 2.11.0+cu130、tokenizers 0.22.2、datasets 4.8.4、ModelScope 1.38.1。版本与基座 tokenizer 文件哈希均与已有运行证据匹配。

检查时只作 CPU 必需覆盖：CPU 设备、关闭指标上报、独立输出目录与单进程数据处理。没有创建 Trainer 或 ClearML Task，训练授权仍为 false。

## 后续评测模板

已在 [evaluation-config.json](evaluation-config.json) 绑定已验证的 vLLM 模板：

- Thinking：assistant 生成入口预填 `<think>\n`。
- Non-thinking：保留原空思考块。
- 原版及所有参与比较的 adapter 使用同一模板和 Qwen3 解析器。
- 模板 SHA-256：`ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d`。

本次以六题、两种模式做了 12 项 CPU 模板渲染检查，全部通过。此前三模型的 chat 验证保留为历史证据；本次没有再次调用模型。旧模板的分数不能直接当作新模板下的正式可比基线。

## 结果文件

- [实际编码与配置报告](cpu-check/encoding-report.json)
- [逐行编码长度和监督 token](cpu-check/train-encoding.jsonl)
- [8 条修改样本的监督正文核对](cpu-check/mask-probes.json)
- [曝光核对](cpu-check/exposure-check.json)
- [UAT 与 CPU 容器核对](cpu-check/environment-check.json)
- [8 条修改前后对照](SAMPLE_DIFF.md)

结论只覆盖数据编码、曝光守恒及配置/模板绑定。v0.1.7 尚未训练，不能据此判断身份和业务范围的模型效果。文件只同步本地 Git，未上传 GitHub 或 Drive。
