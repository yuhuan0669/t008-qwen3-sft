# v0.1.8 训练与开发评测结果

**CPU 检查与一次 Full 训练完成；开发未达标，未选定正式候选；原 UAT 已恢复。** 没有追加 Full、增加曝光或部署新模型。

## 输入与训练

模型名称统一为“能碳章鱼垂直大模型”，公司为“能碳章鱼（湖北）人工智能科技有限公司”；英文语境也使用中文专名。159行仅调整名称，其余1116行字节不变，总数1275，来源曝光1036＋216＋23。训练 System 不额外注入；新版 System 用于 B/D 推理条件。

实际固定环境 CPU 加载与编码1275行，无超长、截断、空监督、静默丢行，最长2048。159行改名正文监督正确。监督token总计1,528,189（较v0.1.7少66），并非增加曝光。见 [CPU检查](../../../stage1/variants/stage1-cpu-v0.1.8/CPU_CHECK.md)。

原始 Qwen/Qwen3-8B＋新LoRA，BF16，r8/alpha32/dropout0.05，lr1e-4，batch1/accum16，2048，default+ignore_empty_think，1epoch。3步Smoke通过，随后单次Full完整80步，没有中断或重试。Full运行809.24秒，train_loss0.62892。实际命令与冻结配方一致（挂载/输出路径映射除外）。

- 数据 SHA256：`3565d6602c8d3e7e47b9a2ea522fd4d4e76d90f9116911cd46422434b5897eb6`
- Adapter SHA256：`0ef3315293a4f14d225b6a98bb67bd5743ba9b9eb1fbf03f4cfc4b9663ad535c`
- ClearML Task：`881d3bdb221c441f95346e83e4abb806`；OutputModel：`d13b6b854ed145fbba194fe136c87546`，上传回读核验通过。
- 本地模型：[adapter.zip](../../local-models/stage1-cpu-v0.1.8/adapter.zip)。

## 开发结果

[全部专项正文对照](development/ANSWERS.md) · [逐项观察](development/observations.json) · [公共开发分数](development/public-comparison.json)

A＝原版无System，B＝原版＋新版System，C＝v0.1.8无System，D＝v0.1.8＋新版System。修正vLLM模板一致，服务端token核对通过，固定seed42，未因失败追加采样。24题×4条件×2模式＝192案例条件、200次请求：接口错误0、空正文0；2次Non-thinking长度截断均在DEV-17（A、C）。这是公开开发检查，不是独立正式验收。

- 无System身份仍失败：DEV-01 nonthinking自称“讯飞星火大模型”，thinking自称“通义千问-72B”；DEV-02、04仍答通义/阿里等身份。
- 加System时DEV-01两模式均答对新的中文模型名；但原版B也答对，因此不能把这一改善全部归功于SFT。
- 英文DEV-04：D的nonthinking使用正确中文专名；thinking仍附加自行翻译的英文名称，不满足“不另行翻译名称”。原版B thinking也附加译名。
- 业务边界未稳定：C在DEV-03多轮中虚构已接入能耗系统；D虽否认已有实时接入，介绍仍扩展未经证实的实时更新、平台功能。
- D thinking在DEV-09翻译中追加产品署名，DEV-11摘要中追加原文没有的碳排放报告语境。DEV-08 nonthinking算术答126，B同样答126，不能仅归因于微调。

公共开发：IFEval20＋GSM8K20，A/C各跑两模式，共160次请求。

| 数据集 | 模式 | 原版A | v0.1.8 C |
|---|---|---:|---:|
| gsm8k | nonthinking | 19/20 | 19/20 |
| ifeval | nonthinking | 18/20 | 16/20 |
| gsm8k | thinking | 20/20 | 19/20 |
| ifeval | thinking | 15/20 | 17/20 |

所有公共空正文均以4096输出token结束，停止原因max_tokens。

公共输出完整性：A：空正文2/80；C_new：空正文1/80。各题预算结束与空正文详情见public-comparison.json；不得把专项“零空正文”扩大为所有问题已解决。样本较小，不作总体能力达标声明。未访问或运行正式留出集。

## 恢复与版本记录

UAT原完整Deployment配置一致、1/1就绪、健康200，任务临时Pod/Job/Service已清理；训练数据和模型PVC保留。暂停与恢复时刻见[window-state.json](window-state.json)。新Adapter和评测模板均未部署到UAT。

执行复核仅修正了一项记录问题：本轮评测协议继承旧System哈希，已在评测前改为新版哈希，公共评测读取本轮输入快照；回读验证通过。没有改变训练配方或扩大实验。

数据、日志和报告保存到本地Git；本轮未上传GitHub/Drive。ClearML记录训练及产物。v0.1.8目录保持准备/CPU检查快照，当前执行状态以本报告和current-state为准。不再自动训练，等待用户讨论下一步。
