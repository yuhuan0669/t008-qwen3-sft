# v0.1.14 CPU编码检查

**通过；未训练、未推理、未加载模型权重。**

| 检查项 | 结果 |
| --- | --- |
| 训练记录 / 原生加载 / 编码保留 | 1325 / 1325 / 1325 |
| 父版本移除 | 第1276、1277行，共2条日期记录 |
| 剩余原字节、顺序、编码、labels及loss_scale | 1325条全部与原父行一致 |
| 训练数据与当前System含公司成立日期 | 均无 |
| 超长 / 截断 / 静默丢行 / 空监督 / 权重不符 | 均0 |
| 全量最大长度 / P99 | 2048 / 2037 |
| 剩余身份曝光与权重 | 234条，仍×3 |
| 原12条中文边界记录 | 全部保留，15个有效助手回答，权重1 |
| 训练超参数及插件源码 | 不变 |
| UAT / GPU | 未暂停、原配置不变，1/1就绪；未申请GPU |
| 临时CPU Pod | 已删除 |

采用此前固定镜像和实装版本：Swift4.4.2、Transformers5.14.1、Torch2.11.0+cu130、PEFT0.20.0。通过真实SftArguments、原生加载、SwiftSft._encode_dataset及Qwen3模板进行核验；逐条与无长度上限编码比较，无截断。按train-map显式映射回父行，避免删除后行号错位。

有效监督token：身份8937、通用1515617、定位与边界2073。删除的两条日期记录合计减少71个有效监督token。剩余样本的掩码与权重均不变；归一化仍按未加权有效token数计算。

数据SHA-256：`0f546c3aa59f8986f6e5f086482d7d40e9c29db6039a6c219ba902830abff6cb`。
新System SHA-256：`3b59da5a0293aa3d8cc677b418226ccd7e16807f3aac9bf41a53ee6273b1f511`。

[原始报告](cpu-check/report.json) · [逐行检查](cpu-check/row-checks.jsonl) · [监督探针](cpu-check/mask-probes.json) · [UAT与清理核验](cpu-check/uat-after-verification.json)。

检查时配置、清单保存在cpu-check/*.checked.json。当前配置仅补记CPU完成状态与报告位置，full_argv和Smoke参数不变。CPU结果不能证明成立日期是唯一根因或幻觉已解决。
