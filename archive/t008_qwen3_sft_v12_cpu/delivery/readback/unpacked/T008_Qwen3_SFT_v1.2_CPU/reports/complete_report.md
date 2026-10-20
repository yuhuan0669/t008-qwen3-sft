# T-008｜Qwen3-8B 身份 SFT v1.2 CPU 执行回报

报告日期：2026-10-18（America/Los_Angeles）；机器证据以各文件 UTC 时间为准。

**建议：GPU No-Go。CPU 数据、来源、真实模板和兼容性检查已完成；数据准入与下一阶段授权未闭环。未运行 GPU Smoke、Full、A/B/C/D 推理，未停止 vLLM，未发布模型。**

## 完成结果

1. 从指定 Drive 下载唯一 v1.2 方案和附件，ZIP CRC 正常，附件清单 12/12 文件的大小与 SHA-256 匹配。独立方案与 ZIP 内方案字节一致。原版只读保留，修复代码另存，不用历史版本覆盖。
2. 在真实 k8s-worker05 上以现有固定镜像运行隔离 CPU 容器：runc、2 CPU、8 GiB、UID 10001、无 GPU 设备、CUDA 不可用；真实基础模型只读挂载。未修改 K8s 对象、服务配置、权限或业务数据。临时节点工作区供本轮计算，归档包上传 Drive；尚未将候选部署为受控 GPU Job 的正式输入。
3. 实际 ms-swift 原生加载、身份替换及 #N 采样输出 2600 行；来源原件、loader 原始输出、规范化训练快照和采样映射均保留。源文件实物 hash 与官方文件级 Revision 元数据匹配。
4. 对全部 108 个不同身份模板及其 600 次曝光完成映射和问题登记；对全部 2600 行执行真实 Qwen3 Tokenizer 无截断检查、真实 Swift 训练模板及 loss mask 检查。
5. 原始 958 个超长曝光未改写。使用 v1.2 排除式工具另生成 1642 行长度候选，逐条保留原始行字节和顺序；原始行号、理由、数量、父快照与 SHA 均已绑定。
6. 修复实际兼容性问题及继承的布尔门禁问题；本机和实际容器均 23/23 测试通过。增量审查未发现本次范围内剩余实质代码阻断，但不构成独立最终验收。
7. 读取实际 GPU、vLLM、Swift、ClearML、PVC、代码版本与镜像 digest；验证 ClearML SDK HTTPS 读取既有合成 Task/Model 及下载字节哈希。未创建本轮训练 Task 或 Model。

## 数据事实与快照

| 对象 | 原始不同记录 | 训练曝光 | 重复情况 |
|---|---:|---:|---|
| Qwen3-SFT-Mixin | 1000 | 2000 | 每条 2 次 |
| self-cognition:qwen3 | 108，58 中文/50 英文 | 600 | 60 条各 6 次，48 条各 5 次 |
| 原始合并 | 1108 | 2600 | 1492 次重复曝光 |
| 长度候选 | 629 | 1642 | 521 条 Mixin 各 2 次，身份曝光不变 |

`600` 不表示 600 个原创身份问题；`2000` 同样不表示 2000 条不同通用记录。

- 原始：`work/original-v1.2/train.jsonl`，SHA-256 `dda551041a12c460b84056f2c58df0ab60f2e9999e0518f116cf5f5b3c5faf6e`。
- 长度候选：`work/length-candidate-v1.2/train.jsonl`，SHA-256 `ad06235bcf0df01f7de4fbfb4f2fe3b156429444478bb1ef0a22cc7ab322b111`。
- 排除清单：`work/length-candidate-v1.2/exclusions.json`，958 行，SHA-256 `62b0786206d25262c51a637a4ec02cd2a811b9eb13ecc6396b8d5079ff414f84`。
- 原始 Manifest SHA-256 `68e4c5d5eecaba984bb6740eb919c5103e5b6aca104c311c846cfd01cabf1ce4`；候选及全部其他文件哈希见最终交付 Manifest。
- 上游 Mixin 原件 17,438,661 bytes，SHA-256 `d261353c05df1f1fde95639d1a9d9243e1d24470dcb4c3732965ab1ab8eeba41`；身份原件 23,839 bytes，SHA-256 `e7b66784f02361cfa0ad4635dae12c0f810d197c22ac89a4b7837195dc4b7b23`。实际原件在 `work/upstream-raw/`。

`raw-loader.jsonl` 保留原生 `dataset` 来源列；v1.2 的 `normal_row` 仅移除该非训练元数据，全部 role/content 字节内容一致。先前误报时捕获的诊断快照与修复后原始 train.jsonl 完全相同，未替换、改写或重采样。对应对账在 `evidence/data_quality_summary.json`。

原始身份占比 23.08%；排除后为 36.54%。958 条全部来自 Mixin，相当于排除原始曝光的 36.85%。**这是待批准的配比变化，不能把长度候选称为原方案已批准数据。** 未擅自增加 max_length、补采或改变 LoRA 路线。v1.2 衍生工具内部 schema 名称含 approved，但实际 `status=PENDING_DERIVATIVE_APPROVAL`，没有批准效力。

