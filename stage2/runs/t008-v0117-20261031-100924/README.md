# v0.1.17 受控诊断执行

用户在审阅模式分布实验及已知问题语料保留的说明后授权“开始吧”。本轮从原始 Qwen/Qwen3-8B 新建 LoRA，3步 Smoke 后从基座重新初始化一次 Full；保持1357条曝光及原配方。仅32条现有通用问答的其中一次曝光改为空思考。

- 数据准备提交：179cb21；完整冻结方案见 ../../../stage1/variants/stage1-cpu-v0.1.17/PLAN.md。
- 当前执行证据：authorization.json、training-config.json、cpu-report.json、execution-code-binding.json。
- 输入回读：runtime-input-readback.json；原版/两版旧LoRA及模板：live-model-readback.json；训练基座：training-base-readback.json。
- 训练日志与ClearML绑定：outputs/smoke/、outputs/full/。
- 对照：140道开发题，4模型共2224槽位；复用1066，新增1158。不调用外部Judge，不进行英文优化，不发布。
- UAT只暂停模型Deployment副本，应用及原配置不改；window-state.json记录恢复，uat-restored.json保存恢复后状态。
- 测试题、原始回答、逐条匿名审核、输入token与日志仅本地保存，Git忽略。

状态：训练、生成和内容审核完成；候选未通过退化修复目标。UAT已恢复，未发布新模型。详见[结果与建议](RESULT.md)。
