# T-008执行记录｜官方2048口径更新

本文件保留原执行记录并追加当前决定。**当前有效口径见文件末尾更新条目及同目录complete_report.md；下方原记录中的额外语义/配比门禁已被本会话选择替代。** 原始旧包文件未改写。

---

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

# 当前追加记录：采用官方2048路线

用户原话：“按qwen官方给的训练命令即可，这是官方给的”。
用户本轮要求：更新执行记录/交付报告并核对前置条件，先不要启动GPU。
已记录官方两来源#2000/#600、2048和默认delete；保留已确认中英文名称/主体，不额外改写、排除或重采身份。
已重算2600→1642，Mixin1042/身份600；206个原包文件hash及成员链复核通过。数据方案选择关闭；旧语义清洗和额外配比裁定改为参考。
只读现场：vLLM1/1且HTTPS200，Swift0，唯一4090已用22176/24564MiB；部署spec探测前后未变。
已保存当前恢复配置；未作服务切换。ClearML服务与存储健康，但最终训练SDK/overlay和Job/PVC仍待绑定。
发现旧启动封装零超长预检、人工衍生输入、Full按epoch保存与官方原生路径/50步保存不一致；只记录差异，未修改训练代码。
剩余条件：入口适配CPU解析、最终运行单元与PVC、ClearML集成、GPU业务窗口和恢复清单；Full前需冻结独立评测。GPU运行验证留给获批Smoke。
没有创建approval.json、ClearML Task/Model、GPU进程或K8s对象；未训练、未停vLLM、未发布。
当前结论：数据方案已选定；GPU仍No-Go。机器可读状态见../gpu_gate_checklist.json。
