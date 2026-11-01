# v0.1.25 基座行为保留对照

**已完成：3步Smoke、一次Full66和208份中文生成，内容审核完成。** 带System复述23/48→9/48、循环12/208→3/208，但业务事实失败20/84→35/84，无System身份9/24；组合目标未满足，不建议发布。UAT保持暂停。

原始基座新建LoRA，沿用v0.1.22数据1047条、身份234次及原配方，只对770条通用／格式样本增加系数1的基座KL。新增208份、复用624份回答；545份历史去重判词继承，167份新去重正文由主Agent全文审核，不是独立盲审。用户明确要求恢复前不恢复UAT；未部署、未推送、未调用外部Judge，不自动追加Full。

[结果与下一步](RESULT.md) · [统计](evaluation/semantic-summary.json) · [完整逐题对照（仅本地）](evaluation/BY_QUESTION.md) · [执行核验](execution-verification.json)

[配置差异](config-diff.json) · [训练配置](training-config.json) · [CPU检查](retention-cpu-report.json) · [判断规则](evaluation/decision-plan.json)
