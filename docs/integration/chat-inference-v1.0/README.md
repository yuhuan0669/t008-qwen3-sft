# 应用推理接入说明 v1.0

日期：2026-10-21。对象：Chat 后端、模型网关和应用开发方。适用已实测的 vLLM 0.25.1；不因查阅文档升级运行环境。

本说明只交付本地文档和请求示例，未部署、未修改应用、未发送推理请求、未暂停 UAT。日常请求省略 `seed`，不发送 `seed: null` 或固定值。历史评测与交接包保留原样。

## 1. 接口与模型配置

项目已有 API 基地址为 `https://vllm.10.140.17.125.nip.io/v1`，聊天接口为 `POST /chat/completions`，请求头为 `Content-Type: application/json`。本次没有重新访问该接口；实际网络和鉴权按应用已有环境配置，凭据不写入本说明。

模型别名由应用的环境配置提供，填写发布方确认且能在 `/v1/models` 中找到的名称。示例中的 `YOUR_MODEL_ALIAS` 是占位符，发送前必须替换；它不是已注册的模型名。若有网关，须确认外部名称映射到目标后端模型，不静默回退到其他模型。

本说明适用于本项目共用的推理配置，不按模型版本另设参数、System 或 Schema。模型选择只改变请求的 `model` 字段，不复制另一套接入配置。本文不变更模型选型结论，也不表示任何候选已发布。

## 2. 配置职责与服务前提

| 配置 | 负责位置 | 要求 |
| --- | --- | --- |
| 模型加载与别名 | vLLM Deployment 启动参数及挂载 | 由发布方配置；如采用 LoRA，另用 `--enable-lora`、`--lora-modules` 注册别名 |
| 聊天模板 | vLLM `--chat-template` | 使用[修正后的 thinking-prefill.jinja](../../../handoffs/manual-sft-v1.0.1/evaluation/materials/thinking-prefill.jinja) |
| 思考解析 | vLLM 启动参数 | `--reasoning-parser qwen3` |
| 总上下文上限 | vLLM 启动参数 | `--max-model-len 8192`，输入和生成合计 |
| 模型、System、模式和采样参数 | Chat 后端／模型网关的请求构造 | 按模型配置和模式显式传递，不依赖引擎默认值 |
| Schema | 结构化任务的请求构造 | 按任务传 `response_format`；普通聊天省略 |

服务前提尚待发布实施；当前在线基座仍使用模型自带模板。本说明不包含切换动作。[手工发布与回退](../../../handoffs/manual-sft-v1.0.1/PUBLISH.md)另列。

模板只处理消息格式，不会根据思考开关自动调整采样参数和预算。应用后端读取开关后选择整套配置；只切界面图标或只传 `enable_thinking` 不够。不需要为了两种模式启动两份模型服务。

## 3. 两种模式的完整请求配置

统一使用以下值，只按思考模式区分。可直接导入 [modes.json](modes.json)，应用默认选择 `nonthinking`。

| 字段 | 非思考 `nonthinking` | 思考 `thinking` |
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
| `stream` | false（示例） | false（示例） |
| `seed` | **不传** | **不传** |
| `stop` / `stop_token_ids` | 不传自定义值，沿用正常结束标记 | 同左 |
| `response_format` | 普通聊天不传；JSON 任务另加 | 同左 |

`model`、`messages` 加上这组字段构成完整请求。JSON 中的 `top_k`、`min_p`、`chat_template_kwargs` 是 vLLM 扩展字段；网关或客户端封装不能丢弃它们。`presence_penalty`、`frequency_penalty` 显式写出默认的 0，未新增惩罚策略。`repetition_penalty=1.0` 不施加额外重复惩罚。

