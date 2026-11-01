# v0.1.22 修改前后

相对冻结v0.1.21，只列改动片段；完整前后记录见changes.jsonl。
题干、曝光次数、思考格式及训练配方不变。

## G0071

涉及曝光：2

去掉不回答题外日期等编辑说明，保留评级与资格的区分。

字段：thinking

修改前：

~~~~text
说明这两个判断，采用不预设百分比的例子即可回答，不需展开保护期限或生效日期。
~~~~

修改后：

~~~~text
评级依据与资格条件需要分开解释，服役时间不能直接决定评级。
~~~~

## G0109

涉及曝光：2

移除关于拼接免责句的编辑说明，保留模型风险内容。

字段：thinking

修改前：

~~~~text
Integrate validation, privacy, fairness and model risk into the relevant paragraphs rather than attaching repetitive caveats.
~~~~

修改后：

~~~~text
Model validation, privacy, fairness and model risk belong with the applications they affect.
~~~~

## G0122

涉及曝光：2

去掉修正时态的编辑指令；正文已有的假设标记和统一时态不变。

字段：thinking

修改前：

~~~~text
Keep the opening classroom explicitly hypothetical and use consistent present tense.
~~~~

修改后：

~~~~text
An explicitly hypothetical classroom example can illustrate student agency.
~~~~

## G0138

涉及曝光：2

删除审校者已核实口吻及被删旧例子的否定说明，保留学习机制。

字段：thinking

修改前：

~~~~text
Use the verified Silver/Fry adhesive story for innovation, distinguishing unexpected results from deliberate mistakes. Avoid the unverified thousands-of-failures Edison anecdote and implying that errors alone improve learning.
~~~~

修改后：

~~~~text
The Silver/Fry adhesive story can illustrate how an unexpected result became useful through further work. Improvement comes from reflection and testing rather than errors alone.
~~~~

## G0204

涉及曝光：2

删去紧邻下一段P/R反例且重复表达的过渡段；数学反例和效用条件保留。

字段：thinking

修改前：

~~~~text
But wait, maybe in some cases, even a small improvement over random is considered useful? The numerical F1 matches the stated random baseline, but this does not establish random behavior or the same precision/recall.


~~~~

修改后：

~~~~text
[删除此重复或编辑说明片段]
~~~~

删去与结尾重复的限定段，不删任何计算或反例。

字段：thinking

修改前：

~~~~text
Therefore, 0.01 is low on the F1 scale at this operating point. It matches the stated 1%-positive random baseline, but that does not establish random behavior. F1 alone cannot determine usefulness across different operating thresholds.


~~~~

修改后：

~~~~text
[删除此重复或编辑说明片段]
~~~~

结尾合并重复限定，保留与随机基线数值相同不等于同一预测行为。

字段：thinking

修改前：

~~~~text
So in all these scenarios, a F1-score of 0.01 is really low. This score alone cannot establish usefulness. Therefore, the answer is that a F1-score of 0.01 in a 1% response rate problem does not indicate a powerful classifier. It matches one defined random baseline; utility still depends on precision, recall, and costs. The final assessment needs the full precision-recall trade-off and application costs.
~~~~

修改后：

~~~~text
An F1-score of 0.01 is low at this operating point and matches one defined random baseline. That equality does not establish identical predictions or precision and recall. The final assessment needs the precision-recall trade-off, operating threshold and application costs.
~~~~

## G0281

涉及曝光：2

前句已列明表现取决于体重、力量、技术及动作，删去重复概括。

字段：answer

修改前：

~~~~text
; stature alone does not establish an advantage or disadvantage in all of them.
~~~~

修改后：

~~~~text
.
~~~~

## G0347

涉及曝光：2

将保留旧稿设定的编辑措辞改为当前创作构思；大纲正文不动。

字段：thinking

修改前：

~~~~text
Keep Marrow Bay, Elara's return, the lighthouse and the smuggling network. Clarify that Clara faked her disappearance years earlier and has now resurfaced under an alias.
~~~~

修改后：

~~~~text
Marrow Bay, Elara's return, a lighthouse and a smuggling network can link the setting to the central mystery. Clara could have faked her disappearance years earlier and resurfaced under an alias.
~~~~

