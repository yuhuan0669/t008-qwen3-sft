# 环境、挂载与外部依赖

以下为v0.1.14成功运行的冻结记录，本次未重新连接集群。模板仅做本地渲染/语法核验，没有重新申请GPU验证。

| 项目 | 固定值 / 位置 |
| --- | --- |
| Kubernetes context | `lmas00-direct` |
| 训练namespace / 节点 | `swift` / `k8s-worker05`，RTX4090 24GB |
| UAT | `vllm` namespace，Deployment `vllm`，API名`octa-carbon-v1` |
| 镜像 | `modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope@sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738` |
| 真实版本 | ms-swift4.4.2，Transformers5.14.1，PEFT0.20.0，Torch2.11.0+cu130，tokenizers0.22.2，datasets4.8.4，ModelScope1.38.1；评测vLLM0.25.1 |
| 原始基座 | `swift/swift-base` PVC，subPath `Qwen3-8B`，容器`/base`；逐文件SHA见evaluation/materials/base-files.json |
| 输入PVC | `swift/swift-train-data`；新目录`RUN/handoff`挂载`/handoff`只读 |
| 输出PVC | `swift/swift-work`；新目录`RUN`挂载`/manual-work`可写 |
| Python叠加依赖 | 输入PVC的`t008-v0114-20261021-145454/deps`，容器`/input/deps`，PYTHONPATH指向它；不在本包，操作时先确认目录存在 |
| ModelScope兼容补丁 | 本包runtime/support/ast_index_file.py；挂载到镜像相应模块。原字节保留，避免已知入口索引异常 |
| CA信任包 | runtime/support/trust-bundle.pem，供ClearML HTTPS使用 |
| ClearML凭据 | namespace `swift`中的Secret `swift-clearml`，只按引用注入access_key/secret_key，不复制明文 |
| 训练记录方式 | `report_to=tensorboard`；进程成功退出后运行archive_run.py，将标量、日志、模型批量归档ClearML并回读SHA |

镜像的命名不等于内部库版本；train.py在真正执行前核对CPU报告中的版本和基座tokenizer/config哈希。单独复制数据或只换一个pip版本，不能视为相同环境。若叠加依赖目录不可用，先在新环境重建并重新做原生Swift编码验证，不能直接复用旧CPU“通过”。

GPU训练、评测vLLM与原UAT在这张卡上不能同时运行。新运行需要新的窗口协调；本包没有延用历史授权或自动停服逻辑。后台训练/推理结束就恢复UAT，后续本地分析不占用停服窗口。

当前recipe为原始基座＋新LoRA。包内Adapter ZIP用于比较/推理，不包含优化器等完整状态，不能当作断点续训checkpoint。若改为继续训练旧LoRA，应单列实验和启动方式。
