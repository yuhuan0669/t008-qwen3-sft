# Qwen3-8B自我认知SFT实施方案

**版本：v1.2（集中执行修复版）｜2026-10-18｜阶段：CPU代码与模拟测试完成；真实数据准入、GPU训练和ClearML实测均未执行**  
**修订原则：** 保留v1.1的官方数据加载＋LoRA主路线；集中消除版本分叉、2600行与审批清洗死锁、无验证集CLI不一致、占位符漏检、超长静默删除、A/B/C/D评测对账弱点。旧v1.0、v1.1、v1.1.1均归档不覆盖。

## 0. 执行结论（先读）

此次只做Qwen3-8B**身份认知LoRA**的首次真实实验，产物是独立候选Adapter，不代表完成能碳业务能力优化、正式备案训练或公网发布。

- **直接使用两个官方数据集**：`swift/Qwen3-SFT-Mixin#2000`＋`swift/self-cognition:qwen3#600`。`#600`是训练曝光/采样数量，**不是600条不同原始身份题**；具体底库条数、重复分布以读取实物为准。
- **沿用官方主要参数**：LoRA、BF16、1 Epoch、lr 1e-4、rank8/alpha32、all-linear、batch1/accum16、2048 tokens、warmup 0.05；**Full按epoch保存最终checkpoint，Smoke每3步保存**（与官方每50步保存明确不同）。训练硬件为现有单RTX4090 24GB。官方“约22GB/30分钟”不是本集群实测保证；完整A/B/C/D及Thinking评测须单独计入GPU占用窗口。
- **ms-swift自己读数据**：先用ms-swift `load_dataset`完成下载/身份占位符替换/`#N`采样，再将它实际输出的训练记录保存为不可变本地快照；训练时从快照读取，避免官方数据更新后悄然变更。本版**取消v1.0自编的重复扩采、额外Mixin筛选及从重复身份集切验证集**。
- **以独立测试为验收依据**：训练前固化独立身份题和通用/Thinking回归题，不复制官方身份模板；不把训练时重复样本随机切出的验证集作为独立效果证据。
- **真实记录ClearML**：每次Smoke/正式训练创建独立Task，绑定输入manifest、真实基础权重文件hash、Git Commit、容器镜像digest、运行参数与审批引用；正式训练成功后打包Adapter、计算hash并建立ClearML Output Model；独立评测完成后另建Evaluation Task挂接结果摘要（不传逐题原文）。
- **终态**：恢复既有vLLM服务，Identity Adapter保持Candidate；仅在后续另行审批后才考虑推广到受控开发服务。不能绕过T-008原有发布门。

## 1. 依据及边界

官方教程：https://github.com/QwenLM/Qwen3/blob/main/docs/source/training/ms_swift.md  
官方身份数据：https://modelscope.cn/datasets/swift/self-cognition  
官方通用数据：https://modelscope.cn/datasets/swift/Qwen3-SFT-Mixin  
ms-swift可复用loader源码：https://github.com/modelscope/ms-swift/blob/main/swift/dataset/loader.py  
Thinking保护的**另一条**示例：https://github.com/modelscope/ms-swift/blob/main/examples/train/think_model/qwen3_demo1.sh  
本项目T-008任务单：https://docs.google.com/document/d/1BQLRq1pQyu7Be60_hxmeVsaFDBIMuul2-EB3aDAe_Ho/edit  
T-008评审记录：https://docs.google.com/document/d/1xhUjGTfRnqQ8eSQKLEUihSScmdIoJPPSLrXoJ1_-7HM/edit

**尚未验证：** 当前实际ms-swift训练镜像CLI（包括`--eval_strategy`/`--evaluation_strategy`、`--data_seed`、`--save_strategy`）、两份官方数据真实bytes/revision和适用许可、Qwen3实际模板训练样本长度、训练显存/时长、ClearML SDK与Model回读。v1.2只有合成数据测试（详见`tests/test_contract.py`）；未下载官方源、未启动真实GPU、未访问项目K8s/ClearML。不得将本地模拟测试冒称现场验收。

