# 手工发布SFT模型：原始基座＋LoRA

本页补齐原v1.0交接包缺少的发布步骤。**只提供材料与离线补丁生成，本次没有操作集群、暂停UAT或发布模型。** 操作者选定模型并安排实际窗口后逐步执行；当前v0.1.14仍是未正式验收候选，不因写好发布手册变成已批准上线。

## 1. 发布物与路由

一次发布要绑定：原始Qwen/Qwen3-8B基座版本、最终Adapter ZIP及SHA、修正模板SHA、System版本、请求预算/Schema和API模型别名。使用同一基座加载LoRA即可，不需要先做权重合并。LoRA目录中的adapter_model.safetensors不是一份完整基座模型。

训练PVC在swift namespace，服务PVC在vllm namespace，不能直接把跨namespace的PVC名称填进Deployment。本流程将Adapter复制到`vllm/vllm-released`的新不可变版本目录，原基座挂载保留。

保留原API名`octa-carbon-v1`作为基座，增加如`octa-carbon-sft-manual-01`的LoRA别名。Chat客户端或后端默认model改为新别名才会调用SFT；仅注册LoRA不会自动切换原model。System与按任务选择的Schema还需在Chat后端发送，详见[SERVING.md](SERVING.md)。

## 2. 本地准备发布目录和配置

ADAPTER_ZIP填写实际训练成功后的文件绝对路径。使用新的RELEASE；发布的Adapter rank必须与--rank一致，当前配方为8。

```bash
PKG="$PWD"
ADAPTER_ZIP=/absolute/path/to/training/outputs/full/adapter.zip
RELEASE="t008-sft-$(date -u +%Y%m%d-%H%M%S)"
MODEL_ALIAS="octa-carbon-$RELEASE"
PUBLISH_WORK="$(dirname "$PKG")/publishes/$RELEASE"
mkdir -p "$PUBLISH_WORK"
ADAPTER_SHA=$(python3 -c 'import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$ADAPTER_ZIP")
K=(kubectl --context lmas00-direct --request-timeout=30s)
"${K[@]}" -n vllm get deployment vllm -o json > "$PUBLISH_WORK/deployment-before.json"
python3 "$PKG/tools/render_publish.py" --deployment "$PUBLISH_WORK/deployment-before.json" --release "$RELEASE" --model-alias "$MODEL_ALIAS" --rank 8 --output "$PUBLISH_WORK/rendered"
```

render_publish只读本地快照并生成文件，不调用kubectl：ConfigMap、CPU暂存Pod、发布JSON Patch、精确回退Patch、期望Pod模板。补丁先test UID和原template再替换template，避免覆盖并发修改。原基座mount、资源、探针、Service、工具解析参数保留；增加LoRA mount和模板ConfigMap mount。

基座必须与训练一致，逐文件哈希见[evaluation/materials/base-files.json](evaluation/materials/base-files.json)；不能只凭模型名判断。同一次发布的模板和System使用包内固定版本。若原Deployment已经有本工具管理的模板volume，渲染器会停止，需审阅现有发布配置后再生成下一版，不能盲目叠加。

## 3. CPU暂存Adapter，不中断现有UAT

```bash
"${K[@]}" create -f "$PUBLISH_WORK/rendered/release-stage-pod.json"
"${K[@]}" -n vllm wait --for=condition=Ready "pod/$RELEASE-stage" --timeout=180s
kubectl --context lmas00-direct --request-timeout=0 cp "$ADAPTER_ZIP" "vllm/$RELEASE-stage:/tmp/adapter.zip"
kubectl --context lmas00-direct --request-timeout=0 cp "$PKG/tools/stage_release.py" "vllm/$RELEASE-stage:/tmp/stage_release.py"
"${K[@]}" -n vllm exec "$RELEASE-stage" -- python3 /tmp/stage_release.py --adapter-zip /tmp/adapter.zip --expected-sha256 "$ADAPTER_SHA" --release "$RELEASE" --execute
"${K[@]}" -n vllm exec "$RELEASE-stage" -- cat "/store/released/$RELEASE/release-manifest.json" > "$PUBLISH_WORK/release-manifest.json"
"${K[@]}" create -f "$PUBLISH_WORK/rendered/template.configmap.json"
```

暂存Pod不请求GPU。stage_release只写新的`released/RELEASE`，验证ZIP和两个Adapter文件后将文件设为只读，不改其他版本。检查release-manifest中的rank、SHA、基座标识；不要把任意中间checkpoint当最终发布权重。新ConfigMap在Deployment引用前不会影响当前服务。

## 4. 在实际发布窗口切换

唯一4090需要等待旧Pod退出后启动新配置。以下会造成UAT短暂停服，实际操作者协调后执行。本页没有自动停服脚本。