## 来源及身份准入

两官方来源当前 API 与固定 README 均声明 Apache 2.0，官方 Qwen3 教程也使用这两个来源。许可原文、来源说明、文件级版本和实物 hash 随包保留。本轮已授权内部 CPU 固定、诊断用途有公开来源依据；上游蒸馏语料逐项权利链未披露，不把仓库许可外推成正式业务准入或备案批准。未将其计入 T-011/T-013 的已批准业务数据。

中文名称“章鱼能碳垂直大模型”、中文主体“能碳章鱼（湖北）人工智能科技有限公司”和 Qwen3-8B 基座有当前项目确认材料支持。本轮负责人又在本聊天明确回复“我确认是官方名字，可用于开发及商业用途”，据此确认英文模型名 Octacarbon LLM 和英文公司名 Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd. 的本次使用口径。确认原话与范围保存在 `evidence/identity_confirmation_overlay.json`。早期来源审查的英文 pending 保留为历史发现，以此后置确认解释；不改训练快照字节，也不把项目确认冒称独立政府证照检验。

全部 108 模板中，78 条涉及未区分定制/基座的研发或训练表述，12 条含较强创造者/研究团队表述，5 条否认 Qwen 身份但未解释基座。问题重叠；映射到实际曝光分别为 434、66、28 行。英文名称确认后，当前并集为 78 个不同模板、434 次曝光仍有语义待裁定标记，**并不等于这些记录均已判为违法或虚假**。逐模板初审和当前逐曝光行号见 `identity_template_review.json`、后置确认及 `identity_exposure_anomalies.json`。

本轮未自动改写或删除这些身份记录；长度候选保留全部 600 次身份曝光，因此仍不能进入训练。待裁定的产品口径建议是“本产品由定制主体基于 Qwen/Qwen3-8B 定制；Qwen 基座由阿里云 Qwen 团队研发”。如需改写正文，应另形成数据变更决定；不能声称仍是官方原样快照。

## Tokenizer、Swift 与 loss mask

| 快照 | HF 无截断最大长度 | HF 超长 | Swift 最大长度 | Swift 超长 | 实际 Swift 保留 |
|---|---:|---:|---:|---:|---:|
| 原始 2600 | 2515 | 958 | 2511 | 958 | 1642 |
| 长度候选 1642 | 2048 | 0 | 2048 | 0 | 1642 |

两实现的超长行号集合一致。Swift 采用实际 `SwiftSft._encode_dataset → AddLengthPreprocessor → template.encode`，不是手写模板替代。全部行有 prompt mask、监督 token 非零，监督位置 labels 与 input_ids 一致；合成角色哨兵另核 system/user 被 mask、assistant 正文被监督。

真实 SftArguments 默认把 loss_scale 扩展为 `default+ignore_empty_think`；空 think 前缀被 mask。这是当前固定版本的默认行为，本轮未人为叠加另一训练示例。原始预检 `ms_swift_template_verified=false`；长度候选为 true 只证明编码和保留数量，不能替代身份、来源、数据变更或 GPU 批准。

## 环境、兼容性及修复

实际版本：ms-swift 4.4.2、Transformers 5.14.1、PEFT 0.20.0、PyTorch 2.11.0+cu130、tokenizers 0.22.2、datasets 4.8.4、ModelScope 1.38.1。镜像 Tag 写 4.4.3/1.39.0，与实装不一致，采用实读版本与 digest。

实际基镜像：`modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope@sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738`。

修复代码 Git Commit：`55042a0c2eb3da96f38b019650838bfdf6b4a03b`。这是本轮从精确 Drive v1.2 建立的独立准备代码仓库，保留原版 commit、修复 diff 与 Git bundle；不是冒充既有基础设施仓库 commit。基础设施仓库实际 HEAD 另在 `live_environment_before.json` 记录，本轮未改其文件。

修复与运行配置：

1. 原占位符正则误拒 Mixin 六个合法 Jinja 曝光。现保留合法代码，仍检查全局大写占位符，以及身份段 NAME/AUTHOR/AUTHOER 的大小写变体；保留原失败和未改写输出。
2. `swift sft --help` 只显示外层 argparse；改为必要时读取实际 `sft_main(['--help'])`，无真实参数则继续拒绝。Full/Smoke 参数经真实 parser 和安全 CPU 初始化核验。
3. 本地基座目录自动模型类型有歧义；显式 `--model_type qwen3 --template qwen3`，不改变模型或训练路线。
4. Transformers 5 的 BatchEncoding 是 Mapping，不是 dict；修复错误的 2-token 计数。错误报告标为 INVALID 随包保留，未作为通过证据。
5. 所有批准及模板验证布尔字段只接受 literal JSON true，字符串 "false"、"true"、数字 1 等均拒绝；不生成任何真实 approval.json。
6. UID10001 在镜像没有 passwd 项，PyTorch getpass 失败；本轮 CPU exec 明确 USER 并设置可写 TORCHINDUCTOR_CACHE_DIR。ModelScope 缺预生成 AST，已仅在隔离容器生成索引，未改现有服务或放宽共享目录权限。
7. 基镜像缺 ClearML SDK；在独立 `/work/deps` 安装 clearml 1.17.0 及三个缺失依赖，原包不升级。完整包版本、overlay 文件 hash 和生成 AST hash 在 runtime-bom.json。
8. 实读 ClearML 1.17.0 源码发现无 output_uri 时可能仅登记本地文件，不能算远端存储回读。入口现强制显式 HTTPS CLEARML_FILES_HOST，Task 设置 output_uri，模型同步上传，登记 URL 必须位于同一远端存储路径，并 force_download 强制重新下载。该修复有针对性回归；本轮未执行新模型上传。

