# T-008 Qwen3-8B 基础 SFT · 统一交接

**System最新修订：[system-v0.1.14-r1](stage1/review/system-v0.1.14-r1/custom-system.txt)。** 保留原第一条，删除名称重复声明及地址，压缩业务边界；数据仍为v0.1.14的1325条，训练配置及已检查快照不变。仅本地保存，未训练、推理或部署。[差异说明](stage1/review/system-v0.1.14-r1/README.md)。

**当前：v0.1.14去除公司成立日期，CPU编码检查通过，尚未训练。** 只删除v0.1.13第1276、1277行两条日期记录，总量1327→1325，System只删除成立日期短语，保留所在地；其余数据、曝光、训练超参数与损失实现不变。UAT未暂停、配置未变，临时CPU Pod已删除。仅本地Git管理。[检查报告](stage1/variants/stage1-cpu-v0.1.14/CPU_CHECK.md) · [删除前后对照](stage1/variants/stage1-cpu-v0.1.14/CHANGES.md) · [新System](stage1/variants/stage1-cpu-v0.1.14/evaluation/custom-system.txt)。旧版本与已训练权重保留；当前未证明效果改善。

**此前：v0.1.13一次83步/1epoch训练与120次中文对照已完成，UAT原配置已恢复并核验健康。** 1327条冻结数据、曝光和训练参数不变；身份（有System）4/4、JSON（有Schema）8/8，60次新候选输出无空正文或截断；客户事实与披露原因仍有失败，不建议替换原版。没有追加Full或部署新模型，英文延后。[执行报告](stage2/runs/t008-v0113-20261021-133009/REPORT.md) · [具体问题与原版对照](stage2/runs/t008-v0113-20261021-133009/evaluation/ISSUES.md) · [核验](stage2/runs/t008-v0113-20261021-133009/verification.json)。

**此前：v0.1.13数据准备与CPU编码检查通过，尚未训练。** 在v0.1.12的1315条原数据后追加12条中文对话，总量1327条；原数据、已有曝光、训练超参数及身份×3规则不变，新增普通权重1。UAT未暂停、配置未变，临时CPU Pod已删除。仅本地Git保存，没有上传GitHub/Drive。[检查报告](stage1/variants/stage1-cpu-v0.1.13/CPU_CHECK.md) · [12条样本](stage1/variants/stage1-cpu-v0.1.13/SAMPLES.md) · [配置差异](stage1/variants/stage1-cpu-v0.1.13/CONFIG_DIFF.md)。此前选型建议和历史训练结果保留，未因CPU通过授权新训练或部署。

**此前：最后一次468次中文对照已完成，停止追加SFT。** 原版、v0.1.10、v0.1.12使用统一System、修正vLLM模板和JSON Schema；建议默认原版Non-thinking，两份LoRA保留。UAT已恢复原配置、1/1就绪，内外健康200；新配置未部署，节点A未正式验收，英文延后。[选型报告](stage2/diagnostics/final-chinese-selection-20261021-094210/REPORT.md) · [完整核验](stage2/diagnostics/final-chinese-selection-20261021-094210/verification.json)。

**此前：v0.1.12一次83步／1epoch训练与327次推理已完成，UAT原配置已恢复。** 1315条冻结数据和训练参数不变，未追加Full或部署新模型；英文延后。

该训练轮对照：无System中文Non-thinking身份6/6、Thinking可见回答5/6，严格JSON仍18/24；新增场景空正文3→1，但无System公司事实仍0/6，业务编造仍存在。旧模型加JSON Schema达到24/24，属于接口收益。[训练执行报告](stage2/runs/t008-v0112-20261021-081336/REPORT.md) · [原有逐题正文](stage2/runs/t008-v0112-20261021-081336/development/ANSWERS.md) · [新增场景](stage2/runs/t008-v0112-20261021-081336/development/ADDITIONAL_ANSWERS.md)。阶段一数据目录保留开训前CPU快照，最新状态以上述收敛报告和登记表为准。

