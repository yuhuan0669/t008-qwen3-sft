# GPU SFT 执行前工程子审

**最新复核：两项恢复路径阻断已修复，针对性mock均通过；当前限定审查未发现新的暂停前必修阻断。实际执行仍须由supervisor通过既定CPU完成、Smoke、Full和恢复门槛，本报告不代表训练或恢复已经发生。**

2026-10-19。只读审查payload、既有CPU和ClearML证据；没有操作Kubernetes、服务、GPU或凭据，没有改实现，没有创建远程Task/Model。继承上下文的工程子审，不是盲审或训练完成验收。

用户本轮已明确授权“暂停vLLM→3步Smoke→Smoke成功后一轮官方Full→成功/失败均恢复原vLLM”，不发布。已读取 `payload/owner_authorization.json`，不要求再次授权。本报告不构造新的批准。

## 应在 supervisor 中补齐的必需检查

### 1. Smoke完成状态本身不足以允许Full

`payload/code/run_identity.py` 的Smoke分支只要求训练进程exit0且找到一个含Adapter文件的checkpoint。`trainer_state.json`缺失不阻断；state步骤与目录不一致被捕获为 `metrics_registration_error`，随后Smoke仍会写 `SMOKE_COMPLETE`；也没有校验真实终态global_step恰为3。

因此supervisor必须在进入Full前验证：wrapper退出0、manifest为SMOKE_COMPLETE、无metrics_registration_error、真实Swift终态日志global_step=3和last_model_checkpoint匹配checkpoint-3、该checkpoint的state.global_step/max_steps均为3、Adapter配置及实际权重文件存在。Smoke只跑3步，不能沿用Full的epoch>=0.999条件。失败则不启动Full，并恢复原服务。可在外部supervisor实现，避免改动已绑定CPU摘要的入口。

### 2. Full完成必须等待注册回读，不读中间成功状态

旧入口在远程文件强制下载和SHA核对之前，将status写为TRAINED_CANDIDATE并上传 `final-run-manifest`。若随后上传URL或回读失败，本地改为FAILED并标失败Task，但此前远程artifact可能仍包含中间成功状态。

supervisor应以wrapper最终退出0为必要条件，并检查最终manifest的 `clearml_model_readback_sha256 == adapter_package_sha256`、Task/Model ID和HTTPS远程URI，再报告注册成功；不能仅看到TRAINED_CANDIDATE或adapter-candidate.zip就放行。若训练完成但注册失败，应保留本地checkpoint并报告“训练已完成、注册/回读失败”，不自动重跑Full，也不发布。

### 3. 服务恢复必须独立于训练Python进程

旧入口不负责暂停/恢复vLLM，也没有SIGTERM外部服务恢复机制。恢复必须由后续supervisor以持久化原服务状态、trap/finally及明确超时/失败流程承担；Job失败、镜像/依赖失败、ClearML失败、OOM、超时和控制连接中断都不应留下服务永久停用。尚未收到Job/supervisor，当前不能确认这项闭环；这不是重新索取用户授权。

## 已核验的支持证据

- payload的 `native_recipe.py/native_guard.py/run_identity.py/train_identity.sh` 四个SHA与 `native-preflight.json.implementation_fingerprint` 全部一致，confirmed身份文件与报告spec一致。
- CPU报告：原生输入2600，默认2048/delete保留1642（Mixin1042、身份600），删除958；验证集0。实际输入和保留数据分别绑定SHA，运行guard核对顺序及重复次数、模板kwargs、双语名称、包版本和批准报告SHA。`same_exposure_multiset_as_old=false`已显式记录，不应错误宣称与旧shuffle=False的曝光完全相同。
- Full的最终checkpoint验证核对单一实际Swift终态记录、last_model_checkpoint路径、目录步数、state.global_step/max_steps和epoch；训练进程非0先失败，不会依靠finally日志误认成功。
- 已读取 `t008_qwen3_native_entry_20261019/evidence/final-save-callback.json`：固定ms-swift4.4.2/transformers5.14.1实际安装回调9/9合成分支通过，含50、100、103最终步和3步Smoke。其源码在global_step==max_steps且save_strategy非no时强制should_save，因此每50步与非整倍数最终保存相容。该证据不证明本次GPU一定103步，也不证明已写checkpoint；应以真实终态为准。
- 已读取ClearML 1.17.0源码片段与只读探测：无输出存储时SDK可能仅登记本地文件。入口已明确Task.output_uri、update_weights(upload_uri,async_enable=False)、HTTPS同host/path及 `Model.get_local_copy(force_download=True)` 摘要回读，避免这个假闭环。此SDK版本的参数签名支持这些调用。
- 历史ClearML只读证据只验证既有33字节synthetic文件，经HTTPS映射读取成功；没有证明本次大Adapter上传权限、容量、网络和注册会成功。该限制通过真实运行后的强制回读闭合，不应写成“之前已证明本次上传成功”。

## 执行包/身份与失败边界

- owner_authorization是用户原话的转录记录，不是旧入口所需的机器gate结构。若用于APPROVAL_FILE，需由主Agent按这次真实授权和确切CPU报告构造对应机器字段，保留原话引用；不能把owner文件直接当作已有全部必需键。此处是格式适配，不要求再次批准。
- 运行时ms-swift必须是报告的4.4.2，不能只信镜像tag4.4.3；torch、transformers等也必须与CPU报告一致。ClearML SDK应核对为已验证的1.17.0或另做只读签名核验，不能把安装成功视为兼容已确认。
- 原生源由官方loader加载，若上游或缓存改变，guard会在Trainer开始前拒绝。官方Swift构造顺序是先加载模型，再加载/编码数据；Task也在启动Swift之前创建。因此数据漂移失败仍可能已有GPU模型占用和失败Task，supervisor必须走恢复路径，不能承诺所有失败均“从未触达GPU/Task”。
- QLoRA/Liger在入口明确禁止，不应为避OOM擅自开启；Smoke失败就停止Full并恢复。OOM本身并不授权改变官方训练方案。
- 无自动发布、替换vLLM基座或Hub推送。恢复目标必须是原服务配置与原模型，不把新Adapter挂上去。