本轮实测是**固定基镜像＋明确记录的 CPU runtime overlay**。没有构建或发布一个声称包含上述 overlay 的新训练镜像；未来 GPU 作业必须固定同样的代码、依赖及运行参数，或先形成独立派生镜像并登记新 digest。不能只凭基镜像 digest 冒称最终 GPU Job 部署已经核验。

Full `eval_strategy=no,save_strategy=epoch`；Smoke `save_strategy=steps,save_steps=3,max_steps=3`；data_seed42、LoRA rank8/alpha32/all-linear、BF16、1 epoch、lr1e-4、batch1/accum16、2048 等均可解析。CPU 初始化仅为避免 GPU 和外部跟踪写入覆盖 `use_cpu=true,report_to=none,add_version=false`；未验证 GPU kernel、TensorBoard callback 或实际模型前向。

## 基座、服务与 ClearML

基础模型实物 16 文件、16,397,461,896 bytes，完整清单规范化聚合 SHA-256 `39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374`。全部文件大小/hash 与 ModelScope 固定 revision `26028140be3ee69b82b1d1450179ab71bb1121b9` 一致；五个权重分片也与官方 HF 固定 revision `b968826d9c46dd6066d109eabc6255188de91218` 一致。历史下载 revision 仍 UNKNOWN，此为内容身份核验。

当前 context 为 lmas00-direct，API 为 https://10.140.17.124:6443，与现场 lmas00 集群节点对应；未改变全局 context。现有单 RTX4090 24,564 MiB，vLLM 检查时约占 22,176 MiB；Swift 为 0，vLLM 1/1、health=200。没有空闲受控 GPU 窗口可直接并行训练。Deployment/Pod、镜像、replica、args、路由、PVC、revision 和前后读回随包保存；恢复沿用已接受的 T-008 机制。本轮没有发生切换，未冒称重新演练恢复或真实生成验证。终态前后 Deployment spec 完全相同，vLLM 仍 1/1、HTTPS health=200；本轮两个隔离 CPU 检查容器均已清理。

ClearML 5 Deployment＋2 StatefulSet 就绪，4 PVC Bound。系统信任下 API/Files HTTPS 入口可读。使用 swift-clearml 既有客户端凭据经 stdin 注入隔离进程，不回显、不入包。SDK 只读原先的合成 Task `d715e54b152b4aa18d38ec0259a54082` 和 Model `891292342c244f1995671bb5da68c83e`；旧模型 URI 为内部 HTTP 服务名，通过已核验 HTTPS Ingress 路径映射下载，33 bytes、SHA-256 `005cc7d6c45910da0030fb43a831fa33eaacd0744f5ce61cafd9bab7a28f29ac` 与历史合成参考一致，未改服务端记录。此结果只证明当前认证、SDK 读取及既有存储下载条件，不是本轮真实模型或新 OutputModel 上传闭环。实际代码使用 `clearml.Model.get_local_copy`，该方法在 1.17.0 存在。

## GPU 门禁与后续窗口估算

机械数据/模板项已核验，**准入及启动仍 No-Go**。缺少或待决：

- 定制方与基座研发方的最终回答口径；身份问题处理后的最终数据版本。英文官方名称及开发/商业名称用途已由负责人确认，不再列为等待项。
- 是否接受 958 条排除及混合比例变化；实际数据、Manifest、预检及基座 hash 的有权批准记录。没有从旧 Risk31 批准或示例 approval 继承授权。
- 最终 GPU Job 对代码/依赖 overlay 或派生镜像、受控数据 PVC 的部署绑定；独立测试题及评分规范冻结。
- 本次共享 vLLM 停启影响窗口、Smoke/Full 授权；A/B/C/D 与 Thinking 评测另需明确 GPU 窗口。

估算仅作排期，不是本机吞吐实测：Smoke 预留 20–30 分钟（含加载/3步/记录），Full 预留 45–90 分钟，恢复检查 15–30 分钟，整体首轮训练切换可先按 90–150 分钟规划，再由获批 Smoke 实测更新。长度候选 1642 行、batch1/accum16 时约 103 个 optimizer steps；原始 2600 为约163，但原始不能按当前2048门禁运行。官方约22GB/30分钟不是本环境保证，24GB BF16 LoRA仍须Smoke检验峰值和OOM。