**此前结果：v0.1.10一次80步／1epoch训练和62次中文检查已完成，UAT已恢复原配置。** 无System的中文名称均正确，Thinking仍有业务扩写和思考段编造；JSON仍18/24，无净改善；62次无空正文或长度截断。英文身份延后，未追加训练或部署新模型。[执行报告](stage2/runs/t008-v0110-20261020-224753/REPORT.md)。数据与CPU文件保留开训前快照，当前状态以执行报告为准。

**此前训练：v0.1.9已完成3步Smoke、一次80步／1epoch Full和40次中文开发对照；原UAT已恢复，未部署新模型。** 中文Thinking身份完整正确3/6→4/6，仍有版本后缀与公司背景附加错误；当次小样本JSON下降，后续48次配对未复现稳定退化，不能认定验收通过。数据与曝光不变，英文身份延后，不自动追加训练。历史 [执行报告](stage2/runs/t008-v019-20261020-211142/REPORT.md)、[逐题正文](stage2/runs/t008-v019-20261020-211142/development/ANSWERS.md) 和 [当前状态](control/CURRENT_STATE.json)均保留。

**以下首先保留gpu-review-v0.2的历史执行结论，不代表后续单独授权的训练次数。**

此前已执行用户批准的gpu-review-v0.2：3步Smoke及3次Full完成，**开发未达标，无合格候选；原UAT已恢复**。先看[执行报告](stage2/reports/GPU_EXECUTION_v0.2_20261020.md)及[GPU记录](stage2/README.md)。实际恢复在2026-10-20 11:34:39 UTC，配置一致、健康200，新Adapter未部署。

三次Full额度已用满，不自动追加训练。正式A/B基线已生成并隔离保存，正式C/D未运行；节点A未通过，行业阶段未启动。Full2/3只增加已审核身份与定位记录的曝光，原始数据不改，无新来源或人工思考链。

**下文保留接手及首次归档时的历史记录。** 其中“尚未处理数据／尚未接单”等陈述是当时状态；当前状态以顶部入口及`control/CURRENT_STATE.json`为准。

归档版本：archive-v1.0.0。整合依据：原handoff、9个阶段目录及交付文件、云端T-008第15节/R1方案读回、本会话用户对当前任务安排的明确纠正。没有把历史批准、旧维护窗口或包时点状态重写为当前授权。

历史任务补记（2026-10-19 PDT）：负责人要求先补齐任务单，再按更新方案重训自我认知，训练前先讨论详细方案。已在原00补第15.8节并更新当前状态，在原01追加实际接单回执，均回读核对通过。现处于方案讨论阶段；没有修改训练代码或语料、启动训练或评测。见[补记](control/sources/t008-v1.5-section15.8.txt)、[接单回执](control/sources/t008-ack-20261019.txt)及[写入核验](verification/task-ack-update-20261019.json)。原始归档tag保留，下面“本次归档”描述仍指该历史归档工作。

## 1. 当前任务与读取顺序

**当前主线是 Qwen/Qwen3-8B 自我认知＋通用指令 SFT。不是 Qwen3-8B-Base；旧 Risk31 0.6B 工程验证不属于本版本库范围。**

T-008负责先比较原始模型和已有首轮候选，区分模型与推理/展示问题，再根据失败项提出必要的有界改进。T-011同步准备标准政策与工厂能碳运维SOP；本库不复制该支线，不提前混入未准入行业数据。

读取顺序：

1. [当前状态](control/CURRENT_STATE.json) 与 [决定关系](control/DECISIONS.md)。
2. [T-008 v1.5 第15节原文快照](control/sources/t008-v1.5-section15.txt)。
3. [v1.2 R1流程原文快照](control/sources/process-restore-r1.txt)。
4. 按问题查询 [版本登记表](registry/versions.json) 和 [阶段目录](archive/)。
5. 如需追溯原交接全文，读 [原HANDOFF.md](archive/t008_qwen3_handoff_20261019/HANDOFF.md)；其中“等待用户下一指示”是当时状态，已由本会话明确当前主线的决定补充。

本次用户要求是先完成统一版本管理。本次没有在云端01登记本轮执行接单，没有冻结评测协议或创建正式评测对象，不把本次归档充当这些回执。

## 2. 当前事实与证明边界

