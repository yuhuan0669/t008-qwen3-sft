# 官方原生入口最小适配建议：ms-swift 4.4.2 只读源码核对

本文件是工程兼容性建议，不是训练批准。未修改旧 `run_identity.py`、旧数据/证据包，未启动容器、加载权重、启动 Trainer、GPU Smoke/Full 或停止 vLLM。只读 `nerdctl ps` / `ps -a` 未找到旧 CPU 容器，因此本子审不冒称完成了当前镜像动态检查。

## 精确版本依据

从 [PyPI ms-swift 4.4.2 元数据](https://pypi.org/pypi/ms-swift/4.4.2/json) 下载 wheel，只解压源文件，未安装/导入发行包。wheel SHA-256 已与 PyPI 元数据匹配；定位及哈希见 `evidence/swift_wheel_source.json`。旧镜像已实读的 pipeline、sft_args、dataset/utils、model/register、template/base 共 5 个源文件 SHA-256 与 wheel **全部逐字节相同**，见 `evidence/swift_wheel_vs_actual_earlier_hashes.json`。这支持精确版本源码调查，但不能代替新 CPU 镜像实际 parser/plugin/callback 检查。

所有新源码位于本目录 `evidence/wheel_source/`，关键文件清单哈希见 `evidence/native_source_hashes.json`。

## 原生数据加载必须由正式参数对象驱动

建议正式命令保持：

```text
--dataset swift/Qwen3-SFT-Mixin#2000 swift/self-cognition:qwen3#600
--model_type qwen3 --template qwen3
--model_name 章鱼能碳垂直大模型 "Octacarbon LLM"
--model_author 能碳章鱼（湖北）人工智能科技有限公司 "Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd."
--seed 42 --data_seed 42
--max_length 2048 --truncation_strategy delete
--split_dataset_ratio 0 --eval_strategy no
--use_hf false --dataset_shuffle true
```

用 subprocess 参数列表传递两个英文完整字符串；不得依靠 shell 二次切词。身份字段含义保持“定制模型名称/定制训练主体”，不得改称基础模型原始研发方。

真实调用链：`BaseArguments.load_dataset()` 取 `get_dataset_kwargs()`（其中 `seed=self.data_seed`、中英文 `model_name/model_author`），然后调用 `load_dataset(..., shuffle=self.dataset_shuffle)`。

**旧快照与原生路线有实质加载差异**：公共 `load_dataset()` 函数自身默认 `shuffle=False`，旧 `prepare_official.py` 没有覆盖它；正式 `SftArguments.dataset_shuffle` 默认 `True`。`#600` 的 108×5 次全量曝光后，余 60 条在原生路线按共享 `RandomState(42)` 随机选择，随后总训练集也会 shuffle。两种路线不可假定有序 hash、部分身份模板曝光分布或来源行号相同。即使最终保留数仍为 1642，也须重新实测。

CPU 探针应使用正式 `SftArguments` 的 `args.load_dataset()`，不要分别独立加载两来源再拼接，不要以旧本地 1642 行文件替代训练入口。原生返回的 `dataset` routing tag 可用于真实来源归因；shuffle 后不再假定“索引 0..1999 是 Mixin”。

模板默认 `loss_scale=default+ignore_empty_think`，`delete` 在模板侧转换为 `raise`，由 `AddLengthPreprocessor` 删除整条超长记录。它不是右截断，不需要将原始超长数伪写成零。应冻结原生加载 2600 次曝光的有序 hash，以及真实过滤后的保留数、有序 messages/lengths/token/mask 摘要；保留超长丢弃清单。

## 保存策略：可保留官方 steps 50 并保存最终尾步

精确 `swift/trainers/patcher.py` 的 `DefaultFlowCallbackNew.on_step_end` 在父 callback 后执行：

```python
if state.global_step == state.max_steps:
    if evaluation_strategy != IntervalStrategy.NO:
        control.should_evaluate = True
    if args.save_strategy != IntervalStrategy.NO:
        control.should_save = True
```

`swift/trainers/__init__.py` 导入 patcher，它将 Transformers `DEFAULT_CALLBACKS` 替换为该 callback；`SwiftMixin._save_checkpoint` 将 `last_model_checkpoint` 设为当前 global step 对应目录。

因此本版本可以保持 **`--save_strategy steps --save_steps 50`**，同时在非 50 整数倍的最终训练步触发额外保存。旧 wrapper 注释中“为避免 checkpoint-150 必须 Full 改 epoch”不再符合此版本实际实现。推荐恢复 steps 50，而不是为尾步保存另改训练路线。Smoke 若未来仅设 `max_steps=3`，该 callback 理论上也在第 3 步强制保存；本轮只能检查状态逻辑，不能执行 Smoke。

注册前仍须核实真实结果：进程退出为 0；完整 adapter 文件存在；目录步数等于 `trainer_state.global_step`；Full 的 `global_step == max_steps > 0` 且 `epoch >= 0.999`；最终 `logging.jsonl` 摘要的 `global_step/last_model_checkpoint` 与选中 adapter 一致。当前仅将 checkpoint 内部 global_step 与自身目录比对不构成完整训练尾步证明。不要以 CPU callback 状态测试冒充真实文件已成功写入或 Full 完成。

## external_plugins 只读 guard：可行接口与边界

`BaseArguments.__post_init__` 很早调用 `_import_external_plugins()`，其逐个执行 `import_external_file`。插件只应安装 wrapper，不应在导入时加载模型、读取 GPU、访问 Task 或要求尚未形成的 expected evidence。expected evidence 的存在/hash校验延迟至受保护方法调用；原方法签名/来源文件 hash 不匹配时应拒绝。

精确 pipeline 顺序为：

1. `SwiftSft.__init__`：`_prepare_model_tokenizer()` → `_prepare_template()`。
2. `SwiftSft.run`：`_prepare_dataset()`。
3. `_prepare_dataset`：`_get_dataset()` → `_encode_dataset(..., pre_process=True)` → 拼接 → `_post_process_datasets()`。
4. 然后才 `prepare_model`（LoRA）、Trainer 构造、`train`。

所以包装 `_get_dataset` 和 `_encode_dataset`、在原方法返回后核对，能够在 Trainer/train 前抛错；**不能阻止已进入正常训练构造器的第一次基座权重加载**。GPU 授权硬门禁必须继续在启动 `swift sft` 子进程之前生效。CPU 探针绝不能直接构造 `SwiftSft(args)`；可用 `object.__new__(SwiftSft)` 装配 args、`model=None`、processor 和 train-mode template，再调用所需原方法。

最小 guard 建议：

- 将完整正式 recipe、身份字段、model/template 类型、seed/data_seed、2048/delete、eval=no、split=0、effective `use_hf=False`、默认 loss kwargs 与模型文件 hash绑定到 evidence。
- 明确拒绝 `cached_dataset/cached_val_dataset/val_dataset` 非空、额外 dataset specs、streaming/packing/lazy_tokenize、`pre_process=False` 等绕过默认预处理的入口。否则后续能拼入未检查缓存数据。
- `_get_dataset` 原样调用一次；确认 val 为 None，原生数量、来源 tag 分布与有序 canonical messages hash 与 CPU evidence 一致，然后返回**同一原结果对象**。
- `_encode_dataset` 用原签名绑定参数并确认 `pre_process=True`；原样调用一次；核对过滤后有序 messages **及 `lengths`** hash、真实保留数/来源分布后返回原对象，不做 select/filter/sort/rewrite。
- 仅 messages hash 不足以排除 tokenizer/template 漂移；还需 base完整 hash、实际安装库/关键源码 hash、有效 template kwargs、CPU token/label 哈希证据绑定。
- 默认后处理会再包 `LazyLLMDataset(strict=False)`，遇到新的编码异常可能重试其他行，因此应确认 CPU 预处理已逐行编码并保留零监督/异常检查；不要把 Lazy 重试当作新的质量通过。
- `--use_hf false` 仍可能被环境 `USE_HF=1` 覆盖；必须验证有效 `self.args.use_hf`，不能只检查命令文本。
- 插件按方法标记实现幂等安装，保留 `__wrapped__` 与源码哈希；不得用会允许正式训练跳过检查的通用 observe-only 环境开关。若 CPU 证据形成阶段须调用未保护方法，应仅在专用探针里显式引用保留的原方法，正式入口仍须强制 guard。

## 最小 CPU 动态核验清单（交主 Agent 执行）

1. 在当前固定镜像完成真实 `HfArgumentParser(SftArguments)` Full/Smoke 参数解析；`use_cpu=true/report_to=none/add_version=false` 仅作为探针覆盖，不创建模型/Trainer。核验所有有效字段和无未知参数。
2. 记录实际安装 `patcher.py`、pipeline、loader/data_args/template_args、训练 mixin 的 SHA-256，与本次 wheel 源码对照；确认真正 `trainer.DEFAULT_CALLBACKS` 含 `DefaultFlowCallbackNew`。
3. 不创建 Trainer，仅对真实 callback 使用 synthetic `TrainerState` / `TrainerControl`，在 steps=50、eval=no 下检查中间非保存步、50 步、以及 synthetic max_steps=103 的第 103 步；最终应 save=True、evaluate=False。另测 save_strategy=no 不强制保存。synthetic 103 仅是分支测试，不宣称本次训练真实步数为 103。
4. 按正式参数 `args.load_dataset()` 和真实 `_encode_dataset` 执行 CPU 原生加载/2048 delete；逐行真实 tokenizer/labels/lengths核验，记录前后有序 hash及来源 tag，val=None。不要复用旧快照 hash当原生输入证明。
5. 以新证据启用插件执行同一路径成功；注入一个 wrong expected hash、wrong identity、wrong truncation、cached dataset、pre_process=False 等不匹配，均应在 Trainer/train 前失败。不得在此测试中启动训练构造器。
6. 验证只读 guard 输入/输出是同一对象且数据字节不变；插件 import不创建 ClearML Task/模型/Trainer，不修改源数据，不调用训练。
7. wrapper 在缺少明确 GPU/实验/来源/身份批准时，启动子进程与 ClearML Task 之前必须拒绝。`RUN_AUTHORIZED=yes` 等环境字符串不能替代可信批准记录；不要自动生成审批 true。
8. 原本地快照验证函数与零超长 gate 只保留为历史/本地数据模式；新原生 gate 应区分“2600加载曝光、原生delete后实际训练行数”，绑定新 evidence，而不是把本地1642目录换名伪装原生输入。

上述 CPU 检查通过后，也只说明入口适配/原生加载/过滤/保护逻辑可复算。GPU窗口、业务服务状态、独立数据裁定及未来训练授权仍是独立门禁，本轮必须停止在训练之前。
