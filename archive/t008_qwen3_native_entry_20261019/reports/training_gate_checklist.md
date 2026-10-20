# T-008｜当前GPU训练门禁

结论：NO_GO_GPU。原E1正式入口/CPU兼容性阻断已关闭，当前数据政策已确认，不重复申请配比裁定。

| 编号 | 条件 | 状态 | 当前阻断 |
|---|---|---|---|
| D1 | 官方2048数据方案与身份名称 | USER_SELECTED_RECORDED | 否 |
| D2 | 原始2600曝光及原生过滤1642成员/哈希 | PASS_FRESH_NATIVE_CPU | 否 |
| D3 | 此前额外语义审核/改写/重配要求 | REFERENCE_ONLY_NOT_A_GATE | 否 |
| E1 | 正式启动入口与官方命令对齐并CPU解析验证 | PASS_IMPLEMENTED_CPU_VERIFIED | 否 |
| E2 | 最终训练镜像/依赖overlay/代码/PVC与精确输入绑定 | OPEN_NOT_BOUND | 是 |
| E3 | ClearML SDK在最终训练环境可导入、凭据与HTTPS输出配置 | OPEN_RUNTIME_BINDING | 是 |
| R1 | 当前受控GPU资源与vLLM切换窗口授权 | NOT_AUTHORIZED_GPU_OCCUPIED | 是 |
| R2 | 服务恢复配置与路由快照 | CAPTURED_NOT_RESTORE_TESTED | 否 |
| R3 | 本次切换负责人/顺序/超时/恢复验收及运行清单绑定 | OPEN_WINDOW_PLAN | 是 |
| V1 | 独立A/B/C/D测试集、评分标准与版本冻结 | OPEN_NOT_FROZEN | 否 |
| V2 | GPU BF16/LoRA显存、吞吐与真实保留数 | NOT_EXECUTED_EXPECTED_SMOKE_VERIFICATION | 否 |
| V3 | 本轮新ClearML Task/Model上传下载、最终checkpoint/epoch核验 | NOT_EXECUTED_LATER_PHASE_RESULT | 否 |

CPU检查不生成批准。正式GPU启动前需将真实批准绑定native预检报告SHA、输入canonical摘要、保留数、基座与实际Job；没有要求负责人重新选择数据方案。尚未执行的GPU阶段产物不能填作已通过。
