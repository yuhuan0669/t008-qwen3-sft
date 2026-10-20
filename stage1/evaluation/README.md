# 第一阶段评测准备（review-v0.4.1）

本目录仅包含训练侧可见的索引、协议、评分规则、公开开发题与CPU适配准备。正式专项120题及公共200题的题文、答案、逐题rubric与官方原始快照保存在仓库外：

`/Users/ben/aiws/codex/keywords/t008_eval_holdout_stage1_20261020/`

目录权限0700，正式文件0600；不提交Git、不上传训练Task、训练侧不读取。此为独立角色和上下文隔离、文件管理约束；同一OS用户仍可访问，0700不等于独立账户的强访问隔离。正式输出和逐题失败将继续留在评测侧。

- `holdout-index.json`：正式文件与来源的SHA、配额、冻结依据和隔离说明，无题文/答案。
- `public-development.jsonl`：40条公共开发（IFEval20、GSM8K20），保留官方native字段、版本和原始行号。与正式公共100+100成员分离。
- `rubric.md`、`protocol.json`：原方案评分/阈值和2080条件矩阵。专项含12个双轮对话，全部执行对应2240逐轮请求；预算应考虑逐轮token，评分分母仍为2080个案例条件。
- `custom-system.txt`：方案§1.1完整自我介绍一整句，无末尾换行；B/D完全一致，A/C无定制System。
- `matrix.json`：可核算条件列表，基线880、候选1200；双模式；C/D身份seed42/43/44，其余seed42。
- `cpu_adapter.py`：不加载模型、不执行推理的配置与样本转换准备。`python3 stage1/evaluation/cpu_adapter.py`只核验矩阵。公开基准配置暂用不可执行占位模型/地址，正式阶段必须绑定已冻结成员的本地数据，不能运行默认全量远程数据集。
- `check_cpu_api.py`、`cpu-api-check.json`：通过 `python3 stage1/evaluation/run_cpu_api_check.py --target kubernetes` 可重复执行现有EvalScope 1.9.1 CPU环境的合成检查；本地已安装同版本时用 `--target local`。检查TaskConfig/GenerateConfig、官方式IFEval规则评分、GSM8K提取、答案不入提示、多轮使用真实assistant历史；未创建模型或发起推理。
- `integrity-check.json`：配额、唯一性、多轮/逐题rubric结构、公开开发分离，以及本轮训练文件只读比对结果。

正式公共来源：[Google Research IFEval](https://github.com/google-research/google-research/tree/master/instruction_following_eval)、[OpenAI GSM8K](https://github.com/openai/grade-school-math)。实际获取使用固定Git提交的raw链接，完整提交、文件SHA和取回时间见索引；开发与正式均来自同一固定官方快照，以固定SHA256排序切分，无成绩驱动挑选。GSM8K使用官方test，不把官方train当测试。IFEval使用官方input_data。许可证副本随公开开发数据保留。

专项由独立评测角色仅按方案及业务依据编写，未读取训练样本；写完后由只读脚本与最终训练文件做比对，只输出计数。当前训练快照无精确/规范化重叠不代表不存在语义近似，更不能证明基座预训练无污染。

CPU准备不代表运行后端已验收。GPU包授权、候选冻结、真实模板/双模式后端预检、吞吐测量、正式一次验收及人工复核仍属后续阶段。专项已准备Sample转换与动态历史拼接，正式集本地加载/逐轮结果持久化及人工rubric接入需在正式运行入口组装；不得将本目录CPU样本检查误报为完整推理链已验证。所有后续运行必须遵守方案的错误、截断、重试和独立保管要求。
