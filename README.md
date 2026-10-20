# T-008 · Qwen3-8B 基础 SFT 统一版本库

这是 Qwen3-8B 自我认知＋通用指令 SFT 的统一维护入口。任务版本为 **T-008 v1.5 第15节**；历史流程方案为 **v1.2 / process-restore-R1**；本库首次归档版本为 **archive-v1.0.0**。三者分别表示任务、流程、归档版本，均不代表模型已验收。

从 [HANDOFF.md](HANDOFF.md) 开始，再读 [当前状态](control/CURRENT_STATE.json) 与 [版本登记表](registry/versions.json)。

当前本地身份修订为stage1-cpu-v0.1.2，未上传；详见[身份口径](stage1/IDENTITY_UPDATE.md)。

当前进展：[第一阶段CPU准备与数据审阅](stage1/README.md)已形成候选。基于[review-v0.4.1](docs/plans/SFT_MINIMAL_INTEGRATION_v0.4.1.md)，原方案正文保持不变。数据改动可在[完整对照页](stage1/review/index.html)查看；1276次曝光、647种最终记录。尚未启动GPU训练或模型推理。云端交付见[阶段登记](registry/stage1.json)。

私有远端：[yuhuan0669/t008-qwen3-sft](https://github.com/yuhuan0669/t008-qwen3-sft)。代码和材料通过Git维护；Git bundle、对象库tar及交付回执存放于同仓库的归档Release。是否完成上传与回读，以该次Release的交付回执为准。

| 内容 | 位置 |
|---|---|
| 当前接续说明 | [HANDOFF.md](HANDOFF.md) |
| 当前决定与历史决定关系 | [DECISIONS.md](control/DECISIONS.md) |
| 保留必要修复的原生训练代码，尚未适配R1快照入口 | [code/](code/) |
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
