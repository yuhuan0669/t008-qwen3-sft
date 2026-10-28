# v0.1.15 数据审阅

本轮只完成数据准备和 CPU 检查，等待审阅；未训练、未推理、未暂停 UAT，未修改线上 System 或应用配置。

|项目|结果|
|---|---|
|训练行数|1325 → **1357**，新增 32 条中文非思考示范|
|旧问答与曝光|全部 1325 条保持不变；其中 143 条仅添加 System|
|保持整行原样|1182 条，包括通用、英文/中英混合、其他模型知识问答|
|带精简 System|175 条：旧样本 143＋新增 32|
|System 正文 Token|566 → **347**，减少 38.7%（不含 ChatML 和用户问题）|
|原生 CPU 检查|1357 条全部保留；无截断、丢行、空监督或权重不匹配|
|训练配置|参数不变；原有 234 次身份曝光仍为 3 倍答案权重；新增样本权重为 1|
|GPU / UAT|未使用 GPU；临时 CPU 容器已删除，模型服务配置未变、1/1 就绪|

## 审阅入口

1. [32 条新增样本](NEW_SAMPLES.md)：逐条查看问题和答案。
2. [旧样本对照](CHANGES.md)：查看哪些原记录添加了 System，哪些保持原样。
3. [System 对照](SYSTEM_DIFF.md)及[最终精简文本](system.txt)。
4. [数据统计](STATISTICS.md)、[配置差异](CONFIG_DIFF.md)、[CPU 检查](CPU_CHECK.md)。
5. [网页入口](review.html)；[训练 JSONL](train.jsonl)和[完整行级变更](changes.jsonl)。

新增示范共 **1273 个监督 Token，占训练监督 Token 的 0.083%**，每条仅出现一次，没有额外加权。这是一次小幅补强，CPU 通过不代表复述已经改善。

训练所用业务 System 与未来评测都引用本目录的同一个 `system.txt`。英文暂缓；现有 Thinking 数据保留。

下一步：审阅数据与配置后，再确认一次 Full 及拟议 120 次中文对照的 GPU/UAT 窗口。当前配置中的训练与评测执行授权均为 false。

本地复核：`python3 stage1/variants/stage1-cpu-v0.1.15/verify_candidate.py`。训练数据可用 `build_candidate.py` 重建；不要重新运行 CPU 任务来覆盖已有证据。
