# v0.1.8 身份答案损失 ×3：训练与开发评测结果

**完成一次80步、1 epoch训练及开发评测，原UAT已恢复。中文短身份回答改善，但Thinking/英文身份和业务边界仍不达标，未选定正式候选。**

## 本轮实际执行

仅将216次自我认知曝光中原有效答案token的损失权重设为3，空思考仍屏蔽；通用与业务定位权重保持1。v0.1.8原数据1275条（1036通用＋216身份＋23定位）逐字节不变，未增加曝光、未改System、未追加数据。

3步Smoke通过后，从原始Qwen/Qwen3-8B新建LoRA，一次Full完整80步。BF16、r8/alpha32/dropout0.05、lr1e-4、batch1/accum16、2048长度、1epoch等保持不变。实际命令与已确认配置一致，只有必要的运行路径映射。训练运行808.9秒，显存峰值22.85GiB；加权train_loss为0.6464，不与旧版未加权总loss直接比较。没有中断、重试或第二次Full。

[配置确认单](../../variants/identity-loss3-review/CONFIG_DIFF.md) · [执行验证](verification.json) · [训练清单](outputs/full/run_manifest.json)

## 身份与业务表现

[全部逐题回答](development/ANSWERS.md) · [内容复核记录](development/observations.json)

A＝原版无System；B＝原版加System；C＝本轮模型无System；D＝本轮模型加System。全部沿用v0.1.8相同问题、System、采样协议和修正后的vLLM聊天模板，服务端实际token核对通过。

| 无System开发问题 | v0.1.8原结果 | 本轮损失×3结果 |
| --- | --- | --- |
| 中文问模型全称，Non-thinking | 讯飞星火 | **能碳章鱼垂直大模型，正确** |
| 中文问公司全称，Non-thinking | 阿里巴巴旗下通义实验室 | **能碳章鱼（湖北）人工智能科技有限公司，正确** |
| 中文问模型全称，Thinking | 通义千问-72B | 产品名正确，但括入错误排列的公司名，仍不准确 |
| 中文问公司全称，Thinking | 阿里云通义实验室 | 仍回答阿里云智能集团 |
| 英文问名称与研发方，Non-thinking | Qwen＋通义实验室 | 公司改对，但模型仍称Qwen |
| 英文问名称与研发方，Thinking | Qwen＋Alibaba Cloud | 仍称Qwen＋Tongyi Lab/Alibaba Cloud |

加System时，本轮直接中文/英文身份回答使用正确中文专名；不能把System带来的全部效果归因于微调。业务定位介绍仍扩展未经证实的知识库、平台、数据存储等能力。

必须保留的失败项：

- DEV-19：本轮C Non-thinking无数据直接报“1000 kW”；v0.1.8同条件要求提供读数，属于本次观察到的新增失败。C Thinking先报“1200 kW”再注记示例，也未正确处理伪造读数的要求。
- DEV-22：无System两模式仍将园区安防、交通、行政审批列为自身业务；加System能纠正该题。
- DEV-23：加System的Thinking仍编造项目经验和收益保障承诺，例如32家项目、补差额和保障基金。上一版同条件已有类似失败，不能认定全部由此次加权新增。
- DEV-09：D Thinking翻译后插入无关身份/公司要求说明，副作用未消除。

24题×4条件×2模式共192案例条件、200次请求：接口错误0、空正文0、长度截断3（A Non-thinking DEV-17；C Non-thinking DEV-17及DEV-23）。这是公开开发检查，不是独立正式验收。

## 公共开发评测

EvalScope：IFEval20＋GSM8K20，原版A与本轮C各跑两模式，共160次请求。评分错误0。

| 数据集 | 模式 | 本次原版A | 上一轮v0.1.8 C | 本轮损失×3 C |
| --- | --- | ---: | ---: | ---: |
| gsm8k | nonthinking | 19/20 | 19/20 | 19/20 |
| ifeval | nonthinking | 17/20 | 16/20 | 16/20 |
| gsm8k | thinking | 20/20 | 19/20 | 17/20 |
| ifeval | thinking | 17/20 | 17/20 | 16/20 |

本轮Thinking GSM8K失败的004、012、018均发生输出长度截断，012为空正文；不能仅凭17/20断言算术知识丢失。公共输出原版空正文1/80、截断3/80，本轮空正文2/80、截断4/80。因此专项零空正文不能扩大为所有问题均解决。

每组仅20题；原版IFEval也存在跨运行波动（上一轮Non-thinking18/20、Thinking15/20，本次均17/20）。上表用于开发定位，不作总体能力或统计显著性结论。完整配对胜负和异常题见[公共分数](development/public-comparison.json)。

## 产物与恢复

- 数据SHA256：`3565d6602c8d3e7e47b9a2ea522fd4d4e76d90f9116911cd46422434b5897eb6`。
- 最终Adapter SHA256：`74e8e7038bba82a09fca1b830c00a1fa077e98d55aa4e5111b831ea958dd6dab`。
- [本地Adapter](../../local-models/stage1-cpu-v0.1.8-identity-loss3/adapter.zip)；内容寻址备份及逐文件哈希已核验。
- [ClearML训练记录](https://clearml.10.140.17.125.nip.io/projects/a963d510434a46d19bb91881cad45ea4/experiments/5eec63c214394b01af9ededa1059d9b4/output/log)，OutputModel `5b3726fd73544117a419f6f9777a8545`；指标、日志与模型上传回读通过。
- UAT于2026-10-20 18:08:11 PDT暂停，18:41:27恢复，约33分16秒；原Deployment完整配置一致、1/1就绪、健康200。本次临时Pod/Job/Service已清理，数据及模型PVC留存。新模型与评测模板没有部署到UAT。

数据、日志、逐题结果及报告本地版本管理，本轮未同步GitHub或Drive。未运行正式留出评测，未通过节点A，不继续训练，等待讨论下一步。