**T-011/T-013边界：** 本次两个公开来源不自动并入T-013既定4＋10来源，也不覆盖T-011原审核数据。作为单独身份技术实验，先核准来源与用途；是否在正式备案训练记录中使用，由实际训练与主管口径分别如实登记。

## 2. 与官方原始训练命令的逐项对照

| 配置 | 官方示例 | v1.2工程适配 | 原因 |
|---|---|---|---|
| 模型、数据来源、2000＋600 | Qwen3-8B，两个官方数据集 | **相同** | 沿用官方 |
| LoRA、BF16、rank8、alpha32、all-linear | 同 | **相同** | 沿用官方 |
| lr1e-4、1 Epoch、batch1、累积16、max_length2048 | 同 | **相同** | 沿用官方 |
| warmup0.05、logging5、workers4、save_limit2 | 适用 | **保留** | 维持主超参数 |
| `save_steps 50`、`eval_steps 50` | 官方示例 | **不同**：Full `save_strategy epoch`，Smoke `steps/3`；明确 `eval_strategy no`，不传 `eval_steps` | 冻结末轮权重、避免空验证集歧义 |
| `data_seed` | 示例未显式设置 | **显式42，必须在现场CLI中支持** | 数据打乱可追溯 |
| `model_name/model_author` | Swift在线替换 | Swift预处理时替换，已替换快照用于正式训练 | 保留最终真实训练字节 |
| `#N`采样 | Swift完成 | **仍由Swift完成**；不再自行重复采样 | 减少自研分歧 |
| 数据输入 | Swift从官方在线数据源读取 | Swift先读取，生成并校验冻结JSONL；Trainer读本地副本 | 版本可追溯 |
| train/val | 示例未显式指定分组/隔离规则 | 显式`split_dataset_ratio=0`；独立测试集另外固定 | 避免重复身份样本造成验证集泄漏 |
| 随机种子 | 依框架默认 | 显式seed42 | 可重做采样 |
| GPU保护/版本登记 | 示例不包含工程部署 | 增加授权、Smoke、ClearML、完整hash及恢复 | 本项目必要工程适配 |
| 模板/Thinking | 官方qwen3身份子集 | **主路线仍为qwen3**；不擅自叠加`ignore_empty_think` | 避免混用不同示例 |

**注意：** 与官方训练超参数高度一致，不等于数据字节和运行环境必然完全相同。预处理框架版本、下载内容、`split_dataset_ratio`、样本顺序和运行镜像都必须记录。v1.2是官方示例的受控工程适配，不冒称官方已验收本集群。

## 3. 身份规格与数据准入

### 3.1 四个必须确认的身份字段

把以下内容放入`identity-spec.json`，**由项目确认，不接受“待填写”直接训练**：

```json
{
  "name_zh": "章鱼能碳垂直大模型",
  "name_en": "Octacarbon LLM",
  "author_zh": "能碳章鱼（湖北）人工智能科技有限公司",
  "author_en": "Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.",
  "base_model": "Qwen/Qwen3-8B"
}
```

**状态提示：** 以上是当前交付文档所载拟用身份字段，不代表已经完成主体授权或身份核定。执行Agent在准备训练快照前，仍须依据真实主体证明与有效批准记录逐项核验；如不符，先更正规格并留痕，不能直接训练。

替换身份名称、训练/定制主体，不等于宣称该主体从零研发了Qwen3-8B。**旧版JSON中的`note`已去除**：脚本不把`note`送给ms-swift，其内容本来不能产生训练效果。审核说明仍保留：“基础模型研发来源不等于本产品定制方；尚未接入的功能不声明已具备”。后者由审核题与运行时System Prompt/后端权限控制，不能声称单纯训练配置已实现。产品应用名“章鱼能碳AI助手”不替换模型正式名称“章鱼能碳垂直大模型”。英文主体拼写仍须根据真实法人材料核验。

### 3.2 两份来源的最小审核

