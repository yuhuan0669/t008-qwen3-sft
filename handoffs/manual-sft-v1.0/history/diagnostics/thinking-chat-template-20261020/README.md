# vLLM 聊天模板修改与六题 chat 验证

日期：2026-10-20。用户授权本次暂停 UAT，完成后恢复；不训练。

**本次六题验证通过：原版、Full2、Full3 共 18 次 chat 请求，均返回非空正文和非空思考内容，全部正常结束。Full3 在同六题、同采样配置下的空正文由此前 6/6 降为本次 0/6。**

## 修改与结果

在原 Qwen3 模板的生成入口增加两行：当 `enable_thinking` 不是 false 时，assistant 前缀后追加 `<think>\n`。Non-thinking 的空思考块保持原样，不改训练数据、权重或解析器。

可复用模板：[thinking-prefill.jinja](thinking-prefill.jinja)；完整差异：[template.diff](template.diff)。

临时 vLLM 实例使用 `--chat-template /tmp/t008-chat-template/thinking-prefill.jinja`，沿用 `--reasoning-parser qwen3`，加载原版及原 Full2、Full3 LoRA。该模板没有部署到 UAT；恢复时使用 UAT 原配置和原模型。

| 模型 | 此前默认模板：空正文 | 本次修改模板：空正文 | 本次非空思考 | 本次正常结束 |
|---|---:|---:|---:|---:|
| 原版 | 0/6 | 0/6 | 6/6 | 6/6 |
| Full2 | 0/6 | 0/6 | 6/6 | 6/6 |
| Full3 | 6/6 | 0/6 | 6/6 | 6/6 |

对照沿用上轮已经保存的默认模板 chat 结果，本次不重复跑旧模板。每题均无 System、Thinking 开启、seed=42、temperature=0.6、top_p=0.95、top_k=20、min_p=0、max_tokens=4096。此次只核对该采样条件，没有追加贪婪生成或训练。

18 次请求都先调用 vLLM 的 chat render 接口，将服务端实际输入 token 与修改后模板的本地编码逐项比较，全部一致。最终结果直接取 `/v1/chat/completions` 的 `content` 与思考字段，没有把思考文本复制成正文，没有给输出补标记。此前的前缀实验因此已完成实际 chat 接口验证。

CPU 核对还确认：六题在 Non-thinking 下的输入逐字不变；关闭生成提示时，模板输出也保持一致。未开展完整多轮、工具调用或所有采样条件的回归，不能把六题结果扩展为全量部署验收。

## 内容问题仍然存在

本次修复的是空正文。Full3 的 DEV-02 仍回答阿里云；DEV-06 仍执行旧保密话术且公司名称有误；DEV-22 仍未准确收束到能碳业务。不能据此认定身份与业务边界已达标。

[六题实际正文对照](CASE_COMPARISON.md)包含三模型的完整 `content`。`chat-results.jsonl` 保存原始响应及思考字段；本次不重新评分正式留出集，不接收 Full3 为正式候选。

## 证据与复用

- `cpu-template-check.json`：模板 CPU 检查。
- `metadata.json`：实际推理版本和采样参数。
- `runtime-bound.json`：服务器模板、执行脚本、两个 adapter 的实际哈希及模型注册。
- `chat-results.jsonl`：18 次 chat 请求、服务端 render 和响应。
- `summary.json`：结果统计，可由 `summarize.py` 从原始记录重新生成。
- `eval-pod.json`：包含修正后核验脚本的可复用临时实例配置；实际运行 Pod 见 `pod-running.json`。
- `execution-notes.md`：首次 CPU 输入检查的返回类型适配说明。
- `window-state.json`、`uat-before.json`、`uat-restored.json`、`verification.json`：暂停与恢复证据。
- `manifest.json`：本地归档文件哈希。

模板 SHA-256：`ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d`。

只在本地保存并做 Git 版本管理；未上传本批原始数据到 GitHub 或 Drive。本次完成临时实例验证，UAT 保留原配置；若后续正式采用，应明确选择使用该模板的服务及模型版本。

UAT 恢复核验：原配置一致、1/1 就绪、健康检查 HTTP 200；临时诊断 Pod 已删除。实际暂停约 8.2 分钟。
