# 训练配置差异

相对v0.1.20，仅改候选数据路径、哈希、行数及相关版本记录。full_argv经版本路径归一后逐项相同；[identity_loss3.py](identity_loss3.py)源码字节相同。身份hash清单随内容重新绑定，不改变loss归一化或倍率。

保持：Qwen/Qwen3-8B原始基座＋新LoRA；BF16，r8/alpha32/dropout0.05/all-linear；lr1e-4，1 epoch，batch1×梯度累积16，warmup0.05，seed/data_seed42，max_length2048，gradient_checkpointing=true；default+t008_identity3_ignore_empty_think，preserve_thinking=false；训练无System。

数据由1069变为1047行，预计步数67→66。保留记录曝光不变，内容及隔离会改变总监督token与调度长度，不能说实际优化过程完全等同。未补步数、增加epoch或重新配比。

推理仍引用冻结的共同System、修正vLLM模板、两模式参数与JSON Schema用法；[evaluation-config.json](evaluation-config.json)与父版本字节一致，其中System引用父版本不可变同一份文件。

[完整配置](training-config.json) · [机器可读差异](config-diff.json)。execution_authorized=false，未启动训练。