Agent对实际数据文件/数据卡做定向核验，记录来源、子集、实际revision或无法确认的事实、下载文件hash、许可证/限制及本次研发使用结论。检查已经替换后的全部不同身份模板，尤其“谁开发你”“基础模型是谁”这类可能混淆定制方与基础模型研发方的语义；有严重错误则**暂停本轮数据准入**，提出最小处理方案，不静默篡改后还声称直接官方复现。

不要把108条当成已经证实的`qwen3`子集条数，也不要将600曝光数当成600条独立原创问题。此次不计算成T-011已审批的业务语料数量。

### 3.3 本次一次性许可/窗口记录

训练容器中提供一个真实完成的`approval.json`，由主Agent归档有效确认引用，参考格式：

```json
{
  "decision_ref": "实际审批/确认记录链接或编号",
  "identity_verified": true,
  "experiment_approved": true,
  "gpu_window_approved": true,
  "sources_approved": {
    "swift/Qwen3-SFT-Mixin": true,
    "swift/self-cognition:qwen3": true
  },
  "source_snapshot_ref": "真实来源许可、数据卡和版本核对记录",
  "approved_rows": 2600,
  "approved_data_sha256": "真实train.jsonl的64位SHA-256",
  "approved_snapshot_manifest_sha256": "真实manifest.json的64位SHA-256",
  "preflight_model_files_sha256": "真实base_files排序清单JSON的SHA-256",
  "preflight_report_sha256": "真实preflight_report.json的SHA-256"
}
```

**这只是结构示例，不能把其中`true`当成项目已经审批，SHA占位文字也不可用于训练。** 若采用排除异常样本的衍生快照，还要在同一独立批准记录中填写`data_change_approved: true`、实际`data_change_ref`和`parent_snapshot_dir`。训练脚本校验批准行数、训练数据SHA、Manifest SHA、长度预检SHA及源快照链路；但JSON校验无法代替对批准人真实性和权限的现场核查。 已有开发环境的普通操作不重复申请；真实停止跨项目vLLM服务须取得**本次**影响窗口许可，不能沿用T-008上一次窗口。未批准可继续CPU数据检查，不能停止服务或启动GPU。

## 4. 官方数据读取与快照

### 4.1 使用提供的`prepare_official.py`

在有权读取ModelScope的开发容器中：

```bash
export WORK='/实际可写PVC/identity-exp001'
mkdir -p "$WORK"
# 先由Agent核对两个官方数据源及identity-spec.json的真实内容和审核状态。
python3 prepare_official.py \
  --spec "$WORK/identity-spec.json" \
  --out "$WORK/official-snapshot-v1" --seed 42
```

脚本调用**真实ms-swift `load_dataset`**，一次输入这两个规格：

```text
swift/Qwen3-SFT-Mixin#2000
swift/self-cognition:qwen3#600
```

并传`model_name/model_author`和`split_dataset_ratio=0`。它不额外重复、随机划分、筛掉长样本或生成伪测试答案。输出：`train.jsonl`（2600条期望训练记录）、`manifest.json`、`identity_spec.json`，包含两个真实文件hash、总唯一内容条数和重复分布。若真实加载不等于2600，则停止，检查官方loader版本或数据变化。

**快照与许可独立：** `PENDING_SOURCE_REVIEW`状态仅表明文件固定，不代表法律和业务准入已通过。衍生快照使用`PENDING_DERIVATIVE_APPROVAL`，同样不代表已审批。Agent保存实际原始下载/cache或对应不可变repo版本及hash；若官方无法提供确切revision，明确记录“版本未知＋本地真实文件hash”，不得伪造上游commit。

训练前由`preflight_data.py`在CPU上使用本地Qwen3 Tokenizer和Chat Template对每一条样本**无截断**计数，并输出`preflight_report.json`（含超长行索引，不含正文）。这项检查只是必要预检，**不是ms-swift训练实际编码/标签掩码的替代证明**。执行Agent必须在固定实际ms-swift镜像中检查真实模板/预处理后的样本数、最长长度、loss mask，并将经审查的`swift-template-evidence.json`交给预检脚本二次绑定；未核对时报告的`ms_swift_template_verified=false`，GPU门禁拒绝运行。任何超过2048或静默丢弃样本都不得放行。

