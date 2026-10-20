"""Build result reports strictly from completed stages and restoration evidence."""
import datetime,hashlib,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
load=lambda p:json.loads((ROOT/p).read_text())
state=load('evidence/session_state.json');assert state['training_verified'] and state['vllm_restored']
full=load('evidence/full-run_manifest.json');smoke=load('evidence/smoke-run_manifest.json')
terminal=load('evidence/full-terminal-state.json');restore=load('evidence/vllm-restoration.json')
collection=load('evidence/output_collection.json');auth=load('evidence/owner_authorization.json')
metrics=load('evidence/full-training-metrics.json');history=metrics.get('log_history',[])
final_metrics=next((x for x in reversed(history) if 'train_loss' in x),{})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=f'''# T-008｜Qwen3-8B 官方原生2048 GPU SFT执行结果

本次3步GPU Smoke及正式一轮LoRA SFT已经完成，最终checkpoint与ClearML候选模型上传/下载哈希闭环通过；原vLLM已恢复。**结果仅为TRAINED_CANDIDATE，未进行独立A/B/C/D效果评测，未合并、上线或发布新模型。**

## 授权和本次执行范围

用户先指示“开始GPU sft吧”，随后明确确认“授权本次暂停、训练并恢复”：临时暂停当前vLLM，先3步Smoke，通过后一轮官方方案SFT，结束或失败后恢复。owner_authorization.json保存原问题、原回答和记录时间；approval.json是对此真实会话授权与已确认输入的绑定，不是示例审批、冒签或虚构批准。用户要求不要过度测试，本轮未增加GPU评测或重复Smoke。

源代码提交`{full['source_git_commit']}`；镜像digest`{full['image_digest']}`。代码文件内容与CPU核验完全一致，实际Job挂载swift-base/Qwen3-8B只读、swift-train-data本次子目录只读、swift-work本次独立输出子目录可写；保留完整实际Job/Pod配置及imageID。运行支持采用已固定ClearML1.17.0依赖overlay、ModelScope AST索引和TLS可信根bundle，不修改权限、镜像原件、历史数据或现有服务模板。

## 配方与实际数据

正式入口原生加载`swift/Qwen3-SFT-Mixin#2000`和`swift/self-cognition:qwen3#600`，模型Qwen3-8B，qwen3模板，默认delete，max_length2048；seed/data_seed42，默认dataset_shuffle=True。按项目确认双语名称/定制主体替换，未将定制主体称为Qwen基座原始研发方。无额外语义清洗、补采、重配或2560调整。

| 来源 | 加载曝光 | 默认删除 | 实际保留曝光 |
|---|---:|---:|---:|
| 通用Mixin | 2000 | 958 | 1042 |
| 身份 | 600 | 0 | 600 |
| 合计 | 2600 | 958 | 1642 |

身份库108条，600是重复曝光；保留不同记录629条。native原生输入canonical摘要`{full['native_input']['sha256']}`，保留结果含lengths的canonical摘要`{full['native_retained']['sha256']}`。训练插件实际加载/默认过滤对象与CPU冻结摘要一致才放行，无本地1642衍生文件替代训练。CPU原生报告SHA `{full['preflight_report_sha256']}`，基座全文件聚合SHA `{full['base_files_sha256']}`。原始文件SHA、来源许可、身份及逐行模板证据仍见历史CPU包与本包绑定输入。

LoRA rank8/alpha32/all-linear、BF16、batch1/累积16、lr1e-4、warmup0.05、workers4、一轮。真实模型8,212.5588M参数，LoRA可训练21.8235M（0.2657%）。正式保存steps/50、save_total_limit2；本轮未启用QLoRA、Liger或其他路线优化。无验证集，eval_strategy=no，eval_steps50没有触发额外训练内评测。

## GPU执行结果

- Smoke：实际3/3优化步骤，checkpoint-3和pipeline终态匹配，Adapter可读且LoRA张量全部有限，wrapper退出0；ClearML Task `{smoke['clearml_task_id']}`。
- Full：实际{terminal['trainer_state']['global_step']}/{terminal['trainer_state']['max_steps']}步，epoch={terminal['trainer_state']['epoch']}，最终checkpoint `{full['checkpoint']}`；目录、trainer_state、真实pipeline terminal logging.jsonl一致；wrapper与训练退出0。
- Trainer最终汇总：`{json.dumps(final_metrics,ensure_ascii=False)}`。训练loss及token_acc是训练集指标，不等于独立能力、身份稳定性或业务验收通过。
- GPU：RTX4090 24,564MiB；Smoke观测峰值{collection['smoke']['peak_observed_memory_used_MiB']}MiB，Full观测峰值{collection['full']['peak_observed_memory_used_MiB']}MiB（10秒遥测采样，不冒充瞬时绝对峰值）。完整遥测和原始训练日志附包。
- ClearML Full Task `{full['clearml_task_id']}`，Model `{full['clearml_output_model_id']}`；候选ZIP {collection['adapter_candidate']['bytes']:,}字节，SHA-256 `{full['adapter_package_sha256']}`，通过Model.force_download回读一致。

[ClearML正式训练任务](https://clearml.10.140.17.125.nip.io/projects/a963d510434a46d19bb91881cad45ea4/experiments/{full['clearml_task_id']}/output/log)。用户询问进度后，额外observer从现有train.log补传步数、loss等标量及百分比到同一Task，未重启训练、未创建额外Task，不调用模型或评测。

## 服务恢复与停止点

vLLM Deployment UID `{restore['deployment_uid']}`，恢复到原副本{restore['original_replicas']}且Ready={restore['ready_replicas']}；spec SHA `{restore['spec_sha256']}` 与暂停前一致，HTTPS health200、TLS验证通过。仅改变本次窗口所需副本数后恢复，没有替换模型、镜像、配置或路由。本次GPU Job在证据采集后已删除释放GPU；训练输出/checkpoint仍持久保存在swift-work PVC本次子目录。

监督脚本使用try/finally保证正常/失败都恢复；证据落盘失败不能阻断scale恢复，单个Job日志采集失败不能阻断两个本轮GPUJob的清理。工程子审为继承上下文复核，不是独立盲审。原始CPU阶段README及No-Go字段属于历史包时状态，不覆盖本次明确GPU授权与真实完成记录。

完整原始checkpoint（含优化器）仍在namespace=swift、PVC=swift-work、subPath=`{auth['run_id']}/outputs`，逐文件大小/SHA见persisted-output-manifest.json；Drive证据包包含元数据、日志、配置和回读证据，最终Adapter ZIP另行交付。基座16GB权重不重复上传。K8s控制平面metadata时钟与执行机墙钟存在约20分钟偏差，保留原值；执行顺序以监督事件链、训练时长以Trainer runtime为准，没有改系统时钟。

尚未完成且未宣称通过：独立A/B/C/D题集冻结与效果评测、模型质量验收、合并/部署/发布。后续优化仍未实施，须基于本次可复现候选再讨论。本次服务影响窗口结束，不自动授权后续GPU占用。
'''
test_path=ROOT/'test_serving/evidence/result.json'
if test_path.exists():
 test=json.loads(test_path.read_text());assert test['status']=='TEST_LOADED'
 report=report.replace('未进行独立A/B/C/D效果评测，未合并、上线或发布新模型。','未进行独立A/B/C/D效果评测，未合并权重或作正式生产发布。后续按用户“现在加载，因为要测试”指示，已新增独立LoRA测试入口，当前为测试加载状态。')
 report += """
## 后续指示：LoRA测试加载（当前服务状态）

用户在训练完成、原vLLM恢复后另行指示“现在加载，因为要测试”。据此新增API模型ID `octacarbon-llm-sft-test`，保留原 `octa-carbon-v1` 基座入口；通过vLLM原生LoRA加载checkpoint-103，没有合并权重。启用enable-lora/max-lora-rank8，只读挂载 `released/t008-qwen3-20261019-094113-test/adapter`；新目录有TEST_SERVING_ONLY_NOT_QUALITY_ACCEPTED清单。未修改既有目录权限、RBAC或Admission Policy，未更改基座文件。

vLLM重启后Ready与HTTPS health200通过，/v1/models同时返回原基座及测试ID；只执行一次真实推理连通性请求，不扩展A/B/C/D或其他测试。当前保留测试入口供用户手工测试；原模板rollback-patch.json已保存，加载失败时自动回退。本次测试加载不等于正式发布、质量验收或允许继续训练。

一次连通请求：`你叫什么名字？`，temperature0、max_tokens128、enable_thinking=false。实际回答：

"""+test['response']+'\n'
tool_fix_path=ROOT/'test_serving/evidence/auto-tool-result.json'
if tool_fix_path.exists():
 tool_fix=json.loads(tool_fix_path.read_text());assert tool_fix['status']=='FIXED'
 report += '''
## Open WebUI兼容性修复（当前生效）

用户实际聊天报错：`"auto" tool choice requires --enable-auto-tool-choice and --tool-call-parser to be set`。确认是vLLM启动参数未启用自动工具调用，与SFT数据或Adapter加载无关。只读检查实际vLLM0.25.1的hermes解析器及注册表，以及基座tokenizer_config.json的`<tool_call>`模板后，在现有base+LoRA配置上追加`--enable-auto-tool-choice --tool-call-parser hermes`。单GPU短暂重启，两个模型入口及只读模型挂载保留，未重训或合并权重。

服务恢复Ready及HTTPS health200后，只发送一次带工具定义和`tool_choice=auto`的请求，返回HTTP200；没有执行外部工具。该请求仅证明原参数报错解除，不是工具能力或业务质量评测。修复前LoRA服务模板与独立rollback补丁已保留。证据见test_serving/evidence/auto-tool-*。
'''
(ROOT/'reports/current_report.md').write_text(report)
old=ROOT.parent/'t008_qwen3_native_entry_20261019/reports/execution_report.md'
append='\n\n---\n\n## GPU授权执行与恢复（本次最终记录）\n\n'+report.split('## 授权和本次执行范围',1)[1]
(ROOT/'reports/execution_report.md').write_text(old.read_text()+append)
gate={'schema':'t008-gpu-sft-final-gates-v1','run_id':auth['run_id'],'training_status':'TRAINED_CANDIDATE','window_closed':True,'vllm_restored':True,'model_published':False,
 'checks':{'native_recipe_and_CPU':'PASS','actual_job_PVC_and_runtime':'PASS','GPU_window_authorization':'EXPLICIT_USER_AUTHORIZATION_CONSUMED','Smoke_3_steps':'PASS','Full_1epoch_final_checkpoint':'PASS','ClearML_model_upload_and_hash_readback':'PASS','original_vllm_restore':'PASS','independent_ABCD_evaluation':'NOT_EXECUTED','model_quality_acceptance':'NOT_GRANTED','deployment_publication':'NOT_AUTHORIZED_NOT_EXECUTED'},
 'stop':'No more GPU work, evaluation, optimization or publishing in this run'}