```bash
ORIGINAL_REPLICAS=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"]["replicas"])' "$PUBLISH_WORK/deployment-before.json")
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$PUBLISH_WORK/switch-start.txt"
"${K[@]}" -n vllm scale deployment/vllm --replicas=0
"${K[@]}" -n vllm wait --for=delete pod -l app=vllm --timeout=180s
"${K[@]}" -n vllm patch deployment vllm --type=json --patch-file "$PUBLISH_WORK/rendered/publish.patch.json"
"${K[@]}" -n vllm scale deployment/vllm --replicas="$ORIGINAL_REPLICAS"
"${K[@]}" -n vllm rollout status deployment/vllm --timeout=900s
"${K[@]}" -n vllm get deployment vllm -o json > "$PUBLISH_WORK/deployment-after.json"
curl --noproxy '*' --max-time 15 -fsS -o /dev/null -w '%{http_code}\n' https://vllm.10.140.17.125.nip.io/health
curl --noproxy '*' --max-time 30 -fsS https://vllm.10.140.17.125.nip.io/v1/models > "$PUBLISH_WORK/models.json"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); assert sys.argv[2] in {x["id"] for x in d["data"]}' "$PUBLISH_WORK/models.json" "$MODEL_ALIAS"
```

预期为原副本数恢复、Pod就绪、健康200、/v1/models同时包含基座和新LoRA别名。再核对deployment-after的template等于rendered/desired-template.json及实际LoRA路径/模板挂载。启动失败、Patch test不通过或模型列表缺别名时，先处理回退，不先修改Chat默认model。

## 5. 少量接口验证，再切Chat默认model

生成器只写JSON；curl才会产生实际推理。下面是身份Non-thinking、普通任务Thinking、JSON三类检查，不是完整120次验收。存在工具调用的Chat入口还应保留并检查原工具行为。

```bash
python3 "$PKG/tools/make_request.py" --model "$MODEL_ALIAS" --mode nonthinking --text '麻烦报一下你的模型全称。' > "$PUBLISH_WORK/request-identity.json"
python3 "$PKG/tools/make_request.py" --model "$MODEL_ALIAS" --mode thinking --text '请用两句话解释功率和电量的区别。' > "$PUBLISH_WORK/request-thinking.json"
python3 "$PKG/tools/make_request.py" --model "$MODEL_ALIAS" --mode nonthinking --case DEV-07 > "$PUBLISH_WORK/request-json.json"
API=https://vllm.10.140.17.125.nip.io
for KIND in identity thinking json; do
  curl --noproxy '*' --max-time 180 -fsS "$API/v1/chat/completions" -H 'Content-Type: application/json' --data-binary "@$PUBLISH_WORK/request-$KIND.json" > "$PUBLISH_WORK/response-$KIND.json"
done
```

检查响应model等于新别名、正文非空、finish_reason不是length，JSON可解析且符合Schema；保留原始请求/响应。Thinking正文与reasoning分别读取。健康200或请求成功只证明服务连通，不能替代内容验收。

随后在实际Chat应用后端/模型选择配置中，将目标model设为MODEL_ALIAS，第一条messages加入System r1；普通聊天不传Schema，结构化任务按需要传response_format，模式开关透传chat_template_kwargs。具体应用文件位置由Chat项目实现决定，本包不擅自改Chat代码或路由。如果业务要求固定外部模型名，应在网关明确映射到新LoRA别名，而不是让客户端继续命中基座别名。

确认后记录该次发布版本、模板/System SHA、LoRA SHA、Chat路由、时间和验证结果；未完成这些检查不写“发布完成”。

## 6. 回退到本次发布前状态

若已更改Chat默认model，先将它改回发布前值。回退Patch以“当前仍是刚生成的发布template”为前提，test失败说明有并发变化，先核查，不整份覆盖旧Deployment。

```bash
"${K[@]}" -n vllm scale deployment/vllm --replicas=0
"${K[@]}" -n vllm wait --for=delete pod -l app=vllm --timeout=180s
"${K[@]}" -n vllm patch deployment vllm --type=json --patch-file "$PUBLISH_WORK/rendered/rollback.patch.json"
"${K[@]}" -n vllm scale deployment/vllm --replicas="$ORIGINAL_REPLICAS"
"${K[@]}" -n vllm rollout status deployment/vllm --timeout=900s
"${K[@]}" -n vllm get deployment vllm -o json > "$PUBLISH_WORK/deployment-restored.json"
python3 -c 'import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); assert a["spec"]==b["spec"]' "$PUBLISH_WORK/deployment-before.json" "$PUBLISH_WORK/deployment-restored.json"
curl --noproxy '*' --max-time 15 -fsS -o /dev/null -w '%{http_code}\n' https://vllm.10.140.17.125.nip.io/health
```

如果发布Patch的test阶段就失败，它没有应用替换，此时不要强行运行仅匹配新template的rollback.patch；保留当前template并按实际原副本数恢复、核查差异。新发布物和ConfigMap保留作追溯，不删除其他版本。完成正常发布或回退后删除本次CPU暂存Pod：

```bash
"${K[@]}" -n vllm delete pod "$RELEASE-stage" --ignore-not-found --wait=true --timeout=90s
```

把本地PUBLISH_WORK的清单、Patch、请求/响应、哈希及恢复记录纳入版本管理。本说明和生成器只做过离线校验，未在本次验证真实切换或Chat应用集成。
