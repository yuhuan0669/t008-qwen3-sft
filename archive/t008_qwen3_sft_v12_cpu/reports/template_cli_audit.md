# T-008 v1.2 CPU：实际 Tokenizer、ms-swift 模板与 CLI 核验

结论：原始 2600 次曝光中 958 行超过 2048-token 训练上限，实际 ms-swift 默认预处理仅保留 1642 行。独立长度衍生候选的 1642 行通过真实 HF Tokenizer 与实际 ms-swift 模板/标签/保留数量机械核验。该通过只涉及 CPU 编码，不构成来源、身份措辞、数据变更、GPU 窗口、训练或模型验收批准。

## 实测环境与边界

- 主机：`k8s-worker05`；既有隔离容器：`t008-identity-v12-cpu`。
- `/base` 为只读真实基座；未加载 8B 权重、未创建 Trainer、未启动训练。所有探针断言 `torch.cuda.is_available()==False`。
- ms-swift `4.4.2`、Transformers `5.14.1`、PEFT `0.20.0`、PyTorch `2.11.0+cu130`、tokenizers `0.22.2`、datasets `4.8.4`。
- 真实 config：`Qwen3ForCausalLM`、`model_type=qwen3`、36 层、hidden 4096、vocab 151936、BF16。processor 实际类名为 `Qwen2Tokenizer`，由实际 qwen3 模型注册加载，类名本身不是模型身份不一致证据。
- 16 个基础文件逐字节 SHA-256 清单：`evidence/template/original-exact/base-files.json`；合计 16,397,461,896 字节。完整清单按 v1.2 `base_fingerprint` 原有 JSON 序列化方法聚合 SHA-256：`39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374`。
- 首轮完整读取基座文件计算哈希；后续在同一只读 `/base` 挂载复用该清单并复查文件/大小，报告中显式保留复用路径与依据，未把复用描述为再次逐字节计算。

## 数据与真实保留数量

| 快照 | 行数 | HF 超长 | HF min/max/mean | Swift 超长 | Swift 实际保留 |
|---|---:|---:|---|---:|---:|
| original-v1.2 | 2600 | 958 | 30 / 2515 / 1399.25 | 958 | 1642 |
| length-candidate-v1.2 | 1642 | 0 | 30 / 2048 / 979.20 | 0 | 1642 |

- 原始 `train.jsonl` SHA-256：`dda551041a12c460b84056f2c58df0ab60f2e9999e0518f116cf5f5b3c5faf6e`。
- 长度候选 `train.jsonl` SHA-256：`ad06235bcf0df01f7de4fbfb4f2fe3b156429444478bb1ef0a22cc7ab322b111`。
- 原始 Swift token 总数 3,635,635、监督 token 3,515,952；候选总数 1,607,849、监督 token 1,553,336。
- 原始 Swift 长度 min/p50/p90/p95/p99/max：30/1689/2133/2158/2217/2511；候选为 30/1250/1894/1954/2030/2048。
- HF 与 Swift 使用各自真实模板实现，个别长度不同；两者都独立执行，未把 HF 计数替代 Swift 训练路径证据。
- 原始 958 行排除占 36.8462%。该比例会改变通用/身份混合权重，候选不继承原始数据的训练批准。原始与候选的删除映射由主任务独立衍生清单提供。

## 实际模板和 loss mask

真实调用链为：`swift.model.get_processor('/base', model_type='qwen3', download_model=False)` → `SftArguments.get_template_kwargs()` → `swift.template.get_template(...)` → `template.set_mode('train')` → `AddLengthPreprocessor(template)`。保存的 `SwiftSft._encode_dataset` 源码确认该类正是普通非 streaming、非 lazy SFT 的实际数据预处理类；不是自行模拟的截断器。

`get_processor` 内部显式 `load_model=False`。`SftArguments` 的 CPU 元数据初始化不创建模型/Trainer。实际默认训练配置为 `template=qwen3`、`template_backend=swift`、`use_chat_template=true`、`loss_scale=default+ignore_empty_think`、`truncation_strategy=delete`、`strict=false`。训练参数中的 `delete` 在模板层映射为 `raise`，由数据预处理器捕获超长并删除整行，绝非静默切断正文。

无截断逐行预检将 `template.max_length=None` 明确解除上限。仅向 `get_template` 传入 `max_length=None` 会自动回退模型最大长度 40960，故探针显式清除该属性。每行保存零基行号、token 数、masked/supervised 数、input_ids/labels SHA-256，不输出源对话正文。

所有原始/候选行均存在 prompt mask、监督 token 大于零，所有监督位置满足 `labels==input_ids`。另用独立合成 system/user/assistant 哨兵验证角色语义：57 tokens 中 41 个 mask、16 个监督；system 正文 `[3,15)`、user 正文 `[20,32)` 全为 `-100`，assistant 正文 `[41,55)` 监督，结尾 `im_end` 和换行监督。自动插入的 `<think>\n\n</think>\n\n` 空思考前缀在默认 `ignore_empty_think` 下 mask。该测试使用合成内容，未向日志泄露数据正文。

