# vLLM、聊天模板、System与JSON Schema如何应用

这些材料原先分散在MANUAL第6节、evaluation/materials/run.py和spec.json；本页集中说明。示例沿用项目实测的vLLM0.25.1，不因查阅新版文档自动升级依赖。本次没有启动服务器或发送推理请求。

## 1. 四个配置位置

| 配置 | 配置位置 | 本项目用法 |
| --- | --- | --- |
| 基座、LoRA、资源和解析器 | vLLM启动参数 / Deployment args | `--model`、`--enable-lora`、`--lora-modules`、`--max-model-len`、`--reasoning-parser qwen3` |
| 聊天序列化模板 | vLLM的`--chat-template 文件路径` | 使用[修正模板](evaluation/materials/thinking-prefill.jinja)；Thinking入口预填`<think>\n`，Non-thinking保留空思考块 |
| 业务身份和行为要求 | 每次请求的`messages`，第一条`role=system` | [精简System r1](evaluation/materials/custom-system.txt)由Chat后端加入；服务器读取模板不等于自动加入这段业务System |
| 模式、预算和JSON结构 | 每次`/v1/chat/completions`请求 | `chat_template_kwargs.enable_thinking`、`max_tokens`、`temperature`、`top_p`；JSON任务另传`response_format` |

## 2. 固定推理配置

| 参数 | Non-thinking | Thinking |
| --- | ---: | ---: |
| `chat_template_kwargs.enable_thinking` | false | true |
| `temperature` | 0.7 | 0.6 |
| `top_p` | 0.8 | 0.95 |
| `top_k` / `min_p` | 20 / 0 | 20 / 0 |
| `max_tokens` | 2048 | 4096 |
| 开发对照seed / repetition_penalty | 42 / 1.0 | 42 / 1.0 |

完整参数来自[spec.json](evaluation/materials/spec.json)。`--max-model-len 8192`是输入和生成的总上下文上限；请求的max_tokens包含思考和可见正文。这里的2048/4096是生成预算，训练的max_length2048是训练序列上限，两者分别配置。当前实测入口没有依赖thinking_token_budget这个额外参数。

开发服务器的`--max-num-seqs 8`和gpu_memory_utilization0.90是本次小规模对照配置，不是未经容量测试的上线最优参数。发布补丁保留现有服务的资源、并发和工具调用设置，仅增加需要的LoRA及模板配置。

## 3. 一份服务器启动示例

这是已准备好基座/Adapter目录之后的命令示例，手工在空闲GPU中运行；不会由本交接包自动执行。API的基座名与LoRA别名保持不同。

```bash
python3 -m vllm.entrypoints.openai.api_server \
  --model /models --served-model-name octa-carbon-v1 \
  --host 0.0.0.0 --port 8000 --dtype bfloat16 \
  --gpu-memory-utilization 0.90 --max-model-len 8192 --max-num-seqs 8 \
  --enable-lora --max-lora-rank 8 \
  --lora-modules octa-carbon-sft-manual-01=/adapters/manual-01 \
  --chat-template /t008-serving/thinking-prefill.jinja \
  --reasoning-parser qwen3
```

现有服务如有`--enable-auto-tool-choice --tool-call-parser hermes`，发布时保留它们；不要用上面短示例整段覆盖原Deployment args。具体发布步骤见[PUBLISH.md](PUBLISH.md)。

vLLM按请求的model选择已注册LoRA。**加载了LoRA后，继续发送`model: octa-carbon-v1`仍是基座；使用新别名才能调用SFT权重。** 这一机制见[vLLM官方LoRA说明](https://docs.vllm.ai/en/latest/features/lora/)。

## 4. 请求示例：业务System和模式

下面工具只生成JSON文件，不访问服务：

```bash
PKG="$PWD"
MODEL_ALIAS=octa-carbon-sft-manual-01
python3 "$PKG/tools/make_request.py" --model "$MODEL_ALIAS" --mode nonthinking --text '麻烦报一下你的模型全称。' > /tmp/t008-request-nt.json
python3 "$PKG/tools/make_request.py" --model "$MODEL_ALIAS" --mode thinking --text '请用两句话解释功率和电量的区别。' > /tmp/t008-request-thinking.json
```

也可直接查看[Non-thinking请求](serving/examples/request-nonthinking.json)、[Thinking请求](serving/examples/request-thinking.json)和[JSON Schema请求](serving/examples/request-json-schema.json)。这些是静态示例，没有实际发送。文件中包含完整System、正确model别名和本页模式参数。由Chat后端组装时采用同样结构；不要让界面只切Thinking图标而漏传enable_thinking。生成结果取choices[0].message.content；reasoning字段另行处理，不把思考文本强行拼成正文。

## 5. JSON Schema：请求参数，不是全局System

例如DEV-07的结构是：

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "dev_07",
      "schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        "required": ["name", "age"],
        "additionalProperties": false
      }
    }
  }
}
```

只在需要结构化结果的任务加response_format；普通聊天不加。Schema约束结构与类型，不保证事实正确。前端有JSON需求时，Chat后端按该任务选择Schema并透传给vLLM；代理或SDK不能丢弃response_format、chat_template_kwargs、top_k等字段。这种用法见[vLLM官方结构化输出说明](https://docs.vllm.ai/en/latest/features/structured_outputs/)。

```bash
python3 "$PKG/tools/make_request.py" --model "$MODEL_ALIAS" --mode nonthinking --case DEV-07 > /tmp/t008-request-json.json
```

[四份Schema](evaluation/materials/json-schema-cases.jsonl)及[原题](evaluation/materials/scenarios.jsonl)已入包。expected_for_scoring_only是评分答案，不发给服务器；make_request.py仅选取user_turns与response_format。上线应用还需检查finish_reason、空正文和JSON解析结果；达到长度上限的半段JSON不能当成功结果。

若服务已由操作者发布，才发送刚生成的文件：

```bash
API=https://vllm.10.140.17.125.nip.io
curl --noproxy '*' --max-time 180 -fsS "$API/v1/chat/completions" -H 'Content-Type: application/json' --data-binary @/tmp/t008-request-json.json
```

本页的当前可执行字段以包内历史真实请求和固定版本为依据；官方latest页面可能随版本变化。没有把这些参数、System或Schema写入SFT权重，也未在本次部署到Chat。
