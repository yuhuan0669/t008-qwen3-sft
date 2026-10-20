"""Build current reports and a faithful decision record, never train or approve."""
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT.parent / 't008_qwen3_sft_v12_cpu'


def main():
    live = json.loads((ROOT / 'evidence/live_readonly_check.json').read_text())
    inputs = json.loads((ROOT / 'evidence/frozen_inputs_recheck.json').read_text())
    decision = json.loads((ROOT / 'evidence/owner_recipe_decision.json').read_text())
    tutorial = (OLD / 'evidence/source_identity/qwen_tutorial_pinned.md').read_text()
    reference = next(code for code in re.findall(r'```bash\n([\s\S]*?)```', tutorial)
                     if 'swift/Qwen3-SFT-Mixin#2000' in code)
    (ROOT / 'official_command.reference.txt').write_text('# Official reference only; NOT EXECUTED; no GPU authorization.\n' + reference)
    intended = {'schema': 't008-official2048-intended-parameters-v1',
        'status': 'DOCUMENTED_NOT_LAUNCH_READY', 'executable': False,
        'model': 'Qwen/Qwen3-8B', 'model_name': decision['selection']['model_name'],
        'model_author': decision['selection']['model_author'],
        'dataset': decision['selection']['source_specs'],
        'train_type_reference': 'lora', 'tuner_type_actual_4_4_2': 'lora',
        'torch_dtype': 'bfloat16', 'num_train_epochs': 1,
        'per_device_train_batch_size': 1, 'per_device_eval_batch_size': 1,
        'learning_rate': 1e-4, 'lora_rank': 8, 'lora_alpha': 32,
        'target_modules': ['all-linear'], 'gradient_accumulation_steps': 16,
        'eval_steps': 50, 'save_steps': 50, 'save_strategy_intended': 'steps',
        'save_total_limit': 2, 'logging_steps': 5, 'max_length': 2048,
        'warmup_ratio': 0.05, 'dataloader_num_workers': 4,
        'native_truncation_strategy': 'delete', 'data_seed_recorded': 42,
        'identity_rewrite': False, 'extra_semantic_filter': False,
        'actual_4_4_2_default_split_dataset_ratio': 0,
        'evaluation_note': 'No val_dataset and split ratio 0 => eval_strategy=no; eval_steps alone does not create validation data.',
        'remaining_cpu_parser_check': 'Final exact argv in final training runtime must be checked without loading model/trainer.',
        'gpu_execution_authorized': False}
    (ROOT / 'intended_parameters.json').write_text(json.dumps(intended, ensure_ascii=False, indent=2) + '\n')
    checks = [
      {'id':'D1','item':'官方2048数据方案与身份名称','status':'USER_SELECTED_RECORDED','phase':'policy','blocking_now':False,'evidence':'evidence/owner_recipe_decision.json'},
      {'id':'D2','item':'原始2600曝光及原生过滤1642成员/哈希','status':'PASS_RECALCULATED','phase':'CPU','blocking_now':False,'evidence':'evidence/frozen_inputs_recheck.json'},
      {'id':'D3','item':'此前额外语义审核/改写/重配要求','status':'REFERENCE_ONLY_NOT_A_GATE','phase':'policy','blocking_now':False,'evidence':'evidence/owner_recipe_decision.json'},
      {'id':'E1','item':'正式启动入口与官方命令对齐并CPU解析验证','status':'OPEN_WRAPPER_MISMATCH','phase':'before_GPU_smoke','blocking_now':True,'evidence':'reports/entrypoint_differences.md'},
      {'id':'E2','item':'最终训练镜像/依赖overlay/代码/PVC与精确输入绑定','status':'OPEN_NOT_BOUND','phase':'before_GPU_smoke','blocking_now':True,'evidence':'evidence/live_readonly_check.json'},
      {'id':'E3','item':'ClearML SDK在最终训练环境可导入、凭据与HTTPS输出配置','status':'OPEN_RUNTIME_BINDING','phase':'before_GPU_smoke','blocking_now':True,'evidence':'evidence/live_packages_base_metadata.json'},
      {'id':'R1','item':'当前受控GPU资源与vLLM切换窗口授权','status':'NOT_AUTHORIZED_GPU_OCCUPIED','phase':'before_GPU_smoke','blocking_now':True,'evidence':'evidence/gpu_fallback_check.json'},
      {'id':'R2','item':'服务恢复配置与路由快照','status':'CAPTURED_NOT_RESTORE_TESTED','phase':'before_GPU_smoke','blocking_now':False,'evidence':'evidence/vllm_restore_snapshot.json'},
      {'id':'R3','item':'本次切换负责人/顺序/超时/恢复验收及运行清单绑定','status':'OPEN_WINDOW_PLAN','phase':'before_GPU_smoke','blocking_now':True,'evidence':'reports/training_gate_checklist.md'},
      {'id':'V1','item':'独立A/B/C/D测试集、评分标准与版本冻结','status':'OPEN_NOT_FROZEN','phase':'before_Full_and_evaluation','blocking_now':False,'evidence':'reports/training_gate_checklist.md'},
      {'id':'V2','item':'GPU BF16/LoRA显存、吞吐与真实保留数','status':'NOT_EXECUTED_EXPECTED_SMOKE_VERIFICATION','phase':'authorized_GPU_smoke','blocking_now':False,'evidence':'reports/training_gate_checklist.md'},
      {'id':'V3','item':'本轮新ClearML Task/Model上传下载、最终checkpoint/epoch核验','status':'NOT_EXECUTED_LATER_PHASE_RESULT','phase':'authorized_smoke_full','blocking_now':False,'evidence':'reports/training_gate_checklist.md'}]
    gate = {'schema':'t008-official2048-current-gate-v1',
            'updated_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'recommendation':'NO_GO_GPU', 'data_policy_choice':'RECORDED',
            'checks':checks,'smoke_started':False,'full_training_started':False,
            'service_interrupted':False,'formal_approval_json_created':False,
            'note':'The user selected the official data recipe. This is not GPU start authorization or a fabricated approval record.'}
    (ROOT / 'gpu_gate_checklist.json').write_text(json.dumps(gate, ensure_ascii=False, indent=2) + '\n')
    entry = '''# 正式入口差异核验（只读，未改代码）

当前准备代码commit为55042a0c2eb3da96f38b019650838bfdf6b4a03b，工作区干净。旧23项测试通过属于该旧封装配置，不证明最新官方命令已经在最终训练运行环境完整解析。

| 项目 | 官方2048执行口径 | 旧v1.2封装实际逻辑 | 当前处理 |
|---|---|---|---|
| 数据 | 原生两个来源#2000/#600，允许默认delete过滤 | 固定本地JSONL；原始快照预检要求overlength_rows=0 | 待适配输入与原生过滤证据；不能再把原始958超长当作整体失败 |
| 有效成员 | 2600载入→1642保留 | 通过人工衍生1642进入训练，要求独立data_change批准字段 | 1642现仅为过滤成员审计证据；不强制人工衍生审批路线 |
| LoRA参数名 | 官方示例--train_type lora | 实际4.4.2帮助仅列--tuner_type；旧封装可选兼容名字 | 最终argv使用实际支持的等价参数，并做CPU解析；不声称字面命令已验证 |
| 保存 | save_steps=50，按steps | Full强制save_strategy=epoch | 待对齐到官方保存口径；不得继续把旧epoch配置标为官方一致 |
| 训练中评估 | eval_steps=50 | 未给验证集且实际4.4.2默认split=0时自动eval_strategy=no | 不擅自切验证集；明确50不等于每50步必有评估 |
| 最终产物 | 记录真实最后完整checkpoint与Trainer state | 旧Full要求选中checkpoint的epoch>=0.999 | 对齐按步保存后需核验最后保存行为，不能登记未完成epoch的checkpoint为正式完成 |
| 运行门禁 | 用户已选数据，仍需真实GPU窗口授权 | 旧入口要求approval.json与多项literal true | 不伪造批准，也不把本次文档决定变成GPU批准；正式入口需绑定实际授权清单 |

本轮只更新执行记录、报告和只读现场证据；没有修改run_identity.py或启动脚本，也没有为消除差异而绕过现有门禁。
'''
    (ROOT / 'reports/entrypoint_differences.md').write_text(entry)
    gate_report = '''# 当前训练前置条件（官方2048方案）

**当前结论：GPU No-Go。数据方案已选定，未授权启动GPU。**

## 启动GPU Smoke前必须满足

1. **正式入口适配与CPU解析**：按官方数据原生过滤规则处理2600输入和1642有效成员；LoRA参数名对齐实装4.4.2；恢复按50步保存；核验最后checkpoint行为。旧wrapper目前未适配，详见entrypoint_differences.md。
2. **固定实际运行单元**：绑定最终镜像digest、代码commit、依赖overlay及hash、UID/cache路径、只读基座/数据与输出PVC、原始快照/来源revision和有效成员hash。当前Swift为0副本的web-ui模板，不是已核验的本次SFT Job；PVC Bound只说明卷存在。训练PVC基座须再核对完整SHA，不用vLLM挂载替代训练输入核验。
3. **ClearML运行接入**：当前基镜像实装没有ClearML SDK；此前仅CPU临时overlay安装1.17.0并完成既有对象只读验证。需在最终训练运行单元固定SDK/依赖、验证可导入，并绑定既有凭据引用和明确HTTPS files输出地址。当前API/files HTTPS 200和服务Ready不等于最终训练容器SDK已就绪。
4. **GPU与业务窗口**：当前唯一RTX4090总24564MiB、已用22176MiB，vLLM运行。须有本次共享GPU使用/服务切换窗口及Smoke授权、可执行切换顺序、超时与恢复负责人。用户明确本轮不启动；不停止服务，不抢占GPU。
5. **运行清单和恢复准备**：将会话数据决定、精确输入/模型/代码/镜像hash与真实启动授权绑定到实际作业。当前已保存vLLM Deployment、Service、Ingress恢复快照并核对健康，但未实际切换或演练恢复。启动前还应固定恢复验收条件及预计影响时长。

## Full与A/B/C/D评测前

- 独立测试题、评分规则、阈值与版本/hash冻结；避免重复身份模板泄漏到验证集。
- 获批Smoke后确认GPU BF16/LoRA内核、显存、吞吐、有效1642行及loss正常，再决定Full；这些是Smoke执行中验证项，不要求在GPU尚未授权时伪造通过。
- 本轮新ClearML Task、Adapter/Model远端上传和回读、Trainer最后global_step与epoch、checkpoint完整性，属于后续获批阶段产出，不能循环要求本轮提前完成，更不能写作已完成。

## 已关闭或仅为参考的旧项

- 使用两个官方来源、保持2048、保留全部600身份曝光及默认958长度过滤，已由本会话选择；不再要求重复裁定或重配为313/419次。
- 78/82条身份语义建议、额外521条通用逐条审核、2560新增177条内容初审，保留为参考记录，不再作为官方路线额外准入门槛。
- 2600原始记录存在958条超长是默认过滤可处理的输入事实，不再直接标为整批数据失败。历史人工长度衍生包字段不被反向改为已批准。

## 时间估算边界

沿用先前排期参考：Smoke20–30分钟、Full45–90分钟、恢复15–30分钟，切换整体可先预留90–150分钟，均非本机训练实测。1642曝光、batch1/accum16、1epoch约103个optimizer steps；官方每50步保存与最后保存行为须实际核验。独立评测题量/输出预算未冻结，不能承诺整个训练和A/B/C/D评测30分钟完成。
'''
    (ROOT / 'reports/training_gate_checklist.md').write_text(gate_report)
    main_report = '''# T-008｜v1.2官方2048方案执行与交付报告（当前口径更新）

更新依据：用户确认“按qwen官方给的训练命令即可，这是官方给的”，并要求更新记录、核对前置条件且先不启动GPU。本报告覆盖此前报告中与额外语义清洗、人工配比裁定相关的当前执行结论；历史实测、原始数据、审查发现和不可变压缩包继续保留。

**当前结论：官方2048数据方案已选定；GPU No-Go。没有启动Smoke、Full或A/B/C/D推理，没有停vLLM，没有发布模型。**

## 当前执行基线

- 模型Qwen/Qwen3-8B；原生数据swift/Qwen3-SFT-Mixin#2000与swift/self-cognition:qwen3#600。
- max_length=2048，使用实装ms-swift默认delete过滤；不额外语义剔除、不改写身份回答、不重配600身份曝光、不采用2560。
- 名称：章鱼能碳垂直大模型 / Octacarbon LLM；定制主体：能碳章鱼（湖北）人工智能科技有限公司 / Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.。官方swift-robot/swift是示例占位值，按本项目已确认值替换。
- LoRA rank8/alpha32/all-linear、BF16、1epoch、lr1e-4、batch1、accum16、warmup0.05、workers4；eval_steps50、save_steps50、save_total_limit2、logging_steps5。参数目标见intended_parameters.json，官方原文命令另存为不可执行参考txt。
- 保留v1.2 CPU修复证据；当前正式wrapper尚有与官方口径的差异，不把“路线一致”写成“字面命令已在当前镜像完整实测”。

## 数据及复算

| 来源 | 原生加载曝光 | 原生2048过滤后曝光 | 保留不同记录 |
|---|---:|---:|---:|
| Mixin | 2000 | 1042 | 521，每条2次 |
| 身份 | 600 | 600 | 108，60条6次/48条5次 |
| 合计 | 2600 | 1642 | 629 |

默认删除958次通用曝光，不自动补足2000。身份曝光占比从加载时23.08%变为有效成员36.54%，这是已选官方原生规则的结果，不再作为额外人工配比裁定项。600曝光不是600条不同身份问题。

- 原始train.jsonl SHA-256：dda551041a12c460b84056f2c58df0ab60f2e9999e0518f116cf5f5b3c5faf6e。
- 有效成员审计快照SHA-256：ad06235bcf0df01f7de4fbfb4f2fe3b156429444478bb1ef0a22cc7ab322b111。
- 958条长度行号清单SHA-256：62b0786206d25262c51a637a4ec02cd2a811b9eb13ecc6396b8d5079ff414f84。

本轮按实际Swift逐条长度证据重算，1642行字节/顺序与既有长度审计快照完全一致。训练口径是固定原始来源/快照并执行默认过滤，不强制改走人工语义清洗或衍生批准路线。未更改旧manifest的历史pending字段。

两官方仓库Apache2.0及来源版本/实物hash证据沿用原CPU包；本会话已选择官方配方。该选择不外推为其他业务数据、备案、独立法律或模型验收批准。既有语义审查/分类记录不作删除，不篡改为“全内容已保证正确”，但不再用于额外阻止当前官方路线。

## 已完成证据与本轮核验

- 原v1.2附件12/12完整性、真实Tokenizer/Swift模板及mask、原CPU代码23项测试证据保留。真实Swift原始最大2511、958次超长，保留1642；HF最大2515，超长集合一致。
- 本轮重新校验旧证据包206个文件hash及数据排除链；旧数据、代码和历史报告未改写。正式准备代码commit仍55042a0c2eb3da96f38b019650838bfdf6b4a03b，工作区干净。
- 本轮只读读取K8s、GPU遥测、部署/PVC/服务、包版本及基座小文件；未加载模型或创建训练进程。GPU遥测首尝试宿主机PATH无nvidia-smi，改从既有vLLM容器读取，失败与恢复证据均保留。
- 当前部署探测前后spec hash一致；与历史脱敏spec的结构也一致。旧env字面值已脱敏，不能将“未脱敏vs脱敏不等”误报为实际配置变化。

## 最新现场状态

- context=lmas00-direct，vLLM1/1、Swift0副本；vLLM HTTPS health=200且证书验证正常。唯一4090总24564MiB、占22176MiB；GPU进程为VLLM::EngineCore，无可直接并行训练的空闲受控GPU。
- 实装ms-swift4.4.2、Transformers5.14.1、PEFT0.20.0、torch2.11.0+cu130、tokenizers0.22.2、datasets4.8.4、ModelScope1.38.1。Tag中4.4.3/1.39.0不代表实装版本。
- vLLM实际imageID为modelscope镜像digest sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738。它是当前已验证基镜像，尚不是已绑定本次训练Job的最终运行单元。
- 基座16文件大小与历史完整SHA清单一致，11个小文件本轮hash相同；5个大权重沿用此前逐文件完整SHA，未为本轮文档检查重读16GB权重。当前读取的是vLLM只读挂载，不冒充训练PVC已完整绑定。
- ClearML5个Deployment、2个StatefulSet就绪，4PVC Bound；API/files HTTPS均200。Swift4PVC Bound。当前基镜像没有ClearML SDK，旧CPU测试使用的clearml1.17.0临时overlay尚未固定到最终训练Job。
- 已保存本次vLLM Deployment、Service和Ingress恢复快照；未切换服务或演练恢复。

## 尚未满足的条件

| 阶段 | 未满足条件 | 证据/下一步 |
|---|---|---|
| GPU Smoke前 | 正式入口与官方数据过滤、LoRA参数名、50步保存对齐 | 旧wrapper要求零超长输入且Full按epoch保存；见entrypoint_differences.md。需适配后CPU解析验证 |
| GPU Smoke前 | 最终代码/镜像/overlay及基座、数据、输出PVC绑定 | 当前Swift仍为web-ui模板；固定实际作业输入与hash，并校验训练PVC实物 |
| GPU Smoke前 | ClearML SDK与运行配置在最终训练单元可用 | 固定SDK/依赖、凭据引用、HTTPS输出及导入验证；历史只读认证证据不能代替最终Job验证 |
| GPU Smoke前 | 共享GPU与服务影响窗口、启动授权 | 用户明确先不启动；当前GPU被vLLM占用 |
| GPU Smoke前 | 本次切换与恢复运行清单 | 有恢复快照，需负责人、顺序、超时和恢复验收条件，与实际窗口绑定 |
| Full/评测前 | 独立测试集、评分规则与版本/hash冻结 | 不擅自从重复身份曝光随机切验证集；A/B/C/D按原v1.2后续要求 |
| 获批Smoke/Full中 | BF16/LoRA显存吞吐、真实有效数、最后checkpoint及ClearML新产物闭环 | 尚未执行，属于后续阶段验证产出，不是假装已通过的前置证明 |

实际4.4.2在无val_dataset且split_dataset_ratio默认0时会设置eval_strategy=no；单独eval_steps50不会自动产生每50步评估。本轮不擅自增加验证集或更改官方数据配比。详细分阶段门禁见training_gate_checklist.md和gpu_gate_checklist.json。

不再列作阻断：身份语义必须改写/排除、剩余521条必须额外逐条语义审核、将身份重配到313/419曝光、升2560、对默认958过滤重新申请配比裁定。用户的方案选择有原话记录，无须重复请示；尚未取得的GPU启动/服务影响窗口授权不从数据决定推导。

## 交付、历史和停止点

本轮更新执行记录、当前交付报告、机器门禁清单、入口差异、数据决定及现场证据。原206文件CPU包和后续审核/分类包保持不可变；旧主报告Drive ID更新为本报告，旧版本仍在Drive修订历史和旧ZIP中。

历史CPU数据与证据包：https://drive.google.com/file/d/1C4Psio7qgU27bFobd92i4oXmDa0JQqG4/view （SHA-256 c0049799f80070b3126397a56f2ae1034eb3e12cbaafbfe4cd6fc1ee180bf1c4）。
历史内容审核包：https://drive.google.com/file/d/1O1vDI4tCU9LGY5vdNw4cjkAlVfRej5jc/view 。其建议/标签为当时工程初审发现，当前额外门禁以本报告和会话官方路线决定为准。

新补充包有独立MANIFEST；上传后回读原始字节并比较SHA-256。正式GPU Job、实际训练入口修复、ClearML新产物、独立评测冻结及GPU阶段均未在本轮执行。预计Smoke20–30分钟、Full45–90分钟、恢复15–30分钟仅为历史排期估算，待授权Smoke校准。

**停止在GPU训练门禁前，等待下一阶段授权。**

官方参考：https://github.com/QwenLM/Qwen3/blob/7a2f61ffc7a20d47efcd2bf97f6f2bf52729042e/docs/source/training/ms_swift.md 。模板/默认参数解释以已核验实装版本为准，不拿官方示例替代现场GPU测试。
'''
    (ROOT / 'reports/complete_report.md').write_text(main_report)
    history = (OLD / 'reports/execution_report.md').read_text()
    prefix = '# T-008执行记录｜官方2048口径更新\n\n本文件保留原执行记录并追加当前决定。**当前有效口径见文件末尾更新条目及同目录complete_report.md；下方原记录中的额外语义/配比门禁已被本会话选择替代。** 原始旧包文件未改写。\n\n---\n\n'
    appendix = '\n\n---\n\n# 当前追加记录：采用官方2048路线\n\n' + '\n'.join([
        '用户原话：“按qwen官方给的训练命令即可，这是官方给的”。',
        '用户本轮要求：更新执行记录/交付报告并核对前置条件，先不要启动GPU。',
        '已记录官方两来源#2000/#600、2048和默认delete；保留已确认中英文名称/主体，不额外改写、排除或重采身份。',
        '已重算2600→1642，Mixin1042/身份600；206个原包文件hash及成员链复核通过。数据方案选择关闭；旧语义清洗和额外配比裁定改为参考。',
        '只读现场：vLLM1/1且HTTPS200，Swift0，唯一4090已用22176/24564MiB；部署spec探测前后未变。',
        '已保存当前恢复配置；未作服务切换。ClearML服务与存储健康，但最终训练SDK/overlay和Job/PVC仍待绑定。',
        '发现旧启动封装零超长预检、人工衍生输入、Full按epoch保存与官方原生路径/50步保存不一致；只记录差异，未修改训练代码。',
        '剩余条件：入口适配CPU解析、最终运行单元与PVC、ClearML集成、GPU业务窗口和恢复清单；Full前需冻结独立评测。GPU运行验证留给获批Smoke。',
        '没有创建approval.json、ClearML Task/Model、GPU进程或K8s对象；未训练、未停vLLM、未发布。',
        '当前结论：数据方案已选定；GPU仍No-Go。机器可读状态见../gpu_gate_checklist.json。']) + '\n'
    (ROOT / 'reports/execution_report.md').write_text(prefix + history + appendix)
    notice = '> **执行口径更新（2026-10-19）：用户已选择Qwen官方2048配方。本文下方为历史工程审查，问题标签和清洗建议保留为参考，不再作为额外语义清洗或重配门禁。当前执行及训练前置条件以[更新后的主报告](https://drive.google.com/file/d/1p-awqvTM89aQ1Y89YHIiq2kbWNRrQDou/view)为准；本轮未授权GPU训练。**\n\n---\n\n'
    (ROOT / 'reports/historical_review_with_current_notice.md').write_text(notice + (ROOT.parent / 't008_qwen3_sft_v12_followup_review_20261019/REVIEW_REPORT.md').read_text())
    (ROOT / 'reports/historical_classification_with_current_notice.md').write_text(notice + (ROOT.parent / 't008_qwen3_identity_classification_20261019/IDENTITY_CLASSIFICATION.md').read_text())
    (ROOT / 'README.md').write_text('# T-008｜官方2048执行口径更新\n\n当前报告：reports/complete_report.md；追加执行记录：reports/execution_report.md；门禁：gpu_gate_checklist.json。\n\n只更新文档和只读证据，不包含新训练快照，不启动GPU。旧206文件CPU包和数据hash保持不变。历史语义审查已改为参考项；正式入口适配、运行单元、窗口授权等仍待满足。\n\n本目录与原t008_qwen3_sft_v12_cpu并列，避免修改原包MANIFEST覆盖的不可变文件。\n')
    print(json.dumps({'reports_written': True, 'gate': 'NO_GO_GPU', 'old_semantic_gates': 'REFERENCE_ONLY',
                      'native_effective_rows': inputs['native_filter_retained_rows'], 'formal_approval_created': False}))


if __name__ == '__main__':
    main()