若采用方案建议的身份80＋通用100题，四组为720次生成；以512输出token预算、假设10–40 token/s，纯解码预算约2.56–10.24小时，另加prefill、四组加载和存储。Thinking 若每组T题、每题2048输出预算，再加 `8192*T/吞吐` 秒。吞吐只是敏感性假设；实际题数、输出长度和效率未固定，因此当前不能批准一个“30分钟内含完整评测”的窗口。A/B/C/D 使用同一 transformers+PEFT 引擎，不能用 vLLM 在线吞吐替代。

## 交付及停止点

完整证据包包含本报告、来源/身份报告、基座来源报告、模板/CLI报告、增量审查、原始及候选快照、上游原件、排除/异常映射、基座清单、日志、脚本、Git bundle 和逐文件 Manifest。完整 Drive 链接及上传回读的 ID/name/parent/bytes/SHA-256 见独立交付回执；不在 ZIP 内虚构对自身的回读证明。

本轮停止在 GPU 训练门禁之前。下一阶段必须依据实际最终数据和有效批准重新核对可变现场状态；本报告不宣布正式训练、模型验收、发布或 T-008 整体关闭。


---

# 附录说明

以下保留分项审查。英文身份审查先于负责人确认；当前英文名称已确认，历史pending由 identity_confirmation_overlay.json 与本报告正文更新。语义和GPU门禁仍No-Go。


---

# 英文身份确认后置记录

负责人在本聊天针对英文模型名和英文公司名核验问题明确答复：“我确认是官方名字，可用于开发及商业用途”。

据此，本轮采用 `Octacarbon LLM` 与 `Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.`，英文名称使用的 pending 关闭。中文名称、中文主体与基础模型沿用本轮已核验项目材料和实际文件。无须改变已生成身份规格或快照字节。

原始来源审查、模板初审与增量审查写作时的英文 pending 保留历史；当前状态以 `evidence/identity_confirmation_overlay.json` 及本执行回报为准。此确认未扩大为 GPU、训练数据变更、研发归属语义或发布授权。

消除仅因英文待确认产生的标记后，当前语义待裁定并集为 78 个不同模板、434 次曝光；含较强创造/研究来源表述的66次和Qwen身份否认的28次均包含于该并集，不相加当成不同记录。没有因本次确认自动接受这些训练表述。


---

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


---

# T-008 Qwen3-8B 实际基座与官方版本内容核验

核验时间：2026-10-19T05:56:24Z。只读 CPU 工作；未下载权重、未训练、未用 GPU、未改服务。状态：**CONTENT_IDENTITY_MATCH；历史下载 revision 仍 UNKNOWN**。

实际只读 `/base` 的 16 个文件、16,397,461,896 bytes，其 size/SHA-256 全部与官方 ModelScope `Qwen/Qwen3-8B` 固定 revision `26028140be3ee69b82b1d1450179ab71bb1121b9` 的完整 tree 元数据一致。五个权重分片同时与官方 Hugging Face revision `b968826d9c46dd6066d109eabc6255188de91218` 的 LFS size/SHA-256 一致。

这证明本轮实际基座具有上述官方版本的文件内容身份；不证明当年从哪一个站点、哪个分支或哪个 commit 下载。没有用当前 HEAD 替代未知的历史下载 revision。

## 实际输入与不可变上游

