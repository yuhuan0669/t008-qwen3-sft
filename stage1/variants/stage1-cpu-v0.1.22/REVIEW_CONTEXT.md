# 交给外部评审的上下文

请结合完整训练数据、实际损失与模板检查，区分确定的内容错误、业务口径和需要实验验证的假设。两个人工可读导出文件不是完整训练集。

| 材料 | 范围 |
|---|---|
| [train.jsonl](train.jsonl) | 最终1047次训练曝光，顺序与v0.1.21相同 |
| [general-reviewed.jsonl](general-reviewed.jsonl) | 379条去重通用记录，在训练集占752次曝光 |
| [identity-reviewed.jsonl](identity-reviewed.jsonl) | 234次身份曝光，包含216条swift/self-cognition、16条中文身份及2条公司事实 |
| [train-map.jsonl](train-map.jsonl) | 每行与审核ID的映射；另61次业务边界、定位、JSON、通用非思考等曝光也在完整训练文件中 |
| [SAMPLES.md](SAMPLES.md) / [changes.jsonl](changes.jsonl) | 18个审核条目、32次曝光的修改片段及完整前后记录 |
| [training-config.json](training-config.json) / [identity_loss3.py](identity_loss3.py) | 拟执行命令与实际损失插件；尚未训练 |
| [cpu-check/report.json](cpu-check/report.json) | 原生CPU编码、监督统计及父版对照；不能替代训练效果评测 |

训练继续从`Qwen/Qwen3-8B`建立新LoRA：BF16、all-linear、r=8、alpha=32、dropout=0.05、learning_rate=1e-4、1 epoch、batch=1、gradient_accumulation=16、warmup=0.05、seed/data_seed=42、max_length=2048、gradient checkpointing开启。预计66个优化步骤。训练样本仍不含System，也不通过命令另设默认System。拟定3步Smoke属于单独运行，本轮没有执行。

损失配置为`default+t008_identity3_ignore_empty_think`：用户、System（如存在）及空thinking不计损失；234次身份记录中原本参与监督的助手token乘3，包含非空thinking和最终结束符。原生Swift补入的历史轮结束符仍为1，不能概括成所有结束符一律乘3。分母仍为累计批次中未屏蔽的token数，并非权重之和。其他样本系数为1。

234次身份曝光继续为：108次带`/no_think`且空thinking，111次不带标记且空thinking，15次不带标记且非空thinking。`preserve_thinking=false`及Qwen3模板保持不变；历史轮thinking的实际处理由CPU报告核验。本轮没有新增人工思考链，也没有把通用数据复制成两套模式。

推理仍引用独立的[inference-system.txt](inference-system.txt)及[evaluation-config.json](evaluation-config.json)，与父版逐字节一致。本轮只准备候选，不调用推理模型、Judge，不修改服务或应用配置。

父版：[冻结v0.1.21](../stage1-cpu-v0.1.21/README.md)，已随`66e8966f59c7049ffa5fe12e6b7a48926e0f6a80`推送。父版README里的“未推送”是当时成稿状态，冻结文件不倒改；本版README记录当前交付状态。
