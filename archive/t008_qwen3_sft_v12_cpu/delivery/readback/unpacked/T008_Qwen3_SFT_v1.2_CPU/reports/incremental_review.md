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
