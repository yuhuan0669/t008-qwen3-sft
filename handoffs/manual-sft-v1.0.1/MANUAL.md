# 人工操作手册

本次交付仅整理本地文件。以下命令供接手人日后逐步执行；**不要整篇粘贴执行**。新训练、推理与UAT维护窗口由实际操作者安排；历史window.json不作为新授权。

## 1. 本地校验与新运行目录

在交接包根目录打开终端。只有本节的校验与渲染不接触集群。

```bash
PKG="$PWD"
python3 "$PKG/tools/verify_package.py"
RUN="t008-manual-$(date -u +%Y%m%d-%H%M%S)"
WORK="$(dirname "$PKG")/runs/$RUN"
python3 "$PKG/tools/render_runtime.py" --run-id "$RUN" --output "$WORK"
```

渲染器只写三个Pod JSON，不运行kubectl。使用自己的context/节点/PVC时，先改新生成文件，保留原模板。源数据SHA应为`0f546c3aa59f8986f6e5f086482d7d40e9c29db6039a6c219ba902830abff6cb`，共1325条。

默认沿用lr1e-4、1 epoch、batch1/累积16、r8/alpha32/dropout0.05/all-linear、长度2048、身份损失×3。欲改参数，将config/actual-v0.1.14-training.json复制到新运行目录后编辑full_argv，通过train.py的`--config`指定；不要改历史配置。1与2 epoch比较可用`--epochs`，每次用新RUN，2 epoch会增加每条样本的实际训练次数，最终步预计83→166。两轮都从原始基座开始。

配置中external_plugins保留为最后一个选项，便于启动器按固定结构替换两个插件路径。默认只打印完整训练命令：

```bash
python3 "$PKG/tools/train.py" --base /base --mode full --epochs 1 --output /manual-work/outputs/full
```

只有显式加`--execute`才训练。它核对数据、库版本和tokenizer/config；原生编码过程中local_data_guard核对样本成员/曝光，防止静默丢行。身份插件必须与identity-keys.json相邻，`is_binary=False`和ignore_empty_think组合名保留；普通边界样本不是全部加权3倍。原归一化和监督证据见[CPU报告](data/v0.1.14/cpu-check/report.json)。训练不注入System。

## 2. 只读检查GPU、UAT和环境

从本节起是将来的集群操作，交接制作时没有执行。

```bash
K=(kubectl --context lmas00-direct --request-timeout=30s)
"${K[@]}" get pods -A -o wide
"${K[@]}" -n vllm get deployment vllm -o json > "$WORK/uat-before.json"
"${K[@]}" -n vllm get pods -l app=vllm -o wide
"${K[@]}" -n swift get pvc swift-base swift-train-data swift-work
"${K[@]}" -n swift get secret swift-clearml -o name
curl --noproxy '*' --max-time 15 -fsS -o /dev/null -w '%{http_code}\n' https://vllm.10.140.17.125.nip.io/health
```

确认唯一GPU属于谁、UAT是否健康及实际窗口，再进入暂停步骤。无请求不等于已协调停服。通过UAT当前Pod执行nvidia-smi可以查看显存，但不要假设旧Pod名仍存在。

## 3. CPU Pod准备输入，不占GPU

```bash
"${K[@]}" create -f "$WORK/stage-pod.json"
"${K[@]}" -n swift wait --for=condition=Ready "pod/$RUN-stage" --timeout=180s
"${K[@]}" -n swift exec "$RUN-stage" -- python3 -c "from pathlib import Path; a=Path('/data/$RUN'); b=Path('/work/$RUN'); assert not a.exists() and not b.exists(); a.mkdir(); (a/'handoff').mkdir(); b.mkdir(); assert Path('/data/t008-v0114-20261021-145454/deps').is_dir()"
kubectl --context lmas00-direct --request-timeout=0 cp "$PKG/." "swift/$RUN-stage:/data/$RUN/handoff"
"${K[@]}" -n swift exec "$RUN-stage" -- python3 -c "from pathlib import Path; import os,zipfile; p=Path('/data/$RUN/handoff'); [(zipfile.ZipFile(p/'models'/v/'adapter.zip').extractall(p/'models'/v/'adapter')) for v in ['v0.1.13','v0.1.14']]; roots=[Path('/data/$RUN'),Path('/work/$RUN')]; [(os.chown(q,10001,10001)) for r in roots for q in [r,*r.rglob('*')] if not q.is_symlink()]"
"${K[@]}" -n swift exec "$RUN-stage" -- python3 "/data/$RUN/handoff/tools/verify_package.py"
```

