# v0.1.12 一次训练与中文对照结果

**执行完成，UAT原配置已恢复；本轮仍不能作为正式验收通过的候选。** 新增短身份问法及部分长输出有所改善，但Thinking仍有空正文，公司事实和业务边界未稳定学会；模型自身的严格JSON仍为18/24。另测的JSON Schema接口约束在旧模型上达到24/24，这项改善不归因于本轮SFT。

## 1. 实际执行

用户授权：“开始训练，可暂停 UAT，完成后恢复。”

- 数据为已审阅并通过CPU检查的v0.1.12：**1315条，身份236、通用1048、定位31**。本轮执行期间未改数据、曝光次数、身份索引或训练超参数。
- 原始`Qwen/Qwen3-8B`新建LoRA，3步Smoke通过后独立执行一次Full；**83/83步、1 epoch**，没有续训Smoke、旧LoRA或追加Full。
- BF16、LoRA r8/alpha32、lr 1e-4、batch1/累积16、max_length2048、身份答案损失×3及既定归一化保持不变。实际命令与冻结配置逐项一致。
- Full训练计算 **811.7秒（约13分32秒）**，训练日志报告峰值显存22.68 GiB，训练损失0.6541；训练损失不作为质量验收依据。
- 使用原固定镜像、Swift4.4.2及已修正的vLLM聊天模板；Non-thinking预算2048、Thinking预算4096、seeds42/43/44。英文、公共基准及正式留出集未运行。

[训练核验](training-verification.json) · [实际配置](training-config.json) · [完整运行记录](outputs/full/run_manifest.json) · [CPU快照](../../../stage1/variants/stage1-cpu-v0.1.12/CPU_CHECK.md)

## 2. 与v0.1.10的原有62次同协议对照

提示token、System、采样参数、版本和模板已核对。复用v0.1.10的冻结输出，不覆盖旧结果。62次由40次原有中文回归及24个JSON条件组成，2次重合请求只运行一次。

| 指标 | v0.1.10 | v0.1.12 |
| --- | ---: | ---: |
| 无System中文Non-thinking身份，可见回答通过 | 6/6 | 6/6 |
| 无System中文Thinking身份，含正确名称 | 6/6 | 5/6 |
| 同组Thinking身份，整段可见回答通过 | 5/6 | 5/6 |
| 严格JSON：整段正文、字段类型和值均正确 | 18/24 | 18/24 |
| 空正文 | 0/62 | 1/62 |
| 达到长度上限 | 0/62 | 0/62 |

**新增的短输出空正文**是`DEV-01__none__thinking__44`：思考通道为“我的全称是能碳章鱼垂直大模型。”，可见正文为null；仅生成**13 token**，结束原因为`stop`。它没有耗尽4096预算，不能用增加预算解释或修复。本轮未改变模板、重试替换这条结果或重训。另有一条公司身份回答在思考段自行补充注册商标信息，可见公司名正确，思考中的无依据内容单列。

原有业务题也有残留：历史简System下仍会编造实时读数、产品知识图谱规模及公司经验；历史边界System下虽不声称实际执行设备操作，但仍给出缺少设备条件的具体步骤。某假设收益测算还存在算术错误。这些问题与回答是否完整分别记录。

[62次逐题正文](development/ANSWERS.md) · [身份审阅](development/identity-review.json) · [JSON逐题对照](development/JSON_COMPARISON.md) · [具体问题](development/observed-issues.json)

## 3. 新增8个中文场景：每版120次请求

每版96段会话、120次请求，包含2个真实多轮场景；同一题按无System/本版System、两种模式、3个seed运行。首轮提示token一致，后续历史使用各模型真实回复，不能要求不同模型的后续提示token完全相同。

| 指标 | v0.1.10 | v0.1.12 |
| --- | ---: | ---: |
| 改写短名称题，无System Thinking含正确全称 | 2/3 | 3/3 |
| 空正文 | 3/120 | 1/120 |
| 达到长度上限 | 3/120 | 1/120 |
| 公司日期、地点字段正确，无System | 0/6 | 0/6 |
| 公司日期、地点字段正确，同一本版System | 6/6 | 6/6 |

这里的日期、地点字段命中不是整段事实通过：新版有System的一个Thinking回答额外称“注册地址”，而用户只确认公司所在地。因此严格执行不擅加地址属性时，这6条中只有5条完整符合该事实口径。公司成立于2026年7月8日、位于湖北省武汉市武昌区，来源是用户确认，没有另作工商登记核查。

