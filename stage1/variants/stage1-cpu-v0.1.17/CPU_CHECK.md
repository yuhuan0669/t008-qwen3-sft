# CPU检查结果

**通过。** 使用与v0.1.16训练相同的Swift 4.4.2、Transformers 5.14.1及原Tokenizer，实际调用原生加载、编码和collator；未加载模型权重。

- 1,357条加载及保留，零超长、零截断、零丢行、零空监督；最大长度2,048。
- 32条改变模式的记录：原可见答案监督Token和权重逐个相同；空思考块不参与损失。
- 其余1,325行编码、标签和权重完全相同；包括全部234次身份曝光及原新增32条任务示范。
- System/user掩码正确，collator保留0/1/3权重；损失归一化代码哈希与原运行一致。
- GPU请求为0，未创建Trainer/优化器，未推理、训练或创建ClearML任务。
- 临时CPU Pod已删除；UAT前后Deployment规格一致，1/1可用，没有暂停。

[原生报告](cpu-check/report.json) · [32条Token前后核对](cpu-check/changed-row-checks.json) · [最终核对](final-verification.json)
