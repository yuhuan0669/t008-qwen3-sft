# Qwen3-8B 自我认知SFT v1.2｜执行包说明

**版本性质：CPU与静态门禁修复，不表示已经下载真实官方数据、取得授权或完成GPU/ClearML联调。** 与压缩包根目录《Qwen3-8B_自我认知SFT_完整实施方案_v1.2_执行修复版.md》互为唯一权威版本。原v1.1/v1.1.1留档不覆盖。

## 内容与用途

| 文件 | 作用 |
|---|---|
| `identity-spec.example.json` | 四个模型身份字段与基础模型名的**待现场核对**示例；没有训练无效的`note` |
| `prepare_official.py` | 按官方ms-swift `load_dataset`做原生采样/身份替换，严格输出2600行原始冻结快照，检查残余`{{...}}`占位符 |
| `derive_snapshot.py` | 仅针对**有编号、有理由**的异常条目生成排除式衍生快照，不修改原始快照、不自动批准 |
| `preflight_data.py` | CPU原样本Tokenizer/Chat Template长度统计，并要求独立真实ms-swift模板证据；没有证据时仅输出未验证报告 |
| `run_identity.py`、`train_identity.sh` | 具备明确授权、数据和模型SHA、预检及真实GPU窗口后启动Smoke/Full；全链路登记ClearML Candidate，不自动发布 |
| `eval_identity.py` | 核对**真实**基础权重及Adapter哈希，串行transformers+PEFT推理；分辨意外Thinking标记 |
| `register_evaluation.py` | A/B/C/D完整性、System Prompt哈希和生成参数一致性校验后，上传Reviewer摘要/哈希到ClearML |
| `tests/test_contract.py` | 合成数据17项CPU测试（无真实模型与GPU） |

## 运行次序和失败即停原则

1. **CPU身份/许可核验**：检查四身份字段、Qwen基础模型来源、两份官方数据许可/revision及真实权利；冻结独立评测题。不能将项目README中的测试数据或模板当审批。
2. **官方原始冻结**：`python3 prepare_official.py --spec "$WORK/identity-spec.json" --out "$WORK/original-v1.2" --seed 42`。脚本拒绝实际行数不是2600和任何`{{NAME}}`/`{{AUTHOR}}`/`{{AUTHOER}}`等残留。
3. **如需清洗**：先由Review角色确认排除零基行号，记录原因，存为`[{"index": 31,"reason": "经审核身份混淆，批准剔除"}]`，执行`python3 derive_snapshot.py --parent "$WORK/original-v1.2" --exclusions "$WORK/exclusions-reviewed.json" --out "$WORK/derivative-v1.2"`。只排除，不可静默改写或重新采样；如需修改正文，应另行审批变更，不使用本脚本冒充官方复现。
4. **CPU长度预检**：`python3 preflight_data.py --dataset "$DATA_DIR" --model "$BASE_MODEL"`。输出初稿`$DATA_DIR/preflight_report.json`，其中`ms_swift_template_verified=false`，**不能训练**。
5. **真实ms-swift模板核验**：固定实际训练镜像，使用一致的model、dataset、template、loss mask、`max_length=2048`在CPU核实训练pipeline实际保留行数及超长行数；留原始终端日志/版本/代码引用，形成`swift-template-evidence.json`，内容格式参考下方。仅凭transformers的Tokenizer预检不等于此步骤。
6. **重新冻结最终预检报告**：`python3 preflight_data.py --dataset "$DATA_DIR" --model "$BASE_MODEL" --out "$DATA_DIR/preflight_report_verified.json" --swift-template-evidence "$WORK/swift-template-evidence.json"`。若无超长且证据与当前数据/模型匹配，在受控目录中用`mv "$DATA_DIR/preflight_report_verified.json" "$DATA_DIR/preflight_report.json"`替换初稿，计算最终文件SHA；**未经现场核验不得填写`verified=true`。**
7. **独立批准**：由有权责任人确认真实身份/来源许可/数据SHA/行数/预检SHA，签发`approval.json`（不能引用示例文件作为批准）。衍生数据还需父快照路径、变更审批引用与确认。此文件的存在并不自动证明批准人真实有权，执行Agent仍须检查批准系统中的原始决定。
8. **GPU窗口**：由实际受影响系统管理员授权、备份K8s恢复点，验证`swift sft --help`是否支持训练时参数；再设置`BASE_MODEL DATA_DIR APPROVAL_FILE TRAIN_IMAGE_DIGEST SOURCE_GIT_COMMIT RUN_AUTHORIZED GPU_WINDOW_APPROVED OUT_DIR`运行`bash train_identity.sh smoke`与新目录下的`bash train_identity.sh full`。不支持`eval_strategy no`、`data_seed`、`save_strategy`直接阻断，不猜参数名。
9. **对照评估**：另按实际串行推理耗时申请GPU资源，四组A/B/C/D保持相同案例、seed、生成参数、base、engine；B/D使用相同System Prompt文件字节。独立Reviewer记录结果摘要；`register_evaluation.py`登记，不提交逐条试题/回答。
10. **恢复与发布**：恢复原vLLM Deployment并实测；新Adapter保留Candidate，未单独批准不得发布。

### 实际ms-swift核验证据JSON（结构示例，**不是审批/实测值**）

```json
{
  "verified": false,
  "evidence_ref": "在固定真实ms-swift镜像中执行的模板/标签掩码/长度检查日志或任务地址",
  "dataset_sha256": "实际train.jsonl哈希",
  "model_files_sha256": "实际训练基础模型文件清单哈希",
  "rows_checked": 2600,
  "max_length": 2048,
  "overlength_rows": 0
}
```

**注意：** `verified`必须由实际ms-swift流水线证据审核后改成`true`；`dataset_sha256`和`model_files_sha256`必须为确切hash，`rows_checked`按现场事实填写。脚本只能校验该记录与数据/模型字节是否一致，**不能替批准人确认记录是否真实**。`ms-swift`实际模板证据的生成/检查由具备真实训练镜像的Agent实施，当前交付没有完成该项现场步骤。

### 训练批准 `approval.json` 扩展字段（展示结构，不是放行授权）

需要保留原有`identity_verified`、`experiment_approved`、`gpu_window_approved`、`sources_approved`、`decision_ref`、`source_snapshot_ref`等字段，并添加：

- `approved_rows`: 经批准的实际训练行数；原始2600或衍生值。
- `approved_data_sha256`: 当前训练目录`train.jsonl`的SHA-256。
- `approved_snapshot_manifest_sha256`: 当前目录`manifest.json`的SHA-256。
- `preflight_model_files_sha256`: 预检使用的**完整基础模型文件清单哈希**。
- `preflight_report_sha256`: **最终**`preflight_report.json`的SHA-256。
- 若清洗：`data_change_approved=true`、非空`data_change_ref`和`parent_snapshot_dir`（指向确切原始快照）。

SHA都是**对最终文件字节**计算。建议把批准文件放在不同受控目录，授权签核不得由准备数据脚本自动填写。每项hash可以用`sha256sum FILE`检验（模型文件清单哈希由`preflight_data.py`自动报告）。

## 本地复核命令（只用合成数据）

```bash
python3 -m py_compile *.py tests/test_contract.py
bash -n train_identity.sh
python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

以上仅证明代码静态/模拟约束；Qwen3-8B完整训练、官方数据下载、真实ms-swift CLI/模板、许可、K8s停启、ClearML OutputModel回读、实际A/B/C/D推理均需后续真实环境核验。本包不会主动操作这些系统。
