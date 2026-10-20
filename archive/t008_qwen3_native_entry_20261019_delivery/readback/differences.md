# 正式原生入口与旧版的差异（已实施）

| 项目 | 旧入口 | 当前已CPU核验入口 |
|---|---|---|
| 数据路径 | 本地DATA_DIR/train.jsonl及零超长前检 | 官方source IDs原生加载，默认2048 delete |
| 1642快照 | 预先生成后作为训练文件 | 仅保留为CPU证据，正式入口不读取它训练 |
| shuffle/曝光 | 旧prepare load_dataset默认shuffle=False | 正式SftArguments默认dataset_shuffle=True，48身份模板曝光次数互换 |
| 保存 | Full按epoch保存 | steps/50；实际Swift callback最终步补存，wrapper核终态 |
| CPU检查 | 无独立正式入口CPU分支 | cpu-check先分流，实际解析、加载和模板编码，零训练 |
| 输入漂移 | 旧本地文件hash | 实际native加载/过滤有序全列摘要与模板/代码/包版本绑定 |
| 授权 | 必须真实GPU及实验批准 | 保留训练门禁；CPU不要求生成假批准 |

核心LoRA路线、2048、官方2000/600采样参数和确认身份不变。没有额外语义清洗或优化。CPU通过不证明GPU训练或模型效果；最终运行单元、SDK/PVC和GPU窗口仍待落实。
