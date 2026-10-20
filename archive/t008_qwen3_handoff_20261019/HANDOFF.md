# T-008｜Qwen3-8B 自我认知 SFT Handoff


交接版本：handoff-r1｜2026-10-19（America/Los_Angeles）
当前方案：v1.2流程恢复修订R1；不是v1.3。本文是事实和接手入口，不是新训练、评估、停服或语料修改授权。先读本节与第2节，再查对应证据，勿重新从头跑流程。


## 1. 当前结论与唯一优先读取顺序


当前状态：一轮身份LoRA历史训练已完成，但独立效果验收未完成，遗忘程度未测定；vLLM现已切回未微调Qwen3-8B，测试LoRA不再加载。用户已恢复v1.2快照审核、异常处理、独立评估流程，并要求仅更新方案和记录、不修改语料、不启动训练。快照正式入口尚未适配，不能直接将当前原生加载代码当作恢复流程已实现。


优先读取：
当前流程方案：https://docs.google.com/document/d/1F_tWpH6yaRLK0aaY4Y-ksKXBjjdLMrOIqM4ufchGBaY/edit
追加执行记录：https://drive.google.com/file/d/18YQ5hwOVZxWw2D8f-f-i10AmLfRb5MsU/view
完整训练命令与复盘：https://docs.google.com/document/d/1VAIcmdCgaO69w0cjkuVV3IzHjo3_aSUJX2a1n53VlRM/edit
问题诊断与用户暂缓决定：https://docs.google.com/document/d/14h2CdaLRZJZT28yhl7-tMfO1NfZE7m6s8fUnk3MenqA/edit
本handoff：https://docs.google.com/document/d/1G-jhFB0OhrIXvaqtZ2aoYYpcD05NkDTYEkmPez9kNiM/edit


权威关系：最新用户决定及当前流程修订决定后续动作；原始v1.2和阶段ZIP是不可变历史；早期README里的GPU未授权/No-Go是当时事实，不否定后来获授权并完成训练；后续文档的“测试LoRA已加载”是历史，现由切回基座记录和本次只读快照更新。不要通过改历史字段来伪造状态一致。


## 2. 已有授权、暂停事项与接手禁区


历史明确授权：CPU准备→官方原生2048→“开始GPU sft吧”及“授权本次暂停、训练并恢复”→3步Smoke+1轮Full→恢复原vLLM；后来“现在加载，因为要测试”→LoRA测试；后来“你先把vllm模型切到未微调版本”→卸载LoRA回到基座。这些动作已结束，不自动授予下一窗口。


当前有效决定：业务范围与语料优化“记录下来，先不处理”；恢复v1.2三项流程仅更新方案/执行记录。本次handoff仍为文档工作，不改数据、不改训练代码、不做新的推理/评测、不建ClearML对象、不停服务、不重训、不重新加载候选、不发布。用户不希望过度测试；接手应优先复用冻结证据。


业务范围尚未裁定。曾建议先聚焦企业能源管理、工业节能、碳排放核算，并暂不作智慧交通/建筑/碳交易等能力承诺；这只是候选建议，用户没有批准，不能写成正式产品范围。若后续请求涉及实质身份/用途变化、无法确认许可、受控GPU/停服或越权变更，按实际边界取得裁定，不反复询问已明确的普通操作。


## 3. 服务现状和资源定位


本次只读刷新：2026-10-19T18:33:52.451100-07:00（PDT），Deployment 1/1 Ready，generation/observedGeneration=44/44；LoRA enabled=False。仅读Deployment，无推理请求、无部署改动。


context=lmas00-direct；namespace=vllm；Deployment=vllm；UID=041c9a49-1693-45a5-8ff6-6136ba9e4074。未微调模型API ID=octa-carbon-v1，尽管名字含carbon，当前加载的是原始Qwen3-8B基座，没有Adapter。模型只读路径released/qwen3-8b-baseline/model → /models。max-model-len8192，gpu-memory-utilization0.90，reasoning-parser=qwen3；保留--enable-auto-tool-choice --tool-call-parser hermes。


API基址：https://vllm.10.140.17.125.nip.io；OpenAI模型列表为/v1/models。原测试ID octacarbon-llm-sft-test已不再加载，WebUI应刷新后选octa-carbon-v1。未微调基座不带训练得到的自定义身份，不应期待它自然回答项目产品名。测试Adapter仍保留，未删除或合并。


