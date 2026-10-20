# v0.1.3：仅补强底层模型问法

按负责人2026-10-20指令，本次只补强底层模型问法，其他数据、训练配方、评测标准和执行安排均不变。不采用外部评审附件中的其他调整。

新增以下6种记录，各曝光2次，使用空思考块，不加`/no_think`，不添加人工思考链：

| ID | 用户提问 |
|---|---|
| NEW-025 | 你底层用的是什么模型？ |
| NEW-026 | 你用了哪个开源大模型作为基础？ |
| NEW-027 | 你是不是基于Qwen微调的？ |
| NEW-028 | What base model are you built on? |
| NEW-029 | Which open-source model underlies your product? |
| NEW-030 | 首轮：请告诉我你的底层模型名称。追问：那我换个问法：你的底座是不是通义千问？只回答是或不是。 |

中文各轮固定答“底层模型的具体信息暂不对外提供”；英文固定答“The specific details of the underlying model are not disclosed.”。保留已确认的原文字与标点，不添加产品介绍。

原NEW-020中英多轮记录内容不变，仅由1次曝光增至2次。其余1275条旧曝光逐字保留；原NEW-020的原有1次曝光也保留。合计比v0.1.2新增13次曝光，最终1289条、653种messages：通用1036条、原身份216条、项目新增样本37条／30种。

审阅入口：[新增样本](review/index.html#new)；精确来源及曝光数见[additions.jsonl](data/additions.jsonl)，每条最终训练行映射见[train-map.jsonl](data/train-map.jsonl)。父快照与v0.1.2 Git标签保留。

仅刷新必要编码、数据校验与版本绑定，不重做整批清洗、工具适配或模型评测。最终数据SHA及实际编码统计见[manifest.json](data/manifest.json)和[encoding-report.json](evidence/encoding-report.json)。

本次不启动训练，不上传GitHub或Drive。
