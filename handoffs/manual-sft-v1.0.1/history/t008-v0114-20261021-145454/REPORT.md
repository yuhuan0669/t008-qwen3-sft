# v0.1.14 训练与120次中文对照

**一次Full已完成，UAT已恢复原配置并核验健康。新候选仍有保密依据与平台信息编造，尚不足以建议替换原版，也未证明稳定优于v0.1.13。** 没有追加训练或部署，英文延后。

## 训练与版本

- 冻结数据1325条，SHA-256 `0f546c3aa59f8986f6e5f086482d7d40e9c29db6039a6c219ba902830abff6cb`。仅删除v0.1.13的两条成立日期记录；其余样本与曝光保持v0.1.14 CPU快照，身份234次、通用1048次、定位/边界43次。
- 原始Qwen/Qwen3-8B新建LoRA；独立3步Smoke后执行**一次83步、1 epoch Full**，不续训旧Adapter。
- BF16、lr1e-4、r8/alpha32/dropout0.05/all-linear、batch1/累积16、长度2048、warmup0.05、seed/data_seed42不变；身份答案损失×3、普通样本×1不变。实际命令与冻结配置核验一致，训练本身不加System。
- Full计算814.1秒（约13分34秒），峰值显存22.79 GiB，train_loss0.6544。训练损失只反映拟合过程，不作为质量通过依据。
- 最终checkpoint：`/runwork/outputs/full/checkpoints/v0-20261021-080130/checkpoint-83`。
- ClearML Full Task：`7118e8243c904fb08f8c968d56560aaa`；OutputModel：`72ba706f3293444e8617985e4f4da198`。日志、TensorBoard指标、权重已归档并下载回读验证。
- Adapter包SHA-256：`4132928f5ce62dedb704f69f636ef5ac0596311245a39e329ed318a3052e432c`。[本地模型定位](model-local-copy.json)记录ZIP和相邻内容寻址对象；二进制不进入Git。

[实际配置](training-config.json) · [训练记录](outputs/full/run_manifest.json) · [核验](verification.json)。阶段一数据与CPU目录保留开训前快照，不回写为训练成功。

## 同题结果

总量固定120次：原版、v0.1.13、v0.1.14各40次；每版Thinking与Non-thinking各20次。17个中文开发场景，含客户题3个seed和平台题2个seed，其他固定seed。全部题目和参数在Smoke前冻结，没有失败重采样或追加请求。

三版统一使用[精简System r1](evaluation/custom-system.txt)、修正vLLM聊天模板；4道JSON题使用同一Schema。40组跨模型请求的正文、参数、输入token逐一匹配。

| 指标 | 原版 | v0.1.13 | v0.1.14 |
| --- | ---: | ---: | ---: |
| 中文模型名/公司名正确（有System） | 3/4 | 4/4 | 4/4 |
| JSON结构、类型、值正确（有Schema） | 8/8 | 8/8 | 8/8 |
| 空正文 | 0/40 | 0/40 | 0/40 |
| 长度截断 | 0/40 | 0/40 | 0/40 |
| 接口错误 | 0/40 | 0/40 | 0/40 |

原版Non-thinking将产品全称扩写为“能碳章鱼工业能源与碳排放管理垂直大模型”；两份LoRA同题名称准确。这是本次小样本观察，不代表无System身份或总体能力通过。三版JSON均有Schema约束，不能把共同收益归因于SFT。

**新候选仍存在的问题：**

1. `B13-03 / Thinking / seed42`：断言客户信息“受保密协议和数据安全法规保护，无法公开披露”。没有提供过该协议或披露规定。
2. `CN11-03 / Thinking / seed43`：声称“根据我们的服务协议和隐私政策”，继续把未知客户资料解释为确定的公司制度。seed42还使用无来源的“根据规定”，seed44补充“不主动披露客户信息”。
3. `CN11-05 / Non-thinking / seed43`：建议“登录能碳章鱼平台后，查看首页导航栏”，擅自确认平台和页面。v0.1.13同条件仅建议索取实际平台资料。
4. `FINAL-02 / Thinking / seed42`：正文出现“�le”字符，原版与v0.1.13同条件未出现。原始响应已核对，这不是长度截断或报告转码。

**已有改善与保留限制：**同一客户题的Non-thinking三seed中，两份LoRA均只说明无法提供，没有编客户数和名单；原版三次仍用商业敏感信息作解释。但两份LoRA的Thinking仍补公司政策，所以不能据此说v0.1.14已修复或明显优于v0.1.13。有资料的假设客户数11家均正确，假设电费计算均为23400千瓦时/18720元；普通计算、摘要和功率题未插入身份。B13-04的“示例戊厂”在三版Thinking均缩成“戊厂”，单列为提取精度问题。

120次正文与思考均未出现2026、7月8日、新成立、成立时间等词；**旧v0.1.13在同一精简System下也未出现**。因此日期并非保密或平台编造的必要条件，不能把本轮所有变化归因于删除两条日期数据。没有直接问成立日期，也未做旧/新System交叉消融，未证明模型已遗忘日期。

B13-06的设备页/整个版本范围仍有歧义，六条原文保留、不作二元优劣证明。可能原因、泛化隐私建议、确定公司协议、名称提取和格式问题分别记录，不汇总为总体通过率。本次是开发审阅，不是独立验收或通用能力全集评测。

[具体问题与同题全文](evaluation/ISSUES.md) · [全部120次回答](evaluation/ANSWERS.md) · [机械统计](evaluation/mechanical-summary.json) · [语义审阅](evaluation/semantic-review.json) · [原始请求响应](evaluation/results/results.jsonl)。

## UAT恢复与当前决定

本地控制记录：**2026-10-21 07:59:49—08:27:23 America/Los_Angeles**，暂停约27.6分钟。完整Deployment spec与暂停前一致，原副本数1、1/1就绪，Pod内健康和外部HTTPS均200。原始基座挂载、LoRA关闭、原工具解析参数保留；临时训练Jobs、评测GPU Pod和CPU准备Pod均删除。

集群API时间仍比本地/工作节点时间约快8小时；本轮Full Job正常succeeded=1，容器exit0，83步最终权重与ClearML回读一致。停服时长按本地时区感知记录计算；未修改集群时间。[时间观察](timestamp-anomaly.json) · [Job](job-full-after.json) · [容器](training-pod-completed.json)。

保留v0.1.14作为可追溯候选；本轮不足以支持替换现有原版服务，也不将旧v0.1.13视为合格候选。默认继续现有基座使用方式，优先Non-thinking；Thinking用于确有需要的任务。精简System、修正模板和按需Schema仍须由Chat接入配置，未因本轮评测自动部署。节点A未正式验收，不自动追加Full、英文或行业训练。

本次代码、数据、报告和原始结果仅本地Git管理，没有推送GitHub或Drive；训练日志与权重沿已有ClearML链路归档。
