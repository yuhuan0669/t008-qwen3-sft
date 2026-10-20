# 第一阶段：运行配置准备

`run-spec.json`固定本地训练文件SHA和完整Swift参数；当前1289次曝光，batch1×累积16×1epoch，预计81个优化步。当前数据已用Swift4.4.2实际加载及编码；参数解析沿用此前结果，`recipe-validation.json`保留检查时版本。

Swift命令行不接受`truncation_strategy=raise`，所以使用其合法`delete`选项，同时挂载`local_data_guard.py`，对真实编码前后成员及曝光做严格比对；任何删行都在Trainer前报错。CPU验证注入缺行并确认阻断。输入文件本身已经全部通过2048检查。

当前只准备参数和插件，没有执行训练命令。后续GPU阶段沿用已有`code/run_identity.py`的Task/OutputModel、终态checkpoint和Adapter上传回读逻辑，需把其旧在线原生数据命令改接本版run-spec本地入口；不得直接运行旧`train_identity.sh full`。此接线和真实GPU预检属于后续执行准备，不能把本次CPU检查写成训练链已验收。

ClearML指标采用`stage1/scripts/collect_metrics.py`：结束后一次读取TensorBoard训练scalar，调用已有Task logger；真实TensorBoard测试已通过，不创建准备Task、不实时桥接、不上传评测题文。已有SDK依赖为ClearML1.17.0；凭据继续引用既有Secret，本阶段未读取凭据或创建云端实验。上传/断网补传在真实运行后验证，失败保留日志，不重训。

Smoke、Full及评测的GPU运行、服务窗口和产物上传仍待负责人确认数据、配方及资源安排。
