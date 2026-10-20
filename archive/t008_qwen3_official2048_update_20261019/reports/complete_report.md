# T-008｜v1.2官方2048方案执行与交付报告（当前口径更新）

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
