# T-008 人工微调交接包 v1.0

**从[人工操作手册](MANUAL.md)开始，再看[各轮实验总表](EXPERIMENTS.md)。** 本包由本地已保存证据整理，未启动训练、推理或集群操作，未暂停UAT。最新训练仍为v0.1.14，服务恢复信息是该轮历史核验，不是本次实时查询。

| 要做什么 | 材料 |
| --- | --- |
| 看操作步骤、复制命令 | [MANUAL.md](MANUAL.md) |
| 看每轮改动、参数、结论 | [EXPERIMENTS.md](EXPERIMENTS.md)；[JSON](history/experiments.json)；[CSV](history/experiments.csv) |
| 使用1325条冻结数据 | [train.jsonl](data/v0.1.14/train.jsonl)；[统计](data/v0.1.14/STATISTICS.md)；[CPU结果](data/v0.1.14/cpu-check/report.json) |
| 看完整训练命令 | [实际配置](config/actual-v0.1.14-training.json)；[实际运行argv](config/actual-v0.1.14-command.json)；[手工启动器](tools/train.py)默认只打印 |
| 身份损失及数据守卫 | [identity_loss3.py](plugins/identity_loss3.py)＋[identity-keys.json](plugins/identity-keys.json)；[local_data_guard.py](plugins/local_data_guard.py) |
| 固定System、模板、题目、Schema | [System r1](evaluation/materials/custom-system.txt)；[模板](evaluation/materials/thinking-prefill.jinja)；[题目](evaluation/materials/scenarios.jsonl)；[Schema](evaluation/materials/json-schema-cases.jsonl) |
| 参考早期开发与公共基准 | [原24题、公共40题、许可证和EvalScope参考](evaluation/historical-development/README.md) |
| 查看最新问题问答 | [具体问题](evidence/t008-v0114-20261021-145454/evaluation/ISSUES.md)；[全部120次回答](evidence/t008-v0114-20261021-145454/evaluation/ANSWERS.md) |
| 定位环境与模型 | [环境及依赖](runtime/ENVIRONMENT.md)；[模型清单](models/LOCATORS.json) |
| 校验包内文件 | `python3 tools/verify_package.py`；[逐文件清单](MANIFEST.json)；[复制来源](SOURCE_MAP.json) |

本包包含v0.1.13/v0.1.14的Adapter ZIP，未包含约16GB基座权重、容器镜像层和凭据。Python叠加依赖仍复用现有PVC路径，详见环境说明；本包不是完全离线运行镜像。复制到另一台机器后，先校验文件，再准备基座与运行环境。

历史原文放在`data/`、`history/`、`evidence/`中，保留原字节及原仓库相对链接，用于追溯，不作为可直接重跑的脚本入口。历史文档里未收进包的旧路径，可通过SOURCE_MAP回到源仓库查询；上表、手册和总表链接均指向包内文件。不要执行旧目录里的execute.py、window.py或run_cpu.py。

包版本：`manual-sft-v1.0`，对应本地Git标签`handoff-manual-sft-v1.0`。历史来源提交见PACKAGE.json。新实验在新的输出目录保存，不覆盖本包；按最终实际参数另行登记数据、epoch、命令和结果。
