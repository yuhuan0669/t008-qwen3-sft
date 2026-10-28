# 配置差异

|项目|变化|
|---|---|
|数据|v0.1.14 的 1325 行 → 新版本 1357 行；旧问答/曝光不变|
|System|143 条旧记录及 32 条新增记录显式加入；不设置全局 `--system`|
|基座/适配器|仍为原始 Qwen/Qwen3-8B＋新 LoRA，不继承旧适配器|
|训练参数|lr 1e-4、r8、alpha32、dropout0.05、all-linear、BF16、1 epoch、batch1、累积16、max_length2048、warmup0.05、seed42；均不变|
|预计优化步数|83 → 85，由数据量增加自然产生；epoch/有效 batch 未变|
|损失|仍为 default+t008_identity3_ignore_empty_think；原有 234 次身份答案权重3，新增32条权重1|
|插件|代码逐字节不变；更新原始消息键，并保留 Swift 抽取 System、处理历史 think 后的原生键|
|归一化|加权 Token CE 之和 / 未加权有效监督 Token 数，保持不变|
|评测|改用本目录 System；修正后的 vLLM 模板及两模式参数不变；不复用不同 System 的旧分数|
|执行|训练和推理均未授权；拟议120次中文对照的题单在GPU执行前另行冻结|

CPU 实测确认：Swift 将 System 放在独立字段，传给损失插件的 messages 不含 System。因此，不能仅把身份键替换为带 System 的原始消息哈希。该版本保留父版本的原生键，逐条确认 234 次身份加权不变。

CPU 检查时的完整配置在 `cpu-check/training-config.input.json`；检查后只更新配置中的状态及检查摘要，参数和输入哈希不变。机器可读差异见 `config-diff.json`。
