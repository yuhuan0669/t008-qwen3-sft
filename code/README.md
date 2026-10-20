# T-008 v1.2｜官方原生2048正式入口（CPU已核验，GPU未授权）

当前默认正式入口是 `train_identity.sh full` → `run_identity.py` → Swift 原生加载：`swift/Qwen3-SFT-Mixin#2000`、`swift/self-cognition:qwen3#600`。不以本地1642行衍生文件代替原生输入，不做额外语义清洗、重配或补采。`max_length=2048`，不覆盖Swift默认`truncation_strategy=delete`；插件核验其实际值。`identity-spec.confirmed.json`记录负责人确认过的四个中英文名称及基座，不能把定制主体当作Qwen基础模型原始研发方。

## CPU核验入口

在固定的CPU隔离环境中（无GPU设备、base和历史快照只读）运行：

```bash
bash train_identity.sh cpu-check \
  --model /base \
  --identity-spec identity-spec.confirmed.json \
  --evidence-dir /work/NEW-nonexistent-evidence-dir \
  --reference-snapshot /reference/original-v1.2/train.jsonl \
  --base-files /reference/evidence/template/original-final/base-files.json
```

解析正式Full argv，再仅覆盖use_cpu=true、report_to=none、add_version=false以执行真实SftArguments后初始化、args.load_dataset、Qwen3 tokenizer与真实SwiftSft._encode_dataset原方法。不会实例化SwiftSft、加载模型权重、创建Trainer、ClearML Task或训练子进程；对基座文件做完整SHA读取不等于加载模型权重到内存。`evidence/native-proof`中的两个JSONL是复算证据，不是正式训练输入。

## 正式训练入口的准备条件（本轮不得执行）

后续经真实GPU窗口及实验授权后，运行单元必须绑定：BASE_MODEL、IDENTITY_SPEC、NATIVE_PREFLIGHT_REPORT、OUT_DIR（必须不存在）、TRAIN_IMAGE_DIGEST、SOURCE_GIT_COMMIT、APPROVAL_FILE，以及RUN_AUTHORIZED=yes和GPU_WINDOW_APPROVED=yes。还需要可导入的ClearML SDK、实际凭据引用和HTTPS CLEARML_FILES_HOST。没有这些条件会阻断；准备脚本不生成approval.json。CPU模式不要求伪造这些批准。

批准记录除原有literal JSON true的身份/来源/实验/GPU窗口确认和decision_ref/source_snapshot_ref外，须由责任人绑定真实native_preflight_report_sha256、approved_rows（实际过滤保留数）、approved_data_sha256（native_input的canonical dataset摘要，非JSONL文件SHA）、preflight_model_files_sha256。CPU报告本身有SHA且含原生输入/过滤结果、包版本、模板参数和实现指纹。旧数据选择已经确认，不需要重新裁定配比；上述记录用于未来作业精确输入与真实GPU授权绑定，不是本轮新增数据政策审批。

Full使用steps/save_steps=50。当前实装Swift4.4.2 callback还在最后一步强制保存；wrapper必须同时核对Swift终态logging.jsonl、checkpoint目录、trainer_state.global_step/max_steps及epoch，才登记Candidate。Smoke仍是独立的3步路径，需要独立获批，CPU检查不启动它。训练产物的真实生成/上传回读需GPU阶段验证。

`native_guard.py`是只读external plugin：原样返回官方加载/过滤后的对象，检查有序数据全部列（包括过滤产生的lengths）摘要、名称、模板、包版本以及批准的报告SHA；发现漂移或cached/streaming/packing/lazy等旁路就失败。基座完整SHA和代码/Swift关键源码指纹由父入口核对。注意未来Swift实例化会在数据guard运行前加载基座；guard保证漂移时不进入Trainer/train，不声称漂移失败发生在Task或GPU模型加载之前。

本轮不启用USE_QLORA/USE_LIGER等优化。旧prepare_official/derive_snapshot/preflight_data和本地快照校验函数留作历史复算兼容，**不再是正式main的数据路径**；其严格旧契约未放宽。QA_REPORT_v1.2.md为历史修复说明，当前结论以本轮reports及CPU证据为准。

## 复核

```bash
python3 -m py_compile *.py tests/*.py
bash -n train_identity.sh
python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

完整CPU容器运行配方、AST索引适配、可信证书bundle及检查脚本在交付包scripts和evidence。基础镜像没有ClearML SDK；最终训练Job/PVC、SDK overlay、凭据和服务切换清单尚待绑定。当前GPU No-Go，CPU通过不代表模型内容质量或上线验收通过。