如果确需清除冲突、非法或超长样本，保留原始2600行快照，先对需删除的原始**零基行号**及原因形成`exclusions.json`清单，再用`derive_snapshot.py`生成**排除式新版本**，继承原顺序与原始数据字节，输出新Manifest及哈希。修订样本正文不属于此工具支持范围，需要另一份经审批的新数据变更方案，不能伪称官方源原样复现。只有独立`approval.json`同时核准实际行数、文件SHA、变更引用及父快照，才可尝试训练。

#### 4.1.1 v1.2 CPU门禁示例（不能跳过真实ms-swift模板核验）

```bash
python3 prepare_official.py --spec "$WORK/identity-spec.json" \
  --out "$WORK/official-snapshot-v1.2" --seed 42
# 如有审核通过的排除清单（若无则沿用官方原始快照）：
python3 derive_snapshot.py --parent "$WORK/official-snapshot-v1.2" \
  --exclusions "$WORK/exclusions-reviewed.json" --out "$WORK/approved-snapshot-v1.2"
# DATA_DIR取实际选用的原始或经过审批的衍生快照
export DATA_DIR="$WORK/official-snapshot-v1.2"
# 先做不依赖GPU的Tokenizer预检；未给模板核验证据会标记未验证，GPU不能启动
python3 preflight_data.py --dataset "$DATA_DIR" --model "$BASE_MODEL"
# 在实际ms-swift镜像中核对与训练一致的Chat Template/标签掩码/真实保留行数，
# 将实际核验信息录入swift-template-evidence.json（参考README中的字段示例），
# 然后删除旧的未认证preflight_report.json，以新路径重新生成已核验报告：
python3 preflight_data.py --dataset "$DATA_DIR" --model "$BASE_MODEL" \
  --out "$DATA_DIR/preflight_report_verified.json" \
  --swift-template-evidence "$WORK/swift-template-evidence.json"
mv "$DATA_DIR/preflight_report_verified.json" "$DATA_DIR/preflight_report.json"
# 将已核验报告作为唯一最终版本部署到 DATA_DIR/preflight_report.json，
# 并由独立批准人在approval.json中绑定其SHA-256（文件与目录权限须受控）。
```

**注意：** CPU预检第一次生成的是待核验报告，不能冒充最终报告。正式批准字段`approved_snapshot_manifest_sha256`、`preflight_report_sha256`等均须按最终字节重新计算，不提供自动填入`true`的捷径。

## 4.2 训练数据与独立评测分开

本轮不从重复的身份训练记录中自动切Validation。独立测试题在训练前固定，建议身份80题＋通用能力100题，另有Thinking专项题。独立题应避开官方训练模板的同义和语义重复；评分依据另存受控文件。

A/B/C/D四组：A原始模型、B原始＋身份System Prompt、C原始＋LoRA、D原始＋LoRA＋同一Prompt。使用相同base、Tokenizer、Thinking配置和**同一评测引擎（当前附件为transformers+PEFT串行生成，并非vLLM）**。vLLM真实业务效果/恢复另测。**为了绑定同一训练Run的明确版本，四组正式对照可在训练完成后统一评估，但全部题目和评分规范须先冻结**，原始base全程不可变。

## 5. 运行环境与训练步骤

### 5.1 复用T-008但不继承Risk31模型

复用现有`lmas00`、RTX4090 24GB、Swift/K8s、ClearML、NFS及候选发布/恢复机制。T-008已通过的研发隔离与发布门不重复建设；Risk31为Qwen3-0.6B分类模型，本次是Qwen3-8B causal LM LoRA，**不复用Risk31分类头、阈值或其发布批准**。

实际运行前检查：K8s context、基础模型文件只读、CUDA/BF16、当前GPU占用、真实ms-swift CLI选项、ClearML SDK认证与Files上传/回读、剩余空间和原vLLM Deployment回滚点。镜像需要调整时做独立可重现镜像，不现场改正在运行的vLLM容器。

### 5.2 GPU训练及评测授权窗口的顺序