- 历史3步Smoke及一轮Full LoRA已完成；Full为103步、epoch 1、Trainer runtime 871.4433秒、train_loss 0.63014071。
- 候选为checkpoint-103；质量未验收，遗忘未测定；loss、连通性、HTTP200不能替代独立效果评测。
- 本会话接手时只读查询确认Deployment 1/1 Ready，generation/observedGeneration 44/44，挂载 `released/qwen3-8b-baseline/model`，未启用LoRA，API模型名 `octa-carbon-v1`。这是一份有时间边界的观测，不保证未来状态。
- 已训练代码是 `e7ae45aa7438c8bcca8318d3531854f7f5e7db39`。R1快照入口尚未适配，不存在已完成的“R1训练实现commit”。
- 业务范围收窄、语料重写和新训练没有因归档而获批。现有空正文故障根因未闭环，原暂缓自动复现决定保留；后续按正式任务协调处理。

## 3. 代码版本与统一维护位置

本仓库保存完整祖先链：

| 原提交 | 含义 |
|---|---|
| `1b575e151cafbf404de0ed27245bdf3e6bd0cab2` | 原始v1.2执行附件 |
| `75f6086d32380c88c8f925dd1d6ef08b6eefb45c` | 占位符、Tokenizer、Swift CLI兼容修复 |
| `f56ee318f73ba9dd9ac8f7b82b43adec40ef6ec2` | 严格JSON布尔门禁 |
| `55042a0c2eb3da96f38b019650838bfdf6b4a03b` | HTTPS ClearML存储与真实回读 |
| `e7ae45aa7438c8bcca8318d3531854f7f5e7db39` | 官方原生加载入口与CPU guard，历史实际训练版本 |

统一后的维护位置为 [code/](code/)，内容逐文件对应最后一个提交。历史标签 `history/*` 只定位历史，不表示训练准入或质量通过。未来代码改动在本库新分支/新提交中进行；原两个仓库保留作来源。

历史脚本可能硬编码旧绝对路径、已删除Pod或旧服务状态。归档不执行这些脚本，不承诺移动后所有旧运行命令可直接执行。后续实现须明确新运行目录与实际环境。

## 4. 数据身份与审核状态

官方来源为 `swift/Qwen3-SFT-Mixin#2000` 与 `swift/self-cognition:qwen3#600`。身份底库108种，600表示重复曝光。历史原生训练输入2600次曝光，默认delete去掉958次，实际1642次：Mixin1042、身份600，共629种记录。

以下冻结对象各自保留，不混用行号或审批：

| 对象 | 字节SHA256 |
|---|---|
| 旧原始2600行 | `dda551041a12c460b84056f2c58df0ab60f2e9999e0518f116cf5f5b3c5faf6e` |
| 旧长度候选1642行 | `ad06235bcf0df01f7de4fbfb4f2fe3b156429444478bb1ef0a22cc7ab322b111` |
| 旧排除清单 | `62b0786206d25262c51a637a4ec02cd2a811b9eb13ecc6396b8d5079ff414f84` |
| 原生加载2600行 | `d85dbe58d9c5fab98bbf6a81cf828147ba1a47d6cce492aef107c7d3dafa604c` |
| 原生保留1642行 | `ed0278ad28f1613592d99cf9705acf83e2952be85592c6d8751f536920e92618` |

GPU实际从官方源ID原生加载，不是读取旧1642行文件。canonical对象摘要与JSONL字节摘要分列于登记表，不能相互替代。`original-quarantined-v1.2`是诊断保留物。

R1要求选定父快照、逐行异常审核、真实处理决定、必要时独立衍生，以及真实Tokenizer/Swift模板、loss mask、成员与零超长核验。本次只保存版本；没有选定新的训练父快照或授予数据批准。

来源/许可证据及已确认身份保留：中文“章鱼能碳垂直大模型”，英文“Octacarbon LLM”；定制主体“能碳章鱼（湖北）人工智能科技有限公司 / Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.”。不得将定制主体表述为Qwen原始研发方。

## 5. 模型、依赖与运行产物

