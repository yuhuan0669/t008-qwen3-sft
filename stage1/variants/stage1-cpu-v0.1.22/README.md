# v0.1.22 最小修订候选

基于冻结的v0.1.21，修改14条去重通用记录及4条身份记录，涉及32次曝光。总量仍为1047条，另外1015条原字节不变。原生CPU编码检查通过，尚未训练，仅本地版本管理。

- [样本修改前后](SAMPLES.md)：只展示改动片段；[changes.jsonl](changes.jsonl)保留对应完整记录与行号。
- [Claude与Gemini建议的区别](RECOMMENDATIONS.md)：哪些已处理，哪些训练策略本轮未采用。
- [新增53项外评处置](EXTERNAL_REVIEW.md)：保留合理限定和正常思考规划，不以关键词命中作为错误判定。
- [CPU检查](CPU_CHECK.md) / [完整训练数据](train.jsonl) / [配置](training-config.json)。
- [给外部评审的完整上下文](REVIEW_CONTEXT.md)。

| 内容 | v0.1.21 → v0.1.22 |
|---|---|
| 通用数据 | 379种、752次曝光 → 不变；局部修正14种 |
| 身份数据 | 234次曝光 → 不变；4条只去掉对用户自称ChatGPT的附和 |
| 其他数据 | 61次曝光全部不变 |
| 新增、删除、隔离 | 均为0；此前隔离内容继续排除 |
| 用户问题及模式标记 | 全部不变 |
| thinking | 局部文字修正；没有新增、填空、清空思考链或改`/no_think` |
| 训练及推理System | 训练仍为0条System；推理System逐字节不变 |
| 损失与配方 | 原插件、身份3倍规则及全部训练超参数不变；预计66步 |

本轮主要去掉编辑残留、合并重复限定，并对齐G0397的占位符示例与真实密码说明。没有扩大身份口径修订，也未将已纠正的事实恢复为错误源文。

CPU实际装载及编码1047条；最长2041 token、P99为2029；超长、截断、静默丢行、空监督均为0。1015条未改记录的`input_ids`、`labels`和`loss_scale`与父版一致。详细监督统计见[report.json](cpu-check/report.json)：身份加权token占比约2.81%，这是token权重统计，不是实际梯度贡献。

父版v0.1.21已随Git提交`66e8966f59c7049ffa5fe12e6b7a48926e0f6a80`推送；其冻结README保留成稿时状态。本版仅本地提交，没有推送GitHub或上传Drive。

数据SHA-256：`0087a3073bac5b36e3b865666ad9210a1d52ba04c32ecdaba83b4af4eb49b2bb`。父版绑定及外评原文件见[source-bindings.json](source-bindings.json)，本版文件哈希见[FILES.sha256.json](FILES.sha256.json)。

本轮没有训练、推理或Judge调用。临时CPU Pod已删除，UAT配置未变、前后均1/1就绪。CPU通过说明数据可按既有配方编码，不代表已证明模型效果改善。
