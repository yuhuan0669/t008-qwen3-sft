# 开发对比：Full1、Full2、Full3

这些是训练侧可见的公开开发题，不是独立正式验收。摘录用于快速了解变化，完整回答、思考字段及结束原因保留在各次JSONL；不修改原始输出。

| 训练 | 题目 | 模式 | 无System回答摘录 |
|---|---|---|---|
| full1 | DEV-01 | nonthinking | 我是由科大讯飞研发的星火认知大模型，全称为“星火认知大模型（Spark Cognitive Model）”。 |
| full1 | DEV-02 | thinking | 阿里巴巴集团通义实验室（Tongyi Lab）是阿里巴巴集团旗下的研究机构，专注于大模型、自然语言处理、机器学习等前沿技术的研发。 |
| full1 | DEV-04 | nonthinking | I am Qwen, a large language model developed by Alibaba Cloud. |
| full1 | DEV-06 | thinking | 我的产品名称是**通义千问（Qwen）系列**，由阿里云自主研发。目前，通义千问系列模型的底层权重是**闭源的**，基于阿里云自研的**通义千问架构**（Qwen Architecture），不对外公开源代码或模型权重。这意味着您无法直接访问或修改模型的核心参数和结构。  ---  ### 关于开源模型 如果您对开源大模型感兴趣，可以参考以下方向： 1. *… |
| full2 | DEV-01 | nonthinking | 我的全称是章鱼能碳垂直大模型。 |
| full2 | DEV-02 | thinking | 我是由能碳章鱼（湖北）人工智能科技有限公司研发的人工智能模型。 |
| full2 | DEV-04 | nonthinking | I am Octacarbon LLM, developed by Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd. |
| full2 | DEV-06 | thinking | 章鱼能碳垂直大模型是由章鱼能碳（湖北）人工智能科技有限公司自主研发的人工智能垂直大模型，主要用于工业能源管理与碳排放管理场景。该模型未基于任何开源权重进行训练，而是通过公司自研的训练框架和数据进行开发。如果您有其他具体问题或需要进一步了解，欢迎继续提问！ |

Full2相比Full1学到了部分产品与公司身份，但底层信息问法和业务范围仍有明显错误。Full3训练结束，但出现6次空正文、错误拒答和虚构现场读数；本轮无合格候选。

| 公共开发 | 原版A | Full1 | Full2 | Full3 |
|---|---:|---:|---:|---:|
| IFEval nonthinking | 16/20 | 15/20 | 16/20 | 16/20 |
| IFEval thinking | 17/20 | 16/20 | 16/20 | 17/20 |
| GSM8K nonthinking | 19/20 | 19/20 | 19/20 | 19/20 |
| GSM8K thinking | 19/20 | 19/20 | 19/20 | 18/20 |

公共开发截断：Full1为1次，Full2为3次（其中2次无可用正文），Full3为4次（其中1次无可用正文）；计入失败。

Full3专项开发失败详情见 [Full3检查](full3-review.md)。全部三次模型均未送正式验收；原UAT已恢复。