模型ZIP已按MANIFEST校验；解压只用于后续LoRA推理。基座与镜像不在交接ZIP，使用环境说明中的现有资源。本包的CPU报告适用于固定数据/环境；若改数据、模板、插件或依赖，先另做原生CPU编码检查。旧run_cpu.py保留作历史证据，依赖原仓库父版本目录，不能在这个精简包内直接执行。

## 4. 在已协调窗口暂停UAT并申请GPU

先记录原副本数和当前模板。以下只缩副本，不修改模型挂载或启动参数。

```bash
ORIGINAL_REPLICAS=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["spec"]["replicas"])' "$WORK/uat-before.json")
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$WORK/pause-start-utc.txt"
"${K[@]}" -n vllm scale deployment/vllm --replicas=0
"${K[@]}" -n vllm wait --for=delete pod -l app=vllm --timeout=180s
"${K[@]}" create -f "$WORK/train-pod.json"
"${K[@]}" -n swift wait --for=condition=Ready "pod/$RUN-train" --timeout=180s
"${K[@]}" -n swift exec "$RUN-train" -- nvidia-smi
```

train-pod只运行sleep，不自动训练。若GPU不空闲，不杀其他作业；重新协调。任何后续失败都优先执行第8节恢复，再在本地分析。

## 5. 手工Smoke与Full

Smoke和Full输出目录不同；Full不继承Smoke。下面默认1 epoch；如已决定2 epoch，改Full的`--epochs 2`并记录，不同时改数据或其他参数。

```bash
"${K[@]}" -n swift exec "$RUN-train" -- python3 /handoff/tools/train.py --mode smoke --epochs 1 --output /manual-work/outputs/smoke --execute
"${K[@]}" -n swift exec "$RUN-train" -- python3 /handoff/tools/archive_run.py --run-output /manual-work/outputs/smoke --name "$RUN-smoke" --clearml
"${K[@]}" -n swift exec "$RUN-train" -- python3 /handoff/tools/train.py --mode full --epochs 1 --output /manual-work/outputs/full --execute
"${K[@]}" -n swift exec "$RUN-train" -- python3 /handoff/tools/archive_run.py --run-output /manual-work/outputs/full --name "$RUN-full" --clearml
```

如果在本地编辑了新配方，先将其复制到新运行的输出PVC，再在对应train.py命令中加`--config /manual-work/recipe.json`；这是容器路径，不是本机路径：

```bash
cp "$PKG/config/actual-v0.1.14-training.json" "$WORK/recipe.json"
# 在本地编辑recipe.json的full_argv，再复制；上面的默认训练命令仅作参考，实际选一套执行。
kubectl --context lmas00-direct --request-timeout=0 cp "$WORK/recipe.json" "swift/$RUN-stage:/work/$RUN/recipe.json"
```

另开终端可tail `/manual-work/outputs/full/train.log`。启动器保存manual-run.json和实际argv，Swift/TensorBoard保存日志；archive_run核对终态checkpoint、步数/epoch，打包Adapter，再批量上传ClearML并回读SHA。训练成功但上传失败，保留权重，只处理归档，不重新训练。没有--clearml时只做本地打包，记录为NOT_REQUESTED。

以最终trainer_state及Swift终态日志确认完成，不能仅看loss下降、文件夹存在或HTTP200。1 epoch预计83步；不因中途指标另挑checkpoint。若操作中断，不把部分模型写成已完成。

## 6. 使用相同协议进行中文开发对照

可以复用训练已退出的同一个GPU Pod，避免再加载一个并发服务。本节仍占GPU；不需要评测时直接跳第8节。本节新建120次开发对照，**不是免费只读查看旧结果**。

```bash
CKPT=$("${K[@]}" -n swift exec "$RUN-train" -- python3 -c "import json;print(json.load(open('/manual-work/outputs/full/archive-manifest.json'))['checkpoint'])")
"${K[@]}" -n swift exec "$RUN-train" -- python3 /handoff/tools/prepare_eval.py --candidate "$CKPT" --output /manual-work/evaluation --approved
"${K[@]}" -n swift exec "$RUN-train" -- python3 /manual-work/evaluation/run.py
"${K[@]}" -n swift exec "$RUN-train" -- python3 /manual-work/evaluation/summarize.py
```

