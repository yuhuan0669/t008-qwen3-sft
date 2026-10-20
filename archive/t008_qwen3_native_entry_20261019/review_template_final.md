# 官方原生入口适配｜最终工程审核

结论：本次官方原生两来源入口、实际 CPU 参数/模板路径、默认 2048 delete、只读 guard 与末步保存 callback 的工程核验通过。复读当前实现和已交付证据后，未发现本范围内尚须修复的工程阻断。该结论只覆盖 CPU 准备及入口保护，不授权 GPU Smoke/Full、不证明训练、模型质量或模型验收完成。

这是继承前序工作上下文的工程复核，不是盲审独立验收。本子审只读最终代码/证据并进行文件哈希、行序、计数与映射复算，没有再次启动容器、执行训练或修改实现。

## 1. 正式参数和真实 CPU 路径

已读取 `code/native_recipe.py`、`code/native_guard.py`、`code/run_identity.py`、`code/train_identity.sh`，并核对 `evidence/native-proof/{formal-command,formal-parser,native-preflight}.json`。

只读回查代码仓库实际提交为 `e7ae45aa7438c8bcca8318d3531854f7f5e7db39`，`git status --porcelain` 无变更输出；本报告位于代码仓库外，不改变该实现提交。

正式命令的 `--dataset` 仍为：

```text
swift/Qwen3-SFT-Mixin#2000
swift/self-cognition:qwen3#600
```

没有将本地 1642 行候选作为正式训练输入。中英文名称、定制主体与 Qwen3-8B 基础模型标识正确保留；两个英文名称/主体作为各自单独参数传递。seed/data_seed 都为 42，split ratio 为 0，eval strategy 为 no，无训练派生 held-out。Full 为 LoRA rank 8 / alpha 32 / all-linear / BF16 / 一轮，正式保存策略为 steps、每 50 步保存。

ms-swift 4.4.2 的实际参数对象确认 `dataset_shuffle=True`、`max_length=2048`、训练 `truncation_strategy=delete`、模板侧 `raise`、`loss_scale=default+ignore_empty_think`。delete/shuffle 使用实际默认值并校验有效值，未另造采样或截断算法。`formal_unknown_flags=[]`。

CPU 检查使用真实 `SftArguments.load_dataset()`，继而对 metadata-only stub 调用真实 `SwiftSft._encode_dataset` 原方法；没有调用会加载权重的 `SwiftSft.__init__`。仅覆盖 `use_cpu=true`、`report_to=none`、`add_version=false`。实测版本：ms-swift 4.4.2、Transformers 5.14.1、PEFT 0.20.0、Torch 2.11.0+cu130、tokenizers 0.22.2、datasets 4.8.4、ModelScope 1.38.1。

## 2. 原生采样和默认 delete 的结果

| 项目 | 原生加载 | 默认 delete 后 |
|---|---:|---:|
| 总曝光行数 | 2600 | 1642 |
| Mixin | 2000 | 1042 |
| 身份 | 600 | 600 |
| 不同 messages 记录 | 1108 | 629 |
| 最大 token 长度 | 2511 | 2048 |

958 行因超过 2048 被真实默认 pipeline 删除整行，无右截断或静默正文改写。保留数据共 1,608,210 tokens，其中监督 tokens 为 1,553,672；val 为 None/0 行。2600 行无截断审计均有正数监督 tokens，labels 长度/监督位置一致性由实际探针断言检查。

本子审独立读取冻结的 loaded/retained JSONL 和完整 row-audit 后复算确认：

- 2600 行审计索引连续完整，958 行超长、1642 行保留。
- 保留 **有序 messages 序列**恰等于 raw 按实际长度 `<=2048` 过滤的结果，不仅是集合或数量一致。
- 原生 `dataset` routing tag 独立复算也得到 `2000+600 → 1042+600`。
- 全行 canonical JSON 哈希与报告的 `native_input/native_retained` 相符。

原生入口与旧快照的区别已明确冻结。公共 loader 默认 shuffle=False，而正式 SFT 参数默认 True；二者内容全集同为 1108 条，但行序及身份曝光多重集不同。身份仍是 108 个模板产生 600 次曝光：60 个模板出现 6 次，48 个出现 5 次；与旧快照相比 48 个模板改变 5/6 次分配（24 个 6→5，24 个 5→6）。本子审复算确认该差异，不能把 600 次曝光解释为 600 个不同身份问题，也不能继承旧快照的有序哈希。此处是本轮授权采用原生默认 loader 的实测结果，未实施额外重加权。

`evidence/native-sampling-comparison.json` 和 `native-proof/source-row-map.jsonl` 保留区别及映射。内容全集相同仅证明来源内容可追溯，**不证明这些内容已通过全量语义质量审核**；之前的内容审核结论不会被本次机械通过自动覆盖。

## 3. guard 与授权门禁

实现已修复先前发现的三项问题：插件不再因缺证据而静默不安装；wrapper 将批准报告 SHA 固定传给子进程，guard 每次读取都复查 bytes；身份中英文 names/authors 与冻结报告逐一核对。

guard 包装真实 `_get_dataset` / `_encode_dataset`，不改变输入数据或过滤规则；核对原生 raw 和 post-filter 全行有序 hash，其中 post-filter 记录包含 `lengths`。缓存训练/验证数据、额外验证集、streaming、packing、lazy tokenize、跳过预处理等不符合路线的入口被拒绝。入口代码和关键 Swift 源文件 hash 已绑定到报告；当前 4 个入口文件 SHA 与报告全部一致。

