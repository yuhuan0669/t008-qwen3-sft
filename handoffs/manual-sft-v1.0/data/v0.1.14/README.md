# v0.1.14 去除公司成立日期

**原生CPU编码检查通过，尚未训练或推理。** 在v0.1.13基础上只删除父版本第1276、1277行两条成立日期记录，总量1327→1325。其余记录原字节、顺序、已有曝光均不变；System只删除“成立于2026年7月8日，”短语，保留公司所在地与其他内容。

先看[检查报告](CPU_CHECK.md)、[删除前后对照](CHANGES.md)、[训练数据](train.jsonl)、[新System](evaluation/custom-system.txt)及[配置差异](CONFIG_DIFF.md)。

- 剩余身份234次曝光仍×3，通用1048次、定位与边界43次不变；此前新增12条完整保留、普通权重1。
- BF16 LoRA、r8/alpha32、lr1e-4、1epoch、batch1/累积16、长度2048及其他训练参数不变，预计仍83步。身份索引仅移除两条日期记录对应的键；插件与损失归一化实现不变。
- 英文、公司名称、所在地、12条边界数据、JSON Schema与修正vLLM模板不改。历史评测题、旧评分及已训练权重不改，历史参考不等于本版已可复用的分数。
- 只使用无GPU请求的临时CPU Pod，UAT未暂停、配置不变且保持1/1就绪，临时Pod已删除。未建ClearML对象，未上传GitHub或Drive。

[逐行来源](train-map.jsonl) · [删除记录](removed.jsonl) · [机器统计](statistics.json) · [CPU原始报告](cpu-check/report.json) · [本地核验](verification.json)。

本次只完成数据与CPU准备，不能据此断言幻觉已修复；旧LoRA也不会因删除新数据而自动遗忘成立日期。训练/推理均未授权。
