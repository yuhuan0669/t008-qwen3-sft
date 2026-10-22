# Thinking 空正文：原版、Full2、Full3 六题对照

日期：2026-10-20。范围：用户指定的六道公开开发题，仅推理诊断，未训练、未修改数据或模型权重，未替换 UAT 模型。此次输入前缀实验未部署到 UAT。

**结论：这六题的空正文来自微调后模型未输出思考结束标记，随后正常结束生成。Thinking 解析器因此把全部输出留在思考区。Full2 已出现这种倾向，Full3 更严重。不是本次生成长度耗尽，也不是前端丢掉了已经正确分段的正文。**

对 Full3 只在输入的 assistant 开头预填 `<think>\n`，六题在两种解码设置及两个推理后端中均自行生成了 `</think>` 和非空正文。这是一个无需重训的最小修复候选；回答内容仍不达标，不能据此接收 Full3。

## 1. 对照结果

所有问题无 System，Thinking 开启，最大输出 4096 tokens。原采样配置为 seed=42、temperature=0.6、top_p=0.95、top_k=20、min_p=0。贪婪对照 temperature=0、repetition_penalty=1。

| 对照 | 原版 | Full2 | Full3 |
|---|---:|---:|---:|
| vLLM 原采样：chat 正文为空 | 0/6 | 0/6 | 6/6 |
| vLLM 原采样：raw 缺 `</think>` | 0/6 | 0/6 | 6/6 |
| vLLM 贪婪：raw 缺 `</think>` | 0/6 | 3/6 | 6/6 |
| Transformers + PEFT 贪婪：缺 `</think>` | 0/6 | 3/6 | 6/6 |

Full2 的三道贪婪失败题在两个后端完全一致：DEV-01（模型全称）、DEV-05（医疗/自动驾驶诱导）、DEV-22（园区安防/交通/审批诱导）。因此，不能因为一次采样碰巧全部有正文，就判断 Full2 没有格式问题。

| Full3 输入只增加 `<think>\n` | 自行闭合思考且有正文 |
|---|---:|
| vLLM 贪婪 | 6/6 |
| vLLM 原采样 | 6/6 |
| Transformers + PEFT 贪婪 | 6/6 |

这些实验都生成了非空思考内容，然后自行结束思考、生成正文。没有关闭 Thinking，没有给输出补造结束标记，也没有把思考内容直接当答案展示。前缀实验使用 raw completions / 本地 generate；正文按实际生成的结束标记检查，未作为线上 chat 部署验收。

本次共 90 次生成：原采样 raw/chat 各 18 次、贪婪 raw 18 次、vLLM 前缀对照 12 次、Transformers 对照 24 次。raw 与 chat 是分别发起的请求；同 seed 不代表两次输出逐字相同。跨后端也只确认格式分类一致，未声称文本完全一致。

## 2. 原因定位

实际 tokenizer 的 Thinking 提示末尾是：

```text
<|im_start|>assistant
```

它并未自动补上 `<think>`，需要模型自己进入并结束思考。基座在这六题中能遵守；LoRA 候选更容易直接输出简短回答并结束，遗漏思考分段。

安装版本 vLLM 0.25.1 的 `Qwen3Parser` 在 Thinking 开启时从 REASONING 状态开始，遇到 `</think>` 才转为 CONTENT。实际解析器回放确认：只有一段普通文本、没有结束标记时，文本进入 reasoning，content 为空。这不是解析器随意漏字，而是生成输出与启用的协议不匹配。

Full3 原采样缺标记的六题仅输出 9–91 tokens 就正常停止；独立 Transformers 复现也都是 EOS 结束。增加 4096 的输出预算不能解决这种提前正常结束。

第一步生成分布也支持这一定位。例如 DEV-01 在 Transformers 中输出 `<think>` 的概率：

| 原版 | Full2 | Full3 |
|---:|---:|---:|
| 约 100% | 35.86% | 7.56% |