1. CPU预先完成来源/身份/数据审核、原始及必要衍生快照、Tokenizer长度预检和实际ms-swift模板证据、独立测试题冻结，确认Git Commit和实际训练容器digest；不占GPU。
2. 取得本次受影响vLLM服务的停启授权；保存原Deployment镜像、Replica、路由、配置和Healthy状态，有序停止共享GPU服务，检查Pod退出和显存释放。
3. Smoke用相同数据快照，`max_steps=3`；失败时保存证据，不复用Smoke Adapter。
4. 正式训练**新进程从原始基础模型初始化**，1 Epoch。即使Smoke成功，也不继承它的梯度。
5. 训练完核实际Adapter与ClearML Model；**重新估算并明确授权评测GPU窗口**（四组＋Thinking可能远超训练时间）；执行A/B/C/D及通用/Thinking回归，做独立Review并登记汇总。
6. 恢复原vLLM Deployment/路由和GPU服务，检查`Ready`、`/health`及一条真实模型生成；新的身份Adapter保持Candidate，不自动发布。

任何时候发生显存不足或重载失败，保存运行日志、恢复原服务，再确定最小修复方案。BF16 LoRA作为第一轮路线；若OOM，先排查残留负载、梯度检查点，必要时另行记录QLoRA变体的新run，不谎称与原官方配置相同。

### 5.3 训练入口（`train_identity.sh`＋`run_identity.py`）

入口**强制**读取实际批准文件、源/衍生数据哈希、行数、ms-swift预检报告以及完整模型文件SHA；无明确窗口授权或预检未闭环则退出，不会自行进行K8s停服。真实`approval.json`由有权审批者提供并独立存放，不能由脚本把示例字段直接置为`true`。准备下列环境变量：

```bash
export BASE_MODEL='/实际只读PVC/Qwen3-8B'
export DATA_DIR="$WORK/official-snapshot-v1.2"
export APPROVAL_FILE="$WORK/approval.json"
export RUN_AUTHORIZED=yes
export GPU_WINDOW_APPROVED=yes
export SOURCE_GIT_COMMIT='<实际训练代码完整commit>'
export TRAIN_IMAGE_DIGEST='sha256:<真实容器镜像digest>'
export CUDA_VISIBLE_DEVICES=0

export OUT_DIR="$WORK/smoke-001"
bash train_identity.sh smoke

# Smoke结束/检查通过后，正式训练使用全新的输出目录。
export OUT_DIR="$WORK/full-001"
bash train_identity.sh full
```

`run_identity.py`完成：验证批准/数据hash、扫描基础模型文件并计算真实SHA-256、核当前包版本及CLI（`--tuner_type`或`--train_type`二者之一）、使用官方LoRA参数启动Swift、记录真实标准输出和退出码；**用ClearML SDK创建Task**，训练成功后找**训练结束时的最终Checkpoint**（Full强制按Epoch保存），核对Trainer实际步数、打包Adapter并计算hash，**注册Output Model并下载回读对比hash**。所有Task和Model ID写进`run_manifest.json`。命令行必须现场支持`--eval_strategy no`（或对应`--evaluation_strategy no`）、`--save_strategy`、`--data_seed 42`，否则停止并定向适配固定镜像；不得盲删不支持参数继续训练。

Full与Smoke是两个不同ClearML Task。Full输出包含`adapter-candidate.zip`及原始Checkpoint；存储在受控可写实验卷，**不会自动移动到released**。不能仅凭Console显示训练完成，必须下载回读ClearML中登记的Adapter，与本地包SHA-256一致；回读失败则不视为闭环。Full使用`--save_strategy epoch`确保最终1 Epoch权重被保存（这是相对官方按50步保存的明确工程差异）。

**实际命令差异应留痕：** `--split_dataset_ratio 0`显式禁止从重复训练数据再划验证集；显式seed、Hub禁用、CUDA保护、Checkpoint保存和ClearML登记属于工程配置。本轮**不传`--eval_steps 50`，显式`--eval_strategy no`**（现场CLI兼容名称），因为没有训练派生验证集；独立评估由后面的A/B/C/D完成。Full使用`--save_strategy epoch`，Smoke使用`--save_strategy steps --save_steps 3`，二者均不是官方原样`save_steps 50`。数据打乱种子显式为`--data_seed 42`。如需修改模板或参数，另记镜像、代码和运行版本。

