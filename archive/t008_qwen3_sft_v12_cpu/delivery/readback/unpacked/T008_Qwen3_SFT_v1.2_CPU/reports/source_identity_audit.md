# T-008 v1.2 来源与身份审查（CPU 准备）

审查时间：2026-10-19 UTC。执行身份：source_identity_audit 子 Agent；未独立声明法律批准权限。状态：**PENDING_IDENTITY_AND_SEMANTIC_DECISION / PENDING_SOURCE_REVIEW**。

## 结论

两官方数据仓库的当前 API 元数据和固定版本 README 均明确声明 Apache License 2.0，官方 Qwen3 教程明确以它们执行身份 SFT。因此在用户已授权范围内，可以继续下载、CPU 固定原始文件和形成明确标记待审的诊断快照。此结论不设置 sources_approved、identity_verified 或训练批准，不等于正式业务语料准入。

中文模型名、中文定制主体及 Qwen3-8B 基座有当前项目事实基线支持；英文模型名和英文主体只在拟实施方案中得到支持，未找到正式确认。官方身份模板存在把定制主体无条件写为模型创造者／研发者的语义，以及否认 Qwen 身份但不说明基础模型的回答。**训练准入暂停，保留实物，不自动清洗、改写或批准。** CPU 检查不必因此中断。

## 身份核验

| 字段 | 值 | 当前证据及状态 |
|---|---|---|
| name_zh | 章鱼能碳垂直大模型 | 项目事实基线 F1-003；负责人确认业务说明，项目事实已支持 |
| name_en | Octacarbon LLM | v1.2 拟用字段；未找到独立确认，PENDING_PROJECT_CONFIRMATION |
| author_zh | 能碳章鱼（湖北）人工智能科技有限公司 | 项目事实基线 F1-001 支持其备案主体身份；本轮未获得营业执照原件，不能将项目确认冒称法定证件核验 |
| author_en | Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd. | v1.2 拟用字段；未找到法定英文名称材料或项目明确授权译名，PENDING_ENTITY_ENGLISH_CONFIRMATION |
| base_model | Qwen/Qwen3-8B | 项目事实基线及官方模型卡支持；本轮未下载模型权重或验证实际训练权重，hash 由主 Agent 实物证据另行绑定 |

