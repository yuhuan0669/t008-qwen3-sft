# 准备脚本只读复核

结论：在当前 4 个脚本及已读取的本地配套配置范围内，未发现阻止主 Agent 进入实际 CPU 准备验证的实质问题。此结论仅为静态控制流、数据绑定与统计口径复核，不代替实际 Swift CPU 编码结果，也不授权训练、推理或 UAT 变更。

完整阅读：`assemble.py`、`verify_candidate.py`、`run_cpu.py`、`cpu-check/check_cpu.py`。为核对调用边界，另只读查看当前 `pod-cpu.json`、v14 `training-config.json`、`identity_loss3.py`、CPU 报告的版本/源文件绑定字段，以及 `local_data_guard.py` 和 v20 `source-bindings.json`。

| 核查点 | 结论及依据 |
|---|---|
| 父对象 | 数据与训练参数都取自 `stage1-cpu-v0.1.14`；v17 仅供已有语言标记。只读重算 5 个父文件绑定 SHA256 全部一致。父训练集和行映射均为 1325 行。 |
| 通用记录和曝光 | 台账实际有 518 个 ID，覆盖 1030 个不重复父行号，恰等于父集全部通用数据行。组装逐父行应用同一 ID 的决定；没有按内容去重。修订和隔离均保留逐次曝光的变更/隔离记录。 |
| 不静默丢行 | 完整决策集合、父行同一性及补丁出现次数均断言；组装后总行数加隔离数必须为 1325。验证器再检查候选行映射顺序、隔离 ID 的曝光 Counter、保留行原始字节及修后对象。即使组装 `zip` 的输入被缩短，总数断言也会失败，不能静默通过。 |
| 不静默截断 | CPU 先用无长度上限模板检查每行，超过 2048 直接失败；再走真实 `_encode_dataset`，逐阶段比较消息及重复次数 Counter；逐记录受限/无限编码的 input_ids、labels、loss_scale 必须完全相同。空监督也直接失败。报告中的零截断/零丢行须以这些断言实际成功为前提。 |
| 身份与非通用数据 | 父数据只读计数确认 295 条非通用、其中 234 次身份曝光。组装及验证器逐对象/顺序比较全部非通用行；验证器固定检查 295/234，并核对身份文件哈希。CPU 再比较身份完整编码和权重，单列动态 EOS 权重为 1 的例外，身份总体权重须与父集一致。 |
| CPU 与 UAT 边界 | 仅构造参数、加载数据/processor、编码和 collator；没有实例化 SwiftSft/Trainer、优化器、模型权重或调用训练/生成。当前 Pod 无 GPU resource，CUDA 隐藏，基础模型和输入挂载只读，网络下载设为离线；编码脚本另检查 CUDA/设备不存在。`run_cpu.py` 对 UAT 仅 GET 快照，不 scale、patch 或暂停；写操作只针对临时 CPU Pod，finally 清理并检查 UAT UID/generation/spec hash/副本及健康状态。运行期事实仍以实际返回的报告和前后快照为准。 |

Token 统计含义一致：`input_tokens` 包括模板与未监督输入；`supervised_tokens` 只数 label != -100 的 token；`weighted_token_units` 是这些位置 loss_scale 的和，不能当作实际 token 数或训练梯度贡献。计数按每次曝光累加，编码缓存不减少曝光。

`segment_tokens` 只在受监督位置统计：think 标记之间为 `thinking_content`，外部为 `answer_content`，think/chat 分隔 token 为 `structure`；空白保留。因此它是模板 token 分区，不等同于把自然语言正文单独重新分词的长度。代码验证三个分区的监督 token 与权重之和等于总量。`by_mode` 则是按记录中是否有非空 assistant think 分类，整条记录的权重进入对应桶，不能误称为 think/body 分段权重。System 子集为零成立的依据是全量无 System 的显式断言，不是执行过 System 样本。

只读验证还确认父集全部 1334 个 assistant 消息均有单组起始 think 标签；4 个脚本的 AST 语法解析通过。本次没有执行这 4 个脚本、集群命令、模型加载或测试；没有读取评测题，也没有改脚本。实际候选最终 SHA256、CPU 编码行数/长度/监督量、临时 Pod 清理和 UAT 健康仍待主 Agent 运行取证。

本次审查脚本 SHA256：

```text
assemble.py              fac3a15233934c698e2c0bbd29762951a683eab83788d70ff99d4f6eb6ada0fc
verify_candidate.py      c747d5b8e02a92ee4ec6fdc0fbf29ad6c42d579ce975ee1eecdb7249812f9dde
run_cpu.py               83db0533e6198139cee8eeef2de0b63dcd49189bff087d9e86673e97f5891df4
cpu-check/check_cpu.py   59a5fe8a87b33756448c6153b9a6a1edcf2a79b19b2a4822f56bced68cd3e745
```
