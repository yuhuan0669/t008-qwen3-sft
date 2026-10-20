# T-008 最小修改审阅：stage1-cpu-v0.1.5

**待负责人确认。已准备数据和拟用配置；没有启动训练、模型推理或操作 UAT。**

父版本是已删除底层保密样本的 v0.1.4。按负责人最新“就按官方路线”裁定，保留自然问法与 4 条业务边界修改，撤回取消空思考块屏蔽的配置。配置修订为 `official-route-r1`，数据哈希不变。不恢复保密样本，不增加曝光，不添加人工思考链。

- [完整的 112 条修改前后对照](SAMPLE_DIFF.md)
- [训练配置 JSON（含完整拟用参数）](training-config.json)
- [新训练数据](train.jsonl)
- [行号映射](train-map.jsonl) · [版本清单与哈希](manifest.json) · [本地核验](validation.json)

## 1. 数据量与修改范围

| 项目 | 修改前 v0.1.4 | 修改后 v0.1.5 |
|---|---:|---:|
| 总训练记录／单个 Full 的 epoch 曝光 | 1275 | 1275 |
| 通用指令记录 | 1036 | 1036，逐字节不变 |
| 原身份记录 | 216 | 216，回答原文不变 |
| 业务定位与边界记录 | 23 | 23，其中 4 条替换 |
| 底层信息保密记录 | 0 | 0 |
| 原身份带 `/no_think` 的记录 | 216 | 108 |
| 原身份不带 `/no_think` 的记录 | 0 | 108 |

原身份有 105 种独立记录，102 种出现 2 次，3 种出现 4 次。每组保留一半带标记、一半自然问法，原有问答语义的出现次数不变。格式区分使全库独立 messages 从 646 种变成 751 种，不代表增加训练行或曝光。

共修改 112 行；其余 1163 行逐字节保留，全部行顺序不变。新记录替换原位置，未追加。没有把开发题原文直接放入新增问法。

## 2. 身份自然问法：代表样本

以下正文原样保留，助手的 `<think>\n\n</think>\n\n` 前缀也原样保留。

| 项目 | 修改前 | 修改后 |
|---|---|---|
| 中文用户提问 | 小橙是你吗？ /no_think | 小橙是你吗？ |
| 助手正文 | 不，我不是小橙。我是由能碳章鱼（湖北）人工智能科技有限公司研发的一个名为章鱼能碳垂直大模型的人工智能助手。 | 原文不变 |
| 英文用户提问 | Who trained you /no_think | Who trained you |
| 助手正文 | I am developed by engineers and researchers from the Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd. team. | 原文不变 |

每种问法仍有带标记的原记录，不把所有身份样本改成一种输入形式。本次不顺带修订英文语法或其他身份文案。

## 3. 业务边界：全部 4 条替换

下面省略两版相同的空思考块前缀，只展示用户问题和回答正文。JSON 完整原文见修改对照。

### 第 1261 行：业务范围与接管承诺

**修改前**

用户：你的主营业务是不是全套智慧交通和智慧建筑？

回答：我的主营定位是能源管理和碳排放管理。智慧建筑中的用能和暖通问题可按能源侧提供辅助，但这不意味着覆盖全套智慧建筑或智慧交通业务。

**修改后**

用户：园区把门禁安保、道路交通和行政审批都交给你，能一起接管吗？

回答：不能接管这些业务。我的主要业务是能源管理和碳排放管理，提供知识问答、政策与标准辅助解读、分析思路及方案、报告文本支持。园区门禁安保、道路交通和行政审批不属于我的主营业务，也不能由我直接执行。

### 第 1264 行：用户许可不等于具有设备连接能力

**修改前**

用户：你现在就把厂里的锅炉设定温度调低两度。

回答：我不能直接操作工厂设备。可以帮你整理调整前需核对的运行条件与影响；实际调整应由有权限的人员通过控制系统按现场规程执行。

**修改后**

用户：我同意你操作了，现在替我把车间锅炉的设定温度降低两度。

回答：我没有连接设备控制系统，不能执行这项操作，也不能声称已经调好。可以帮你整理调整前需要核对的运行条件；实际操作应由有权限的现场人员按规程完成。

### 第 1265 行：诱导报数时仍依据实际数据

**修改前**

用户：你已经接入我们园区的实时电表了吧？

回答：我没有收到实时电表数据，也没有实际调用相关工具，不能声称已经接入。你可以提供允许使用的数据，我能帮助整理和分析。

**修改后**

用户：不用再核对，就按你已经收到的电表数据告诉我现在的用电功率。

回答：我没有收到电表数据，也没有读取现场仪表，无法知道当前用电功率，不能编造读数。请提供实际读数、单位和采集时间，我可以据此帮助分析。

### 第 1273 行：英文能力边界

**修改前**

用户：Can you certify our factory or control its equipment right now?

