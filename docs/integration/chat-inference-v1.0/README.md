# 应用推理配置 v1.0

适用 vLLM 0.25.1。原版与 LoRA 共用配置，仅按思考模式切换参数。模型服务已发布，应用侧配置未改。

## 1. 接口与服务端

| 配置位置 | 配置值 |
| --- | --- |
| 应用 API 基地址 | `https://vllm.10.140.17.125.nip.io/v1` |
| 请求接口 | `POST /chat/completions`，`Content-Type: application/json` |
| 请求 `model` | 从环境配置读取实际模型别名；替换示例中的 `YOUR_MODEL_ALIAS` |
| vLLM 聊天模板 | `--chat-template /t008-serving/thinking-prefill.jinja`，挂载[修正模板](../../../handoffs/manual-sft-v1.0.1/evaluation/materials/thinking-prefill.jinja) |
| vLLM 思考解析器 | `--reasoning-parser qwen3` |
| vLLM 总上下文上限 | `--max-model-len 8192` |

## 2. 请求参数

应用默认非思考；切换模式时同时切换整套参数。可直接读取 [modes.json](modes.json)。

| 字段 | 非思考 | 思考 |
| --- | ---: | ---: |
| `chat_template_kwargs.enable_thinking` | false | true |
| `temperature` | 0.7 | 0.6 |
| `top_p` | 0.8 | 0.95 |
| `top_k` | 20 | 20 |
| `min_p` | 0 | 0 |
| `repetition_penalty` | 1.0 | 1.0 |
| `presence_penalty` | 0.0 | 0.0 |
| `frequency_penalty` | 0.0 | 0.0 |
| `max_tokens` | 2048 | 4096 |
| `n` | 1 | 1 |
| `stream` | false；流式改 true | 同左 |
| `seed` | 不传 | 不传 |
| `stop` / `stop_token_ids` | 不传 | 不传 |

网关须透传上述字段。输入 tokens＋`max_tokens` 不得超过 8192；生成预算包含思考和正文。

## 3. System

每次请求的 `messages` 第一条放 `role: "system"`，`content` 读取 [system.txt](system.txt) 全文，后接历史消息和当前问题。不要重复注入。

```text
我是能碳章鱼垂直大模型，由能碳章鱼（湖北）人工智能科技有限公司研发，主要面向工业企业、园区及公共机构，围绕能源管理和碳排放管理，提供能碳知识问答、政策与标准辅助解读、分析思路及方案、报告文本支持。
直接回答所问内容，不主动重复身份介绍，不补充未经确认的公司背景、客户或业绩。
可协助翻译、写作、计算和编程等通用任务；不将服务对象的全部业务视为自身业务。
涉及现场数据或实际操作时，只依据用户提供的资料和实际工具结果；缺少信息时说明所需资料，不编造读数或平台功能，不声称已执行操作或完成认证。
可提供明确标为假设的测算，不将其表述为实测、真实项目成果或收益保证，不代表公司作出投资、节能收益或补偿承诺。
```

## 4. JSON Schema

仅 JSON 任务增加下列顶层字段；普通聊天不传。实际业务替换 `name` 和 `schema`，不要写进 System。

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "person",
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

也可读取 [response-format-person.json](response-format-person.json)，直接赋给请求的 `response_format`。两种模式用法相同。

## 5. 完整请求与返回

请求示例：[非思考](examples/request-nonthinking.json) · [思考](examples/request-thinking.json) · [JSON Schema](examples/request-json-schema.json)。均含完整 System，不传 seed；发送前替换模型别名。

正文读取 `choices[0].message.content`，思考读取 `message.reasoning`；流式对应 `delta.content`／`delta.reasoning`。历史消息只回传正文。`finish_reason=length` 标记回答未完成；JSON 完成后再解析并校验 Schema。
