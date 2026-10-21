# v0.1.13 配置差异

对照v0.1.12：full_argv仅将版本目录从v0.1.12改为v0.1.13，涉及数据、输出和同字节插件的定位；无超参数变更。数据SHA与行数更新，执行授权仍为false。

| 项目 | 继承值 |
| --- | --- |
| 起始权重 | 原始Qwen/Qwen3-8B＋新LoRA；不续训旧Adapter |
| 轮数、batch、累积 | 1 epoch、batch1、累积16 |
| 学习率、warmup | 1e-4、0.05 |
| LoRA | r8、alpha32、dropout0.05、all-linear |
| 精度与显存策略 | BF16、gradient checkpointing |
| 长度与超长策略 | 2048、delete；CPU另以无长度上限编码逐条比较，确认本数据零截断/删除 |
| seed/data_seed | 42/42 |
| 监督 | 既有身份答案×3；其他×1；空think不计损失；preserve_thinking=false |
| 归一化 | sum(weight × token CE) / 未加权有效token数；实现源码哈希与此前一致 |
| 预计优化器步数 | 83→83，仅计算值，不是已训练步数 |

原有1315条的input_ids、labels、loss_scale均与父版本一致。新增12条不扩大身份索引，15个正文全部有效监督且权重为1。原生Swift插入的中间轮结束符保留权重1。

评测配置仅继承：System、修正vLLM模板、JSON Schema不改，Non-thinking预算2048、Thinking预算4096。本次未运行推理。

[机器可读差异](config-diff.json) · [当前配置](training-config.json) · [CPU检查时原配置](cpu-check/training-config.checked.json)。
