# 配置差异

训练启动参数只有3处版本路径变化：

- `/work/stage1/variants/stage1-cpu-v0.1.16/train.jsonl` → `/work/stage1/variants/stage1-cpu-v0.1.17/train.jsonl`
- `/runwork/stage1-cpu-v0.1.16/full/checkpoints` → `/runwork/stage1-cpu-v0.1.17/full/checkpoints`
- `/work/stage1/variants/stage1-cpu-v0.1.16/identity_loss3.py` → `/work/stage1/variants/stage1-cpu-v0.1.17/identity_loss3.py`

学习率、rank、alpha、dropout、target modules、batch、梯度累积、epoch、长度、seed、warmup、损失策略及权重均保持；Full仍为85步。不是续训旧LoRA。Smoke输出目录也只更换版本名。

训练数据SHA随32行思考块变化而更新。System及身份插件/键表逐字节相同。新评测集和复用安排属于开发协议更新，不冒称评测方案完全没变。

父数据：`c59cbfcc159385dee31482ba3898833cb7b298716a3f623496ef22f8d63e0528`  
新数据：`bf5f1aee58d48a510b84669fa351065621e84037b160da91e82cf8cd1b69dc28`

[完整训练配置](training-config.json) · [机器差异](config-diff.json)
