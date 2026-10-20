# Native 入口工程子审结果

2026-10-19。本报告针对本目录代码的只读工程审查，不是独立盲审、GPU执行批准或真实训练验收。未启动容器、GPU、训练、ClearML Task/Model；没有改实现。审查期间主Agent并行更新了实现，以下明确区分发现和已修复方向。

## 当前结论（修复后复核）

已重新读取最新实现并独立重跑 `python3 -B -m unittest discover -s code/tests -v`，**32/32通过**。此前首次CPU建证据被训练guard阻断的问题已修复；当前限定审查未发现尚未修复的必须阻断本轮CPU准备的代码问题。真实CPU原生加载/编码仍未由本子审完成，不能把本机合成测试等同真实SDK加载通过或GPU训练准入。

### 已修复：CPU构造证据调用原官方编码方法

`cpu_check` 现在用 `getattr(SwiftSft._encode_dataset, '__wrapped__', SwiftSft._encode_dataset)` 取得插件保存的原方法，在metadata-only stub上编码。`native_guard` 使用 `functools.wraps` 提供该引用；正式训练仍走校验包装，没有新增无证据训练开关。测试fixture已同步SHA、spec、versions和双语name/author。

除32项已有测试外，本子审用临时假Pipeline执行了3个有针对性的CPU探针（不修改实现、不用真实SDK/容器/GPU）：

1. 无批准环境，通过当前cpu_check使用的原方法选择表达式，可编码并保留输入对象：通过。
2. 同环境直接调用正式训练包装方法：按预期拒绝缺少报告/SHA。
3. 正确SHA绑定通过后替换报告文件而保持SHA不变：按预期拒绝。

此前记录的8通过/1错误是并行修改期间旧fixture的历史结果，已由本次32/32和三个探针结果替代。初读与摘要采集时点跨越了并行修复，末尾hash表用于当前复核版本定位，不再用来指认失败版。

## 已确认改善

- 默认 full 构造官方两项native源规格、qwen3模板与类型、seed/data_seed42、2048，未显式覆盖truncation_strategy；真实parser默认delete仍由CPU实测确认。没有新增语义筛选。
- full 命令已恢复 `save_strategy=steps` / `save_steps=50`；smoke分支明确3步。
- `verify_final_checkpoint` 要求本次目录只有一条带终态checkpoint/global_step的Swift记录，并比较目录步数、终态步数、trainer_state.global_step/max_steps、checkpoint路径及epoch。它不再仅依赖checkpoint自身编号。
- 已读取存证官方Swift `pipelines/train/sft.py`：`_save_trainer_state` 确实记录 `last_model_checkpoint`、`global_step` 到logging.jsonl；训练异常也在finally写此记录，但wrapper先检查训练进程退出码，再做checkpoint验证，避免把异常终态直接注册为成功。是否确实保存最终非50整倍数checkpoint，还需以固定实际Transformers/Swift回调源码和CPU证据支持；本子审未运行训练。
- 数据guard按原生顺序与重复次数digest核对加载前/删除后的数据，不只检查行数；同时比较实际模板kwargs、seed、delete和缓存旁路配置。
- 已保留literal True批准校验、OUT_DIR禁止覆盖、显式HTTPS存储/同步上传与强制下载哈希回读。英文确认不重新设为pending。

## 审查中已补上的绑定缺口

初读版本的guard每阶段直接重新读取报告而不校验主入口批准的SHA，报告被替换可改变期望数据。已向主Agent反馈。最新代码由主入口设置批准SHA，插件每次读取同一raw bytes后先计算SHA再解析，并复核版本与身份；这已堵住“单独替换报告文件”的缺口。实现还新增entry及关键Swift文件指纹并在validate_report对比，模板kwargs guard也已加入。

仍建议主入口 `validate_report` 像插件一样只读一次bytes同时做摘要和JSON解析，避免当前read_text与另一次sha(path)不是同一读快照；把绝对报告路径明确传入child。部署需保持代码、基座和证据只读，不能把“关键文件指纹”表述为全部依赖源码逐文件验证。

## 需要准确陈述的副作用边界

- CPU入口在训练授权、torch.cuda检查和Task创建之前返回，这一分支结构正确；本次已补原方法选择和训练guard负例的合成探针；完整真实CPU执行仍由主Agent验证。
- 正式训练分支仍在image/commit格式、CLI和base完整指纹校验之前执行torch.cuda检查；如果要求这些无效静态输入连GPU探测都不能触发，应把静态校验前移。
- 官方SwiftSft初始化先 `_prepare_model_tokenizer`，然后run才 `_get_dataset/_encode_dataset`。wrapper也先创建Task再启动Swift。因此运行时数据漂移guard失败发生在Task创建和模型加载之后。它能防止Trainer开始训练，但不能宣称“所有数据漂移失败都没有Task/GPU触达”。若要该更强保证，须有训练前CPU核对及只读来源绑定；否则准确报告已创建失败Task和已加载模型的边界，不把它等同本轮CPU路径。
- CPU metadata-only stub、不调用SwiftSft构造函数的设计正确；使用该设计不意味模型权重已训练或生成checkpoint。

## 本次审读版本定位

以下摘要已在修复后复核时重新采集，定位本次32/32测试与探针对应的代码；后续实现变更应重新检查：

| 文件 | SHA256 |
|---|---|
| code/run_identity.py | `47f353024312912dbe76f028caca2943fe1a6f54c5f636b41c92ffe9b906c395` |
| code/native_recipe.py | `30024469aa91e68711809b2f975a34d3f5a4652b38af8c5a8d7c7246ab5f8774` |
| code/native_guard.py | `05a7458ce978607da507fb40ce5ab67528798eeb47b22829b608c3eb88dd16e3` |
| code/tests/test_native_entry.py | `24d72d8aed1b9389312b973d1cad308f336c9da4d73217b4739345e08f6189a4` |

本轮没有要求额外语义清洗，也没有改动旧数据或旧证据包。CPU回归已修复且本机验证通过。主Agent报告真实ModelScope加载仍受TLS信任环境阻塞，正在处理可信根bundle而不关闭SSL验证；该外部执行状态本子审未独立验证。尚待真实CPU执行结果，不能将这份文件的“final”名称解释为准入批准。