单RTX4090（24564MiB）节点=k8s-worker05；训练namespace=swift。历史GPU训练Jobs和本轮临时CPU/发布Pod已清理，训练文件仍在PVC。不要再执行progress.py或collect_outputs.py：它们依赖的prep Pod已删除。原始Pod UID相关kubelet路径是历史，不能照抄。


## 4. 本地目录与版本管理


本机根目录：/Users/ben/aiws/codex/keywords/。它不是统一Git仓库；本项目按阶段目录、Git Commit、Manifest和Drive冻结ZIP管理。禁止把目录名字当成已验收状态。


/Users/ben/aiws/codex/keywords/t008_qwen3_sft_v12_cpu
原始v1.2输入、原版baseline、修复代码work/code、原始及长度候选快照、来源/许可、CPU证据、首轮交付回执


/Users/ben/aiws/codex/keywords/t008_qwen3_sft_v12_followup_review_20261019
后续讨论/复核记录；属于历史，不自动覆盖当前R1


/Users/ben/aiws/codex/keywords/t008_qwen3_identity_classification_20261019
108种身份模板分类与质量讨论；未因此自动改写/排除语料


/Users/ben/aiws/codex/keywords/t008_qwen3_official2048_update_20261019
用户当时选官方2048配方的历史记录


/Users/ben/aiws/codex/keywords/t008_qwen3_native_entry_20261019
原生正式入口code、CPU真实原生加载/长度/mask、Git bundle及测试


/Users/ben/aiws/codex/keywords/t008_qwen3_gpu_sft_20261019
GPU训练输入payload、真实Job/日志/终态、候选outputs、LoRA加载test_serving、切基座baseline_switch；private不上传


/Users/ben/aiws/codex/keywords/t008_qwen3_training_runbook_20261019
全流程文档、空正文诊断、2条API对照证据、private原始聊天/SSE（禁止对外打包）


/Users/ben/aiws/codex/keywords/t008_qwen3_v12_process_restore_20261019
当前流程恢复R1、process_state.json、真实决定、追加记录、94文件前后不变证明


/Users/ben/aiws/codex/keywords/t008_qwen3_handoff_20261019
本handoff、结构化状态、文件/Drive索引、基座切换补充证据、交付核验


各目录对应的_delivery及*.readback*主要是下载回读、临时传输/校验文件，不能当成新的数据或代码版本。阶段目录外的ZIP是对应包时点快照，不会自动收录后来追加文件。


/Users/ben/aiws/codex/keywords/t008_qwen3_sft_v12_cpu/work/code
HEAD=55042a0c2eb3da96f38b019650838bfdf6b4a03b；工作区干净=True。


/Users/ben/aiws/codex/keywords/t008_qwen3_native_entry_20261019/code
HEAD=e7ae45aa7438c8bcca8318d3531854f7f5e7db39；工作区干净=True。


提交脉络：1b575e1（原始v1.2归档）→75f6086（占位符/Tokenizer/Swift CLI修复）→f56ee31（严格布尔门禁）→55042a0（HTTPS ClearML存储及回读）→e7ae45a（官方原生加载入口与CPU guard）。当前R1没有改训练代码，故代码HEAD仍e7ae45aa，不存在一个已实现的“R1快照入口commit”。GPU payload/code是该提交的归档副本，无.git。


Git没有正式tag；旧仓库无remote，原生入口仓库origin指向旧本地work/code，不是远程Git备份。已有preparation-code.git.bundle及native-entry.git.bundle随CPU包上传Drive。尚未统一总仓库/长期远程备份，handoff索引只改善导航，不等于完成仓库整顿。


## 5. 数据身份、审核状态和不可变规则


官方源：swift/Qwen3-SFT-Mixin#2000和swift/self-cognition:qwen3#600。Mixin底库1000条；身份底库108条，600是重复曝光，非600种不同提问。旧快照由prepare_official加载，正式原生SftArguments默认shuffle=True，身份5/6次分配部分变化；内容集合一致但顺序/重复分配及摘要不同，不能互换行号/审批。


旧原始2600行
/Users/ben/aiws/codex/keywords/t008_qwen3_sft_v12_cpu/work/original-v1.2/train.jsonl
文件字节SHA-256=dda551041a12c460b84056f2c58df0ab60f2e9999e0518f116cf5f5b3c5faf6e


旧长度候选1642行
/Users/ben/aiws/codex/keywords/t008_qwen3_sft_v12_cpu/work/length-candidate-v1.2/train.jsonl
文件字节SHA-256=ad06235bcf0df01f7de4fbfb4f2fe3b156429444478bb1ef0a22cc7ab322b111


