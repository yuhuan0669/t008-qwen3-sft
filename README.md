# T-008 · Qwen3-8B 基础 SFT 统一版本库

这是 Qwen3-8B 自我认知＋通用指令 SFT 的统一维护入口。任务版本为 **T-008 v1.5 第15节**；历史流程方案为 **v1.2 / process-restore-R1**；本库首次归档版本为 **archive-v1.0.0**。三者分别表示任务、流程、归档版本，均不代表模型已验收。

从 [HANDOFF.md](HANDOFF.md) 开始，再读 [当前状态](control/CURRENT_STATE.json) 与 [版本登记表](registry/versions.json)。

最新执行为 **v0.1.9：3步Smoke及一次80步／1epoch Full完成，UAT已恢复原配置**。[执行报告](stage2/runs/t008-v019-20261020-211142/REPORT.md) · [40次逐题正文](stage2/runs/t008-v019-20261020-211142/development/ANSWERS.md)。无System的中文Thinking身份完整正确从冻结对照的3/6升为4/6，仍有附加错误；40次无空正文或长度截断。严格JSON格式有退步，不认定正式验收通过，未部署新模型、未追加训练。

训练使用 [v0.1.9数据](stage1/variants/stage1-cpu-v0.1.9/README.md)：只改5条中文记录，1275条总量、216次身份曝光及训练参数不变；[CPU检查](stage1/variants/stage1-cpu-v0.1.9/CPU_CHECK.md)与数据目录保持开训前快照，当前执行状态以本轮报告为准。英文身份延后。[5条样本前后对照](stage2/variants/chinese-minimal-review-v0.1/SAMPLE_DIFF.md)保留。

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