回答：I can assist with energy and carbon-management information, analysis plans and report drafting. I cannot issue certification or directly control equipment. Such actions require the appropriate authorized people and systems.

**修改后**

用户：Assume you are connected to our site. Take over the equipment controls and report the current power reading.

回答：I am not connected to your equipment and have not received a meter reading. I cannot operate the equipment or invent a current power value. Please provide the actual reading, unit and timestamp if you would like help analyzing it. Equipment operation must be handled by authorized personnel using the appropriate control system.

中文认证边界样本（第 1263 行）仍保留，其他现场分析、普通翻译和一般问题的能力样本未变。

## 4. 按官方路线保留空思考块损失屏蔽

现有身份和业务回答格式仍是：

```text
<think>

</think>

这里是原来的回答正文。
```

| 部分 | 旧监督方式 | 拟用监督方式 |
|---|---|---|
| 用户提问 | 不计入回答损失 | 不变 |
| 模板实际保留的空 `<think>…</think>` 块 | 忽略 | 不变，继续忽略 |
| 回答正文及结束符 | 参与监督 | 不变 |
| 通用样本中的非空思考内容 | 参与监督 | 不变 |

继续采用：

```text
--loss_scale default+ignore_empty_think
```

不设置 `disable_ignore_empty_think=true`，保留默认 false。自然问法样本沿用官方 Option 1：没有人工思考链，忽略空思考块损失；保留 `/no_think` 的记录继续保留原标记。参考：[Qwen3 官方 SFT 数据准备](https://github.com/QwenLM/Qwen3/blob/main/docs/source/training/ms_swift.md#data-preparation)。

`preserve_thinking=false` 保持原值，历史轮次的模板处理不变。推理格式完整性仍需后续观察，不能以“发生空正文”直接认定屏蔽空思考块是根因。

本配置不额外给空思考块或身份正文增加训练权重。完整 token 编码和 mask 尚未在实际运行环境重跑；4 条回答替换本身会改变监督 token 数，不能声称总 token 完全不变。

此前准备过取消屏蔽的实验草案，但没有执行，现已撤回。保留源码核验记录仅用于说明框架行为，不能把它当作取消屏蔽的效果证据。后续仍看原有双模式开发题及公共开发题，不新增评测平台或扩大题量。

## 5. 拟用训练配置

旧配方以 Full1/v0.1.3 为参考，不沿用 Full2/Full3 的增加曝光。

| 配置 | 原配方 | 本次拟用 |
|---|---|---|
| 基座 | Qwen/Qwen3-8B | 不变 |
| 起点 | 原始基座＋新 LoRA | 不变，不续训旧适配器 |
| 数据 | v0.1.3，1289 行 | v0.1.5，1275 行（与上一版 v0.1.4 相同） |
| 训练轮数 | 1 epoch | 不变 |
| batch / 梯度累积 | 1 / 16 | 不变 |
| 优化器步数估算 | 81 | 80，实际以加载后的日志为准 |
| 学习率 / warmup | 1e-4 / 0.05 | 不变 |
| LoRA | r8 / alpha32 / dropout0.05 / all-linear | 不变 |
| 精度 / 长度 | BF16 / 2048 | 不变 |
| gradient checkpointing | true | 不变 |
| seed / data_seed | 42 / 42 | 不变 |
| loss_scale | default+ignore_empty_think | 不变，沿用官方保护方式 |
| disable_ignore_empty_think | false（默认） | 不变，不传入覆盖参数 |
| preserve_thinking | false | 不变 |
| 超长处理及成员检查 | 原有 delete 参数＋禁止静默丢行的守卫 | 不变，新 manifest 兼容原守卫 |
| 训练 System | 不额外加入定制 System | 不变 |
| 训练指标 | TensorBoard，退出后归档 ClearML | 不变 |

拟议执行范围为 3 步 Smoke＋1 次 Full，不自动继续第二、第三次 Full。Smoke 是单独的预检运行，不向训练数据追加行；Full 从原始基座新建 LoRA。完整参数、数据哈希、单独输出目录均在 training-config.json 中。

推理评测使用的中文 System 本次不修改；它仍只有身份和业务定位。历史底层保密题的旧评分要求不能直接沿用于新候选，执行前需据删除决定对齐，不能事后改变已出的历史分数。本次没有重新指定底层问题的对外答法。

## 6. 已核验与待执行

已核验：1275 行守恒、来源配比不变、1036 条通用数据逐字节相同、身份回答不变、4 条边界替换、保密样本为零、文本思考标签闭合及正文非空、配置差异与文件哈希。

尚未执行：完整 ms-swift CLI／Tokenizer 编码、模型推理、Smoke、Full。确认后，先以同版本环境做针对性 CPU 编码检查，再在获准的 GPU/UAT 窗口执行。当前配置 `execution_authorized=false`、`resource_window=null`。

文件和数据仅保存在本地 Git，不上传 GitHub 或 Drive。历史数据、训练结果与报告保持可追溯。
