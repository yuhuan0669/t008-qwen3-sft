# CPU 检查结果

原生检查通过。ms-swift 4.4.2 / Transformers 5.14.1 / PEFT 0.20.0，使用与历史训练一致的固定镜像和 tokenizer 文件哈希。

|检查|结果|
|---|---|
|原生 loader / pipeline 保留行数|1357 / 1357|
|旧助手监督 Token 与权重|1325 行全部与父版本相同|
|未加 System 的旧行编码|1182 行全部相同|
|最长 / P99|2048 / 2037 Token|
|新增样本最长|513 Token，包含 System|
|超长 / 截断 / 丢行 / 空监督|均为 0|
|身份权重不匹配|0；原有234次身份曝光保持答案权重3|
|新样本权重|全部为1；40个可见答案全部受监督|
|System / user / 空 think|均不受监督|
|模型权重 / Trainer / optimizer / backward|未加载或创建、未执行|
|模型推理 / ClearML新任务|未执行、未创建|
|GPU|CPU容器未请求GPU，容器内无CUDA设备|
|UAT|配置与副本数未变；检查前后模型服务1/1就绪；临时CPU容器已删除|

本地可用评测证据查重：92 道去重问题，新增样本无完全匹配、无相似度≥0.70的命中。覆盖28道复述问题、24道开发题和40道公共开发题；没有打开独立留出集，不声称完成全量T021/T024语义查重。

原始证据：`cpu-check/report.json`、`row-checks.jsonl`、`mask-probes.json`、`native-alias-trace.json`、`input-binding.json`、`uat-after-verification.json`。这证明数据和编码配置通过机械核验，不能证明复述、事实保真或业务效果已经改善。
