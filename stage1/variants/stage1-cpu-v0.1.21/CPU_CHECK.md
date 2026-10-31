# CPU检查

ms-swift 4.4.2及父版本绑定的tokenizer/模板/损失源码核验一致。仅加载tokenizer和数据，未加载模型权重、构造Trainer/优化器或执行前向/反向传播。

首次预检发现5种修订记录超过2048 token（10次曝光），已删减重复说明后重查；题干和必要内容保留，没有截断或静默删除。第一次结果保存在[cpu-check/attempt1/](cpu-check/attempt1/)。

- 实际装载、原生编码和成员守卫：均为1047行。
- 最长2041 token，P99为2029；2048上限内，超长、截断、静默丢行、空监督均为0。
- 462行未改记录的input_ids、labels、loss_scale与父版本逐项一致。
- 身份234次曝光：新正文对应hash及4个原生预处理别名已实测绑定，助手监督倍率3仍生效。未改插件算法。
- 用户位置和空think损失为0，本候选不含System；原生补入的中间轮结束符保持1，身份最终suffix沿既有插件保持3。
- GPU不可见、无GPU设备；仅用临时CPU Pod，检查后已删除。UAT Deployment配置hash不变且1/1就绪。

[完整结果](cpu-check/report.json) · [逐行检查](cpu-check/row-checks.jsonl) · [变更行](cpu-check/changed-row-checks.json) · [原生别名](native-identity-key-aliases.json) · [集群前后](cpu-check/cluster-after.json)。

这些是数据编码与监督实现检查，不是模型效果或训练收敛证明。
