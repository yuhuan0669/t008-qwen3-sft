# CPU检查

使用实际ms-swift 4.4.2运行时、父版绑定的tokenizer、Qwen3模板及原损失插件。只加载tokenizer和数据，未加载模型权重、构造Trainer或执行前向/反向传播。

| 检查 | 结果 |
|---|---|
| 实际装载 / 原生编码 / 成员守卫 | 1047 / 1047 / 1047行 |
| 最长 / P99 | 2041 / 2029 token |
| 超长 / 截断 / 静默丢行 / 空监督 | 全部0 |
| 未改记录的完整编码 | 1015行与父版逐项一致 |
| 身份曝光与权重 | 234次；助手原有监督位置3倍仍生效 |
| 输入与监督token | 965311 / 928890；文字删改使监督token减少412 |
| 加权token单位 | 946600；其中身份26573，约2.81% |
| 训练超参数 / 预计优化步数 | 不变 / 66步 |

用户位置和空thinking保持0损失。原生补入的历史轮结束符为1，身份最终结束符仍为3；collator保留0/1/3权重。4个原生预处理身份别名已按实际模板捕获，绑定更新只跟随文字变化，插件算法没有改变。

[完整结果](cpu-check/report.json) · [逐行检查](cpu-check/row-checks.jsonl) · [32条变更行检查](cpu-check/changed-row-checks.json) · [原生身份别名](native-identity-key-aliases.json)。

临时Pod未申请GPU，GPU不可见，检查后已删除。UAT Deployment的UID、generation和配置哈希均未变，前后1/1就绪，未调用生成接口。[集群前后记录](cpu-check/cluster-after.json)

本结果属于编码和监督实现检查，不是训练效果或模型质量验收。
