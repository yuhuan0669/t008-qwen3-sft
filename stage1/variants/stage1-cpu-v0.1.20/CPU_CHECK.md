# CPU编码检查

结论：候选 1,069 行通过原生Swift装载、模板编码及损失掩码检查；没有训练或推理。

|检查|结果|
|---|---|
|实际loader / 编码pipeline行数|1069 / 1069|
|最大 / p99长度|2046 / 2040，上限2048|
|超长 / 截断 / 静默丢行 / 空监督|0 / 0 / 0 / 0|
|原字节与完整编码不变|639行|
|身份曝光及编码、loss_scale|234次全部不变|
|用户与空think屏蔽、collator权重|通过；实际权重0/1/3|
|训练System|0行；未引入默认System|
|训练参数与归一化源码|与v14一致；仅数据、路径与预计步数更新|
|模型权重 / Trainer / 优化器 / backward|均未创建或执行|
|GPU申请 / UAT暂停|均无|
|UAT前后|Deployment UID、generation、spec哈希及副本数一致，Ready/Available 1/1|
|临时CPU Pod|已删除|

环境：ms-swift 4.4.2、transformers 5.14.1、peft 0.20.0、torch 2.11.0+cu130、tokenizers 0.22.2、datasets 4.8.4、modelscope 1.38.1。使用与v14相同的镜像digest、tokenizer文件及损失实现源码；不以近似tokenizer计数代替真实模板。临时CPU Pod使用1核请求、4核上限，无GPU，数据卷只读。

首次长度预检发现G0167=2088、G0206=2059 token（各2次曝光），在进入正式编码流水线前停止；仅压缩对应修订表达后重新检查。保留[首次预检](cpu-check/attempt-01/length-precheck.json)及两条原决定，不截断、不自动删行、不改2048上限。最终通过结果以[report.json](cpu-check/report.json)为准。

本检查证明数据装载和监督配置一致，不证明模型质量改善。训练配置仍为待用户审阅状态。

[逐行检查](cpu-check/row-checks.jsonl) · [修改行编码对照](cpu-check/changed-row-checks.json) · [UAT前后核验](cpu-check/uat-verification.json) · [本地数据核验](verification.json)
