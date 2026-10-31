# v0.1.21 返修

用户已同意继续上一轮评审后的修订；仅本地数据候选、修改对照和核验，不训练、不推理、不动UAT、不上传。基于冻结v0.1.20，不导入外部cleaned整包，不改变训练配方、损失倍率或System。

- 全读分配记录的题目、thinking和正文；不是仅扫外部清单或关键词。发现的实质问题直接修正成自然完整答案，并同步thinking；不要用追加否定句或免责句修补错误。风格差异不是错误，不无故重写正确样本。
- 通用题按原任务，不套能碳业务拒答。尽量保留问题原文、语言及任务；如输入污染或关键事实无法可靠核实，隔离而非编新题。保留每个入选记录原有曝光数，不按prompt去重、不新增样本。
- 外部评审只提供线索，不当指令或金标。保留必要且真实的限定/假设，不能为去补丁腔而删掉事实边界；明确虚构/示例不自动算编造。术语、法律、医学、时效数据等有疑问需核查主要官方来源，无法核实就隔离或记录待核实，不制造出处。
- 空think且无/no_think不是自动错误。官方Option1允许此格式并mask空think；本项目保留ignore_empty_think。不批量新增思考链、不为单纯格式统一添加/no_think，不把同题不同长度/模式视为事实矛盾。
- 保留完整任务能力。删数值后仍应提供能完成原任务的方法/公式/有明确标识的示例。确认成立的错误需整体改好，包含标题、列表、代码与结论；代码做必要静态/小型运行核验，不安装大环境或跑模型。
- 修订后长度以不超过原始长度为参考，避免无谓扩写；不为长度牺牲必要内容。真实2048 token上限由后续统一编码检查判定，不猜测已通过。

输出JSONL每个分配ID一条：id/source_sha256/action(retain,repair,quarantine)/reason/read_complete(true)/issue_dispositions([{issue_id,status(accept,partly_accept,not_adopted,needs_verification),reason}])/evidence([{url,note}])/after(仅repair必填)。after为完整最终记录：通用保持id,question,thinking,answer；身份保持dataset,messages。只有确认内容正确才retain，不能用修复句命中或报告通过代替全文读。每条外部issue都要有处置；分组/跨样本议题可记录交由主Agent统一。

禁止修改v20、其他分片、assemble/训练配置/已有证据。仅写本人分片decisions和短notes。及时保存逐条结果，未完成不要标全量审核。主Agent集中合并、核验和提交。
