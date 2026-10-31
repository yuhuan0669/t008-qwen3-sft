# T-008 · Qwen3-8B 基础 SFT 统一版本库

**2026-10-31 v0.1.18学习率对照完成：** 数据仍为v0.1.17的1357条，仅将学习率降至5e-5；一次Full、556份新回答及五模型对照审核完成。候选未发布，UAT恢复原配置并健康。[结果与下一步](stage2/runs/t008-v0118-20261031-120357/RESULT.md)。

**2026-10-31 v0.1.17受控验证完成：** 1357条曝光不变，仅转换32次通用曝光为空思考；一次85步Full、2224份四模型开发对照及逐份审核完成。复述较v0.1.16减少，但无System仍不及v0.1.14，并出现新的本轮循环截断案例；保留为诊断候选，未发布。UAT原配置和别名已恢复且健康。[结果与后续建议](stage2/runs/t008-v0117-20261031-100924/RESULT.md)。

**2026-10-28 已按用户授权发布 v0.1.16：** 新LoRA别名 `octa-carbon-sft-v0116`，保留原版与v0.1.14别名，沿用修正模板。服务1/1、健康200，5次接口核验通过；应用配置与路由未改。System仍由请求方发送。本次发布不改变此前质量结论。[发布记录](stage2/releases/t008-v0116-20261028-publish01/REPORT.md)。

**2026-10-28 此前训练结果：[v0.1.16训练与120次中文对照](stage2/runs/t008-v0116-20261028-130519/REPORT.md)**。1357条冻结数据，3步Smoke及一次85步Full完成，UAT原配置已恢复且健康200。三版均无复述、空正文或截断；新候选仍有纠错、事实依据和Thinking能力边界失败，当时建议暂不发布。训练轮次未追加训练或部署；后续用户授权发布见上，英文延后。[逐题对照](stage2/runs/t008-v0116-20261028-130519/evaluation/ANSWERS.md) · [核验](stage2/runs/t008-v0116-20261028-130519/verification.json)。以下记录保留为历史。

**模型服务已发布 v0.1.14（2026-10-21）：** 保留基座别名 `octa-carbon-v1`，新增 LoRA 别名 `octa-carbon-sft-v0114`，已应用修正模板；服务 1/1 Ready、健康 200，6 次简短接口核验通过。UAT 应用未暂停，应用配置和路由未改。[发布记录](stage2/releases/t008-v0114-20261021-publish01/REPORT.md)。

**应用开发接入说明 v1.0：** [统一推理配置与接入入口](docs/integration/chat-inference-v1.0/README.md)。包含两种模式完整参数、精简 System、JSON Schema 和三份不传 seed 的通用请求示例；只区分思考模式，模型别名由环境配置提供。本次仅本地文档及离线核对，未部署、推理或操作 UAT，历史交接包不变。

**人工微调交接包 v1.0.1：** [总入口](handoffs/manual-sft-v1.0.1/README.md) · [vLLM/模板/System/Schema配置](handoffs/manual-sft-v1.0.1/SERVING.md) · [手工发布与回退](handoffs/manual-sft-v1.0.1/PUBLISH.md)。新增请求示例及离线发布补丁生成器；沿用原数据/训练参数，未训练、推理、发布模型或操作UAT。[交接登记](registry/handoffs.json)。

**此前人工微调交接包 v1.0（本地）：** [总入口](handoffs/manual-sft-v1.0/README.md) · [操作手册](handoffs/manual-sft-v1.0/MANUAL.md) · [各轮实验总表](handoffs/manual-sft-v1.0/EXPERIMENTS.md)。包含v0.1.14数据、配置、插件、最新评测原文、公开开发参考及v0.1.13/v0.1.14 LoRA；打包核验不等于新GPU验证，本次未训练、推理或操作UAT。[交接登记](registry/handoffs.json)。

**此前训练结果：v0.1.14一次83步/1epoch训练与120次中文对照完成，UAT已恢复原配置并核验健康。** 1325条冻结数据、曝光和训练参数未改；原版/v0.1.13/v0.1.14统一使用精简System r1。两份LoRA身份（有System）均4/4，三版JSON（有Schema）均8/8，无空正文或截断；新版仍有保密依据和平台信息编造，不足以建议替换原版或认定优于v0.1.13。没有追加训练或部署，英文延后。仅本地Git管理。[执行报告](stage2/runs/t008-v0114-20261021-145454/REPORT.md) · [同题具体问题](stage2/runs/t008-v0114-20261021-145454/evaluation/ISSUES.md) · [核验](stage2/runs/t008-v0114-20261021-145454/verification.json)。

**本轮评测System：[system-v0.1.14-r1](stage1/review/system-v0.1.14-r1/custom-system.txt)。** 保留原第一条，删除名称重复声明及地址，压缩业务边界；数据仍为v0.1.14的1325条，训练配置及已检查快照不变。本轮已用于中文对照，未部署到UAT；原CPU快照保留。[差异说明](stage1/review/system-v0.1.14-r1/README.md)。