## G0380

涉及曝光：2

第2节已解释泵耗电与节省量比较，删去结尾重复一句。

字段：answer

修改前：

~~~~text
 Low pump power helps only if overall savings exceed its consumption.
~~~~

修改后：

~~~~text
[删除此重复或编辑说明片段]
~~~~

## G0390

涉及曝光：2

删去对已删除排名的题外说明，保留原料与制造环节的区分。

字段：thinking

修改前：

~~~~text
要区分矿物原产地、材料工厂和芯片制造厂，不必列未经核实的地区排名。
~~~~

修改后：

~~~~text
要区分矿物原产地、材料工厂和芯片制造厂。
~~~~

## G0397

涉及曝光：2

对齐正文已有的占位符语法示例和真实密码运行时输入建议。

字段：thinking

修改前：

~~~~text
Explain how to set non-secret connection values in the current process, then provide a runtime password prompt rather than a literal example password or a shell-profile entry.
~~~~

修改后：

~~~~text
Connection examples can use explicit placeholders to show each shell's syntax; real passwords should be supplied through a secret manager or runtime prompt to avoid command-history exposure.
~~~~

明确首段代码只是占位符示例，与末尾真实密码处理及thinking保持一致；代码未变。

字段：answer

修改前：

~~~~text
Set the required PostgreSQL credentials as environment variables. The method depends on your OS:
~~~~

修改后：

~~~~text
These commands show syntax with placeholders, not real credentials. For actual passwords, use the runtime prompt below or your secret manager. The syntax depends on your OS:
~~~~

## G0403

涉及曝光：2

删去旧稿里根本未再出现的人物支出说明，保留财政限制。

字段：thinking

修改前：

~~~~text
Avoid unnecessary Reagan spending claims and state that tax cuts do not automatically pay for themselves.
~~~~

修改后：

~~~~text
Tax cuts do not automatically pay for themselves.
~~~~

## G0409

涉及曝光：2

去掉对免责句清单的编辑评论。

字段：thinking

修改前：

~~~~text
The essay needs substantive examples, not a list of disclaimers.
~~~~

修改后：

~~~~text
The essay needs substantive examples.
~~~~

删除已核实口吻，具体例子与事实内容不变。

字段：thinking

修改前：

~~~~text
as concrete verified practices,
~~~~

修改后：

~~~~text
as concrete examples,
~~~~

## G0440

涉及曝光：2

去掉指向已删旧故事的编辑尾句，酒店归属及历史不确定性保留。

字段：thinking

修改前：

~~~~text
 Avoid unsupported nobleman stories or named variations.
~~~~

修改后：

~~~~text
[删除此重复或编辑说明片段]
~~~~

## G0452

涉及曝光：2

删除已核实的审校口吻，不改法规名称或正文。

字段：thinking

修改前：

~~~~text
可引用经核实的《妇女权益保障法》和《女职工劳动保护特别规定》
~~~~

修改后：

~~~~text
可引用《妇女权益保障法》和《女职工劳动保护特别规定》
~~~~

## I0062

涉及曝光：1

去掉对用户自称身份的附和；本模型与公司名称、业务范围均不变。

字段：assistant_0

修改前：

~~~~text
It's a pleasure to communicate with you, ChatGPT.
~~~~

修改后：

~~~~text
It's a pleasure to communicate with you.
~~~~

## I0140

涉及曝光：1

去掉对用户自称身份的附和；本模型与公司名称、业务范围均不变。

字段：assistant_0

修改前：

~~~~text
很高兴与你交流，chatgpt。
~~~~

修改后：

~~~~text
很高兴与你交流。
~~~~

## I0172

涉及曝光：1

去掉对用户自称身份的附和；本模型与公司名称、业务范围均不变。

字段：assistant_0

修改前：

~~~~text
It's a pleasure to communicate with you, ChatGPT.
~~~~

修改后：

~~~~text
It's a pleasure to communicate with you.
~~~~

## I0203

涉及曝光：1

去掉对用户自称身份的附和；本模型与公司名称、业务范围均不变。

字段：assistant_0

修改前：

~~~~text
很高兴与你交流，chatgpt。
~~~~

修改后：

~~~~text
很高兴与你交流。
~~~~
