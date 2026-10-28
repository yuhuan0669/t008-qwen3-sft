# v0.1.16 K8s 发布记录

**已按用户授权发布，接口核验通过。** 新模型别名：`octa-carbon-sft-v0116`。

| 项目 | 结果 |
|---|---|
| 服务 | `vllm/vllm`，generation86，1/1 Ready，外部健康200 |
| 模型 | 保留原始 `Qwen/Qwen3-8B`，挂载 v0.1.16 LoRA，未合并权重 |
| 保留别名 | `octa-carbon-v1`、`octa-carbon-sft-v0114` |
| 新LoRA目录 | `vllm-released` PVC 的 `released/t008-v0116-20261028-publish01/adapter` |
| 模板 | 沿用修正后的 `thinking-prefill.jinja`，运行挂载哈希一致 |
| 原有配置 | 镜像、资源、探针、基座、旧LoRA挂载、工具解析参数、Service与Ingress保留 |
| 缓存 | 增加 `--max-cpu-loras 2` 以保留两份LoRA；GPU并发LoRA容量未扩大 |
| 应用 | 未暂停UAT应用、未改应用配置和路由；122个其他Deployment规格哈希不变 |
| 接口检查 | 5/5通过：原版、旧LoRA各1次；新LoRA非思考、Thinking、JSON各1次 |
| 回退 | 服务端dry-run确认回退补丁恢复发布前完整Deployment spec |
| 临时资源 | CPU暂存Pod已删除，保留不可变发布目录 |

## 请求配置

API：`https://vllm.10.140.17.125.nip.io/v1/chat/completions`。

调用新候选须设置 `model: "octa-carbon-sft-v0116"`。现有应用仍按自己的模型配置请求，发布不会把原版或v0.1.14别名自动改指向新权重。

五次核验均携带 **[v0.1.16 System](system.txt)＋问题**，使用既定两套模式参数，不传seed；JSON任务透传Schema。System没有写入服务端，也没有替换应用的System。完整示例见[核验请求及响应](probes/summary.json)和同目录 `*-request.json`。

新候选非思考正确给出模型和公司全称；Thinking回答2千瓦×3小时为6千瓦时；JSON包含指定的两项缺失资料与`incomplete`。五次均正常结束、正文非空，Thinking包含推理字段。这里是发布接口检查，未重跑120次评测、未训练；此前质量问题及未正式验收的结论保留。

## 切换及证据

首次切换于2026-10-28 07:01:26（America/Los_Angeles）开始。新Pod达到Ready后，首次外部health返回503，脚本自动回退；原配置恢复后也出现首次503、随后200。第一次没有发出推理核验请求。证据保存在[attempt-01](attempt-01/recovery.json)。

第二次使用**相同模型与模板补丁**，只将控制脚本改为最多等待120秒、连续两次外部health200后继续。持久失败仍回退，不重试生成请求。07:07:06重新切换，07:09:24就绪，07:09:31完成核验。成功尝试从补丁到Ready约138秒；首次及回退另有模型服务中断，未连续采样HTTP，不能把138秒当作本次总停服时长。[修正说明](READINESS_FIX.md)

Adapter ZIP SHA-256：`b4d413519053a48c95ca6998f116c5b06404122f887e493efe8e11274f1b1973`。

模板SHA-256：`ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d`。

基座16个文件、暂存Adapter和实际服务挂载均核验。核验材料先保存在本地Git，未上传Drive。

[发布核验](verification.json) · [模型列表](models-after.json) · [范围核验](scope-verification.json) · [发布补丁](rendered/publish.patch.json) · [回退补丁](rendered/rollback.patch.json)