旧排除清单958行
/Users/ben/aiws/codex/keywords/t008_qwen3_sft_v12_cpu/work/length-candidate-v1.2/exclusions.json
文件字节SHA-256=62b0786206d25262c51a637a4ec02cd2a811b9eb13ecc6396b8d5079ff414f84


正式原生加载证据2600行
/Users/ben/aiws/codex/keywords/t008_qwen3_native_entry_20261019/evidence/native-proof/native-loaded.jsonl
文件字节SHA-256=d85dbe58d9c5fab98bbf6a81cf828147ba1a47d6cce492aef107c7d3dafa604c


正式原生保留证据1642行
/Users/ben/aiws/codex/keywords/t008_qwen3_native_entry_20261019/evidence/native-proof/native-retained.jsonl
文件字节SHA-256=ed0278ad28f1613592d99cf9705acf83e2952be85592c6d8751f536920e92618


GPU实际从官方源ID原生加载，不是从上述1642本地文件读取。2600→默认delete958→1642，其中Mixin1042（521种）、身份600（108种），总629种；身份曝光占36.54%。GPU输入canonical SHA=fe0911174ed4a9b4f088804a901409d25be1af00c3cdd8a9f6981df1e6abe7aa；保留canonical SHA=9fa63f2d87ac24130a6e4f7c31ebcfd6c91ddb5a91c8bad716326e5c708f43aa。canonical对象摘要与JSONL字节SHA不同。


来源缓存两文件SHA：Mixin d261353c05df1f1fde95639d1a9d9243e1d24470dcb4c3732965ab1ab8eeba41；身份 e7b66784f02361cfa0ad4635dae12c0f810d197c22ac89a4b7837195dc4b7b23。Apache-2.0仓库声明、README、归档文件与revision证据在CPU包；实际SDK曾为master/etag=null，不宣称CLI锁定上游commit，不将公开仓库许可等同其他项目/备案用途准入。


R1恢复后：选定审核父快照、逐行异常、独立衍生链及真实批准、零超长与真实Swift样本/mask成员一致性。当前旧1642候选和历史原生输入都未因R1自动被批准。当前不生成新数据、不补采、不调比例、不改2048、不重写身份。original-quarantined-v1.2是早期诊断保留物，不能误选为训练输入。


## 6. 模型、训练结果与环境证据


固定身份：中文章鱼能碳垂直大模型；英文Octacarbon LLM；定制主体能碳章鱼（湖北）人工智能科技有限公司 / Octacarbon (Hubei) Artificial Intelligence Technology Co., Ltd.；基础模型Qwen/Qwen3-8B。用户已确认英文名为官方名可用于开发及商业，不重新置pending；不得称定制公司为Qwen原始研发方。


实际镜像：modelscope-registry.cn-hangzhou.cr.aliyuncs.com/modelscope-repo/modelscope@sha256:822d99beed4984a421c8d1da397993c6a8a5f88cdad7dde940bd52df0067d738
实装依赖：ms-swift=4.4.2, transformers=5.14.1, peft=0.20.0, torch=2.11.0+cu130, tokenizers=0.22.2, datasets=4.8.4, modelscope=1.38.1；ClearML1.17.0，vLLM0.25.1。tag不代表实装版本。基座16文件16,397,461,896字节；聚合SHA=39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374。


历史配方：BF16 LoRA、r8/alpha32/all-linear、dropout实装默认0.05、1epoch、lr1e-4、batch1/accum16、warmup0.05、max_length2048、seed/data_seed42、workers4、gradient_checkpointing=true；无QLoRA/Liger，无训练派生验证集，eval_strategy=no。实际Full steps50/save_total_limit2并保存最终103；原v1.2 Full epoch保存，差异保留，不在handoff擅自裁定新命令。


3步Smoke通过；Full103/103、epoch1，Trainer runtime871.4433s（14m31s），train_loss0.63014071。21.8235M可训练参数，占8212.5588M的0.2657%。10秒遥测观测峰值Full22034MiB、Smoke23084MiB，不是瞬时绝对峰值；Trainer另报22.16GiB，口径不同。训练loss不等于验收效果。


最终checkpoint=/runwork/outputs/full/checkpoints/v0-20261019-025405/checkpoint-103；保留100和103。实际Swift terminal、Trainer终态、wrapper退出0、LoRA张量有限性、ClearML模型下载hash闭环完成。没有独立A/B/C/D，无遗忘结论，无正式质量通过或生产发布。


