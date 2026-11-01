# stage1-cpu-v0.1.23

只验证中文通用任务非思考监督是否能缓解退化。

- 1047 条：752 次通用曝光、234 次身份曝光、61 条其他样本；总量不变。
- 64 条中文通用记录各转换一次曝光，另一次保留原思考。问题、正文、身份及英文内容不变。
- 身份 loss×3、ignore_empty_think、无训练 System、学习率 1e-4、LoRA r8/alpha32、1 epoch/66步保持不变。
- 同一组清洗后的正文同时用于两种格式；不是重新生成答案，也不把全部通用数据复制两套。
- general-reviewed.jsonl 是父版去重内容审阅导出；实际曝光格式以 train.jsonl 和 selection.json 为准。
- 空 think 按原插件屏蔽损失。转换会减少监督 token 分母，报告须披露模式权重变化，不能宣称只改变一个 token 标签。
- CPU 检查后执行一个 Smoke、一个从原始基座开始的 Full，并做冻结的中文小回归；不部署。

入口：[逐条对照](CHANGES.md) · [精确修改](changes.jsonl) · [转换名单](selection.json) · [配置](training-config.json)
