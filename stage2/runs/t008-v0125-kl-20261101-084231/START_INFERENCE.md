# 启动 v0.1.25 推理

工作区：`/Users/ben/aiws/codex/keywords/t008_qwen3_sft`。

目标是启动已训练的 **Qwen3-8B 原始基座＋v0.1.25 LoRA** 临时推理服务。KL只用于训练，推理不需要KL插件。此说明不代表发布验收。本轮只核对了本地文件，集群路径与GPU状态须在启动时回读。

## 文件与环境

|内容|位置|
|---|---|
|已训练LoRA包|`/Users/ben/aiws/codex/keywords/t008_qwen3_sft/stage2/local-models/model-v0.1.25/adapter.zip`|
|原始启动参数|[evaluation/vllm-command.json](evaluation/vllm-command.json)|
|GPU容器、环境变量及PVC挂载参考|[eval-pod.json](eval-pod.json)|
|版本、别名及权重文件哈希|[evaluation/runtime-binding.json](evaluation/runtime-binding.json)|
|基座文件校验表|[evaluation/base-files.json](evaluation/base-files.json)|
|修正后的聊天模板|[evaluation/thinking-prefill.jinja](evaluation/thinking-prefill.jinja)|
|推理System|[evaluation/system.txt](evaluation/system.txt)|
|完整请求参数|[evaluation/evaluation-config.json](evaluation/evaluation-config.json)|

本地LoRA ZIP已核对SHA-256：

```text
fe6579750e821bb9de5c57a7688cdd9b85de991cd882b2d27a7946ca30e911dd
```

ZIP根目录只有`adapter_config.json`及`adapter_model.safetensors`，解压后将目录交给vLLM；不能将ZIP直接传给`--lora-modules`。权重单独保存，另一台机器需要取得它和原始基座，仅有Git代码不足以启动。

归档成功运行环境：vLLM **0.25.1**、Transformers **5.14.1**、Torch **2.11.0+cu130**，单张4090。容器镜像及`PYTHONPATH=/input/code:/input/deps`等依赖挂载以`eval-pod.json`为准；不能只选同一个镜像而忽略其中的依赖目录。

## 在现有K8s启动

历史context为`lmas00-direct`，namespace为`swift`，GPU节点为`k8s-worker05`。先核对当前GPU占用、其他作业及PVC文件，使用新的临时Pod和日志目录。用户当前要求UAT保持暂停，直到用户明确说恢复；启动本服务不修改UAT Deployment、应用路由、Service或Ingress。

历史挂载映射：

|容器内位置|来源|
|---|---|
|`/base`|`swift`命名空间PVC `swift-base`的`Qwen3-8B`子目录，只读|
|`/models-work`|同命名空间PVC `swift-work`根目录，只读|
|`/input`|PVC `swift-train-data`的`t008-v02-20261020-091453`子目录，含既有依赖，只读|
|`/runwork/evaluation/thinking-prefill.jinja`|将上表归档模板复制到本次新的工作目录并挂载；不要覆盖原实验文件|

历史LoRA实际路径如下，启动时须核对存在性及文件哈希；若已清理，可使用已校验的本地ZIP恢复到新的目录并修改这一个路径：

```text
/models-work/t008-v0125-kl-20261101-084231/outputs/full/checkpoints/v0-20261101-014804/checkpoint-66
```

以下是归档中已成功运行的服务命令，在挂载和依赖就绪的GPU容器内执行：

```bash
python3 -m vllm.entrypoints.openai.api_server \
  --model /base \
  --served-model-name octa-carbon-v1 \
  --host 127.0.0.1 --port 8000 \
  --gpu-memory-utilization 0.90 \
  --max-model-len 8192 \
  --trust-remote-code \
  --reasoning-parser qwen3 \
  --enable-auto-tool-choice --tool-call-parser hermes \
  --enable-lora --max-lora-rank 8 \
  --chat-template /runwork/evaluation/thinking-prefill.jinja \
  --lora-modules '{"name":"t008-diagnostic-v0125","path":"/models-work/t008-v0125-kl-20261101-084231/outputs/full/checkpoints/v0-20261101-014804/checkpoint-66","base_model_name":"octa-carbon-v1"}' \
  --max-cpu-loras 3
```

命令保留历史工具解析开关以复现环境；请求不传`tools`，这些开关不表示产品已支持工具调用。模板SHA-256为`ae8a1b27c3bac461eb5f6c78d5d39cbe29427ad91c9d2da8378e236b8a38448d`。

归档`eval-pod.json`本身只启动等待进程，不会自动启动vLLM；新Pod应按上述命令启动服务并保存日志。不要直接运行`execute.py`（会重新Smoke/Full训练），也不要运行`evaluation/run.py`（会自动批量生成评测答案）。

保持归档的loopback监听时，可在持有kubectl连接的机器建立本地入口：

```bash
kubectl --context lmas00-direct -n swift port-forward pod/<本次Pod名称> 18025:8000 --address 127.0.0.1
```

这样入口为该机器的`http://127.0.0.1:18025/v1`。另一台电脑不能直接使用这个localhost；应在调用方机器建立port-forward或SSH隧道。若要提供集群内/外共享地址，需要另行明确暴露方式，不自动改应用路由。

## 请求

请求`model`必须填写 **`t008-diagnostic-v0125`**；填写`octa-carbon-v1`得到的是原始基座。

System由调用方读取`evaluation/system.txt`，作为`messages`中的system消息传入，保持原字节和空行。它不会由聊天模板自动注入。文件SHA-256为`3ae02d520406f73e735752ef04ff395785f84fec7ee1619fd9d392d86cb92933`。

非思考普通请求参数：

```json
{
  "model": "t008-diagnostic-v0125",
  "messages": [
    {"role": "system", "content": "此处替换为system.txt完整内容"},
    {"role": "user", "content": "你好"}
  ],
  "chat_template_kwargs": {"enable_thinking": false},
  "temperature": 0.7,
  "top_p": 0.8,
  "top_k": 20,
  "min_p": 0,
  "max_tokens": 2048,
  "repetition_penalty": 1,
  "presence_penalty": 0,
  "frequency_penalty": 0,
  "n": 1,
  "stream": false
}
```

不传seed。若明确开展无System对照，移除整条system消息。Thinking模式另用`enable_thinking=true`、`temperature=0.6`、`top_p=0.95`、`max_tokens=4096`，其余按归档配置；不要只切开关而混用两套历史预算。

启动完成后检查`/health`与`/v1/models`，确认LoRA别名和权重绑定，报告访问地址、Pod、实际参数与日志路径。本交接只覆盖服务启动；不自动运行整批测试、Judge、训练或恢复UAT。
