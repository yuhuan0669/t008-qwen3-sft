# 官方 native 入口适配：工程子审准备

2026-10-19。本轮只读检查旧 `t008_qwen3_sft_v12_cpu/work/code/run_identity.py`、`prepare_official.py`、`train_identity.sh`、身份示例及两个测试文件；未修改实现、运行容器/GPU/训练或创建 ClearML 对象。继承上下文工程子审，不是独立盲审，也不是对尚未完成的新实现的验收。

## 已授权范围

本轮授权是适配正式入口到官方 native 数据、2048 默认 delete，并完成 CPU 解析验证和报告。不要额外要求语义清洗，也不要把先前语义初审变成新的自动筛选器。CPU 解析成功不等于训练执行授权，不能生成批准字段或默认置真。英文模型名及主体名称已有负责人确认，不应重新写为 pending；保留确认引用及确切四字段，基座仍为 Qwen/Qwen3-8B，不将定制主体称为基座原研发方。

## 旧实现需要针对性迁移的事实

1. `validate_training_dataset` 和 `validate_length_preflight` 是“本地不可变文件+批准行数+零超长”契约，后者强制 `overlength_rows==0`。native 在模板编码时 delete 超长，不能用“原始2600必须零超长”去拒绝该授权模式，也不能伪造零超长报告。应区分输入2600、删除958、保留1642；这些是已有固定源/模板/seed的实测预期，不是任何上游版本永远恒定的公理。
2. full 命令当前 `save_strategy=epoch`，没有50步周期保存；smoke实际是3步保存，旧注释所说50步不符合代码。
3. `latest_adapter` 仅挑目录编号最大的完整Adapter。目录名与该目录自身 `trainer_state.global_step` 一致，不证明它等于本次实际训练最终步；旧 `epoch>=0.999` 也应配合本次运行终态证据。步骤50保存与最终保存必须同时成立。
4. 旧命令别名是在 `torch.cuda` 检查后才解析；新的 CPU-only 路径必须能先完成参数/身份/版本验证，不触发GPU检查或ClearML生命周期。
5. 现有23项测试主要覆盖快照、衍生字节保持、批准literal True、模板Mapping长度、help fallback、HTTPS注册边界；尚不能证明新的native参数、delete行为、50步+最终保存与CPU无副作用。

## 有意义的回归场景

| 场景 | 应验证的结果与反例 |
|---|---|
| 默认正式入口 | 未显式选择数据模式时构造官方 `swift/Qwen3-SFT-Mixin#2000` 和 `swift/self-cognition:qwen3#600`；不是本地衍生train.jsonl，也不自定义补足/重复/过滤样本。保留seed/data_seed=42、split_dataset_ratio=0、qwen3模型类型及模板。 |
| 身份注入 | 两个双语name/author值按真实Swift解析顺序传入；完整英文主体含空格括号时仍是单一参数。四字段缺失/空白/占位符失败，英文已确认值成功；Mixin中的普通Jinja不误删。 |
| 长度边界 | 用真实已固定Swift parser证实max_length=2048和最终生效的truncation_strategy=delete。通过自行编写的合成用例检查2048保留、2049删除；不允许悄悄left/right截断、自动补采或改写答案。 |
| native CPU实际证据 | 固定源缓存/上游revision、SDK实际版本、base/tokenizer/template指纹、模型名作者名和seed；复核2600→1642、958删除及逐行索引/长度对应。源输入内容哈希不变；有效数据是默认delete的结果，不称内容审核通过。若实际结果变化，报告差异，不篡改数据凑1642。 |
| 授权与CPU分离 | CPU parse/计划路径不要求伪造GPU批准，不导入训练模型、不调用torch.cuda或训练subprocess、不创建Task/OutputModel、不上传、不产生批准。训练入口仍拒绝缺失批准、字符串true/false、数字1及不匹配的引用/数据指纹。测试对这些副作用设调用即失败的哨兵，并实际调用入口分支。 |
| 周期保存 | full最终参数为steps/50，不被后续分支覆盖成epoch或save_steps=3；smoke若仍存在应明确属于另一路并保持原授权边界。不要仅测试字符串包含50，检查真实parser解析值。 |
| 最终checkpoint | 合成文件目录：只有checkpoint-50而实际终态global_step=103必须失败；有完整checkpoint-103且运行终态/该checkpoint state一致才可打包。还应覆盖最终步恰为100、总步少于50、缺权重/配置/state、state步数矛盾、训练退出非0和未完成epoch。不能只选择最大目录编号。 |
| 保存机制版本 | 若依赖官方Trainer训练结束自动保存，以所用固定SDK/Trainer源码及CPU构造可验证行为证明；若该版本不保证final-save，则应显式实现可审查的最终保存机制。仅恢复save_steps50而未证明最终保存不足。CPU证据不宣称已经产出训练checkpoint。 |
| CLI兼容 | 覆盖外层help不完整→真正SFT parser fallback；tuner_type/train_type、eval_strategy/evaluation_strategy双方别名；都缺失或不支持delete/身份参数时明确失败。真实CPU参数解析只到解析/预处理，不调用会进入训练的无help sft_main。未知关键参数不能静默删除或借help子串误判。 |
| 失败无副作用 | 无效模式、身份字段、CLI、source/base指纹、批准或已存在OUT_DIR均在Task.init/Popen之前失败；CPU路径更须在GPU访问之前失败。失败不写成功/批准，不覆盖已有run或数据。已开始的训练失败应保留FAILED证据，不能声称“从未创建Task”。 |
| 来源/数据绑定 | native运行读取的官方缓存与CPU审计必须能绑定相同内容，不能用浮动远程HEAD替代已审快照；至少记录并核对实际源内容摘要、有效行序列/删除索引摘要与版本。不要因native模式绕开来源许可和身份确认引用，也不要新增未经授权语义门槛。 |
| 旧包不可变 | 新实现/新报告仅写新目录。读取旧快照和报告前后哈希一致；旧文件模式如保留，仍沿用原契约，不能由native分支放宽其衍生批准或字节一致性验证。 |
| ClearML原有边界 | 保留HTTPS存储、显式upload_uri、同步上传、同host/path注册URL和force_download哈希回读。此轮用假对象检查调用参数/负例即可，不创建真实Task/Model或上传。 |

## 推荐验证层次与报告措辞

先跑纯函数/入口哨兵回归，再在主Agent已授权的CPU隔离环境使用实际固定Swift parser验证解析值与官方delete结果。分开报告“静态构造正确”“真实CPU解析/编码成功”“GPU训练未执行”；没有运行的最终checkpoint和远程上传只能报告代码契约验证。不要把模拟SDK测试称为真实服务闭环，也不要把CPU预处理当作训练/部署批准。

本文件仅提供回归建议；后续收到新实现后才审核具体改动与实际测试证据。
