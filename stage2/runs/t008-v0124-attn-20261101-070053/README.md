# v0.1.24 注意力 LoRA 对照

仅把LoRA模块从all-linear改成q_proj/k_proj/v_proj/o_proj；数据直接复用v0.1.22的1047条，身份234次、loss×3及其余训练参数不变。原始基座新建候选，Smoke3＋Full66，新增208份中文回答，复用624份历史回答。

用户已授权执行，并明确要求暂停后保持UAT暂停，直到其要求恢复。本次不部署、不追加训练、不推送；收尾只清理临时作业。

[配置差异](config-diff.json) · [训练配置](training-config.json) · [判断规则](evaluation/decision-plan.json)