候选 `AddLengthPreprocessor` 输出的逐行 token 哈希多重集与显式无截断检查的合法行多重集完全相同。候选 `swift-template-evidence.json` 的 `verified=true` 只表示上述实测成立；原始因为 958 超长而为 `false`。

## CLI 兼容性发现与修复依据

1. 当前镜像的 `swift sft --help` 只展示外层 `tuner_backend`，不能证明内层参数缺失。安全执行 `from swift.pipelines import sft_main; sft_main(['--help'])` 可得到真正训练参数帮助，并在帮助退出前停止。主任务已据此添加 CLI 帮助 fallback，训练批准门禁不变。
2. 对通用本地路径 `/base`，`SftArguments` 不能在 `qwen3` / `qwen3_emb` / `qwen3_reranker` 中自动选型。显式 `--model_type qwen3 --template qwen3` 后 CPU 初始化成功。
3. Transformers 5.14.1 的 `apply_chat_template` 返回 `BatchEncoding`，它是 `Mapping` 而不是 `dict`。原 v1.2 仅检查 `dict`，错误地把字典键数 2 当作 token 数。首个失败报告 `evidence/template/baseline_mapping_bug_report.INVALID.json` 仅作故障证据，不可用作预检通过证据。主任务将检查改为 `collections.abc.Mapping` 后重跑，得到上表真实值。
4. 真实 HF parser 对 Full 与 Smoke 原有训练参数均无未知项。加入显式 qwen3 选型后，真实 `SftArguments.__post_init__` 和 `training_args` CPU 初始化成功：`eval_strategy=NO`；Full `save_strategy=EPOCH`；Smoke `save_strategy=STEPS,max_steps=3,save_steps=3`；data seed 42；LoRA rank 8 / alpha 32 / target `all-linear`；BF16；max_length 2048；split ratio 0；gradient checkpointing 开启。
5. CPU 初始化仅覆盖 `use_cpu=true, report_to=none, add_version=false`，避免 GPU、跟踪写入与版本输出副作用。`report_to=tensorboard` 原参数已完成 parser 验证，未执行实际 callback、ClearML Task、GPU kernel 或训练前向。

`torch_dtype`、`warmup_ratio` 的弃用提示在当前镜像仍可解析；导入时缺少可选 `kernels` 的 CPU 4-bit GEMM 提示没有影响本轮普通 LoRA 编码。未启用 QLoRA，也未由此证明未来 QLoRA 兼容。

## 证据与复算

- `scripts/template_probe.py`：实际模板、mask、逐行 hash 与保留数量核验；final 原始和候选 `summary.json` 记录执行脚本 SHA-256。
- `scripts/cli_probe.py`：实际 parser 与安全 CPU dataclass 初始化；`evidence/template/cli/cli_parse.json` 保存失败与最小修复后的结果。
- `scripts/tokenizer_probe.py`：执行 v1.2 `preflight_data.scan`，仅显式复用先前逐字节实测的只读基座 fingerprint，不修改基线源码或源数据。
- `evidence/template/original-final/`：原始真实 Swift summary、2600 行 mask/token 审计、958 行 exceptions、HF `preflight_report.json`（`ms_swift_template_verified=false`）。
- `evidence/template/length-candidate-final/`：候选真实 Swift/HF 结果、1642 行审计、空 exceptions、绑定真实模板证据的 `preflight_report.json`（`ms_swift_template_verified=true`）。
- 各目录保存 API 源码片段、实际安装文件 SHA-256、合成 role mask 测试；原始及候选运行日志位于 `evidence/template/*.log`。
- 探针脚本均通过 Python 语法编译；真正可信的行为证据是本轮实际 CPU 执行和逐行/流水线哈希一致性。

复算命令（在现有 CPU 容器内部执行，输出目录必须不存在）：

```bash
python /work/probes/template_probe.py \
  --dataset /work/length-candidate-v1.2/train.jsonl \
  --out /work/evidence/template/reproduce-candidate \
  --base-fingerprint /work/evidence/template/original-exact/base-files.json
python /work/probes/tokenizer_probe.py \
  --dataset /work/length-candidate-v1.2 \
  --base-fingerprint /work/evidence/template/original-exact/base-files.json \
  --evidence /work/evidence/template/reproduce-candidate/swift-template-evidence.json \
  --out /work/evidence/template/reproduce-candidate/preflight_report.json
```

GPU Smoke/Full 仍应 **No-Go，等待下一阶段授权**。本报告不对待裁定的身份语义、许可/数据用途、候选变更批准或受控 GPU 资源作代签。
