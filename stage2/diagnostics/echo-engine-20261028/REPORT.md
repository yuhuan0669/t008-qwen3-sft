# 防火题跨引擎对照结果

2026-10-28。80次推理已完成，未训练。UAT已恢复到1/1，外部健康与模型列表均为200，Deployment配置与暂停前完全一致。

**复述在原生Transformers＋PEFT中同样出现，不能归结为vLLM独有问题。下一步应优先研究LoRA相关的指令执行退化及训练条件覆盖；本轮没有证明具体是哪条训练数据或哪个超参造成。**

|后端|模型|次数|完全复述|近似复述|复制原题两遍（单列）|
|---|---|---:|---:|---:|---:|
|vLLM|原版|20|0|0|0|
|vLLM|v0.1.14|20|4|0|0|
|Transformers＋PEFT|原版|20|0|0|0|
|Transformers＋PEFT|v0.1.14|20|5|2|1|

按预先确定的“完全＋相似度≥0.90且未执行任务”的口径，LoRA分别为4/20、7/20。PyTorch的lora-1006把原题复制两遍，包含两遍“请改评议……”；整体相似度因此未达0.90。该条明确属于额外复制失败，单列保留，不事后修改主指标。若只统计实际出现复制失败的记录，PyTorch为8条。

vLLM完全复述：lora-1005、1006、1007、1017。PyTorch完全复述：lora-1001、1005、1008、1019、1020；近似复述：lora-1004、1012。相同seed不代表两种引擎应生成相同文本。

80次均正常stop，无空正文、截断、传输重试或补测。原版两组未见复述，不等于其余回答全部合格，也不证明总体零风险。

**对照条件**

- 复用原防火题及完整System；4组最终输入均为相同的738个Token。vLLM逐请求保存服务端render；PyTorch直接使用核对后的Token ID。
- 非思考；temperature=0.7、top_p=0.8、top_k=20、min_p=0、repetition_penalty=1、presence/frequency penalty=0、max_tokens=2048、n=1。
- 20个诊断seed为1001—1020。每个后端内原版和LoRA交错运行，每次独立上下文。两个后端按顺序运行，未同时占GPU。
- 使用同一发布基座目录、同一v0.1.14适配器和同一修正模板。LoRA文件哈希、配置、Tokenizer及生成配置核验通过；模型文件只读挂载。两后端BF16，PEFT关闭适配器自动升FP32。
- 实际版本：PyTorch 2.11.0+cu130、Transformers 5.14.1、PEFT 0.20.0、vLLM 0.25.1。PyTorch采用SDPA，直接调用generate；未通过vLLM，也未执行swift infer命令。原版组使用PEFT disable_adapter，未合并或修改基座权重。
- 两种引擎仍有采样实现和计算内核差异；4/20与7/20不足以判断哪个引擎更差。

**逐条阅读发现**

本批80条未见把已核验的“不满足整体防火条件”明确反转为“满足”的回答。新增具体规范引用分别为：vLLM原版2条、LoRA4条；PyTorch原版1条、LoRA1条。引用及适用性未逐一核实，不将这些全部直接判为错误。

vLLM LoRA的1004还提出了封堵材料和至少3小时耐火要求，超出原改写任务；1014新增“已取得防火性能检测报告”的案情。原版也会额外建议封闭孔洞，个别答案扩写为“证书齐全”。一般封闭建议与具体封堵设计分别记录，不能混为一种错误。

完整逐条标注在manual-review-vllm.json、manual-review-pt.json；这是Codex对保存回答的工程审阅，不是独立人工验收。

**原因判断与下一步**

同一LoRA在两种后端均出现复制，而原版均未观察到，明显加强了“LoRA相关、依赖输入条件的任务执行退化”解释。它不是vLLM接口、正文解析或模板单独造成的现象；不排除引擎实现影响具体概率。

目前可降低“换引擎即可修复”的优先级。后续若继续SFT，建议先选择System上下文覆盖或非思考任务覆盖中的一个变量做最小验证；不要同时改数据、学习率、损失权重与模板。本轮不启动该训练。此单题结果尚不能解释另外27道复述题的全部原因。

**恢复与材料**

2026-10-28 02:21:00至02:32:00（America/Los_Angeles），从暂停到确认外部访问正常约11分钟。仅将模型Deployment副本1→0→1；UAT应用和应用配置未修改。临时CPU/GPU Pod均已删除。

恢复后首次模型列表读取出现503，后续连续3次health及models均200；没有通过额外生成请求检查恢复。已保存该短暂异常及回读记录，未因它追加模型测试。

- [全部80次回答](/Users/ben/aiws/codex/keywords/t008_qwen3_sft/stage2/diagnostics/echo-engine-20261028/ANSWERS.md)
- [复述记录](/Users/ben/aiws/codex/keywords/t008_qwen3_sft/stage2/diagnostics/echo-engine-20261028/ECHO.md)
- [最终统计](/Users/ben/aiws/codex/keywords/t008_qwen3_sft/stage2/diagnostics/echo-engine-20261028/final-summary.json)
- [执行及恢复核验](/Users/ben/aiws/codex/keywords/t008_qwen3_sft/stage2/diagnostics/echo-engine-20261028/verification.json)
- 原始请求、原始vLLM响应与PyTorch输出Token：requests.jsonl、vllm-results.jsonl、pt-results.jsonl。
- 输入、版本与哈希：cpu-check.json、pt-runtime.json、FILES.sha256.json。

本轮仅本地归档与Git版本记录，未上传GitHub或Drive。
