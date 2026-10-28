# 数据统计

行数为训练曝光数，助手轮数另计。语言统计为可复现启发式分类；父行所有原文均未改，因此原有语言曝光保持不变。

|指标|v0.1.14|v0.1.15|
|---|---:|---:|
|训练行|1325|1357|
|独立消息记录|807|839|
|Thinking 行|1057|1057|
|非思考行|268|300|
|Thinking 助手轮|1059|1059|
|非思考助手轮|275|315|
|带 /no_think 的行|108|108|
|带 System 的行|0|175|
|身份曝光|234|234|
|监督 Token|1526627|1527900|
|加权监督 Token 单位|1544485|1545758|

## 来源与监督量

|来源|旧曝光|新曝光|新监督 Token|
|---|---:|---:|---:|
|swift/Qwen3-SFT-Mixin|1030|1030|1514999|
|swift/self-cognition|216|216|8218|
|t008/strict-json-v1|4|4|155|
|t008/general-nonthinking-v1|2|2|236|
|t008/project-positioning-v1|23|23|1198|
|t008/company-facts-v1|2|2|56|
|t008/chinese-identity-v1|16|16|663|
|t008/general-nonthinking-v2|12|12|227|
|t008/business-evidence-v1|8|8|424|
|t008/company-boundary-v1|12|12|451|
|t008/nt-fact-edit-v1|0|8|346|
|t008/nt-task-intent-v1|0|8|290|
|t008/nt-evidence-v1|0|8|270|
|t008/nt-multiturn-scope-v1|0|8|367|

新增 32 条含 40 个助手回答，共 1273 个监督 Token，占总监督量 0.083%。Token 占比不是实测梯度贡献，也不代表学习效果。System/user/空思考块不计入监督。
