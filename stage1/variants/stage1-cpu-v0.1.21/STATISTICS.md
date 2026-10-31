# 数据与监督统计

|项目|v0.1.20|v0.1.21|
|---|---:|---:|
|训练曝光行|1069|1047|
|通用独立记录|390|379|
|身份曝光|234|234|
|身份曝光占比|21.89%|22.35%|
|预计每epoch优化步数|67|66|
|输入token|1,185,555|965,723|
|监督token|1,147,740|929,302|
|加权token单位|1,165,598|947,044|
|身份监督token占比|0.78%|0.96%|
|身份加权token占比|2.30%|2.81%|

本轮保留通用中，thinking有改动197种，正文有改动275种；题干0处变化。并非全部thinking改写。

token来自实际ms-swift模板及labels/loss_scale，不是字符估算。加权token份额不等于实测损失或梯度贡献；内容缩短和隔离会改变相对份额，未通过重采样抵消。

|当前来源模式|曝光行|监督token|加权token占比|
|---|---:|---:|---:|
|thinking|779|919,324|97.23%|
|nonthinking|268|9,978|2.77%|

来源模式按任一助手轮是否含非空think划分；真实编码沿用preserve_thinking=false，历史轮thinking会被原生模板处理。逐来源/逐行结果见[cpu-check/report.json](cpu-check/report.json)和[row-checks.jsonl](cpu-check/row-checks.jsonl)。
