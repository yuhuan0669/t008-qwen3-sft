import datetime,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
OLD=ROOT.parent/'t008_qwen3_official2048_update_20261019'
r=json.loads((ROOT/'evidence/native-proof/native-preflight.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
commit=subprocess.run(['git','rev-parse','HEAD'],cwd=ROOT/'code',capture_output=True,text=True,check=True).stdout.strip()
base='https://drive.google.com/file/d/1C4Psio7qgU27bFobd92i4oXmDa0JQqG4/view'
gate=json.loads((OLD/'gpu_gate_checklist.json').read_text())
gate['schema']='t008-native-entry-current-gate-v2';gate['updated_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
for c in gate['checks']:
 if c['id']=='D1':c['evidence']='evidence/owner_decisions.json'
 if c['id']=='D2':c.update(status='PASS_FRESH_NATIVE_CPU',evidence='evidence/native-proof/native-preflight.json')
 if c['id']=='D3':c['evidence']='reports/complete_report.md'
 if c['id']=='E1':c.update(status='PASS_IMPLEMENTED_CPU_VERIFIED',blocking_now=False,evidence='evidence/native-proof/native-preflight.json')
 if c['id'] in ('E2','E3','R1'):c['evidence']='evidence/live_readonly_check.json'
(ROOT/'gpu_gate_checklist.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n')
main=f'''# T-008｜v1.2 官方原生2048正式入口与CPU核验报告

本次已完成正式入口适配、真实CPU解析/原生加载/模板核验、测试及执行记录更新。**CPU工程范围通过；GPU仍为No-Go。** 未启动GPU Smoke、Full、A/B/C/D推理，未停止vLLM，未发布模型，未创建ClearML Task/Model或虚构批准记录。优化留待验证后单独讨论，本轮未实施。

## 已落地的正式入口

代码提交：`{commit}`（父提交55042a0c2eb3da96f38b019650838bfdf6b4a03b），工作区干净。完整代码、Git bundle、patch、测试和README均在新包，旧206文件包与原始数据不变。

`train_identity.sh full` → `run_identity.py` → 官方Swift SFT，默认原生加载`swift/Qwen3-SFT-Mixin#2000`和`swift/self-cognition:qwen3#600`，不再读取预筛1642行本地文件；不做语义排除、样本改写、重配、自动补采或2560调整。max_length=2048，真实默认delete（模板内部raise、预处理捕获并删除），保留默认dataset_shuffle=True、seed/data_seed=42。

LoRA rank8/alpha32/all-linear、BF16、一轮、batch1/accum16、lr1e-4、warmup0.05、workers4；Full恢复steps/save_steps=50，save_total_limit2、logging_steps5。实装4.4.2使用tuner_type；显式qwen3模型类型/模板以消除本地基座元数据歧义。split_dataset_ratio=0、eval_strategy=no，与当前官方无验证集默认行为一致；eval_steps=50保留但不产生每50步评估。未额外从重复身份样本拆验证集。

四个确认字段：章鱼能碳垂直大模型 / Octacarbon LLM；能碳章鱼（湖北）人工智能科技有限公司 / Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.。基座为Qwen/Qwen3-8B，定制主体不表述为Qwen基座原始研发方。负责人英文名与用途确认原话及本轮路线指示见owner_decisions.json，不要求重新裁定已选数据配比。

新增cpu-check模式在任何训练授权、GPU模型加载、Task或训练子进程前分流。只读native_guard external plugin不修改数据，仅核对真正加载/过滤返回对象的全部列有序摘要、模板、名称、版本和批准的CPU报告SHA，并拒绝cached/packing/lazy/streaming等旁路。该guard在未来训练中位于Trainer/train前；Swift初始化会先加载基座，故不能称所有数据漂移失败都发生于Task或GPU模型加载之前。

## 真实CPU数据与模板结果

| 来源 | 原生加载曝光 | 默认2048删除 | 保留曝光 | 保留不同记录 |
|---|---:|---:|---:|---:|
| Mixin | 2000 | 958 | 1042 | 521 |
| 身份 | 600 | 0 | 600 | 108 |
| 合计 | 2600 | 958 | 1642 | 629 |

身份原始库108条；600为重复曝光，60条6次、48条5次。有效身份曝光比例36.54%是本轮已选官方规则的结果，不作为额外人工配比门禁。原生源为1000条Mixin和108条身份模板。默认过滤只处理长度/编码合格性，不是内容真实性或think闭合检查；此前语义审查发现保留为参考，本轮未据此额外剔除，也不宣称全内容质量/模型效果已经验收。

本次使用**正式SftArguments.load_dataset**，不使用旧prepare脚本的shuffle=False。与旧快照内容集合完全一致，但全局顺序及部分重复曝光分配不同：48个身份模板发生5/6次互换（24增、24减）。故新原生输入/保留结果独立冻结，不冒用旧train.jsonl的字节SHA、行号或审批。原始2600快照和旧1642衍生快照保持不变，新JSONL仅为证据，正式训练仍使用数据源ID。

- native_input：{r['native_input']['sha256']}（全列canonical数据摘要）。
- native_retained：{r['native_retained']['sha256']}（含dataset、messages、lengths全列canonical摘要）。
- native-loaded.jsonl文件SHA：{sha(ROOT/'evidence/native-proof/native-loaded.jsonl')}。
- native-retained.jsonl文件SHA：{sha(ROOT/'evidence/native-proof/native-retained.jsonl')}。
- CPU报告文件SHA：{sha(ROOT/'evidence/native-proof/native-preflight.json')}。

摘要算法见native_recipe.digest；canonical数据摘要与JSONL字节SHA是不同概念。逐行source-row-map、token/labels摘要、保留/删除标志、正式argv与解析值均附包。模板qwen3、loss_scale=default+ignore_empty_think；无截断全长编码及实际SwiftSft._encode_dataset方法确认保留成员，所有样本有监督token且监督label等于对应input id。没有实例化SwiftSft或Trainer，没有加载模型权重；读取全文件计算SHA属于完整性校验。

## 来源、版本及基座

本轮实际原生缓存两文件SHA与既有审核原件一致：Mixin `d261353c05df1f1fde95639d1a9d9243e1d24470dcb4c3732965ab1ab8eeba41`；身份模板 `e7b66784f02361cfa0ad4635dae12c0f810d197c22ac89a4b7837195dc4b7b23`。原生SDK下载元数据记录Revision=master、etag=null，**不将其冒充已固定远端revision**；依靠内容哈希与此前固定内容证据绑定，并由训练插件拒绝漂移。此前固定Mixin内容revision e587cae71fc7084ab93dccbc37d0056df3569543、self内容revision d2a385942cb0d47e3fb3cdb9d98adb8b8c01dcfc的来源/Apache2.0声明证据沿用历史包，相关README及许可副本随本次包提供。仅用于已选身份SFT用途。

本轮重新完整读取16个基座文件（含5个大权重）校验，全部与既有SHA清单一致，合计16,397,461,896字节，聚合指纹`{r['model_files_sha256']}`。检查的是vLLM现有只读基座挂载；最终训练PVC绑定仍待完成。权重本体不重复上传Drive。

实装：ms-swift4.4.2、Transformers5.14.1、PEFT0.20.0、torch2.11.0+cu130、tokenizers0.22.2、datasets4.8.4、ModelScope1.38.1。实际镜像digest `sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738`，不以镜像tag中的4.4.3/1.39冒充实装版本。关键已安装Swift源码SHA与4.4.2官方发行wheel一致，附源码及对照证据。

## 检查、故障修复与边界

- 本机及实际镜像32/32测试通过；Python语法、shell语法及git diff --check通过。
- 真实正式Full参数无未知项，CPU dataclass后初始化成功，数据/模板/长度实际预处理通过。仅CPU额外覆盖use_cpu=true、report_to=none、add_version=false。
- 实际DefaultFlowCallbackNew 9/9 CPU场景通过：每50步保存、非整50的最后一步强制保存，以及save=no等边界；没有真正产生训练checkpoint。
- 实际插件正例通过，报告SHA/身份/cached旁路/跳过预处理/输入顺序五个负例全部阻断。插件_get_dataset正例采用已冻结原生输入回放，真实网络/native加载由另一CPU步骤证明；不冒称一次完整GPU训练链路集成测试。
- 镜像非root启动缺ModelScope预建AST索引、默认配置目录不可写：独立CPU生成索引并只读挂载、设置MODELSCOPE_HOME到本轮工作目录，未改服务镜像。首次TLS设置误把仅供ClearML的私有CA当作完整根bundle，导致官方源验证失败；改用宿主机可信根加项目CA的bundle，TLS验证始终启用，失败日志保留。未改HOME或系统权限。
- torch_dtype/warmup_ratio弃用提示和可选4bit kernels缺失提示已记录；本轮普通BF16 LoRA不依赖4bit kernels，未借此引入QLoRA等优化。
- 两位继承上下文的工程子审已复核，无本范围剩余必修问题；这不是独立盲审或模型验收。历史包206/206哈希及旧排除链再次通过。6个本轮CPU容器已收集记录后删除。

## 当前现场与门禁

最新只读检查15项成功；清理后再次回读vLLM/Swift spec与检查前一致。vLLM1/1、Swift0副本，HTTPS health=200且TLS验证通过；4090总24564MiB、占22176MiB，GPU进程仍为VLLM::EngineCore（22166MiB）。没有空闲受控GPU可直接并行训练。ClearML服务与PVC健康检查沿用本轮只读现场记录，未创建新对象。

| 条件 | 当前状态 |
|---|---|
| 正式入口原生加载、默认过滤、CLI及50步保存 | **已完成CPU核验，原E1阻断关闭** |
| 精确数据/基座/代码/镜像证据 | 已冻结本轮CPU实测；待绑定最终运行单元 |
| 最终训练Job、代码/数据/基座/输出PVC及运行支持挂载 | **未绑定**，当前Swift为web-ui模板 |
| ClearML SDK/依赖、凭据引用、HTTPS输出在最终单元可用 | **未绑定**；基镜像没有SDK，历史1.17.0 overlay不能代替最终作业验证 |
| 共享GPU、服务影响窗口及本次真实启动授权 | **未授权**，GPU被vLLM占用 |
| 本次切换负责人、顺序、超时、恢复验收运行清单 | **待落实**；已有恢复配置/路由快照，未演练恢复 |
| 独立A/B/C/D题集、评分规则及hash冻结 | Full/评测前待完成，不从重复身份曝光随机拆分 |
| BF16 LoRA显存、吞吐、真实最终checkpoint、ClearML新产物回读 | 后续获批GPU阶段验证，本轮未执行 |

历史排期估算Smoke20–30分钟、Full45–90分钟、恢复15–30分钟，需后续获批Smoke实测校准；不是当前硬件上的保证。A/B/C/D窗口在独立题集冻结及吞吐实测后估算，不给虚假确定时长。

## 交付与停止点

本包包含正式入口、32项测试、Git bundle/diff、原生2600与默认过滤1642证据快照、原始官方文件、逐行映射/长度mask摘要、来源/许可、运行适配、故障日志、现场门禁及工程复核。所有文件在MANIFEST中逐项记字节数与SHA；上传后的Drive父目录/字节/SHA回读见独立交付回执。

历史不可变CPU包：[v1.2 CPU原始包]({base})（SHA c0049799f80070b3126397a56f2ae1034eb3e12cbaafbfe4cd6fc1ee180bf1c4）。本轮只在新目录实现，主报告Drive ID更新后保留修订历史。

**停在GPU门禁之前。CPU核验通过不代表训练完成、效果通过或获得下一阶段授权；后续再讨论此前优化方案。**
'''
(ROOT/'reports/complete_report.md').write_text(main)
append=f'''\n\n---\n\n## 2026-10-19｜正式原生入口适配完成（覆盖此前“入口尚未实施”状态）\n\n本轮负责人明确授权原生加载/默认过滤适配及CPU核验，仍禁止GPU训练。新提交{commit}；已从旧本地1642路径切换为两项官方source IDs，恢复Full每50步保存，以只读插件核原生输入和默认delete结果。真实CPU2600→1642（1042+600），32项镜像测试、9项保存回调、插件正反例通过。\n\n原生SftArguments默认shuffle=True，导致顺序及48个身份模板5/6次曝光分配与旧prepare不同，已冻结独立新证据；没有修改旧原始数据。正式入口旧零超长/本地路径阻断已关闭，优化未实施。实际镜像、关键源文件、16个基座全文件SHA均核验；工程子审为继承上下文复核，不是盲审或模型验收。\n\n非root AST/配置目录及TLS可信根适配和失败日志已记录；本轮6个CPU容器已删除。现有服务spec不变，vLLM健康。GPU仍No-Go：最终Job/PVC/SDK/凭据绑定、GPU与服务窗口授权及恢复运行清单未完成；独立评测冻结和GPU产物验证留待后续。无GPU训练、vLLM停止、ClearML对象或发布。详见本轮complete_report.md及gpu_gate_checklist.json。\n'''
(ROOT/'reports/execution_report.md').write_text((OLD/'reports/execution_report.md').read_text()+append)
(ROOT/'reports/training_gate_checklist.md').write_text('# T-008｜当前GPU训练门禁\n\n结论：NO_GO_GPU。原E1正式入口/CPU兼容性阻断已关闭，当前数据政策已确认，不重复申请配比裁定。\n\n| 编号 | 条件 | 状态 | 当前阻断 |\n|---|---|---|---|\n'+''.join(f"| {c['id']} | {c['item']} | {c['status']} | {'是' if c['blocking_now'] else '否'} |\n" for c in gate['checks'])+'\nCPU检查不生成批准。正式GPU启动前需将真实批准绑定native预检报告SHA、输入canonical摘要、保留数、基座与实际Job；没有要求负责人重新选择数据方案。尚未执行的GPU阶段产物不能填作已通过。\n')
(ROOT/'reports/entrypoint_differences.md').write_text('''# 正式原生入口与旧版的差异（已实施）

| 项目 | 旧入口 | 当前已CPU核验入口 |
|---|---|---|
| 数据路径 | 本地DATA_DIR/train.jsonl及零超长前检 | 官方source IDs原生加载，默认2048 delete |
| 1642快照 | 预先生成后作为训练文件 | 仅保留为CPU证据，正式入口不读取它训练 |
| shuffle/曝光 | 旧prepare load_dataset默认shuffle=False | 正式SftArguments默认dataset_shuffle=True，48身份模板曝光次数互换 |
| 保存 | Full按epoch保存 | steps/50；实际Swift callback最终步补存，wrapper核终态 |
| CPU检查 | 无独立正式入口CPU分支 | cpu-check先分流，实际解析、加载和模板编码，零训练 |
| 输入漂移 | 旧本地文件hash | 实际native加载/过滤有序全列摘要与模板/代码/包版本绑定 |
| 授权 | 必须真实GPU及实验批准 | 保留训练门禁；CPU不要求生成假批准 |

核心LoRA路线、2048、官方2000/600采样参数和确认身份不变。没有额外语义清洗或优化。CPU通过不证明GPU训练或模型效果；最终运行单元、SDK/PVC和GPU窗口仍待落实。
''')
(ROOT/'evidence/source_lineage.json').write_text(json.dumps({'source_commit':commit,'parent_commit':'55042a0c2eb3da96f38b019650838bfdf6b4a03b','cpu_tested_entry_fingerprints':r['implementation_fingerprint'],'note':'Final committed entry contents exactly match CPU staged files; CPU staging repository metadata was not used as a training provenance claim.'},indent=2)+'\n')
print(json.dumps({'commit':commit,'cpu_input_rows':r['native_input']['rows'],'cpu_retained_rows':r['native_retained']['rows'],'gate':'NO_GO_GPU'},ensure_ascii=False))