if test_path.exists():
 gate['test_model_loaded']=True
 gate['checks']['user_authorized_test_LoRA_serving']='PASS_TEST_ONLY'
 gate['checks']['deployment_publication']='NO_FORMAL_RELEASE_OR_QUALITY_ACCEPTANCE'
 gate['stop']='SFT window closed; retain only user-authorized test serving; no more training or agent-driven evaluation/optimization.'
if tool_fix_path.exists():
 gate['checks']['OpenWebUI_tool_choice_auto_compatibility']='PASS_HTTP200_SINGLE_REQUEST'
(ROOT/'gpu_gate_checklist.json').write_text(json.dumps(gate,ensure_ascii=False,indent=2)+'\n')
(ROOT/'reports/gpu_gate_checklist.md').write_text('# T-008 GPU SFT最终门禁\n\n本次一轮SFT候选完成，训练后已恢复原服务；随后按新指示加载独立LoRA测试入口。当前base+test双入口，训练窗口结束，未作正式生产发布。\n\n| 条件 | 状态 |\n|---|---|\n'+''.join(f'| {k} | {v} |\n' for k,v in gate['checks'].items())+'\n训练完成不代表模型验收通过。后续独立评测/优化/上线未执行，不沿用本次窗口自动启动。\n')
print(json.dumps({'training_status':'TRAINED_CANDIDATE','step':terminal['trainer_state']['global_step'],'model_id':full['clearml_output_model_id'],'vllm_restored':True}))