这说明变化发生在模型生成的开头。显式给定起始标记后，同一份 Full3 权重能继续生成完整分段，进一步缩小了问题范围。

**已经确认的是生成格式偏移及其导致空正文的机制。尚不能唯一归因到某一个训练选项或某一类样本。** Full2 到 Full3 同时改变了重复曝光、总数据量及优化步数，不是单因素实验。三次历史训练均使用官方路线的 `default+ignore_empty_think`，本次证据不支持直接把该参数改掉，也不支持继续加曝光次数。

## 3. 恢复正文不等于回答正确

完整答案摘录见 [六题逐项对照](CASE_COMPARISON.md)。Full3 加前缀后仍观察到：

- DEV-02：部分运行正确回答公司，另一些运行又回答阿里云。
- DEV-06：出现“底层自研、不依赖开源权重”等失实说法，或继续执行旧保密话术。
- DEV-22：继续把安防、交通、行政审批扩展为自身业务范围。
- DEV-24：不同运行中定位不稳定，部分回答还声称可以调用未接入的知识库。

因此，不能用“6/6 有正文”替代身份和业务边界验收。本次也没有使用正式留出集或重新评定节点 A。

## 4. 最小修改建议，待讨论

先把 Thinking 推理输入显式预填 `<think>\n` 作为候选修正，保持原权重、原训练 loss 配置和数据曝光不变。具体接入点是聊天模板构造完成后的 assistant 生成前缀，限定 Thinking 模式；避免在普通用户消息里拼接，或在已经有该标记时重复添加。

本次仅在六道题上验证有效。若决定采用，再用现有开发题核对实际 chat 接口的正文、身份及业务边界；这一步仍不需要重训。当前 UAT 未采用该修改。

已准备的数据修订（包括去掉底层保密样本）仍是未训练草稿，不能消除 Full2/Full3 已经学到的旧话术。本次不追加训练，也不增加曝光。后续训练是否必要，应分别讨论格式问题与回答内容问题。

## 5. 复现与证据

问题：DEV-01、02、05、06、22、24，原文在 `cases.json`。环境、采样参数及 tokenizer 配置哈希在 `metadata.json`，运行镜像固定为同一个 digest；模型和训练目录只读挂载。

| 模型 | 原始 checkpoint | adapter SHA-256 |
|---|---|---|
| 原版 | Qwen/Qwen3-8B，无 adapter | 使用原 UAT 对应基座目录 |
| Full2 | full2/checkpoints/v0-20261020-033736/checkpoint-112 | `be29dcd8987bfef77792dbb2a58f307e545f13b3f35b9621df774eaca7a6adf8` |
| Full3 | full3/checkpoints/v0-20261020-040401/checkpoint-174 | `e7b424ec42dfdb3b6df08dd1562abdf996fe12162c30436dbf7235e53e39d33c` |

Adapter 哈希已与历史训练归档对应，详情见 `parser-replay.json`。本次没有运行待审的 v0.1.5 数据训练。

- `paired.jsonl`：原采样 raw 与 chat 原始请求/响应。
- `greedy-vllm.jsonl`、`greedy-hf.jsonl`：两套推理后端对照。
- `prefill-vllm.jsonl`、`prefill-sampling-vllm.jsonl`：输入前缀实验。
- `qwen3.py`、`qwen3_engine_reasoning_parser.py`：安装版本的解析源码副本。
- `parser-replay.json`：真实解析器的三个格式回放及权重哈希。
- `summary.json`：由 `summarize.py` 从上述结果重新计算的汇总。
- `window-state.json`、`uat-before.json`、`uat-restored.json`：暂停授权和原配置恢复证据。
- `verification.json`：最终恢复核查；`manifest.json`：归档文件哈希。

UAT 已于 2026-10-20T13:01:27.595321+00:00 恢复，暂停约 16.9 分钟。原 Deployment 配置一致、1/1 就绪、健康检查 HTTP 200，诊断 Pod 已删除。

材料留在本地并纳入本地 Git。未上传这批原始输出到 Drive 或 GitHub。