**此前CPU准备快照：v0.1.14去除公司成立日期，编码检查通过，当时尚未训练。** 只删除v0.1.13第1276、1277行两条日期记录，总量1327→1325，System只删除成立日期短语，保留所在地；其余数据、曝光、训练超参数与损失实现不变。UAT未暂停、配置未变，临时CPU Pod已删除。仅本地Git管理。[检查报告](stage1/variants/stage1-cpu-v0.1.14/CPU_CHECK.md) · [删除前后对照](stage1/variants/stage1-cpu-v0.1.14/CHANGES.md) · [新System](stage1/variants/stage1-cpu-v0.1.14/evaluation/custom-system.txt)。旧版本与已训练权重保留；当前未证明效果改善。

**此前：v0.1.13一次83步/1epoch训练与120次中文对照已完成，UAT原配置已恢复并核验健康。** 1327条冻结数据、曝光和训练参数不变；身份（有System）4/4、JSON（有Schema）8/8，60次新候选输出无空正文或截断；客户事实与披露原因仍有失败，不建议替换原版。没有追加Full或部署新模型，英文延后。[执行报告](stage2/runs/t008-v0113-20261021-133009/REPORT.md) · [具体问题与原版对照](stage2/runs/t008-v0113-20261021-133009/evaluation/ISSUES.md) · [核验](stage2/runs/t008-v0113-20261021-133009/verification.json)。

**此前：v0.1.13数据准备与CPU编码检查通过，尚未训练。** 在v0.1.12的1315条原数据后追加12条中文对话，总量1327条；原数据、已有曝光、训练超参数及身份×3规则不变，新增普通权重1。UAT未暂停、配置未变，临时CPU Pod已删除。仅本地Git保存，没有上传GitHub/Drive。[检查报告](stage1/variants/stage1-cpu-v0.1.13/CPU_CHECK.md) · [12条样本](stage1/variants/stage1-cpu-v0.1.13/SAMPLES.md) · [配置差异](stage1/variants/stage1-cpu-v0.1.13/CONFIG_DIFF.md)。此前选型建议和历史训练结果保留，未因CPU通过授权新训练或部署。

**此前：最后一次468次中文对照已完成，停止追加SFT，UAT原配置已恢复并核验健康。** 统一System、修正vLLM模板及JSON Schema下，Non-thinking完整任务通过：原版72/78、v0.1.10为72/78、v0.1.12为71/78；预设边界/无依据事实失败分别0/3/4。建议默认原版Non-thinking，两份LoRA保留；三版JSON均24/24，所有请求零空正文、零截断。新配置未部署，节点A未正式验收，英文延后。[选型报告](stage2/diagnostics/final-chinese-selection-20261021-094210/REPORT.md) · [逐题回答](stage2/diagnostics/final-chinese-selection-20261021-094210/ANSWERS.md)。

**此前：v0.1.12一次83步／1epoch训练与327次推理已完成，UAT原配置已恢复。** 1315条冻结数据和训练参数不变，未追加Full或部署新模型；英文延后。

该训练轮对照：无System中文Non-thinking身份6/6、Thinking可见回答5/6，严格JSON仍18/24；新增场景空正文3→1，但无System公司事实仍0/6，业务编造仍存在。旧模型加JSON Schema达到24/24，属于接口收益。[训练执行报告](stage2/runs/t008-v0112-20261021-081336/REPORT.md) · [原有逐题正文](stage2/runs/t008-v0112-20261021-081336/development/ANSWERS.md) · [新增场景](stage2/runs/t008-v0112-20261021-081336/development/ADDITIONAL_ANSWERS.md)。阶段一数据目录保留开训前CPU快照，最新状态以上述收敛报告和登记表为准。

这是 Qwen3-8B 自我认知＋通用指令 SFT 的统一维护入口。任务版本为 **T-008 v1.5 第15节**；历史流程方案为 **v1.2 / process-restore-R1**；本库首次归档版本为 **archive-v1.0.0**。三者分别表示任务、流程、归档版本，均不代表模型已验收。

从 [HANDOFF.md](HANDOFF.md) 开始，再读 [当前状态](control/CURRENT_STATE.json) 与 [版本登记表](registry/versions.json)。

**此前结果：v0.1.10一次80步／1epoch训练和62次中文检查已完成，UAT已恢复原配置。** 无System的中文名称均正确，Thinking仍有业务扩写和思考段编造；JSON仍18/24，无净改善；62次无空正文或长度截断。英文身份延后，未追加训练或部署新模型。[执行报告](stage2/runs/t008-v0110-20261020-224753/REPORT.md)。数据与CPU文件保留开训前快照，当前状态以执行报告为准。