- 实际清单由独立 CPU 模板审查 Agent 从隔离容器只读 `/base` 完整逐文件计算，本审查消费已保存的 `evidence/template/original-exact/base-files.json`；实际项数为 **16**（不是即时协调消息的 15）。
- 清单原始文件 SHA-256：`a1b77d34bda8a913bc050ba2b8b343b6104f77fa701c8b5275a0b438baedfd56`。
- 清单按项目 `json.dumps(list, sort_keys=True, ensure_ascii=False)` 聚合 SHA-256：`39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374`。两者序列化字节不同，不能互换。
- [ModelScope 固定版完整文件元数据](https://modelscope.cn/api/v1/models/Qwen/Qwen3-8B/repo/files?Revision=26028140be3ee69b82b1d1450179ab71bb1121b9&Recursive=true)：16 项，全部匹配；文件自己的 last-changed revision 另存，不误称所有文件都在 LICENSE commit 修改。
- [Hugging Face 固定版 API 元数据](https://huggingface.co/api/models/Qwen/Qwen3-8B/revision/b968826d9c46dd6066d109eabc6255188de91218?blobs=true)：15 项。LFS 文件直接比对官方 SHA-256；非 LFS 小文件按固定 revision 下载并计算 SHA-256，不将 Git blob SHA-1 当成文件 SHA-256。
- 先读取 main/master 只是发现候选固定版本，随后已按不可变 revision 再次取得元数据并完成匹配。

## 权重匹配

| 文件 | bytes | SHA-256（本地、MS、HF 相同） |
|---|---:|---|
| model-00001-of-00005.safetensors | 3,996,250,744 | `31d6a825ae35f11fb85b195b4c42c146c051e446433125a215336abdf95cbf5f` |
| model-00002-of-00005.safetensors | 3,993,160,032 | `5991236cea6fe21f3d43cab0f0e84448734fbbe0789816202989f2ddc9d18282` |
| model-00003-of-00005.safetensors | 3,959,604,768 | `c5185c4794be2d8a9784d5753c9922db38df478ce11f9ed0b415b7304d896836` |
| model-00004-of-00005.safetensors | 3,187,841,392 | `b5ee7de71fbf17db3d5704e0c8f2bc7d005ca9e1d7ca2aeb19827b0cfcaa917a` |
| model-00005-of-00005.safetensors | 1,244,659,840 | `20c2d6366ab85c90786ccdd829cd2b9e7d30ef3b2ebbb998280e7e4014b542ff` |

权重合计 16,381,516,776 bytes。ModelScope 所列五分片最后修改 revision 为 `7c9709d23bd2136dac1d6ea1fe30f4107d681cd6`。本审查只下载 API 元数据和非权重小文件，没有下载上述五分片。

## 配置、Tokenizer 与平台差异

实际 `config.json`、`generation_config.json`、`merges.txt`、`model.safetensors.index.json`、`tokenizer.json`、`tokenizer_config.json`、`vocab.json`、`README.md`、`LICENSE` 均与两个官方固定版本相同。Tokenizer JSON 通过官方 LFS SHA-256 比对，未重复下载。实际 `tokenizer_config.json` SHA-256 为 `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101`，可绑定本轮模板核验。

HF 与本地有两项平台附属差异：

1. `.gitattributes`：本地/ModelScope 为 2,127 bytes、SHA-256 `088e25d6bceaa8943f4f292006210358292349cc36e7578f80c62fce75535f46`；HF 为 1,570 bytes，内容不同。
2. `configuration.json`：ModelScope 与本地有 73 bytes 的同一文件，HF 仓库没有此文件。

因此结果准确表述为“MS 16/16；HF 14 个同名内容匹配、1 个附属文件不同、1 个仅 MS 存在”，不是全部文件与 HF 仓库完全相同。实际 LICENSE 已匹配官方 Apache 2.0 文本，SHA-256 `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e`。

## 证据位置与范围

全部上游 API 原件、固定版小文件及请求/时间/hash 在 `evidence/source_identity/base_upstream/`；完整逐项比较为 `base_content_comparison.json`，原件清单为 `evidence_manifest.json`。本次新增报告不改先前来源身份报告。

本结论只闭合本轮实际基础文件的内容身份，不新增训练或来源批准，也不改变英文身份、定制/基座研发语义待裁定状态。主 Agent 已报告原始训练快照 958 行超长及待批长度衍生候选；这些数据门禁与本基座内容匹配分别记录，不能因匹配成功放行训练。


---

# T-008 v1.2 CPU：实际 Tokenizer、ms-swift 模板与 CLI 核验

结论：原始 2600 次曝光中 958 行超过 2048-token 训练上限，实际 ms-swift 默认预处理仅保留 1642 行。独立长度衍生候选的 1642 行通过真实 HF Tokenizer 与实际 ms-swift 模板/标签/保留数量机械核验。该通过只涉及 CPU 编码，不构成来源、身份措辞、数据变更、GPU 窗口、训练或模型验收批准。

## 实测环境与边界

- 主机：`k8s-worker05`；既有隔离容器：`t008-identity-v12-cpu`。
- `/base` 为只读真实基座；未加载 8B 权重、未创建 Trainer、未启动训练。所有探针断言 `torch.cuda.is_available()==False`。
- ms-swift `4.4.2`、Transformers `5.14.1`、PEFT `0.20.0`、PyTorch `2.11.0+cu130`、tokenizers `0.22.2`、datasets `4.8.4`。
- 真实 config：`Qwen3ForCausalLM`、`model_type=qwen3`、36 层、hidden 4096、vocab 151936、BF16。processor 实际类名为 `Qwen2Tokenizer`，由实际 qwen3 模型注册加载，类名本身不是模型身份不一致证据。
- 16 个基础文件逐字节 SHA-256 清单：`evidence/template/original-exact/base-files.json`；合计 16,397,461,896 字节。完整清单按 v1.2 `base_fingerprint` 原有 JSON 序列化方法聚合 SHA-256：`39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374`。
- 首轮完整读取基座文件计算哈希；后续在同一只读 `/base` 挂载复用该清单并复查文件/大小，报告中显式保留复用路径与依据，未把复用描述为再次逐字节计算。

## 数据与真实保留数量

| 快照 | 行数 | HF 超长 | HF min/max/mean | Swift 超长 | Swift 实际保留 |
|---|---:|---:|---|---:|---:|
| original-v1.2 | 2600 | 958 | 30 / 2515 / 1399.25 | 958 | 1642 |
| length-candidate-v1.2 | 1642 | 0 | 30 / 2048 / 979.20 | 0 | 1642 |

- 原始 `train.jsonl` SHA-256：`dda551041a12c460b84056f2c58df0ab60f2e9999e0518f116cf5f5b3c5faf6e`。
- 长度候选 `train.jsonl` SHA-256：`ad06235bcf0df01f7de4fbfb4f2fe3b156429444478bb1ef0a22cc7ab322b111`。
- 原始 Swift token 总数 3,635,635、监督 token 3,515,952；候选总数 1,607,849、监督 token 1,553,336。
- 原始 Swift 长度 min/p50/p90/p95/p99/max：30/1689/2133/2158/2217/2511；候选为 30/1250/1894/1954/2030/2048。
- HF 与 Swift 使用各自真实模板实现，个别长度不同；两者都独立执行，未把 HF 计数替代 Swift 训练路径证据。
- 原始 958 行排除占 36.8462%。该比例会改变通用/身份混合权重，候选不继承原始数据的训练批准。原始与候选的删除映射由主任务独立衍生清单提供。

## 实际模板和 loss mask

真实调用链为：`swift.model.get_processor('/base', model_type='qwen3', download_model=False)` → `SftArguments.get_template_kwargs()` → `swift.template.get_template(...)` → `template.set_mode('train')` → `AddLengthPreprocessor(template)`。保存的 `SwiftSft._encode_dataset` 源码确认该类正是普通非 streaming、非 lazy SFT 的实际数据预处理类；不是自行模拟的截断器。

`get_processor` 内部显式 `load_model=False`。`SftArguments` 的 CPU 元数据初始化不创建模型/Trainer。实际默认训练配置为 `template=qwen3`、`template_backend=swift`、`use_chat_template=true`、`loss_scale=default+ignore_empty_think`、`truncation_strategy=delete`、`strict=false`。训练参数中的 `delete` 在模板层映射为 `raise`，由数据预处理器捕获超长并删除整行，绝非静默切断正文。

无截断逐行预检将 `template.max_length=None` 明确解除上限。仅向 `get_template` 传入 `max_length=None` 会自动回退模型最大长度 40960，故探针显式清除该属性。每行保存零基行号、token 数、masked/supervised 数、input_ids/labels SHA-256，不输出源对话正文。

所有原始/候选行均存在 prompt mask、监督 token 大于零，所有监督位置满足 `labels==input_ids`。另用独立合成 system/user/assistant 哨兵验证角色语义：57 tokens 中 41 个 mask、16 个监督；system 正文 `[3,15)`、user 正文 `[20,32)` 全为 `-100`，assistant 正文 `[41,55)` 监督，结尾 `im_end` 和换行监督。自动插入的 `<think>\n\n</think>\n\n` 空思考前缀在默认 `ignore_empty_think` 下 mask。该测试使用合成内容，未向日志泄露数据正文。

候选 `AddLengthPreprocessor` 输出的逐行 token 哈希多重集与显式无截断检查的合法行多重集完全相同。候选 `swift-template-evidence.json` 的 `verified=true` 只表示上述实测成立；原始因为 958 超长而为 `false`。

## CLI 兼容性发现与修复依据

1. 当前镜像的 `swift sft --help` 只展示外层 `tuner_backend`，不能证明内层参数缺失。安全执行 `from swift.pipelines import sft_main; sft_main(['--help'])` 可得到真正训练参数帮助，并在帮助退出前停止。主任务已据此添加 CLI 帮助 fallback，训练批准门禁不变。
2. 对通用本地路径 `/base`，`SftArguments` 不能在 `qwen3` / `qwen3_emb` / `qwen3_reranker` 中自动选型。显式 `--model_type qwen3 --template qwen3` 后 CPU 初始化成功。
3. Transformers 5.14.1 的 `apply_chat_template` 返回 `BatchEncoding`，它是 `Mapping` 而不是 `dict`。原 v1.2 仅检查 `dict`，错误地把字典键数 2 当作 token 数。首个失败报告 `evidence/template/baseline_mapping_bug_report.INVALID.json` 仅作故障证据，不可用作预检通过证据。主任务将检查改为 `collections.abc.Mapping` 后重跑，得到上表真实值。
4. 真实 HF parser 对 Full 与 Smoke 原有训练参数均无未知项。加入显式 qwen3 选型后，真实 `SftArguments.__post_init__` 和 `training_args` CPU 初始化成功：`eval_strategy=NO`；Full `save_strategy=EPOCH`；Smoke `save_strategy=STEPS,max_steps=3,save_steps=3`；data seed 42；LoRA rank 8 / alpha 32 / target `all-linear`；BF16；max_length 2048；split ratio 0；gradient checkpointing 开启。
5. CPU 初始化仅覆盖 `use_cpu=true, report_to=none, add_version=false`，避免 GPU、跟踪写入与版本输出副作用。`report_to=tensorboard` 原参数已完成 parser 验证，未执行实际 callback、ClearML Task、GPU kernel 或训练前向。

`torch_dtype`、`warmup_ratio` 的弃用提示在当前镜像仍可解析；导入时缺少可选 `kernels` 的 CPU 4-bit GEMM 提示没有影响本轮普通 LoRA 编码。未启用 QLoRA，也未由此证明未来 QLoRA 兼容。

## 证据与复算

- `scripts/template_probe.py`：实际模板、mask、逐行 hash 与保留数量核验；final 原始和候选 `summary.json` 记录执行脚本 SHA-256。
- `scripts/cli_probe.py`：实际 parser 与安全 CPU dataclass 初始化；`evidence/template/cli/cli_parse.json` 保存失败与最小修复后的结果。
- `scripts/tokenizer_probe.py`：执行 v1.2 `preflight_data.scan`，仅显式复用先前逐字节实测的只读基座 fingerprint，不修改基线源码或源数据。
- `evidence/template/original-final/`：原始真实 Swift summary、2600 行 mask/token 审计、958 行 exceptions、HF `preflight_report.json`（`ms_swift_template_verified=false`）。
- `evidence/template/length-candidate-final/`：候选真实 Swift/HF 结果、1642 行审计、空 exceptions、绑定真实模板证据的 `preflight_report.json`（`ms_swift_template_verified=true`）。
- 各目录保存 API 源码片段、实际安装文件 SHA-256、合成 role mask 测试；原始及候选运行日志位于 `evidence/template/*.log`。
- 探针脚本均通过 Python 语法编译；真正可信的行为证据是本轮实际 CPU 执行和逐行/流水线哈希一致性。

复算命令（在现有 CPU 容器内部执行，输出目录必须不存在）：

```bash
python /work/probes/template_probe.py \
  --dataset /work/length-candidate-v1.2/train.jsonl \
  --out /work/evidence/template/reproduce-candidate \
  --base-fingerprint /work/evidence/template/original-exact/base-files.json
python /work/probes/tokenizer_probe.py \
  --dataset /work/length-candidate-v1.2 \
  --base-fingerprint /work/evidence/template/original-exact/base-files.json \
  --evidence /work/evidence/template/reproduce-candidate/swift-template-evidence.json \
  --out /work/evidence/template/reproduce-candidate/preflight_report.json
```

GPU Smoke/Full 仍应 **No-Go，等待下一阶段授权**。本报告不对待裁定的身份语义、许可/数据用途、候选变更批准或受控 GPU 资源作代签。


---

# T-008 v1.2 CPU 修复增量审查

范围：只读检查 `evidence/code_changes.patch`、`work/code` 的三处现场修复、既有审批/不可变门禁，以及身份曝光和长度衍生映射。未修改实现，未查 Risk31 数据，未运行 GPU/训练。此次是同项目上下文中的增量复核，不是盲测或独立最终验收。

结论：三处修复未发现新增的许可审批或数据不可变性弱化；复核最新代码后本地 **23 项测试通过**。曾发现一项继承自 baseline 的实质审批类型缺陷，主 Agent 已修复，本审查已复测关闭。长度候选仍为 `PENDING_DERIVATIVE_APPROVAL`；身份语义未裁定，不能据长度通过宣称可训练。

## 实质发现

**[P1，已修复并验证] 审批门禁接受字符串假值（继承缺陷，非最初三处 diff 引入）。**

修复前 `work/code/run_identity.py` 第 171–177 行对 `identity_verified`、`gpu_window_approved`、`experiment_approved` 和两个 `sources_approved` 使用 Python truthiness；第 83 行附近的 `data_change_approved` 同理。JSON 中误写 `"false"`、`"0"` 等非空字符串会被视为已批准。在其余摘要与预检合法时，这会绕过该项“明确为 true”的布尔门禁。现有测试没有覆盖错误类型。

已仅提取并执行 AST 中的审批条件，无运行 main、GPU 或训练：布尔 `false` 被拒绝，字符串 `"false"` 和 `"0"` 均通过该条件。证据：`evidence/incremental_review/approval_truthiness_probe.json`。

已核对实际修复：新增纯函数 `validate_authorization`，三个主要审批字段及两个来源批准均要求 `is True`；`data_change_approved`、预检 `template_tokenization_completed` 和 `ms_swift_template_verified` 同样要求字面布尔 true。main 在导入 torch/GPU 探测前调用该函数。新增负向测试逐字段覆盖字符串 `"false"`/`"true"`、整数 1、空列表、None 和 False，全部被拒绝；真实布尔 True 才接受。此修复不产生任何实际批准，批准主体/引用真实性依旧需人工授权链核实。

## 三处变更判断

1. **占位符范围。** `prepare_official.unresolved_placeholders` 允许 Mixin 中正常的低写 Jinja 变量，同时对所有行保留大写占位符检查；身份段进一步拒绝 NAME/AUTHOR/AUTHOER 的大小写变体。训练门禁对衍生集依据原始父快照与排除列表重新找出身份行再检查。当前真实快照的全部 600 身份行已精确匹配官方模板，故本轮没有因范围收窄漏掉未替换身份字段的证据。其分段依赖原始 2000/600 顺序，本轮映射已证实；未来不同 loader 默认顺序不能仅凭注释继承此结论。

2. **CLI fallback 与显式 Qwen3。** `swift_cli_help()` 在外层帮助不完整时调用真实 SFT parser 的 `--help`；仍缺必需参数则拒绝。它没有删除或降低批准字段检查。新增 `--model_type qwen3 --template qwen3` 与实际 CPU `explicit_qwen3_cpu_init.ok=true` 对应；full/smoke 原始自动推断失败及显式修复证据见 `evidence/template/cli_parse.json`。后续训练仍需绑定本轮实际镜像与包版本，帮助输出成功不等于 Trainer/GPU 已运行。

3. **Transformers Mapping。** 将 `dict` 改为 `collections.abc.Mapping` 能正确读取 BatchEncoding 的 `input_ids`，避免把两项字典键误计为 2 tokens。现场回归测试以 2050 个 ID 验证为超长。预检依然使用无截断计数并另行绑定真实 ms-swift 证据；原始 958 行超长没有被这个修复吞掉。

## 数据不可变性与身份曝光复核

采用本地原始身份文件、实际 identity_spec、原始 2600 行训练快照与已生成映射，独立重做精确替换后的全内容匹配（无模糊匹配）：

- 映射恰好覆盖原始零基 2000–2599，共 600 行；600 个消息 hash、原始来源行 hash 和内容均匹配。
- 108 个源模板、108 个不同替换后模板；60 条曝光 6 次、48 条曝光 5 次。字典匹配在本批次没有同内容多源碰撞。
- 排除列表 958 行全部来自前 2000 个 Mixin 曝光，未删除身份行。
- 长度候选 1642 行，严格等于原始逐行字节按排除索引保留的顺序；600 身份曝光完整保留。结果见 `evidence/incremental_review/mapping_verification.json`。
- `validate_training_dataset` 仍要求独立批准绑定行数、数据 SHA、manifest SHA；衍生集还要求父清单/父训练文件/排除清单哈希及逐行字节顺序一致。未发现本次变更允许静默改写已批准训练正文。

600 身份曝光全部保留也意味着定制与基座研发语义问题保留。英文名称/主体 pending 已由后述负责人直接确认关闭；历史来源报告保留确认前状态。`approved_derivative`/`identity-approved-snapshot-v1.2` 是既有技术 schema 名称；实际 `status=PENDING_DERIVATIVE_APPROVAL`，不是审批事实。真实模板证据的 `verified=true` 只说明指定数据/模板长度与 mask 核验，不授予数据用途或训练权限。

## 验证与边界

最终复测：在 `work/code` 运行 `python3 -m unittest discover -s tests -v`，23 项，0 failures/errors，耗时 0.819 s（初检 21 项，严格布尔修复后 22 项，ClearML 存储修复后 23 项）。另完成 600 行映射与衍生字节校验，以及无 GPU 的审批条件 AST 最小复现。

审批主体真实性、正式训练窗口及身份语义裁定不由测试推导。严格布尔问题已修复关闭；本次范围内未发现剩余实质代码阻断项。英文身份已由负责人确认；身份语义等非代码决策仍待裁定。本报告不将主 Agent 的 ClearML 只读验证转写为本审查亲自执行的证明。


## 最后增量：负责人确认与 ClearML 真实上传门禁

已读取 `evidence/identity_confirmation_overlay.json`：负责人明确回复“我确认是官方名字，可用于开发及商业用途”，覆盖 `Octacarbon LLM` 和 `Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.`。当前英文名称确认状态为 `OWNER_CONFIRMED_OFFICIAL_NAMES`，不再列为待确认。该证据是负责人确认，不改写为政府登记文件独立核验；不扩展为身份训练语义、数据删减比例、GPU 窗口或发布批准。

当前身份语义并集为 78 个模板、434 次实际曝光，仍待裁定。长度候选保留全部 600 身份曝光，因此没有解决这些语义。

已通过只读 SSH 检查固定宿主 `/tmp/t008-identity-v12-cpu-20261019/deps/clearml/model.py` 与 `task.py` 的真实源码；片段由主 Agent 留在 `evidence/clearml-1.17.0-storage-source-excerpts.txt`。源码 `update_weights` 在没有 model/task upload storage 时确实仅注册本地文件；`get_local_copy` 对本地 URI 可直接返回本地路径。原实现存在把本地同文件 hash 误当远端闭环的风险。

最新修复与 SDK 实际调用签名/分支一致：

- `CLEARML_FILES_HOST` 明确为无内嵌凭据、无 query/fragment 的 HTTPS endpoint，并在 GPU 探测前验证。
- `Task.init(output_uri=files_host)` 指定任务输出存储；`update_weights(upload_uri=files_host, async_enable=False)` 明确上传目的地并同步完成，避免 SDK 无存储时仅注册本地 URI 的分支。
- 新建 `Model` 读取登记 URL，要求 HTTPS 且 netloc 相同、路径在预期 storage 子路径下；本地路径、file URI、HTTP、不同 host 和相似路径前缀均被拒绝。
- `get_local_copy(extract_archive=False, force_download=True)` 经 SDK 明确传递强制下载参数，避免直接复用旧缓存；随后要求真实文件存在且 SHA-256 与候选包相同。失败走原异常路径标记 FAILED，不能完成正常闭环。

新增 URL 门禁测试已纳入本轮 23/23 成功结果。未发现此次存储修复的实质错误或审批弱化。尚未执行新 Task/OutputModel 上传，因此结论是源码与门禁复核通过，不能表述为 Adapter 真实上传已成功。既有 synthetic 对象的只读 SDK 回读由主 Agent 单独留证。
