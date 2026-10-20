# 公开来源及本轮变更声明

官方数据来源：swift/Qwen3-SFT-Mixin、swift/self-cognition（ModelScope）。实际数据卡和 API 宣示 Apache License 2.0，许可全文在 LICENSES/Apache-2.0.txt；原始声明、固定版本及校验值在 evidence/source_identity/ 与 work/upstream-raw/。

保留下载原件。训练快照由实际 ms-swift 4.4.2 原生预处理、身份替换和 #N 采样产生；v1.2 规范化只移除非训练 dataset 来源元数据，原生输出另存。长度候选只按独立清单删除超长曝光，没有修改其余消息字节或顺序。脚本兼容性修复另有 Git diff 和测试。

模型权重未随包分发；仅提供实际文件 hash、来源对比及必要元数据。项目定制主体不作为 Qwen3-8B 基座原始研发方。名称使用确认不等于训练数据、GPU 窗口、模型发布或正式备案批准。上游未提供的逐项权利链不在本包伪造。