已读取 `native-guard-checks.json`、相应日志和检查脚本：正例通过，且以下 5 个反例全部被实际插件拒绝：报告 SHA 变化、身份变化、cached dataset 绕行、`pre_process=False`、输入行序变化。

测试边界需准确保留：guard 正例中的 `_get_dataset` 使用冻结 `native-loaded.jsonl` 回放来稳定验证 wrapper，未在该次 guard 测试中重新请求来源；真正正式参数驱动的原生加载已由 `cpu-check` 另行执行。组合证据支持这两层行为，但不是启动 Full 的完整训练端到端测试。

现有 `RUN_AUTHORIZED/GPU_WINDOW_APPROVED` 与严格 JSON true 的身份、两来源、实验和 GPU 窗口授权要求仍在 `swift sft` 子进程和 ClearML Task 创建之前。批准必须绑定新的 native report、输入 hash、实际保留数与基座 hash；CPU evidence 的 `verified=true` 不会自动生成任何审批 true。

pipeline 顺序限制仍然存在：正常 `SwiftSft.__init__` 首先加载基础模型，后在 `run` 中核对数据。因此 guard 能阻断后续 LoRA 准备、Trainer/train，不能声称阻止了正常训练构造器第一次加载基座。控制该动作的仍是外层训练/GPU授权门禁。

## 4. 最终 checkpoint 保存

已读取真实镜像的 `final-save-callback.json`。实际安装的 `DefaultFlowCallbackNew` 已注册为默认 callback，源码 hash 与调查的 4.4.2 发行源码一致。9/9 synthetic state 场景通过：25/102 非保存步不保存，50/100 周期步保存，103/103 非整周期末步强制保存，100/100 整周期末步保存，两种 Smoke 末 3 步设置保存，save=no 时末步不强制保存；所有场景 eval=no 均未触发评估。检查前后 CUDA 均未初始化。

所以 Full 可以保留官方 steps/50，同时获得本版本末步强制保存逻辑，无需改成 epoch 保存。callback 只验证 **保存决定**，没有创建任何真实 checkpoint，也未证明磁盘写入、adapter完整性或实际一轮训练完成。synthetic max_steps=103 不等于本项目已实测的优化器步数。

未来 Full 包装器还要求实际 terminal `logging.jsonl` 记录、最终 checkpoint 路径、global_step、max_steps 和 epoch 相互一致，再进入 adapter 打包/登记；这比仅检查 checkpoint 自身目录名严格。本轮没有运行这些训练后操作。

## 5. 测试和冻结指纹

已回读本地测试日志及真实镜像测试日志：同一组 **32 项测试在两环境各通过**，不是 64 个不同测试。真实原生 CPU 检查、9 个 callback 状态场景、guard 正例/5 个反例属于另行明确列出的行为证据。

注意报告内 `native_input.sha256` 与 `native_retained.sha256` 是 **全行列表 canonical JSON 哈希**，不是下载文件的字节 SHA：

| 对象 | SHA-256 |
|---|---|
| 原生加载全行 canonical JSON | `fe0911174ed4a9b4f088804a901409d25be1af00c3cdd8a9f6981df1e6abe7aa` |
| 原生保留全行 canonical JSON | `9fa63f2d87ac24130a6e4f7c31ebcfd6c91ddb5a91c8bad716326e5c708f43aa` |
| native-preflight.json 文件 bytes | `bc602fe28f782200b3351b9130e0cfd40807e67fe6ed20a0660a4f240a0247ed` |
| native-loaded.jsonl 文件 bytes | `d85dbe58d9c5fab98bbf6a81cf828147ba1a47d6cce492aef107c7d3dafa604c` |
| native-retained.jsonl 文件 bytes | `ed0278ad28f1613592d99cf9705acf83e2952be85592c6d8751f536920e92618` |
| source-row-map.jsonl 文件 bytes | `bc5789abcb1bcda9ee684afbff5ade174b70a5cfb1d88dd730523d0423361279` |
| final-save-callback.json 文件 bytes | `468e9db5610ba7072fc6020d8d9baa0d90ae69678a2ac6b3d12dedccc1cbb073` |
| native-guard-checks.json 文件 bytes | `ec8d8d9c8353ad0cfa6b2fc63659d12e124e3aa49961bebd362a6ef446b83abf` |

基座完整文件清单聚合 hash 仍为 `39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374`，新 CPU 代码对清单中的基座文件重新逐字节计算 SHA 并匹配，没有将仅核大小描述为完整重算。

## 6. 本轮结论的使用范围

可以将本结果用于确认：官方原生加载入口已适配、CPU实测可复算、默认 delete 行为和身份曝光差异已记录、未来运行具备数据/证据一致性保护。

不能据此确认：样本已全量语义合格、原始身份模板对研发主体的措辞已得到最终批准、数据使用许可或训练准入已代签、GPU资源窗口已授权、GPU kernel/真实前向/显存/吞吐通过、ClearML Task/Model 写入成功、训练尾步已真实保存、A/B/C/D评测或模型验收完成。无 GPU Smoke/Full、vLLM 停止或模型发布操作由本审核发起。

工程适配/CPU核验：**通过本范围检查**。GPU训练执行：**保持在门禁之前，等待下一阶段明确授权**。