采样温度、top_p、top_k、min_p 沿用 [Qwen3 官方推荐](https://huggingface.co/Qwen/Qwen3-8B#best-practices)；不是本项目调参得到的最优值。输出预算 2048/4096 是项目已使用的起始配置，不是官方通用推荐，也不保证任何任务都能完成。非思考从 1024 提高到 2048 的直接依据见[历史长度对照](../../../stage2/diagnostics/engine-compare-20261020/REPORT.md)。

`max_tokens` 包含思考和正文，不是仅正文长度。当前接口接受此字段；如客户端改用 `max_completion_tokens`，值保持一致，不同时发送两个字段。`8192` 是服务端总上下文上限，不放进聊天请求当成生成预算。按同一 tokenizer／模板计算输入后，须满足“输入 tokens＋所选预算 ≤ 8192”；超出时提示缩短输入或按应用既有策略整理历史，不静默截掉当前问题或 System。

日常请求不指定 seed；这不等于关闭服务端全局种子，当前 vLLM V1 服务端默认全局 seed 为 0。固定请求 seed 有助于复查同一生成路径，不能保证身份和事实正确，也不保证在线并发时逐字一致。测试排障可显式使用并记录 42/43/44，日常示例全部省略。见 [vLLM 0.25.1 可复现性说明](https://docs.vllm.ai/en/v0.25.1/usage/reproducibility/)。

## 4. System：统一从后端加入

统一使用下列精简 System r1。完整可读文件为 [system.txt](system.txt)，与已评测版本逐字节一致：

```text
我是能碳章鱼垂直大模型，由能碳章鱼（湖北）人工智能科技有限公司研发，主要面向工业企业、园区及公共机构，围绕能源管理和碳排放管理，提供能碳知识问答、政策与标准辅助解读、分析思路及方案、报告文本支持。
直接回答所问内容，不主动重复身份介绍，不补充未经确认的公司背景、客户或业绩。
可协助翻译、写作、计算和编程等通用任务；不将服务对象的全部业务视为自身业务。
涉及现场数据或实际操作时，只依据用户提供的资料和实际工具结果；缺少信息时说明所需资料，不编造读数或平台功能，不声称已执行操作或完成认证。
可提供明确标为假设的测算，不将其表述为实测、真实项目成果或收益保证，不代表公司作出投资、节能收益或补偿承诺。
```

每次请求的 `messages` 第一条为 `{"role":"system","content":读取的全文}`，后接历史 user/assistant 消息及当前用户问题。应用统一维护一份，避免网关与 Chat 重复注入，或额外叠加旧名称、公司成立日期、地址及已删除的底层信息保密话术。不要在用户提问末尾自动拼接 `/think` 或 `/no_think`，模式按第 3 节显式传递。

保存多轮历史时只保存助手可见正文，思考字段不拼入历史。模板不会自动注入业务 System，加载 LoRA 或合并权重也不替代这一步。

System SHA-256：`8d9946d0d9424941ce2a966a49e6da1c9842cfe00a0bb4daf3d5be504ae01513`。

修正模板 SHA-256：`ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d`。

## 5. JSON Schema：按任务发送

只对需要结构化结果的任务，在第 3 节请求上增加以下顶层字段。文件版：[response-format-person.json](response-format-person.json)。

```json
{
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "person",
      "schema": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "age": {"type": "integer"}
        },
        "required": ["name", "age"],
        "additionalProperties": false
      }
    }
  }
}
```

示例用户输入是“只输出JSON，把姓名小林、年龄26写成name和age两个字段。”Schema 定义字段和类型，用户消息提供待处理内容；实际业务换成对应任务的字段和来源。普通聊天省略 `response_format`，不是全局强制 JSON，也不需要把 Schema 塞进 System。文件版只包含上例 `response_format` 的值；读取后赋给 `body["response_format"]`。

两种模式使用同一结构化接口；可将此字段加入 Thinking 请求，不改变思考解析配置。只解析最终 `message.content`，不把思考字段拿来拼 JSON。Schema 约束结构和类型，不保证字段事实正确；应用仍须做 JSON 解析、Schema 校验和业务值检查。评分答案与测试 rubric 不进入生产请求。见 [vLLM 0.25.1 结构化输出说明](https://docs.vllm.ai/en/v0.25.1/features/structured_outputs/)。

## 6. 完整请求示例与组装顺序

以下文件含完整 System、全部模式参数，均不含 seed；它们是本地静态示例，没有发送到服务。三份示例共用模型占位符 `YOUR_MODEL_ALIAS`，不按模型版本重复提供。

| 场景 | 完整请求 |
| --- | --- |
| 非思考普通聊天 | [request-nonthinking.json](examples/request-nonthinking.json) |
| 思考普通聊天 | [request-thinking.json](examples/request-thinking.json) |
| 非思考 JSON Schema | [request-json-schema.json](examples/request-json-schema.json) |

思考 JSON 请求的组装方式：读取 `request-thinking.json`，将 user 内容换成 JSON 任务，再增加 `response_format`，值取 `response-format-person.json`。无需新增另一套 Schema。

后端组装顺序：读取环境中的模型别名 → 选择模式配置 → 加入 System 与消息 → JSON 任务增加 Schema → 发送。网关不得通过自身默认值覆盖这套显式配置。

应用可将 `stream` 改为 true；该流式接入不是本次新实测。流式分别读取 `delta.content` 和 `delta.reasoning`，直到完成事件后再解析完整 JSON。非流式正文取 `choices[0].message.content`，思考取 `message.reasoning`；旧客户端如只识别 `reasoning_content`，需适配当前版本。两者不能混为正文。见 [vLLM 0.25.1 思考输出说明](https://docs.vllm.ai/en/v0.25.1/features/reasoning_outputs/)。

## 7. 应用返回处理与交付范围

检查接口错误、正文是否为空和 `finish_reason`。`finish_reason=length` 表示达到生成／上下文限制，须标记“回答未完成”，不当成完整回答或合格 JSON。正常工具调用按应用既有工具流程处理，不能因为 content 为空就误报失败，也不能把工具调用当成普通正文。

回答长短优先用用户要求或任务提示控制，不通过随意压低生成预算实现“简洁”。上线日志至少记录实际模型别名、模式、有效采样参数与预算、System／模板／Schema 版本及 `finish_reason`，方便定位问题。

最小界面只需思考开关；模型选择和参数配置由管理员／后端维护，普通用户不需要填写 seed、top_k 或 Schema。

本次仅做文档与本地示例机械核对，[核对记录](CHECKS.json)记录范围。既有正式请求参数来源为[评测 spec](../../../handoffs/manual-sft-v1.0.1/evaluation/materials/spec.json)及[请求构造](../../../handoffs/manual-sft-v1.0.1/evaluation/materials/run.py)。历史评测显式使用 seed，本次按约定省略 seed 后没有重新推理，不能保证逐条复现旧答案；本说明也不代表 Chat 真实调用链、模型别名或模板已经部署验证。