Full ClearML Task=97ac5246ae9c43d9aa65ee2ac4c2aaef；OutputModel=0552c3ab6b39456e9ec8b32129015be0
https://clearml.10.140.17.125.nip.io/projects/a963d510434a46d19bb91881cad45ea4/experiments/97ac5246ae9c43d9aa65ee2ac4c2aaef/output/log
Smoke Task=ba54d19171294484a2358f0fef2a6e07。进度observer向现有Full Task补传日志，最终100%，没有重启或创建额外正式训练Task。


候选ZIP：/Users/ben/aiws/codex/keywords/t008_qwen3_gpu_sft_20261019/outputs/adapter-candidate.zip
80,736,700字节；SHA=33feb7cfe9e3bafa1a5b72f32e179fe89448c4c4251e152763dd846d3adffd1d
Adapter权重文件SHA=b3099ee58150332b29a7a1dc5f22fa69d797b56b2bc4381c3060b31454140e5f。


完整原始训练checkpoint含优化器：namespace=swift，PVC=swift-work，subPath=t008-qwen3-20261019-094113/outputs；63文件清单在GPU目录outputs/persisted-output-manifest.json。输入PVC=swift-train-data同运行子目录；基座PVC=swift-base/Qwen3-8B。Drive未重复存储16GB基座与全部优化器，仅Adapter+元数据/日志。


服务侧保留的测试Adapter：namespace=vllm，PVC=vllm-released，released/t008-qwen3-20261019-094113-test/adapter；TEST_SERVING_ONLY_NOT_QUALITY_ACCEPTED。目录位于released前缀仅因既有只读挂载策略，不代表质量发布。当前不挂该Adapter。训练角色UID10001、推理10002、publisher10003，未改RBAC或既有Admission Policy。凭据通过既有swift-clearml Secret引用；不得打印Secret、打包private目录、签名下载URL或原始聊天/SSE。


## 7. 已知问题、修复与证据边界


已修复工程问题：CLI真实帮助和参数名；显式qwen3；BatchEncoding按Mapping计数；正确身份占位符范围；严格JSON布尔；非root ModelScope索引/缓存；完整TLS根bundle；ClearML固定SDK overlay/HTTPS同步上传和强制回读；最终checkpoint强绑定；监督器异常恢复；WebUI auto调用增加Hermes参数。不得用恢复原版脚本重新引入这些缺陷。


空正文：目标WebUI聊天3次只保存reasoning、正文空，思考427/410/402 tokens；缺原始payload、finish_reason和usage。2条新单轮直接API（thinking/nonthinking各1）都有正文，均stop，不能锁定原故障是输出预算、提前EOS或WebUI流处理。尚未修复根因，不继续自动复现。


未闭合think：原始302种assistant答案、604次曝光，实际2048保留训练集合中0次；不能归咎其进入本次SFT。身份原样本为/no_think并有空think前缀，默认ignore_empty_think被mask；不能因此保证整个模型思考行为不退化。


业务夸大与事实可信性：截图声称训练覆盖智慧交通/建筑/碳交易/资产；身份模板无该业务清单，确切来源未锁定。本次仅通用Mixin+身份SFT，没有经审核专业能碳语料；2条API回答还报无来源且不一致的精确数字。需边界/澄清/不编造/工具失败可见回退，但用户要求先不处理。


没有系统效果评估：身份连通请求只证明一次正确名称；工程Smoke不证明遗忘/通用能力保持；auto API HTTP200不证明工具能力。没有基座同题完整对照，不能把所有异常归为微调新增，也不能宣布没有遗忘。


## 8. R1下一步清单（未授权立即执行）


先等用户选择下一具体工作，不自动从handoff继续实现。后续若授权CPU恢复实现：选定父快照与审核对象→异常审核及真实决定→如需排除才生成独立衍生→适配快照入口并保留必要修复→真实Tokenizer/Swift模板、mask、成员与零超长检查→冻结代码/镜像/数据/基座和决定。旧native guard不能拿旧原生report/hash直接为快照新路径放行。


独立评估：A=基座无定制身份System；B=基座+冻结System；C=基座+指定Adapter无该System；D=基座+同Adapter+与B逐字节相同System。相同cases/seed/模式/生成参数/baseSHA/引擎，thinking与nonthinking分组，独立冻结case/rubric，不复制训练模板。独立Reviewer不是本会话换角色。当前checkpoint-103可先评估，不要求先重训，但需新的GPU/服务窗口授权。