项目来源：[事实与方案基线](https://docs.google.com/document/d/1Sj3vWWxSMBM1atq9FgRyBnC89TYmDRNN6R_X6MIUFo4/edit)、[负责人确认的业务描述](https://docs.google.com/document/d/1c_V3oLZ2pf7T6Hh4gpjaF0XiaJ9bGD2hjkqN7V0mkX8/edit)。业务说明更新时间为 2026-10-19T04:10:29.620Z，基线为 2026-10-19T04:05:32.382Z。核验当前基线后不重开其已接受的 Qwen3 备案映射问题。

Drive 搜索词为“章鱼”“Octacarbon”“营业执照”“主体”，并列举指定 T-008 父目录及交付目录。搜索返回的[主体认证申请表](https://docs.google.com/document/d/1NAt-nLyFnZquakxye4ejpqrbB8w_QdSO/edit)是空白模板，不是公司证明。未读取搜索结果中的测试题或 Risk31 数据。有限搜索未发现材料不等于证明材料不存在。

最小补证：负责人提供既有中文主体证件引用，确认 name_en；对 author_en 指明“法定登记英文名称”或“本项目授权英文译名”，并确认实际拼写。无需推断中国公司必有法定英文注册名称。四字段最终核定与准入批准应由有权主体给出。

## 官方来源及不可变证据

1. [swift/Qwen3-SFT-Mixin](https://modelscope.cn/datasets/swift/Qwen3-SFT-Mixin)：官方 swift 组织发布，数据卡称用于 Qwen3 身份微调中的通用知识混合，1K 条、Qwen3-32B 蒸馏。数据卡未逐项披露蒸馏所用提示语料/上游权利链，因此不把仓库许可证夸大成每条底层素材权利完备证明。API 和 README 均声明 Apache 2.0；仓库 tree 未列独立 LICENSE/NOTICE 文件。README revision `f63337318d5fe2bca19964d26873a338d04816b1`，190 bytes，SHA-256 `5ba7ca44d005c04ad1a2fea4508d24e97fec11bb47029ad5a90127c84c1194a9`。数据文件 tree 声明 `qwen3_32b_distill_1k.jsonl` revision `e587cae71fc7084ab93dccbc37d0056df3569543`、17,438,661 bytes、SHA-256 `d261353c05df1f1fde95639d1a9d9243e1d24470dcb4c3732965ab1ab8eeba41`；本子任务没有下载整个 Mixin 数据文件，主 Agent 须核对实际 bytes/hash，不能将 API 声明冒称本子任务实物校验。

2. [swift/self-cognition](https://modelscope.cn/datasets/swift/self-cognition)：官方 swift 组织创建，可替换名称与作者模板，中文/英文。API 和 README 均声明 Apache 2.0；仓库 tree 未列独立 LICENSE/NOTICE。README revision `0398d25de0d330a065ed0f8e5d7046b9e2e21e45`，1,984 bytes，SHA-256 `6c8e590ca5e86716d17017def3dc2e2104c613415d8acba9e1af8a97850e0537`。原始数据 `self_cognition.jsonl` revision `d2a385942cb0d47e3fb3cdb9d98adb8b8c01dcfc`，实物 23,839 bytes、108 行（58 zh / 50 en），SHA-256 `e7b66784f02361cfa0ad4635dae12c0f810d197c22ac89a4b7837195dc4b7b23`，与官方 tree 一致。README 中英文叙述分别写 108/134；本结论采用实际文件 108，不套用文字计数。

文件级 Revision 是对应文件更新版本；不可冒称均为仓库统一 HEAD。每个下载请求、hash 对比记录见 `data_card_downloads.json`、`additional_downloads.json`、`official_downloads.json`。ModelScope API 在 web 阅读器失败，使用验证 TLS 的系统 `/usr/bin/curl` 取得官方原件；Python 系统 CA 初次失败记录保留，未关闭 TLS 验证。

[Apache 2.0 原文](https://www.apache.org/licenses/LICENSE-2.0)赋予复制与衍生许可，并要求在分发时附许可证、保留适用声明并标明修改；不授予商标许可，不对上游权利作保证。本轮下载和内部 CPU 处理与数据卡宣示用途相符；正式训练/发布仍应分别处理项目准入、身份真实性及实际分发义务。本报告不是法律批准。

## qwen3 子集与官方示例

`qwen3` 是 Swift 注册的预处理配置，不是仓库中的另一个 108/600 行文件。[固定 ms-swift 源码](https://github.com/modelscope/ms-swift/blob/2efb43ffe61294735be6816abca991fb2ca16011/swift/dataset/dataset/llm.py)第 885–928 行：以 tag 选择中英文替换值，替换 `{{NAME}}`/`{{AUTHOR}}`，qwen3 在 query 后加 ` /no_think`、response 前加 `<think>\n\n</think>\n\n`。源码 SHA-256 `e2d629fd2993a313330806769eccdea28dfd52258d36da34e9588fc62e0f6a7d`。这仅证明当前官方实现；主 Agent 必须绑定实际使用版本与实测 loader 输出。

[固定 Qwen3 官方教程](https://github.com/QwenLM/Qwen3/blob/7a2f61ffc7a20d47efcd2bf97f6f2bf52729042e/docs/source/training/ms_swift.md)列出 `swift/Qwen3-SFT-Mixin#2000` 和 `swift/self-cognition:qwen3#600`；其用途是演示自我认知微调。`600` 为采样曝光而非独立原题数。主 Agent 本轮真实 Swift 加载已报告 Mixin 原始 train split 为 1000 行，`#2000` 同样由官方重复采样至 2000；因此重复并不限于身份数据。主 Agent 同时发现镜像 tag 4.4.3 内实际 ms-swift 4.4.2，实际快照须绑定实测包版本，不能用 tag 或本审查的最新源码替代运行证明。该运行事实由主 Agent 的 loader 日志提供，最终证据包须交叉引用其日志与 manifest。教程原件 SHA-256 `2f5b68ed88bf943b5cac764f567ac06f5c3ebd1fc3c2a7b90e8b26e99ea68980`。

## 全部身份模板的语义审查

已阅读全部 108 原始模板。`identity_template_review.json` 保留逐行零基索引、原行规范化 hash、按拟用身份机械替换的审核预览及问题标记。此预览是审查派生物，**不是实测 Swift loader 输出或训练集**。

- 78 条 response 带作者占位符；大量“由公司研发/训练”没有区分基座和定制。不能把这 78 条都机械认定为法律虚假，但均需依产品定制语义核准。
- 12 条较强创造/训练来源表述（零基 25、28–32、80、82–86）；例如研究团队、创造者、研究人员等，容易外推为从零研发基座。
- 5 条 Qwen 身份否认（42–44、96–97）未说明“产品名称不同，但基座为 Qwen3-8B”。保留来源说明较好的 48–50、100–102 不能保证训练后不混淆。
- 50 条英文模板依赖尚未核定英文身份。本实验不是正式业务语料路线；中英数据不得并入 T-011/T-013 中文业务语料计数。

最低裁定需求：确认产品级定制方与基座研发方的回答口径，并决定逐条排除还是另行批准改写。建议口径为“本产品由能碳章鱼（湖北）人工智能科技有限公司基于 Qwen/Qwen3-8B 定制；Qwen 基座由阿里云 Qwen 团队开发”。此处仅是待决措辞，不生成新增训练样本，不直接改原数据。若只做排除，应由主 Agent 在真实 2600 行快照映射源模板与零基行号，走现有衍生快照流程；改写则是不同数据变更方案，不能声称官方原样复现。

## 证据与边界

证据统一位于 `evidence/source_identity/`，`evidence_manifest.json` 逐文件记录 bytes/SHA-256。官方下载文件为原始返回 bytes；Drive 原生文档保存的是连接器返回和派生文本，其 hash 不是 Google Docs 内部原生文件 hash。未把文档文本 hash 冒称法人原件 hash。

本轮未训练、未用 GPU、未改共享服务、未读 Risk31 测试正文、未修改既有 Drive 文档、未向外发送消息、未创建批准记录。结论交主 Agent 归档并与真实 CPU loader、长度及模板证据关联。
