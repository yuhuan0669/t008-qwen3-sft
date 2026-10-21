# v0.1.10：中文身份与 JSON 最小修订

**8条替换和实际Swift CPU检查已完成，尚未训练。英文继续延后。**

[完整修改前后对照](SAMPLE_DIFF.md) · [CPU检查](CPU_CHECK.md) · [配置差异](CONFIG_DIFF.md) · [JSON配对诊断](../../../stage2/diagnostics/json-format-check-20261020/REPORT.md)

| 父版本行号 | 类型 | 新的可见回答 |
| ---: | --- | --- |
| 449 | 中文名字问法一 | 我的名字是能碳章鱼垂直大模型。 |
| 877 | 中文研发方问法 | 我的研发公司是能碳章鱼（湖北）人工智能科技有限公司。 |
| 946 | 中文名字问法二 | 我叫能碳章鱼垂直大模型。 |
| 1064 | JSON对象 / Non-thinking | {"product":"铅笔","quantity":4} |
| 1074 | 中文创作者问法 | 我由能碳章鱼（湖北）人工智能科技有限公司研发。 |
| 1160 | JSON对象 / Thinking | {"product":"铅笔","quantity":4} |
| 1174 | JSON数组 / Non-thinking | [{"title":"春日","in_stock":true,"note":null},{"title":"山海","in_stock":false,"note":null}] |
| 1190 | JSON数组 / Thinking | [{"title":"春日","in_stock":true,"note":null},{"title":"山海","in_stock":false,"note":null}] |

总条数1275、身份曝光216、通用曝光合计1036、定位曝光23不变。4条新编JSON单列来源；被替换的原通用样本均保留另一次曝光。四条身份记录对应的空思考版本也保留。除这8条外，1267行逐字节不变。

身份非空思考示范从2次变为6次；JSON为两种任务各一个空思考和一个短思考版本。数组任务覆盖true/false与null的区别，来自本次诊断发现；没有使用诊断题原文或答案。业务与英文样本不变，底层保密数据没有重新加入。

身份损失×3、其他超参数、System和修正后的vLLM模板保持原状。本次没有新建ClearML训练Task，未上传GitHub或Drive。

数据文件：[train.jsonl](train.jsonl)；SHA-256：`5b455659b0e3fea30efd5822be1a7fee0e57d2788bc0dcbf79ec755cd5f22788`。父版本保留原样。
