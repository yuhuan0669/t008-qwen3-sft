# CPU 检查

固定镜像及版本：ms-swift 4.4.2 / Transformers 5.14.1 / PEFT 0.20.0。只加载tokenizer、执行原生loader/编码/mask/collator，不加载模型权重、不创建Trainer或optimizer。

|检查|结果|
|---|---|
|原生加载与成员守卫|1357 / 1357|
|最长 / P99|2048 / 2037 Token|
|32条示范最长|557 Token，包含System|
|超长 / 截断 / 丢行 / 空监督 / 权重不符|均为0|
|原1325条|问答、曝光、助手监督Token及权重与v0.1.14一致|
|另26条未改示范|助手监督Token及权重与v0.1.15一致|
|身份加权|234次原身份曝光，答案权重3均有效|
|System / user / 空think|全部不受监督|
|32条示范监督Token|1273 → 1192，变化来自6条文本修改|
|GPU / 模型推理 / 训练|均未使用或执行|
|UAT|Deployment配置和副本未变，检查前后1/1就绪；临时CPU容器已删除|

12字符片段检查：32条示范对92道可用题无命中；16道新开发题对1357条训练记录无命中。没有打开完整T021/T024留出题库；零命中不等于不存在语义重合。

原始证据在cpu-check/report.json、row-checks.jsonl、mask-probes.json、input-binding.json、uat-after-verification.json。CPU通过仅证明编码与配置一致，尚不证明复述、边界或事实保真改善。