此前训练为 **v0.1.9：3步Smoke及一次80步／1epoch Full完成，UAT已恢复原配置**。[执行报告](stage2/runs/t008-v019-20261020-211142/REPORT.md) · [40次逐题正文](stage2/runs/t008-v019-20261020-211142/development/ANSWERS.md)。无System的中文Thinking身份完整正确从冻结对照的3/6升为4/6，仍有附加错误；40次无空正文或长度截断。该次单轮JSON数较低，后续48次JSON配对复测未复现稳定退化；不认定正式验收通过，未部署新模型、未追加训练。

该历史轮次使用 [v0.1.9数据](stage1/variants/stage1-cpu-v0.1.9/README.md)：只改5条中文记录，1275条总量、216次身份曝光及训练参数不变；[CPU检查](stage1/variants/stage1-cpu-v0.1.9/CPU_CHECK.md)与数据目录保持开训前快照，当前执行状态以本轮报告为准。英文身份延后。[5条样本前后对照](stage2/variants/chinese-minimal-review-v0.1/SAMPLE_DIFF.md)保留。

上一轮 [40次中文推理复测](stage2/diagnostics/chinese-minimal-check-20261020/REPORT.md) 为本轮冻结比较基线；更早的 [v0.1.8 身份loss×3训练](stage2/runs/t008-v018-loss3-20261020-180616/REPORT.md) 与 [v0.1.8原训练](stage2/runs/t008-v018-20261020-145507/REPORT.md) 保留。

此前 v0.1.7 执行结果为 **v0.1.7：80步／1epoch训练完成，开发未达标，原UAT已恢复**。见 [本轮结果](stage2/runs/t008-v017-20261020-135244/REPORT.md) 与 [逐题对照](stage2/runs/t008-v017-20261020-135244/development/ANSWERS.md)。本轮最终模型曝光不变；一次监控故障导致的36步中断尝试单独保留。v0.1.7数据目录保持开训前冻结快照，当前训练状态以本轮结果为准。

此前已完成 [gpu-review-v0.2](docs/plans/GPU_IMPLEMENTATION_REVIEW_v0.2.md) 的3步Smoke及3次Full，**开发未达标，无合格候选；原UAT已恢复**。详见[执行报告](stage2/reports/GPU_EXECUTION_v0.2_20261020.md)。正式C/D未运行，节点A未通过，新模型未部署。

父数据 [stage1-cpu-v0.1.3](stage1/UNDERLYING_SUPPLEMENT.md) 保留1289条／653种原文；Full2与Full3只增加已有身份、定位及底层问法的重复次数，见 [Full2改动](stage2/variants/full2/CHANGE.md)、[Full3改动](stage2/variants/full3/CHANGE.md)。身份口径以[最新修订](stage1/IDENTITY_UPDATE.md)为准。数据和中间日志本地保存，必要执行报告另行同步。

私有远端：[yuhuan0669/t008-qwen3-sft](https://github.com/yuhuan0669/t008-qwen3-sft)。代码和材料通过Git维护；Git bundle、对象库tar及交付回执存放于同仓库的归档Release。是否完成上传与回读，以该次Release的交付回执为准。

| 内容 | 位置 |
|---|---|
| 当前接续说明 | [HANDOFF.md](HANDOFF.md) |
| 当前决定与历史决定关系 | [DECISIONS.md](control/DECISIONS.md) |
| 历史原生训练代码；当前本地数据入口见stage2/scripts | [code/](code/) |
| 9个历史阶段及相邻交付记录的原字节归档 | [archive/](archive/) |
| 全部本地文件及保存方式 | [local-files.json](registry/local-files.json) |
| 原始5个代码提交与代码文件校验值 | [code-lineage.json](registry/code-lineage.json) |
| 数据快照、候选、依赖和远端资料定位 | [versions.json](registry/versions.json)、[drive-assets.json](registry/drive-assets.json) |
| 冻结ZIP、Adapter、依赖包等对象清单 | [objects.json](registry/objects.json) |
| 核验结果 | [verification/](verification/) |
| 后续更新、恢复与备份方法 | [VERSIONING.md](docs/VERSIONING.md) |

大文件采用 SHA256 寻址，保存在本库相邻的 `t008_qwen3_assets/sha256/`，不把权重反复塞入 Git。该目录和本仓库必须共同备份。私有聊天、原始SSE等7项只登记原路径与hash，保留在原受控目录；不复制进版本库或交付包。

本库继承原5个提交的完整历史；历史代码在那些提交中位于根目录，本次统一后位于 `code/`。首次归档只整理版本，没有修改训练代码内容、语料、模型或运行服务；当前阶段一衍生数据另见上述入口。归档脚本可以核验文件；`code/` 和历史目录中的训练、发布、采集脚本不会因入库获得执行授权。

快速只读核验：

```sh
python3 tools/verify_archive.py
python3 tools/audit_frozen_packages.py
git fsck --full
```

原 `t008_qwen3_handoff_20261019/HANDOFF.md` 和其他阶段目录保持原样。今后从本库读取当前状态；原handoff属于历史快照。
