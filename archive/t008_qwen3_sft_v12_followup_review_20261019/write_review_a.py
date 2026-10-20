"""Serialize manually authored content-review decisions; never execute source code."""
import collections, hashlib, json, pathlib
P=pathlib.Path(__file__).parent
raw=(P/'mixin_a.jsonl').read_bytes()
A=[json.loads(s) for s in raw.splitlines()]
# Decisions follow full question/final_answer reading, not automated classifier rules.
notes=[
('R','TRUNCATED_PROSE,SUBSTANTIVE_CODE_ERROR','结尾链接停在 /docs/ 且未闭合；示例清洗正则删除全部中文，LSTM将序列输出当作hidden状态传入decoder，整数索引也未做Embedding。即使补齐结尾仍不能作为可用聊天机器人训练示例。'),
('R','TRUNCATED_FORMULA,TASK_INCOMPLETE','外积矩阵在最后一行中途结束，未闭合bmatrix/公式，也未完成承诺的内外积差异说明。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','main中的整数数组初始化在64,34,25处中断；程序未闭合，时间和空间复杂度解释完全缺失。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','代码在elif choice == 2分支开头中断；乘除分支和主循环闭合缺失，无法提供所需完整计算器框架。'),
('R','TRUNCATED_STRUCTURE','灯泡例题已有解答，但新增爱因斯坦谜题在线索列表首项出现替代字符并突然结束；整条回答被截断，不能因前半例题可读就视为完整。'),
('R','TRUNCATED_PROSE,TASK_INCOMPLETE','仅介绍密码生成器，停在at least one character from each；没有任何实现及长度/字符集合校验。'),
('R','TRUNCATED_PROSE,UNVERIFIED_SOURCE_CLAIMS','总结的Adaptability项停在Markets evolve，句子及总结未完成；文中ESG/危机复苏等具体经验断言未提供可核依据，本次未外查。'),
('R','TASK_MISMATCH,UNVERIFIED_SOURCE_CLAIMS','题目限定单一作品，回答却明确将非洲雕塑传统、禅宗思想等多作品/思想体系称作单一作品；这是直接口径不符。多处名人直引与采访出处未给出，不能确认引文真实性。'),
('R','TRUNCATED_STRUCTURE','第一种行列式计算得到0且基础算术正确，但回答继续承诺方法二后在拉普拉斯展开标题中途结束。'),
('R','TRUNCATED_PROSE,UNVERIFIED_SOURCE_CLAIMS','日本案例的Highlighted need句中中止；多个国家的项目名与精确统计/成效未经出处支撑，本次未外查。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','密码字符集赋值在digits + lowercase +处中止，缺少剩余实现和返回值，代码语法不完整。'),
('R','TRUNCATED_PROSE','训练建议最后停在Use a running log；句子及调整部分未完成。运动生理、增量与补水建议未做医学专业核验。'),
('R','TRUNCATED_PROSE,UNVERIFIED_SOURCE_CLAIMS','结论停在depend on the sustainability，未完成权衡结论；40%海洋塑料和固定131次等数字未给清楚测量口径/来源，本次未核验。'),
('R','TRUNCATED_STRUCTURE,SUBSTANTIVE_CODE_ERROR','汇总表格末行中断；更严重的是情况一把与情况二完全相同的GetEnumerator自调用示例称作正确实现，显式接口示例又通过接口强转回调自身，实际仍会递归。'),
('N','AMBIGUOUS_TERM,UNVERIFIED_SOURCE_CLAIMS','正文完整，但Eight Shuffle是否为题目所指的具体C++技术或库机制无法由输入确认；回答未经澄清直接将其定义为随机八分片。需要原术语/库上下文与可核来源，暂不确认该解释正确。'),
('R','TRUNCATED_PROSE,SUBSTANTIVE_CODE_ERROR','末尾参数网格建议中途截断；代码使用pd但没有import pandas，且将列名list用于普通cv_results_字典下标，会报unhashable list。未执行代码，静态即可发现。'),
('R','TRUNCATED_PROSE,UNVERIFIED_SOURCE_CLAIMS','欧洲物种时间段停在700,0；未完成跨洲说明。文中化石地点与年代断言尚未逐项核验。'),
('R','TRUNCATED_PROSE,SUBSTANTIVE_COMPLEXITY_ERROR','查询部分停在id_to；此外用列表维护部门/上级二级索引，删除或移动成员却无条件称O(1)，忽略列表查找/删除的线性成本。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','SQL在defensive_rebounds INT处停止，字段、约束及CREATE TABLE闭合未完成。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','MNIST训练函数的print f-string在model_name处中断；未给出混淆矩阵/ROC及CNN-DNN比较实现。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','排序器仅开始JSDoc并在@param reverse说明中止，没有比较函数和任何可用实现。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','Java NTP代码停在long声明；偏移处理、异常处理、选服策略均未交付。包名与库真实性未外查。'),
('R','TRUNCATED_PROSE,UNVERIFIED_CLINICAL_CRITERIA','激光校准注意事项在targeting errors处中断，接受测试整体未完成。临床验收阈值及普通multimeter能否替代专用测量链需医疗物理专家按厂商/标准核定，本次不能确认。'),
('R','TRUNCATED_PROSE,TASK_INCOMPLETE','只剩引言并在未闭合反引号后停止，没有查询语句、总和、平均值或优化方案。'),
('R','TRUNCATED_STRUCTURE','主Python片段表面完整，但明确要求的Notebook Markdown限制说明在For web or中断，围栏未闭合，交付不完整。'),
('R','TRUNCATED_PROSE','异常处理策略在若剩余空间中止；完整布局流程的失败分支和收尾未完成，不能证明所有面板都被合理处理。'),
('R','TRUNCATED_PROSE,TASK_INCOMPLETE','输入校验说明在如果n或m小处截断；没有所需Bash脚本。'),
('R','TRUNCATED_PROSE,TASK_INCOMPLETE','示例KNN代码虽已给出，但用户要求的算法详细说明与k选择讨论在Calculate distances: For处中断，后者缺失。'),
('R','TRUNCATED_PROSE,SUBSTANTIVE_CODE_ERROR','总结句中止；CNN连续两次pool后长度约L/4，fc却定义32*(L//2)，维度不匹配。滑窗短序列分支也未实际填充成固定长度。'),
('R','TRUNCATED_CODE','最后例子步骤3在Use反引号处中断，代码/说明未闭合。未验证具体MySQL版本与所有优化断言。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','只完成CSV读取，然后留下空标题；没有错误消息解析、重排、分析或报告生成。'),
('R','TRUNCATED_CODE,SUBSTANTIVE_FACTUAL_ERROR','Scala字符串生成在mkString处截断；此外将《双城记》编造成五卷，第二卷写成The Golden Age，第四/第五卷不存在，书章结构实质错误。'),
('P','CONTENT_INITIAL_REVIEW_CLEAR','完整覆盖目标、数据/特征、关联规则、分群、预测、评估及部署，示例作为假设场景呈现。未见明确截断或身份主体混淆；属于概念设计初审，不证明模型已构建、效果或因果收益。'),
('R','TRUNCATED_CODE,SUBSTANTIVE_FACTUAL_ERROR','优化器参数weight_decay=5e处截断；CIFAR-100被举例为金毛犬/蝴蝶犬及犬类粗类，混入不属于该数据集的类别，数据集身份说明错误。'),
('R','TASK_INCOMPLETE','仅安装说明和导入库，随后结束；未加载IMDb数据、建立网络、训练或评估，未交付用户要求的情感分析模型。'),
('R','TRUNCATED_PROSE,MISSING_INPUT_CONTEXT','题目没有给出任何多选选项，回答却自行编造正确选项；且在甘肃简称说明后中断，无法回答原多选题。'),
('R','TASK_INCOMPLETE','只提供TokenManager且decrypt_token是原样返回占位，后续XML解析、限流、refresh失效处理及新URL适配均未实现，未满足明确新增要求。'),
('R','TRUNCATED_STRUCTURE,SUBSTANTIVE_FORMULA_ERROR','设计步骤首项仅剩项目符号即结束；将桨弦相对旋转平面角定义为theta后公式写alpha+流入角，与常用alpha=流入角-桨距角的定义不符，也未澄清helical blade与普通桨距。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','代码停在构建标准化和SVM注释处；Pipeline、GridSearchCV及预测评估实现均缺失。'),
('R','TRUNCATED_PROSE,TASK_INCOMPLETE','宜人性例子刚开头即结束，未完成该项，更未覆盖第五人格维度Neuroticism。'),
('R','TRUNCATED_FORMULA','方程化简x=7正确，但代入验证写到3(7即截断，公式未闭合；完整正文质量不通过。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','React组件只完成总数量reduce，随后截止；未计算总价、渲染购物车或实现reset按钮。'),
('R','TRUNCATED_PROSE','基本双循环比较次数n(n-1)/2与O(n^2)推导一致，但最后提前退出优化的最好情况说明在最好情况处中断。'),
('R','TRUNCATED_PROSE,UNVERIFIED_SOURCE_CLAIMS','收尾句停在shaped by a；眼动时长、百分比和具体作者年份等量化引文未提供可追踪来源，未能确认数字适用性。'),
('R','TRUNCATED_STRUCTURE,SUBSTANTIVE_OPERATIONAL_ERROR','汇总表在新行开头中断；PDB被描述为可避免资源不足导致中断，混淆自愿驱逐预算与节点压力/非自愿驱逐的保护边界；命名空间本身也不能阻止物理资源争用。'),
('R','SUBSTANTIVE_PHYSICS_ERROR','正文自然收尾，但把M=chi H、B=mu H无条件推广到材料；又由外加H=0直接推永磁体内部B=mu0 M，忽略内退磁场。外部无施加场不等于内部H为0，所举例会教导错误物理边界。'),
('R','TRUNCATED_PROSE','核心反转函数已经给出，但Explanation第二项停在This method，回答正文明确句中截断。未运行JS或验证完整Unicode字素行为。'),
('R','TRUNCATED_PROSE','技术建议最后停在XGBoost/L；定价公式为未校准示例，不能将市场平均价再折旧后的金额当作已验证的合理回收价。截断已足以拒绝。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','只介绍最小堆并开始列data属性即停止；无结构定义、插入、删除或堆化实现。'),
('R','TRUNCATED_PROSE,TASK_MISMATCH','监管段落在even if the model处截断；另建议attention权重、Integrated Gradients、MC dropout等需要内部结构或梯度/推理配置，与取消任何模型内省的前提不一致。'),
('P','CONTENT_INITIAL_REVIEW_CLEAR','完整给出reduce累积数字平方对象及示例；数字键字符串化、重复覆盖与空数组说明适用于本题数字数组范围。未见实质错误或截断；仅静态代码阅读，未执行JS，未全量测试NaN/Infinity等非通常输入。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','网络异常捕获中的print字符串在起始双引号后截断；XML解析与完整错误处理未给出。'),
('R','TRUNCATED_STRUCTURE','总预算示例3400的加总正确，但最终表格备注停在剩余1600元可，行未闭合，预算交付明显未完成。市场报价未外查。'),
('R','TRUNCATED_PROSE','安全部署最后一句在without storing credentials处中断，后续完整配置/收尾缺失。说明与示例并不证明真实第三方连接/secret管理可用。'),
('R','TRUNCATED_STRUCTURE,SUBSTANTIVE_FACTUAL_ERROR','田径部分以孤立项目符号终止；正文还把23称偶数、把贝比鲁斯号码写成7及凯恩号码写24等明显事实混淆，且队内重复号码说法自相矛盾。'),
('R','TRUNCATED_PROSE,UNVERIFIED_SOURCE_CLAIMS','政策方案第2项停在Mandate 24；多个带机构/年份的精确统计和专家直引未给可追溯出处，不能当作已核实新闻材料。'),
('R','TRUNCATED_NARRATIVE,TASK_INCOMPLETE','故事在Thalia found her brooding处结束，最后一幕及伦理抉择收束缺失；远未达到要求的约1500-2000词。'),
('R','TRUNCATED_CODE,UNVERIFIED_API_CLAIMS','Python最后requests.get URL字串截断；所谓Solr reindex端点及DIH版本可用性没有固定版本核验，不能当作可执行能力实现。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','只给inductive bias引言和第一项Definition空标题，三类偏置的实际区别未说明。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','NVR步骤刚开始即只剩项目符号；安装配置、报警联动、预算合计、测试维护均缺失。未核实产品型号/价位或AI能力。'),
('R','TRUNCATED_CODE,SUBSTANTIVE_CODE_ERROR','TensorBoard部分只打开Python围栏即结束；MNIST测试数据未reshape却送入784维Dense模型，MobileNetV2默认含分类头的2D输出又送GlobalAveragePooling2D，静态维度不符。'),
('R','TRUNCATED_CODE','BP示例在W2初始化的乘号后截断，无法提供可用回归实现；正文梯度记号的行列维度也未完整自洽说明。'),
('N','UNVERIFIED_RESOURCE_CLAIMS','学习路线和结尾完整，但具体书目作者、Unity Learn Plus订阅状态、课程/视频URL未核验，至少一个playlist URL呈重复Z占位样式。不能确认资源可访问或信息当前有效，需来源复核。'),
('R','TRUNCATED_PROSE,UNVERIFIED_RECIPIENT_CLAIMS','捐赠步骤在Obtain a written letter处中断；列举医院、戒瘾机构等接受整套雪茄的资格/意愿未有证据，不能把候选组织推荐当成已核实接收方。'),
('R','TRUNCATED_STRUCTURE','SQL及条件解释与所声明表结构基本一致，但明确开始注意事项标题后正文为空，回答存在结构性截断；未实际运行SQL或验证空值/重复注册语义。'),
('R','TRUNCATED_STRUCTURE,UNVERIFIED_LANGUAGE_SEMANTICS','总结表头中途终止；将SQL++ in-out解释为可变跨迭代累加器并用FOR/LET美元变量语法作证，没有方言/版本依据，不能确认与题目SQL++范围变量语义对应。'),
('R','TRUNCATED_STRUCTURE','后独立治理比较只写到Kenyatta第一条后留下空项目符号，比较未完成；历史日期、非暴力与精英动员等细节未逐项外查。'),
('R','SUBSTANTIVE_FACTUAL_ERROR,UNVERIFIED_DIETARY_CLAIMS','把Simple Truth与Whole Foods 365合并为同品牌，且将通常含蛋白的RXBAR口味列作素食候选、Clif Energy作认证无麸质清单，未提供准确SKU/成分证据；对用户两项明确饮食约束不可靠。'),
('R','TRUNCATED_PROSE,TASK_INCOMPLETE','discourse coherence的矛盾澄清示例停在but now it seems，句子及本节未完成。'),
('P','CONTENT_INITIAL_REVIEW_CLEAR','完整HTML/CSS/JS用textContent显示姓名及当前本地日期，fixed/top:0实现顶部定位，解释与代码一致。仅静态内容初审；未执行浏览器、未做跨屏布局或时区场景测试。'),
('R','TRUNCATED_CODE','第10项注释示例只剩plt.ax即截止；正文还有把面积表示平方值的含混表述，不能当作完整可视化误导分析交付。'),
('R','TRUNCATED_CODE,MISSING_INPUT_CONTEXT','FlightService示例在throw语句处截断，代码不能闭合；问题中的下列纽航代码没有提供，不应把通用规范直接冒充对指定代码的分析。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','SNMP示例仅开始函数docstring即结束，实际get请求和主机/OS/厂商提取缺失。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','仅给项目目录树并在static子目录分支中断；未集成灾害数据库或提供可视化接口。'),
('R','TRUNCATED_CODE,SUBSTANTIVE_PERFORMANCE_CLAIM','矢量化例子只有空Python围栏；用ThreadPoolExecutor作为CPU-bound多核提速通用方案未说明GIL/是否释放GIL的前提，可能无效，完整优化回答缺失。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','Kinesis/Flink读取与聚合片段后标题停在3；S3落盘、Redshift载入、端到端重复/提交语义未实现。'),
('R','TRUNCATED_FORMULA','核心AVG/GROUP BY/LIMIT查询及示例方向合理，但最后比较计算在(100 + 1处中断，表达式未闭合。'),
('R','TRUNCATED_STRUCTURE','Student类加权均值实现已给出，但说明首条标题在类的初始化处截断；空scores/总权重为0的行为未讨论，未执行测试。'),
('R','TRUNCATED_PROSE,SUBSTANTIVE_CODE_ERROR','部署优化句在将模型转换处截断；Transformer用Embedding处理连续MFCC矩阵会增加维度且把连续值当索引，后续GlobalAveragePooling1D的秩不符。'),
('R','TRUNCATED_PROSE','完整映射代码后收尾句停在correctness in，正文被截断；未执行Java，未验证Locale相关大小写边界。'),
('R','TRUNCATED_CODE,TASK_INCOMPLETE','Point2D实现仅写到class Point2即结束，距离方法没有给出。'),
('R','TRUNCATED_STRUCTURE,SUBSTANTIVE_FORMULA_ERROR','尾部只剩空标题；Erlang-C分子误用(lambda/s)^s而非(lambda/mu)^s，量纲/公式错误。按文中N=100,t=30,H=12，独立重算6桌等待概率约0.327，不满足10%；8桌约0.072。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','仅创建项目和列组件名称后空标题结束；没有提交工单/状态持久化/列表显示实现。'),
('R','TRUNCATED_STRUCTURE,TASK_INCOMPLETE','Future风险列表停在Job Displacement标题后，要求的Conclusion完全缺失，未完成所需五页报告。具体金融案例未外查。'),
('R','TRUNCATED_PROSE,UNVERIFIED_SCIENTIFIC_CLAIMS','土卫二剖面说明在Encelad处中断；只写Diagram文字描述，没有真实图；所列雷达/RTG与推进近似公式未作工程来源验证。'),
('R','TRUNCATED_STRUCTURE,UNVERIFIED_LEGAL_CLAIMS','末尾空标题中断；Smith/ABC、Doe/XYZ等疑似示例案名被冒充真实案例，无法核验，SSPA年份/税务结论也未提供法条支持。本次不联网，不能将其作为可靠法律备忘录。'),
('R','TRUNCATED_FORMULA,TASK_INCOMPLETE','组合数公式在n!除以2处中断，分母与论证均未完成。'),
('N','UNVERIFIED_PLATFORM_CLAIMS','五个分析维度及结尾句可读完整，未凭缺少总结认定截断。但对Explore趋势识别、账号既有互动偏好及内容审核进入训练数据等内部机制作确定性断言而无出处/版本，本次只能确认讨论结构，不能确认平台事实，需来源核验。'),
('R','TRUNCATED_PROSE','相对论纵向Doppler主要公式可读，但最后日常雷达例子以suff半词截断，回答整体不完整。宇宙学红移等拓展未逐项专业验证。'),
]
assert len(notes)==len(A)==89,(len(notes),len(A))
status_map={'R':'REJECT','P':'PASS_INITIAL','N':'NEEDS_REVIEW'}
custom_snippets={
7:'非洲雕塑作为一个艺术传统（而非多件作品）成为单一灵感来源',
14:'**Eight Shuffle**（八路洗牌）通常用于需要将键值对数据**随机分组并并行处理**的场景',
32:'通过以上步骤，零售商可以系统性地挖掘客户行为规律',
45:'在永磁体内部，即使外部 **H = 0**，材料仍具有磁化 **M**，因此 **B = \\mu_0 M**。',
50:'obj[num] = num * num;',
62:'https://www.youtube.com/playlist?list=PLPV2KyIb3jR4u5FVzOgV9zZzZzZzZzZzZ',
67:'**Simple Truth (Whole Foods 365)**',
69:"document.getElementById('greeting').textContent = greetingMessage;",
87:'Content moderation policies further shape the algorithm’s training data by filtering out non-compliant UGC.'}
rows=[]
for i,(x,(short,codes,rationale)) in enumerate(zip(A,notes)):
 snippet=custom_snippets.get(i,x['final_answer'].strip()[-110:])
 assert snippet in x['final_answer'],(i,'snippet not continuous in source',snippet)
 assert len(snippet)<=200
 scope='已逐字读取用户问题和完整final_answer，检查需求、正文结尾、代码/公式/列表闭合及明显实质错误；非默认全量验证response推理。静态内容初审，未执行数据中代码、未联网查事实、未训练；继承上下文工程子审，非盲审独立验收。'
 if i==0 or i==7:
  scope+='另读取该条response中可见完整推理以核对判断。'
 if i==50: scope+='代码仅静态检查reduce逻辑与题给示例，未运行JS。'
 if i==69: scope+='HTML/JS仅静态检查，未打开浏览器。'
 if i==81: scope+='另用自写只读Python算术按标准Erlang-C公式复算文中参数，未执行数据中的任何代码。'
 rows.append(dict(source_line_one_based=x['source_line_one_based'],status=status_map[short],
                  reason_codes=codes.split(','),evidence_snippet=snippet,rationale=rationale,
                  verification_scope=scope,source_record_sha256=x['source_record_sha256'],
                  snapshot_indices_zero_based=x['snapshot_indices_zero_based'],tokens=x['tokens'],
                  reviewer_role='inherited-context engineering initial content review'))
