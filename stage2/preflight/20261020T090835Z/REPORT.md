# v0.2 执行：GPU与UAT检查

当前状态：方案执行已获用户授权；**窗口未确认，未创建训练作业**。

检查时间：2026-10-20 02:09 PDT（09:09 UTC）。集群上下文：`lmas00-direct`。

- 唯一GPU：worker05上的RTX4090，24564 MiB；已用22174 MiB，可用1908 MiB。主要进程为VLLM::EngineCore。
- vLLM申请并占用1张GPU，Deployment 1/1 Ready；模型octa-carbon-v1，仍挂载原Qwen3-8B基座。
- 模型`/health`和`/v1/models`返回200；采样时运行／等待请求均为0。该瞬时读数不证明UAT已结束，也不代表未来时段允许停服。
- UAT相关cms-bai前后端、cms-front、cms-kong及open-webui均为1/1 Ready。这里只检查服务状态，没有执行用户业务测试或宣布UAT验收通过。
- 现有数据v0.1.3、1289行的SHA与训练配置和CPU编码报告一致。

没有停止、缩容、重启或修改服务；没有提交GPU作业，也没有发送模型推理请求。

唯一卡仍被现有服务占用，无法确认不影响UAT的训练窗口。已向负责人请求已协调好的起止时间及时区或其他GPU资源；未把历史窗口作为本次授权。

训练包装器接入本地数据、实际评测入口组装仍是执行准备事项，不能将输入绑定完成写成训练入口已经就绪。窗口明确后继续按v0.2范围完成接线、基线、Smoke和Full。

证据：本目录的cluster-snapshot.json、gpu-usage.txt、model-health.json、uat-workloads.json、run-readiness.json。
