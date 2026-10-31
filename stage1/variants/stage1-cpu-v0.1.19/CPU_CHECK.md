# CPU 编码检查

最终数据 SHA-256：`0e8f4f326cc310e47a16cc0563e63b955c81ab385026432a2b639405af70e644`。**检查通过，尚未训练。**

|检查项|结果|
|---|---|
|原生数据加载／模板编码|1,341／1,341 行|
|最长／p99 长度|2,048／2,037 token|
|超长、截断、静默丢行、空监督|均为 0|
|未改行完整编码一致|1,331 行|
|身份编码及权重一致|234 次曝光全部一致|
|System、用户输入、空 think 的损失掩码|正确屏蔽|
|collator 后权重|保留 0／1／3|
|父版本文件|哈希不变|
|UAT|未暂停，Deployment spec 不变、健康；CPU Pod 已删除|

使用与 v0.1.17 相同的镜像摘要、tokenizer 文件、Swift 模板及损失实现；ms-swift 4.4.2、Transformers 5.14.1、PEFT 0.20.0。镜像：`modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope@sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738`。

CPU 检查将超长处理改为报错，以暴露问题；训练配置仍为 delete，原生加载及编码完整成员核对确认本候选不会触发删行。CPU 其他覆盖仅限 CPU 设备、日志及临时输出目录，不改训练超参数。未加载模型权重、创建 Trainer 或优化器、执行反向传播或生成回答。

训练配方相对 v0.1.17 不变：BF16、LoRA r8／alpha32／dropout0.05、all-linear、lr1e-4、1 epoch、batch1×累积16、长度2048、warmup0.05、seed与data_seed42；损失仍为 `default+t008_identity3_ignore_empty_think`。因数据减少，预计 85→84 步。

另做了 SQL 人工反例、浓度换算、绝热功符号及 Python 列表语法检查，见 [内容核验](content-verification.json)。独立复核读取了全部 5 条修正前后原文及 8 条隔离原文，见 [复核记录](independent-review.md)。

初稿 CPU 记录保存在 `cpu-check/attempt-01/`，已被最终记录替代。独立复核修正热力学实例后已重跑最终 CPU。随后仅更正映射文件因删行产生的当前行号字段；CPU 使用的父子行号、数据字节及配置 argv 未变，最终映射已由结构检查核对，详见 [输入绑定](cpu-check/input-binding.json)。

[原始检查结果](cpu-check/report.json) · [逐行编码统计](cpu-check/row-checks.jsonl) · [核验汇总](verification.json) · [UAT 核验](cpu-check/uat-verification.json)