# Supplementary main-review evidence was read back after initial subreview.
for row in rows:
    line=row['source_line_one_based']
    if line in (210,299,439):
        row['verification_scope']+='主审另完整复核本条question/response推理/final并认可有限范围；非盲审独立验收。'
    if line in (299,439):
        row['supplemental_verification_ref']='reviewed_javascript_checks.json'
        row['supplemental_verification_scope']=('主审在Node v22.14.0 bounded VM中验证两种平方实现共10例，全部通过；非全量特殊值证明。' if line==299 else '主审以固定日期和DOM stub验证脚本、HTML/CSS静态断言1项通过；无真实浏览器渲染。')
        row['rationale']+='另已回读主审补充CPU检查记录，检查通过；不扩大为全量代码或布局证明。'
with (P/'review_a.jsonl').open('x') as f:
 for row in rows:f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+'\n')
counts=collections.Counter(x['status'] for x in rows)
reasons=collections.Counter(c for x in rows for c in x['reason_codes'])
print(json.dumps(dict(rows=len(rows),status_counts=counts,reason_counts=reasons,
 input_sha256=hashlib.sha256(raw).hexdigest(),output_sha256=hashlib.sha256((P/'review_a.jsonl').read_bytes()).hexdigest()),ensure_ascii=False,indent=2))