prepare_eval只准备文件，--approved由实际操作者填入这次评测决定，不继承旧window授权。runner会启动临时vLLM并在结束/异常时停止自身进程。三模型为原版/v0.1.14/手工新候选，共120次；固定17场景及seeds，NT预算2048、Thinking4096，System r1、聊天模板、Schema一致。两份LoRA均按rank8配置；若改rank，需同时调整runner的max-lora-rank并记录，不能直接套旧设置。

JSON Schema放在每次JSON请求的response_format，不放进全局System；expected_for_scoring_only只评分，不进入请求。System与模板由脚本按字节核验，服务端实际prompt token也核验。失败结果原样保留，不重复采样挑答案。总结脚本只统计JSON、空正文、截断等机械项；事实/业务回答人工看全文，不能自动当通过。B13-06范围有歧义，不用于二元选优。

要复现旧原版/v0.1.13/v0.1.14矩阵，应复制materials到新可写评测目录，保持原模型名，将spec.json两条adapter.path改为`/handoff/models/v0.1.13/adapter`和`/handoff/models/v0.1.14/adapter`，重新填写当前authorization后执行；不要在历史evidence目录运行。

## 7. 输出回收与判读

```bash
kubectl --context lmas00-direct --request-timeout=0 cp "swift/$RUN-stage:/work/$RUN/." "$WORK/results"
```

保留manual-run.json、train.log、完整checkpoints、archive-manifest、adapter.zip、TensorBoard、评测spec/题目/System/模板/原始results及人工意见。先回收关键权重与日志，GPU无作业后立即恢复UAT；详细阅读与Git归档放在恢复后。

选型先看新增事实/边界错误是否减少，再看身份和普通任务；不能用名称命中替代整段正确，也不能把Schema收益归因于SFT。最新已知失败见[问题问答](evidence/t008-v0114-20261021-145454/evaluation/ISSUES.md)。这些题已公开用于开发，不能作独立留出验收。

## 8. 恢复与核验UAT（正常结束和失败均执行）

```bash
"${K[@]}" -n swift delete pod "$RUN-train" "$RUN-eval" --ignore-not-found --wait=true --timeout=180s
"${K[@]}" -n vllm get deployment vllm -o json > "$WORK/uat-before-restore.json"
python3 -c 'import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); assert a["spec"]["template"]==b["spec"]["template"], "Concurrent UAT template change; inspect before restoring"' "$WORK/uat-before.json" "$WORK/uat-before-restore.json"
"${K[@]}" -n vllm scale deployment/vllm --replicas="$ORIGINAL_REPLICAS"
"${K[@]}" -n vllm rollout status deployment/vllm --timeout=600s
"${K[@]}" -n vllm get deployment vllm -o json > "$WORK/uat-after.json"
python3 -c 'import json,sys; a=json.load(open(sys.argv[1])); b=json.load(open(sys.argv[2])); assert a["spec"]==b["spec"]; assert b["status"].get("readyReplicas",0)==a["spec"]["replicas"]' "$WORK/uat-before.json" "$WORK/uat-after.json"
UAT_POD=$("${K[@]}" -n vllm get pods -l app=vllm -o jsonpath='{.items[0].metadata.name}')
"${K[@]}" -n vllm exec "$UAT_POD" -- python3 -c "import urllib.request;print(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=8).status)"
curl --noproxy '*' --max-time 15 -fsS -o /dev/null -w '%{http_code}\n' https://vllm.10.140.17.125.nip.io/health
date -u '+%Y-%m-%dT%H:%M:%SZ' > "$WORK/restored-utc.txt"
"${K[@]}" -n swift delete pod "$RUN-stage" --wait=true --timeout=90s
```

默认原副本数为1，恢复后应1/1，内外200，完整spec相等。未核验成功就不能写“恢复完成”。发现并发配置变化时先核查，勿把旧快照整份apply覆盖他人改动。历史控制面/worker时间约差8小时，耗时采用本地时区感知记录，不使用kubectl AGE。

恢复后在源仓库另建新运行目录，登记实际参数、哈希、ClearML ID、完整结果与恢复证据，再提交本地Git。Adapter等二进制单独内容寻址保存，Git记录哈希与定位。不覆盖本包与旧版本，不因训练完成自动部署候选。

服务配置的分层与请求示例见[SERVING.md](SERVING.md)；将选定候选发布到服务及回退见[PUBLISH.md](PUBLISH.md)。这两步不在训练完成后自动执行。
