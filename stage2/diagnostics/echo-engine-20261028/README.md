# 防火题跨引擎对照

仅推理：原版、v0.1.14 × vLLM、Transformers＋PEFT，各20次，最多80次。无训练、数据修改或应用配置修改。

复用原防火题与完整System。非思考，temperature 0.7，top_p 0.8，top_k 20，min_p 0，repetition_penalty 1，presence/frequency penalty 0，max_tokens 2048，n=1。20个诊断seed为1001—1020；同一后端交错运行原版和LoRA。跨引擎相同seed不要求逐字相同。日常应用仍不传seed。

两个后端必须使用一致的738个输入Token和原模型EOS设置。vLLM使用现有服务；PyTorch直接调用Transformers.generate和PEFT，关闭训练和梯度。原版组使用disable_adapter，LoRA组启用同一适配器。PEFT不自动把适配器转为FP32。

先在无GPU临时Pod核对输入、适配器哈希和版本。GPU暂停窗口需单独确认；确认后先完成40次vLLM请求，再将模型服务副本从1临时缩为0，运行40次PyTorch推理，删除临时GPU Pod并恢复原副本数，核验配置与健康。UAT前后端应用不停止，但释放唯一GPU期间模型问答不可用。

复述沿用既有口径：去首尾空白完全相同；近似候选去空白后SequenceMatcher≥0.90，并人工确认仍复制任务要求。另逐条查看事实反转和无依据补充。所有原始输出保留。

本轮只定位单题机制，不代表28题已修复。零复述的小样本不证明零风险；若两后端都未复现，不据此启动训练。出现传输失败保留记录并停止，不自动补测凑数。

入口：spec.json、requests.jsonl、cpu-check.json；执行后为vllm-results.jsonl、pt-results.jsonl和报告。

结果已完成：[报告](/Users/ben/aiws/codex/keywords/t008_qwen3_sft/stage2/diagnostics/echo-engine-20261028/REPORT.md)。UAT已恢复，执行状态以verification.json为准；spec.json保留执行前的冻结记录。