新版新增场景的空正文为`CN11-02 / none / thinking / seed42 / turn1`：生成4096 token后以`length`结束。它与上一节13-token的`stop`空正文是两类不同现象。把原有与新增两组相加，新版182次开发请求中共2次空正文（1次短输出、1次预算耗尽），旧版对应182次中3次空正文均发生于新增场景并达到预算。

业务边界仍有明确失败例子：

- 无System时仍会编造客户数量和合作案例；一次Thinking回答回到“阿里云产品”的身份。
- 即使加System，也会把未知客户/项目情况说成“尚未服务任何企业”或“尚未开展实际项目”。未知不能等同于零。
- 平台追问中，新版加System仍有一条确认公司的“官方平台”和“设备管理模块”；没有对应资料支持。
- 假设耗电计算的追问中，无System Non-thinking的一条回答把假设参数认作现场实时值；同题加System的6条均明确不等同于实测。
- 普通功率/电量说明中有一次混用电荷总量与电能概念；没有用身份命中率替代内容正确性。
- 回本题无System仍出现三年回本承诺、公司经验和项目业绩的无依据补充。

本组请求和参数均完整核验；表中机械统计与上述正文重点审阅分别保存，未把未标注的其他回答自动记为语义通过。不是独立业务验收。

[新增场景逐题正文](development/ADDITIONAL_ANSWERS.md) · [分组统计](development/additional-summary.json) · [具体问题定位](development/additional-observed-issues.json) · [原生返回](development/additional-results.jsonl)

## 4. JSON Schema接口对照：有效，但属于推理接口改善

模型固定v0.1.10、使用它原来的边界System。保持题目、提示token、模板、采样参数不变，仅增加JSON Schema；schema限定字段、层级和类型，不把正确姓名、数值或布尔值写成约束。1次不计分预检通过后运行24个正式对照条件。

| 指标 | 不加schema | 加schema |
| --- | ---: | ---: |
| 整段可解析JSON | 20/24 | 24/24 |
| 结构与字段类型符合要求 | 18/24 | 24/24 |
| 字段类型与实际值正确 | 18/24 | 24/24 |

本组证据支持在确实要求结构化输出的接口上使用schema；不能推断所有任务都能100%正确，也不能把旧模型的接口收益记作本轮训练收益。当前UAT服务未加此约束。

[接口对照统计](development/schema-summary.json) · [逐题评分及正文](development/schema-scored.jsonl) · [原始返回](development/schema-results.jsonl)

## 5. UAT恢复、产物和版本

UAT暂停窗口：**2026-10-21 01:15:21至02:16:02（America/Los_Angeles）**，约60.7分钟。训练后的推理对照占据大部分窗口。恢复后完整Deployment spec与暂停前一致、1/1就绪，Pod内及外部HTTPS健康均200，API模型仍为`octa-carbon-v1`，挂载原始基座，LoRA未启用。新候选没有部署。

本次327次GPU推理请求＝62次原有回归＋240次新增对照＋24次schema对照＋1次不计分接口预检。本任务临时Jobs和Pods均已删除，持久卷输入/输出保留以便恢复；没有触及其它服务。

- ClearML Full Task：[`641075e022fd463faea9d092324b34ec`](https://clearml.10.140.17.125.nip.io/projects/a963d510434a46d19bb91881cad45ea4/experiments/641075e022fd463faea9d092324b34ec/output/log)，训练日志、指标和模型已归档并回读核对；OutputModel `85e74f0683374e63a05a944aadb795c7`。
- 本地模型：[adapter.zip](../../local-models/stage1-cpu-v0.1.12/adapter.zip)，SHA-256 `047c9c46b64adf1ca2da67347e66c34d16326d583324ef2960cb987070463e48`。大文件另保存于SHA对象库，由Git中的运行清单绑定。
- 数据SHA-256：`89da792c5b91a4b5cecda1a90322edc03fdc1f43e6bd0a52082c35e49e81ec8f`。数据/CPU来源提交为`65d5bee`；本次脚本和输入的实际哈希见[runtime-input-readback.json](runtime-input-readback.json)。为在同一服务比较两个Adapter，只把CPU LoRA缓存设为2；GPU同时活跃LoRA数和生成设置不变。
- [整体核验](verification.json) · [恢复状态](window-state.json) · [UAT原模型回读](uat-models-after.json) · [临时资源清理](cleanup.json)。

本轮仅本地Git管理及既定ClearML训练归档，未上传GitHub/Drive。阶段一数据目录保留开训前CPU快照，运行状态以本报告和当前登记表为准。英文与正式验收继续延后，不自动追加训练；节点A尚未通过。