### 5.4 推理评测与记录

在Adapter已生成、训练Task/Model成功登记后，使用`eval_identity.py`运行A/B/C/D。评测前**逐文件重算基础模型SHA-256并与训练Manifest一致**，Adapter路径及其文件SHA也必须匹配。非Thinking出现`<think>`或`</think>`则标记`unexpected_think_tag`，异常生成不可当成合格最终回答。示例：

```bash
export RUN_MANIFEST="$WORK/full-001/run_manifest.json"
export ADAPTER='/实际full-001/checkpoints/运行子目录/checkpoint-实际步数'
export CASES="$WORK/eval/identity-test.jsonl"

python3 eval_identity.py --model "$BASE_MODEL" \
  --run-manifest "$RUN_MANIFEST" --cases "$CASES" --mode nonthinking \
  --output "$WORK/eval/A-identity.jsonl"

python3 eval_identity.py --model "$BASE_MODEL" --adapter "$ADAPTER" \
  --run-manifest "$RUN_MANIFEST" --cases "$CASES" --mode nonthinking \
  --output "$WORK/eval/C-identity.jsonl"
```

B/D另指定同一个`--system-file "$WORK/identity-system.txt"`。Thinking模式单独运行`--mode thinking`，保持Qwen3官方推荐采样配置（Thinking 0.6/top-p0.95/top-k20；非Thinking 0.7/top-p0.8/top-k20），不要用贪心推理假装有可比的Thinking测评。

每次评测生成原始回答JSONL（仅保留受控存储）和`.meta.json`（测试集hash、System Prompt hash、生成参数、输出hash、训练Task和Adapter版本）。`eval_identity.py`目前使用单卡`transformers+peft`逐条串行真实生成，**不是vLLM评测脚本**；具体吞吐必须在开发环境实测并独立安排GPU资源，不能引用官方训练30分钟作为整套评估工期。脚本只生成输出，**不会伪造自动评分或评价结论**。

独立Reviewer根据预先冻结的评分标准输出简明`reviewed-summary.json`（不含逐条测试题/回答），需要真实`reviewer_ref`和`conclusion`。汇总与每组meta通过：

```bash
python3 register_evaluation.py \
  --run-manifest "$RUN_MANIFEST" \
  --reviewed-summary "$WORK/eval/reviewed-summary.json" \
  --eval-metadata "$WORK/eval/"*.meta.json
```

该脚本在上传前要求每个案例集具备完整A/B/C/D四条件、相同`(cases SHA, mode, seed, max_new_tokens, temperature, top_p, top_k, base model SHA, inference engine)`，且B/D的**System Prompt SHA必须逐字节一致**。随后才创建Evaluation Task，写入对应训练Task ID、Output Model ID和各测试输入/输出hash；上传的仅是Reviewer汇总及digest索引，不上传原始试题与逐条生成内容。

**内部试验判据：** Identity C组建议≥95%且没有严重虚构研发主体/权限；A/C通用能力差异与B/D服务效果并列报告；下降3个百分点触发复核；Thinking需看解题正确率、正常结束、是否出现明显行为退化。阈值是项目首轮内部目标，不是监管标准。不得为了通过而反复使用同一冻结测试集挑Checkpoint。

## 6. 版本留痕与发布/回滚

**原始基础模型 → 本地数据快照（源规格＋sha）→ 训练镜像digest＋Git Commit＋参数 → ClearML Task → Adapter package SHA＋Output Model ID → 独立评测meta/汇总＋Evaluation Task → 另行发布决定。**