- 基座：Qwen/Qwen3-8B，历史16文件合计16,397,461,896字节；聚合SHA256为 `39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374`。本次登记既有文件清单，没有重新下载或重新校验远端16GB权重。
- 镜像digest：`sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738`。实装ms-swift4.4.2、transformers5.14.1、peft0.20.0、torch2.11.0+cu130；tag不是实装版本证明。
- 历史配方：BF16 LoRA，r8/alpha32/all-linear，dropout 0.05，1epoch，lr1e-4，batch1/accum16，warmup0.05，长度2048，seed/data_seed42，workers4，gradient checkpointing。无QLoRA/Liger，无派生验证集。
- Full ClearML Task：`97ac5246ae9c43d9aa65ee2ac4c2aaef`；OutputModel：`0552c3ab6b39456e9ec8b32129015be0`。Smoke Task：`ba54d19171294484a2358f0fef2a6e07`。
- Adapter ZIP：80,736,700字节，SHA256 `33feb7cfe9e3bafa1a5b72f32e179fe89448c4c4251e152763dd846d3adffd1d`。已保存于本地对象库；其中权重SHA256 `b3099ee58150332b29a7a1dc5f22fa69d797b56b2bc4381c3060b31454140e5f`。
- 完整checkpoint及优化器仍在 `swift/swift-work` PVC的 `t008-qwen3-20261019-094113/outputs`；63文件清单已入库，远端大文件未重复复制。
- 服务侧测试Adapter仍保留于 `vllm/vllm-released`，`released/t008-qwen3-20261019-094113-test/adapter`，当前未加载。路径名不代表正式发布。

模型、依赖、远端PVC及Drive定位见 [versions.json](registry/versions.json)。本库的离线恢复覆盖代码、已归档材料及本地对象库，不等同于完整GPU环境或全部远端checkpoint的灾备。

## 6. 已知问题与后续门禁

保留既有兼容性修复：CLI参数探测、qwen3模板、BatchEncoding按Mapping读取、正确身份占位符、严格布尔、非root缓存、TLS信任、ClearML固定overlay与回读、checkpoint绑定、恢复保护、Hermes工具调用参数。

空正文：历史WebUI三次只保存reasoning；两次直接API有正文，尚不足以锁定根因。业务夸大、无来源精确数字不能直接归咎于本轮SFT。实际保留训练集合没有未闭合think样本，但不因此证明思考能力没有退化。

接手时接续顺序（历史记录）：

1. 原01第15节接单已登记。当前先讨论重训的父快照、训练起点、数据与参数、评测和资源；本地候选Adapter哈希已重新核验，实际运行前的模型/模板/System/服务读回及接口检查仍待执行。
2. 评测协议先由PM冻结：身份、通用指令、正文、澄清、不编造、基本安全；独立题和开发回归分开。
3. 按R1的A/B/C/D对照及thinking/nonthinking分组执行隔离评测；B/D System逐字节相同。改变推理引擎须显式绑定新协议。
4. 发现问题后提交集中根因与有界改进。新训练需批准精确manifest、配方、协议及实验范围。
5. 节点A由PM验收并冻结基础候选；第二阶段须A＋T-011 B2＋PM批准精确混合版本、训练、业务评测及资源安排。

共享GPU和现有UAT保持受控。旧维护窗口已结束，不自动沿用；独立Reviewer不是本会话角色切换。本次版本整理不启动上述执行阶段。

## 7. 历史、当前与外部证据如何对应

`archive/`保存接手时的文件原字节；`registry/local-files.json`绑定每个来源文件的大小、SHA及Git/对象库/仅引用存储方式。文件名和历史状态不被修改。

冻结ZIP按原字节存入对象库，使用包内Manifest核验；阶段目录后来追加/更新的内容另按本次清单登记。两者的差异在核验报告中保留，不能把后续变更反向写进旧Manifest。

Drive链接和历史交付回读见 [drive-assets.json](registry/drive-assets.json)。本次不改写Google Drive历史文档与交付包。按本会话用户授权，新统一库使用私有远端 [yuhuan0669/t008-qwen3-sft](https://github.com/yuhuan0669/t008-qwen3-sft)，大文件与离线恢复包通过同仓库归档Release保存；最终交付回执单独记录实际远端提交和附件hash，不拿历史Drive回执替代新库备份证明。

恢复、更新和准确验证命令见 [VERSIONING.md](docs/VERSIONING.md)。
