# v1.2 执行修复版｜审查与测试记录

**审查对象**：原v1.1执行附件评审所列2项版本/门禁冲突与5项脚本边界缺陷；基线为v1.1.1校核版。

## 修复证据与执行状态

| 问题 | v1.2处理位置 | 静态/模拟结论 | 现场状态 |
|---|---|---|---|
| 文档和身份字段分叉 | 包内权威MD、根目录MD SHA一致，`identity-spec.example.json`四字段，`prepare_official.py`剔除仅说明的`note` | 已修复 | 主体真实批准未核验 |
| 2600行硬编码导致清洗死锁 | `derive_snapshot.py`与`run_identity.validate_training_dataset`双链核对（独立批准的行数+数据hash+manifest hash，父快照+排除清单+顺序） | 正常2600、合法2599、伪造数据/审批不一致测试通过 | 真实清洗证据未生成 |
| 无验证集评估/save行为 | `run_identity`兼容检测后强制`eval_strategy=no`，Full按epoch，Smoke 3步，显式data_seed42 | 代码检查通过；未运行真实CLI | 待现场固定ms-swift镜像读回 |
| `{{AUTHOER}}`笔误漏检 | `prepare_official`通用占位符正则 | 合成模板注入被拒绝 | 真实数据未拉取 |
| 静默删除超长样本 | `preflight_data`逐样本Token计数+ms-swift真实模板证据标志；`run_identity`对最终预检报告 SHA 与0超长检查 | 假Tokenizer超长行识别、无真实证据拒绝训练 | 待实际Qwen3/ms-swift编码比对 |
| 非Thinking异常和基础模型错配 | `eval_identity`检查全部原始基础权重文件SHA，检测`unexpected_think_tag` | 模拟基础权重篡改及标签溢出测试通过 | 推理未运行 |
| B/D Prompt SHA 不一致 | `register_evaluation.validate_comparisons`相同case/模式/生成参数/模型/引擎分组并比对SHA字符串 | 同Prompt接受、不同Prompt拒绝、重复及变参拒绝 | ClearML SDK未连接 |

## 本地执行命令和结果

```text
python3 -m py_compile *.py tests/test_contract.py  -> PASS
bash -n train_identity.sh                          -> PASS
python3 -W error::ResourceWarning -m unittest discover -s tests -v
  -> 17 tests, 0 failed, 0 errors (CPU合成样本/Mock)
```

上述测试是**当前生成环境内的静态检查和合成数据模拟**，不能替代真实官方数据许可复核、模型权重/Tokenizer、ms-swift训练CLI/模板、GPU BF16/显存、K8s回滚、ClearML真实文件回读、独立业务评测。

## 交接阻断（真实执行Agent清单）

1. 获取真实基础模型只读权重、训练镜像、官方两份数据及实际许可证证据，核验产品名称与合法定制主体。
2. CPU用官方loader做原始2600行快照；如需排除，单独生成排除版本、审查理由和审批；不得修改原始快照。
3. 在实际固定镜像核对CLI`eval_strategy`/`data_seed`/`save_strategy`、样本长度/loss mask与真实保留数量，冻结`swift-template-evidence.json`和最终`preflight_report.json`。
4. 核对独立审批记录真实签发者/权限，绑定样本数及全部文件哈希，才可请求有时效的GPU维护窗口；需要同时覆盖训练+大批量A/B/C/D串行生成或安排不同窗口。
5. Smoke、正式训练、ClearML真实OutputModel下载校验、Independent Review、原vLLM恢复均需真实测证；Adapter始终为Candidate，禁止自行发布。

**本轮不宣称训练、部署、Source许可或ClearML联调已经完成。**