## 本次文件定位

- payload/native-preflight.json SHA256：`bc602fe28f782200b3351b9130e0cfd40807e67fe6ed20a0660a4f240a0247ed`
- payload/owner_authorization.json SHA256：`963124097430777db7bfc75bd5e7a0b04ddce0a109c24d29767ea127ed863178`
- payload/code/run_identity.py SHA256：`47f353024312912dbe76f028caca2943fe1a6f54c5f636b41c92ffe9b906c395`

结论：入口与CPU证据绑定一致，Full最终checkpoint和ClearML回读设计有依据；启动Full前必须补强Smoke三步成功检查，执行成功必须等待回读，服务恢复闭环待下一轮Job/supervisor审查。本轮没有重新审查或要求额外语义清洗。

## Supervisor / Job 增量审查

已读取 `scripts/session_supervisor.py`、`scripts/gpu_stage.py`、`scripts/runtime_preflight.py` 和两个GPU Job。Smoke三步门槛已在stage_verified补齐；Job Complete要求gpu_stage退出0，后者保持wrapper退出码；Full进一步核对state/max_steps/epoch、Model ID与回读SHA。它们关闭了前述两个主要阶段判定缺口。

**历史发现（已由下方修复复核关闭）：证据采集失败曾阻断恢复关键动作。**

1. `stop_owned_gpu_jobs` 对每个本轮Job先执行 `capture_job`，之后才delete。capture_job中的API超时、日志超时或证据写盘失败会跳出整个函数，不删除当前Job，也不继续处理另一个。restore虽捕获错误并scale回原副本，但仍运行的GPU Job会占用唯一GPU，使vLLM恢复长期Pending。应把证据采集与删除拆开：已确认归属的Job无论采集成功与否都尝试删除，各stage独立处理并最终汇总错误；仍应保留归属校验。
2. restore第一行调用event；event写文件和print均可能抛错。磁盘满或输出管道关闭时，恢复在任何scale动作之前终止。恢复关键路径应使用不抛错的best-effort事件记录，不能让证据保存失败阻断清理/恢复。finally内的错误记录同样不能再次抛错遮盖真实恢复状态。

本子审用仅含mock的本地探针确认：模拟capture超时后delete调用数为0；模拟event的OSError使restore在任何kubectl调用前退出。未执行真实kubectl或服务动作。以上两项曾是暂停服务前的阻断点；修复复核结果见下方，不是额外授权请求。

其余已见正向约束：只有本RUN标签Job被清理；scale前检查Deployment UID/spec与HPA；restore核对UID、原副本数、observedGeneration、完整spec和HTTPS健康；设置恢复意图早于scale请求；GPU Job backoffLimit=0/restartPolicy=Never、明确deadline，基座/输入只读、输出独立子目录、单GPU请求与限制一致、镜像digest固定、Secret仅引用、不装ServiceAccount token、禁止QLoRA/Liger和发布。

`gpu_stage` 在启动wrapper前检查GPU进程，结束保留退出码。该边界依赖NVML实际可见性以及先前vLLM pod排空；本子审没有使用GPU验证。supervisor对SIGTERM/INT进入finally有处理，但无法对SIGKILL、宿主掉电或进程所在机器长期失联提供Python finally保证；应准确描述恢复保证边界并使用可靠运行载体，不能声称代码覆盖一切外部中断。

此次增量版本：supervisor `f8dce0b2ad02048ecc8eff042a7d13421dea9083b66b7d1f8a91a4670215a5c8`；gpu_stage `0d5873a379fc68ff8dc6fae2ae0357836f9115f6ad41a9df622df7a64bcdda96`；smoke Job `650fd5bfc9759c99aa98555772b6eb82e73b8815bc7cbc40f018c7fb6a74f599`；full Job `8038abcedf720c5310820969fdb639c2fffcf9e97da1370e8cd9c7fb223e951f`。

## 恢复路径修复复核（最新）

已重新读取最新supervisor：event写盘及print各自捕获OSError；清理对每stage独立处理，确认归属后try采集/finally删除，并继续另一个stage；随后对仍存活的本RUN GPU pod轮询与重试删除。没有为修复修改训练入口或放宽数据/批准门槛。

本子审重跑两个纯本地mock，所有kubectl/服务调用均被替换：

- capture_job在两个stage均抛TimeoutError，仍观察到smoke和full两个删除调用；通过。
- event落盘抛OSError且print同时抛BrokenPipeError，restore仍到达原副本数scale调用；通过。探针在此后主动停止，未假称验证真实集群恢复。

此前两项阻断关闭。当前脚本SHA256：`974379b7f99bcdabee740c2328aa3911272bc30287144ed917e8768525267b62`。

主Agent报告实际PVC/SDK CPU preflight已通过；复核时本机 `evidence/runtime_preflight.json` 尚未出现，本子审未独立读取该次运行结果。已读supervisor确实在pause前要求preflight Job Complete并读取verified结果，成功后才进入暂停服务流程。GPU执行、模型注册及最终服务健康仍以接下来的实际证据为准。

残余边界：恢复健康已确认后的证据文件写入仍可能失败并被保守记为RESTORE_FAILED，但不再阻止前面的清理与scale动作；SIGKILL/宿主失联不在Python finally保证内。当前审查结论不额外要求用户确认，不扩大既有暂停/训练/恢复授权。
