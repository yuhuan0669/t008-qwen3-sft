# v0.1.14 模型服务发布记录

状态：已发布并完成接口核验。时间：2026-10-21T21:53:41.465034-07:00（America/Los_Angeles）。

| 项目 | 结果 |
| --- | --- |
| 服务 | `vllm/vllm`，generation 79，1/1 Ready，健康 HTTP 200 |
| 原始基座 | 保留原目录及 `octa-carbon-v1` 别名；16 个文件哈希一致 |
| v0.1.14 LoRA | `octa-carbon-sft-v0114`；权重与本地冻结版本哈希一致 |
| 模板 | 已应用修正后的 `thinking-prefill.jinja`，挂载哈希一致 |
| 原有配置 | 镜像、资源、基座挂载、工具解析器、Service、Ingress 保留 |
| UAT 应用 | 未暂停、未修改配置；115 个其他 Deployment 规格哈希不变，前后端等关键服务均 1/1 |
| 接口核验 | 6/6：两模型各测非思考、Thinking、JSON；HTTP 200、正文非空、正常结束，JSON 结构及示例值正确 |
| 回退 | 已保存精确补丁，针对现有 Deployment 的服务端 dry-run 能恢复完整原 spec |
| 临时资源 | CPU 暂存 Pod 已删除，版本目录和模板 ConfigMap 保留 |

本次只重建模型服务 Pod，Deployment 副本数始终为 1；应用没有执行停服或配置切换。模型服务从应用补丁到 Ready 约 134 秒，这是重建耗时，不是精确 HTTP 中断时长。

**应用侧未切换：继续请求 `octa-carbon-v1` 仍使用基座；调用新 LoRA 必须使用 `octa-carbon-sft-v0114`。** System、Schema 和两套预算未写入服务端或应用；本次核验请求自行携带统一 System／参数，日常请求均未传 seed。

LoRA ZIP SHA-256：`4132928f5ce62dedb704f69f636ef5ac0596311245a39e329ed318a3052e432c`。模板 SHA-256：`ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d`。

证据：[核验](verification.json) · [模型列表](models-after.json) · [请求与结果](probes/summary.json) · [变更范围](scope-verification.json) · [发布补丁](rendered/publish.patch.json) · [回退补丁](rendered/rollback.patch.json) · [执行说明](execution-notes.md)。

这是部署及少量接口核验，不是新的全面质量验收；没有训练。