| 节点 | 记录/文件 | 由谁生成 |
|---|---|---|
| 官方训练来源与身份 | `official-snapshot-v1/manifest.json`、`train.jsonl`、`identity_spec.json` | `prepare_official.py` |
| 数据准入与实际GPU授权 | `approval.json`引用真实有效的审批/原件 | 授权人/执行Agent归档，非脚本伪造 |
| 基础模型 | 每个基础模型文件sha、完整revision（如能证实） | `run_identity.py`＋来源证据 |
| Git/镜像/参数/真实GPU | `full-001/run_manifest.json`、`train.log`、Checkpoint | `run_identity.py` |
| 实验与权重 | ClearML Task ID、Output Model ID、`adapter-candidate.zip`及SHA | `run_identity.py`＋ClearML |
| 独立测试 | `*.jsonl`（受控）、`*.meta.json`、Reviewer汇总 | `eval_identity.py`＋Reviewer |
| 评估关联 | ClearML Evaluation Task及digest索引 | `register_evaluation.py` |
| 原服务恢复 | K8s部署前后记录、health及一条生成结果 | 主Agent现场核对 |
| 发布或不发布 | PM明确结论；默认Candidate，不改released | PM/有权发布者 |

数据文件或身份规格改变即新快照；学习率、量化或镜像改变即新Training Task；生成文件hash改变即新Adapter版本；System Prompt或部署配置改变即新服务版本。ClearML `completed`不等于模型适合业务，也不代表备案验收完成。

**范围要求：** 当前ClearML仅允许上传授权的**版本元数据、模型Adapter及摘要**。原训练正文、逐题预测、个人信息、凭据和完整测试题不自动上传社区实例。若权限/存储不满足，先留本地不可变产物，不能假写ClearML ID；修复实际接入再补登记并完成回读，正式闭环之前保持未完成。

## 7. 一次性验收与交付物

由主Agent提供以下四个包（可合并打一个文件，无需再造多份相似制度文件）：

1. **数据包**：身份确认、来源许可与真实数据快照、重复统计与hash；不必把2600条全文塞进Google Doc。
2. **训练包**：实际命令、commit、镜像digest、GPU记录、训练日志、Checkpoint、ClearML Task ID及错误处理记录。
3. **模型包**：Adapter文件hash、可读取/下载的模型文件、Output Model ID和基础模型绑定。
4. **评测恢复包**：A/B/C/D及通用/Thinking实际比较、Reviewer结论、Evaluation Task ID、原vLLM服务恢复实测、Candidate/未发布状态。

**交付失败示例：** 只拿到模型权重却没有关联数据hash；只创建ClearML占位模型；拿训练loss当成身份合格；将已重复官方身份题作为独立Test；没有通过本次GPU恢复；未经批准替换线上模型。出现这些情况只能算未闭环。

### 执行角色与本轮范围

一名执行Agent可完整推进CPU准备、训练与证据登记；评分由未参与样本生产/训练的Review角色完成。本次正常开发操作一次授权即可；启动影响现有推理服务的GPU切换须取得有效窗口确认。项目负责人不需要逐条审300～600条模板，不因小问题反复开新任务。

当前文件仅为**可执行方案与代码**，不表示官方数据已下载、ClearML Task已创建、模型已经训练或现有服务已操作。执行时必须将占位值替换为现场事实。

---

## 8. v1.0→v1.1历史实质变更与审计说明

- 数据：取消`fetch`＋`freeze`两阶段的人工重采样与验证划分；改官方loader单次输出→冻结，统一`prepare_official.py --spec ... --out ...`。
- 训练：新增`run_identity.py`，通过真实ClearML SDK创建Task、Output Model、Adapter ZIP与完整文件hash。`train_identity.sh`保留简洁入口。
- 评测：`eval_identity.py`新增`--run-manifest`与每次调用的digest元数据；新`register_evaluation.py`仅登记汇总而非逐条题目。
- 模型选择：仍只选1 Epoch**结束时**Checkpoint；不按独立测试成绩反复挑选。
- 工程验收：要求真实ClearML OutputModel文件回读；不再把“计划接ClearML”写成“已经自动接入”。
- 旧v1.0及其附件原样保留，可按真实变化追溯。本版附件未在现有ms-swift/ClearML训练镜像上联调，GPU验证待Agent执行。


## 9. v1.1.1历史交付校核记录（归档事实）

