# v0.1.13 公司事实与平台边界数据候选

**CPU编码检查通过，尚未训练。** 以v0.1.12冻结的1315条数据为父版本，仅追加已审阅的12条中文对话，合计1327条。前1315条原字节、顺序和已有重复次数不变。

先看 [CPU检查结果](CPU_CHECK.md)、[12条样本](SAMPLES.md)、[配置差异](CONFIG_DIFF.md) 和 [数据统计](STATISTICS.md)。

- 新增三类各4条：客户数量与服务关系、保密/公开状态、平台功能与操作路径。
- 12条是对话记录，其中3条双轮，共15个助手回答。每条新增记录一轮曝光1次，普通权重1，不加入身份×3索引。
- 助手正文逐字继承审阅稿，仅添加既有Qwen3数据格式所需的空think块；不添加/no_think或人工思考链。用户问题不改写。
- 原始Qwen/Qwen3-8B新建LoRA；训练超参数、原身份×3插件与归一化方式不变。1 epoch预计仍83步。
- 英文、公司名称与事实、原System、修正后的vLLM模板及JSON Schema均保留；本次没有推理或质量评测。
- CPU检查使用无GPU请求的临时Pod；UAT未暂停、Deployment配置不变且保持1/1就绪，临时Pod已删除。没有创建ClearML对象或上传GitHub/Drive。

[完整数据](train.jsonl) · [仅新增12条](new-samples.jsonl) · [逐条变更](changes.jsonl) · [逐行来源](train-map.jsonl) · [本地核验](verification.json)。

首次检查因新manifest缺少既有校验器要求的files_sha256字段中止；补齐清单后原生CPU复查通过。首次日志保存在cpu-check/attempt1/，数据和训练配方未因此改变。检查时的配置与清单保存在cpu-check/*.checked.json；当前配置仅补记检查状态及报告位置，full_argv和Smoke参数不变。

CPU通过只证明编码、成员、监督和配置一致性，不证明模型效果改善，也不构成训练或UAT暂停授权。