v1.2内部参考：Identity C≥95%、A/C通用下降3个百分点触发复核、Thinking正确性/正常结束与B/D服务效果并列；实际题量/评分/阈值须先冻结，不是自动验收标准。没有这些证据就继续标“质量未验收/遗忘未测定”。


## 9. Drive交付索引与校验


统一文件夹：https://drive.google.com/drive/folders/1fhiuIhZNgHJjO09sFD9hrB6ULYiQFV84
原始v1.2方案：https://drive.google.com/file/d/17kVO_pWDZJIvX5N0vU-yImJyPTXvlBrA/view
原附件：https://drive.google.com/file/d/1sGwZoIbvrny6y1zSXTQrnqz5vRioNaC_/view


v1.2原始CPU审核包
https://drive.google.com/file/d/1C4Psio7qgU27bFobd92i4oXmDa0JQqG4/view
SHA-256=c0049799f80070b3126397a56f2ae1034eb3e12cbaafbfe4cd6fc1ee180bf1c4


官方原生入口CPU包
https://drive.google.com/file/d/1V-oysRsNKQwXKSWuqvWpjZlBUMr8HmrI/view
SHA-256=c8e56ac313905e8a89ce981c822a9af10eb16862a58188c7dd2e02414ed918aa


GPU训练与测试加载证据包
https://drive.google.com/file/d/1LJ7fwnAhQ0TlUe_2GWj_4tTUoJpHB1nh/view
SHA-256=7530995129dbb66932a7cd77d4da4d3ce487f9d4458ddff21c5228ef51bb1f46


checkpoint-103 LoRA ZIP
https://drive.google.com/file/d/1Be0WI7PKbQmcfcKj-YIyQRGikGf_ulaB/view
SHA-256=33feb7cfe9e3bafa1a5b72f32e179fe89448c4c4251e152763dd846d3adffd1d


全流程命令及诊断附件
https://drive.google.com/file/d/1PZTfbAI5rpTwIKDRz9tU5PMtaXu86xLu/view
SHA-256=76ece6efeefbd2fd060fecfb831ee8652782b21974d75cc72f895ee14b3c6335


v1.2流程恢复R1证据包
https://drive.google.com/file/d/1kVscp_ukoOCXrG66aFlmw8Db4GQaoD3A/view
SHA-256=6c00ad4e1a62e45714cd1dcb31ad5f56c17749df7decd47232bc15c7dd67bdea


GPU包Manifest：https://drive.google.com/file/d/1Y2T8jv9YL_wnknwuoywjxOgx1IyyTn2k/view
GPU交付回执：https://drive.google.com/file/d/1FaLcYhk5PQmArHhWINcYvGYfhbEscYIg/view
当前R1证据包含13个payload文件，原始GPU包159个payload、CPU原始包206个payload。它们是各自包时点，后追加文件不应让旧Manifest失效。本次handoff附件另补收切回基座的result/models/switch.log，不覆盖旧GPU包。


校验原则：Docs以原生文档回读内容、位置和父目录核验；文件包以Drive原始下载字节SHA、ZIP CRC与内部Manifest逐项hash核验。Docs后来追加R1的内容不会反向改动此前冻结runbook ZIP，阅读当前Docs与历史ZIP须区分。阶段ZIP/回执不是统一实时备份。


## 10. 最小接手动作和禁止重做事项


接手只需先读第1/2节、当前R1 process_state.json与当前服务只读快照；按用户下一指示定位一个阶段。不要重新下载所有数据、重跑所有旧测试、启动GPU Smoke、修改官方语料、创建审批或评测对象、替换线上模型，除非后续具体授权。不要在当前工作根目录假定git可用；git命令需指定两个真实code仓库。


```text
cd /Users/ben/aiws/codex/keywords
cat t008_qwen3_v12_process_restore_20261019/process_state.json
git -C t008_qwen3_native_entry_20261019/code status --short
git -C t008_qwen3_native_entry_20261019/code rev-parse HEAD
# 如需刷新现场，仅只读；不是评测/生成请求：
kubectl --context lmas00-direct --request-timeout=30s -n vllm get deployment vllm
# 不运行历史supervisor、gpu_stage、训练/加载脚本。
```

K8s控制平面metadata与worker/执行机墙钟历史上有约20分钟偏差；时间保留原值，执行顺序看监督事件，训练耗时看Trainer runtime。用户日期按America/Los_Angeles，2026-10-20 UTC部分记录对应2026-10-19 PDT，不是版本跨日错误。