- 针对先前Drive在线同名文档与ZIP内文档的差异，以**已核验的最新身份字段**修正本交付文档，并恢复可直接解析的JSON代码块。
- 以实际`run_identity.py`为准：正式运行应强制保存结束时有效Checkpoint、在ClearML登记Candidate Output Model，并调用`get_local_copy(extract_archive=False)`读回比对本地Adapter压缩包SHA-256；如现场SDK版本不兼容应作为阻断和最小修复记录，不能将读回失败判为验收通过。
- 随包新增`identity-spec.example.json`只是候选配置，真实训练前仍需确认身份字段、许可及本次GPU窗口审批。脚本版本、数据源和训练超参数不因本次文字校核而改变。
- 本轮仅对附件执行本地语法编译、JSON解析与ZIP完整性检查，**未运行训练/推理、未访问GPU或ClearML线上服务**。


## 10. v1.2集中修复及静态测试记录

**修补口径（相对于v1.1.1）：**

1. **权威正文、身份四字段**：统一`章鱼能碳垂直大模型 / Octacarbon LLM`和定制主体；取消无训练效力的`note`配置字段，保留其语义于身份审核指南，不虚构模型已掌握能力边界。
2. **2600样本与审批清洗兼容**：`prepare_official.py`保留完整原始2600，`derive_snapshot.py`只允许有理由的原行排除；`run_identity.py`不仅对照`approved_rows`，还验证批准记录的训练SHA、Manifest SHA、原始父快照SHA与排除清单、实际字节及顺序一致。不可用篡改Manifest自放行。
3. **训练期评估与Checkpoint**：无验证集时显式`eval_strategy no`，Full末轮按epoch保存，Smoke保留第3步，带`data_seed 42`；与官方示例不同的参数统一列明，并要求真实CLI读回。
4. **残留占位符**：通用正则检测包括官方资料笔误`{{AUTHOER}}`在内的未替换大写/下划线占位符；发现即在写文件前拒绝。
5. **长度与静默丢行**：`preflight_data.py`无截断预检且要求真实ms-swift模板处理证据。超长/未经核验则门禁失败；对于确实发现的异常，通过新数据版本/批准文件处理，不能直接静默删除后声称原始复现。
6. **评测模型与Thinking异常**：`eval_identity.py`重算基础模型真实全部文件SHA，并检查Adapter文件；非Thinking出现思考标记时单独标志、剥离或空答案，不能默认为正常。
7. **A/B/C/D对照严格性**：`register_evaluation.py`对B/D System Prompt SHA做精确相等检查，并对案例、参数、引擎和base模型哈希统一分组；有缺组/重复组即拒绝登记。

**测试证据：** `tests/test_contract.py`提供17项CPU-only合成数据单元测试，覆盖原始/排除快照审批、篡改与父源追溯、未验证长度门禁、Tokenizer超长、漏网占位符、基础权重篡改、Thinking异常、B/D Prompt和生成参数一致性。命令：`python3 -m unittest discover -s tests -v`；另用`python3 -m py_compile *.py`、`bash -n train_identity.sh`。在本地执行通过，不代表完成真实官方数据或GPU/ClearML现场测试。

**执行进度/门禁：**
- [x] v1.2脚本与方案同步、静态/合成数据测试、ZIP完整性及文件SHA清单（以最终交付校验为准）。
- [ ] 官方数据/许可/来源revision真实核查、下载与冻结（CPU）。
- [ ] 身份字段和定制主体由真实业务/审批材料复核（CPU）。
- [ ] 实际ms-swift镜像CLI与训练模板预检、数据审批SHA/行数及完整证据（CPU）。
- [ ] 授权GPU窗口、Smoke、Full、ClearML回读、独立评测与恢复原服务。
- [ ] 发布（不在本轮范围，默认Candidate）。

**止步原则：** 模拟数据中的`true`或示例哈希不能视为审批、训练或生产能力实证。完整GPU验证必须由具有模型卷、训练容器、K8s和ClearML访问权的执行Agent在已授权环境运行；任何失败记录为未闭环，而不是直接把候选Adapter发布到`released`。
