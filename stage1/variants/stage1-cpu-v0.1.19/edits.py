"""Bounded assistant-content edits; caller binds exact parent records and exposure IDs."""
import re

REPAIR = {
    'G0002':'部门全员均薪在内层计算，再筛选数据分析师；修正思考及正文中的查询和说明。',
    'G0008':'纠正0.01%→100 ppm；删除无依据的更严阈值、露点和操作建议，明确质量基准。',
    'G0038':'统一对外做功为正、ΔU=Q−W；补公式适用条件，删除热量或功必非零的泛化。',
    'G0115':'删除用户要求思考过程和给过示例的虚构归因；正文标为虚构续写。',
    'G0334':'纠正不存在的reserve及错误表达式，区分长度和容量、对象和引用、CPython与语言保证；修正扩容及deque适用描述。',
}
QUARANTINE = {
    'G0010':'术语未确认即写成另一模型，整条前提缺失；不凭猜测重写定义。',
    'G0065':'问题残缺，退税名称、门槛、时限及流程存在多处问题；不在本轮重写税务指南。',
    'G0090':'推荐版本不支持题给Python3.7，伴随未核依赖与替代关系；不临时拼装未经验证的软件组合。',
    'G0111':'堆叠顺序、故障原因与建议不一致，并含未核工具菜单；不只删一个错误排序项后声称整条可靠。',
    'G0260':'虚构先输出思考的指令，正文又输出思考计划，并加入大量未核数字；不把去掉标题当作内容修复。',
    'G0262':'ISO标准名称错误，且含未经完整核实的危险施工建议；不据此生成替代操作指导。',
    'G0436':'三个ISBN校验均失败且无实际检索证据；不靠改校验位制造看似有效的书目。',
    'G0479':'把维生素C列作元素，并混合生物分类与未经限定的营养量描述；不只改一词保留其他疑点。',
}

def replace(text, old, new, count=1):
    assert text.count(old)==count, (old[:100], text.count(old), count)
    return text.replace(old,new)

SQL = """WITH DepartmentStats AS (
    SELECT EmployeeId, Name, Role, Department, Salary,
           AVG(Salary) OVER (PARTITION BY Department) AS AvgDepartmentSalary
    FROM Employees
)
SELECT EmployeeId, Name, Role, Department, Salary, AvgDepartmentSalary
FROM DepartmentStats
WHERE Role = '数据分析师';"""

def repair(sample_id, content):
    match=re.fullmatch(r'<think>([\s\S]*?)</think>([\s\S]*)',content)
    assert match and match[1].strip() and match[2].strip()
    t,b=match.groups()
    if sample_id=='G0002':
        start=t.index('对于第一个查询，')
        end=t.index('例如：',start)+len('例如：')
        t=t[:start]+'第一个查询把“部门平均薪资”解释为该部门全部员工的平均薪资。先在内层对全部Employees计算部门窗口均值，再在外层筛选数据分析师；若先筛选角色，均值就只包含分析师。例如：'+t[end:]
        pattern=r"SELECT EmployeeId, Name, Role, Department, Salary,\s*AVG\(Salary\) OVER \(PARTITION BY Department\) AS AvgDepartmentSalary\s*FROM Employees\s*WHERE Role = '数据分析师';"
        t,n=re.subn(pattern,lambda _:SQL,t);assert n==2,n
        t=replace(t,'这样每个员工的记录都会显示他们部门的平均薪资。而部门会被分组计算平均值。','内层按全部员工计算部门均值，外层只保留数据分析师，均值因此包含同部门的其他岗位。')
        b,n=re.subn(r'```sql[\s\S]*?```',lambda _: '```sql\n'+SQL+'\n```',b,count=1);assert n==1
        b=replace(b,"**`WHERE Role = '数据分析师'`**：筛选出所有担任“数据分析师”角色的员工。","**外层 `WHERE Role = '数据分析师'`**：在部门全员均值计算后筛选员工，避免把均值缩小为仅分析师。")
        b=replace(b,'使用窗口函数计算每个部门的平均薪资','在内层使用窗口函数计算每个部门全部员工的平均薪资')
    elif sample_id=='G0008':
        t=replace(t,'0.01%就是1000 PPm','0.01%就是100 PPm')
        t=replace(t,'不过，用户可能是在问更严格的要求，比如是否需要更低的PPm值，或者是否有行业标准。比如在某些高纯度工艺中，可能要求水分低于100 PPm或者更低。','这里应先完成题给质量分数的换算，不能由此自行确定更严的工艺阈值。')
        t=replace(t,'不过，实际应用中可能需要更严格的要求，比如100 PPm或更低，以确保树脂的稳定性。','题目没有给出气相水分的计量基准，不能将树脂中的质量分数直接当成空气水分的体积分数。')
        t=replace(t,'总结来说，用户需要将0.01% w/w转换为PPm，得到1000 PPm，但实际应用中可能需要更低的值，比如100 PPm或50 PPm，具体取决于工艺要求。因此，回答时需要明确转换结果，并指出可能的实际应用标准，同时建议用户参考具体行业规范或设备手册。','总结来说，0.01% w/w等于100 ppm（质量比）。按题中同一质量基准的填空可填100；空气纯度或露点参数还需要对应的计量基准与工艺要求，不能由这个换算自行推断。')
        b=b.split('2. **实际工艺要求**：')[0].rstrip()+'\n\n**计量基准提示**：上述100 ppm是质量比。若填空实际指空气中的水分体积分数或露点，不能直接套用树脂水含量的质量比，需要先确认对应的指标与计量基准。'
        b=replace(b,'这是基于质量比（w/w）的直接换算，适用于干燥或净化工艺中的水分控制。','这是基于质量比（w/w）的直接换算。')
    elif sample_id=='G0038':
        t=replace(t,'例如，等温过程中的内能变化为零，而绝热过程中内能变化等于做功。','例如，理想气体等温过程的内能变化为零；约定系统对外做功为正时，第一定律为ΔU=Q−W，因此绝热过程有ΔU=−W。')
        t=replace(t,'同时，要区分可逆和不可逆过程，但用户的问题可能不需要深入这部分。','同时要注明可逆与理想气体等适用条件，不能把可逆绝热关系用于所有绝热过程。')
        intro='以下气体公式按封闭、定量理想气体、仅有体积功且热容近似恒定讨论；以系统吸热为正、对外做功为正，第一定律为 $ \\Delta U = Q-W $。涉及气体状态压力积分的功公式采用准静态可逆路径；过程定义本身不依赖这些近似。\n\n'
        i=b.index('---');b=b[:i]+intro+b[i:]
        b=replace(b,'系统与外界可以交换热量（$ Q \\neq 0 $）。','系统与外界可以交换热量，是否非零取决于具体过程。')
        b=replace(b,'系统与外界交换热量以维持温度恒定（$ Q \\neq 0 $）。','可通过与外界换热维持温度；理想气体等温时 $ Q=W $，二者不必总非零。')
        b=replace(b,'系统与外界交换热量（$ Q \\neq 0 $），但不做体积功（$ W = 0 $）。','系统可与外界交换热量，但不做体积功（$ W = 0 $）。')
        b=replace(b,'系统通过做功改变内能（$ \\Delta U = W $）。','若仅有体积功，内能变化为 $ \\Delta U = -W $。')
        b=replace(b,'理想气体：$ PV^\\gamma = \\text{常数} $','可逆绝热理想气体：$ PV^\\gamma = \\text{常数} $')
        b=replace(b,'| 等压     | 压力（P）      | ≠ 0            | ≠ 0      | ≠ 0              |','| 等压     | 压力（P）      | 视过程而定     | PΔV      | Q−W              |')
        b=replace(b,'| 等温     | 温度（T）      | ≠ 0            | ≠ 0      | 0                |','| 等温     | 温度（T）      | Q=W            | 视过程而定 | 0（理想气体）   |')
        b=replace(b,'| 等容     | 体积（V）      | ≠ 0            | 0        | ≠ 0              |','| 等容     | 体积（V）      | 视过程而定     | 0        | Q                |')
        b=replace(b,'| 绝热     | 无热量交换     | 0              | ≠ 0      | ≠ 0              |','| 绝热     | 无热量交换     | 0              | 视过程而定 | −W              |')
        b=replace(b,'### **图示（PV图）**','### **图示（定量理想气体的可逆过程PV图）**')
        b=replace(b,'封闭容器中的气体被加热或冷却（如内燃机的燃烧阶段）。','刚性密闭容器中的气体被加热或冷却（边界体积不变）。')
        b=replace(b,'**等容过程**：内燃机的燃烧阶段（体积固定）。','**等容过程**：刚性密闭容器内气体加热或冷却。')
    elif sample_id=='G0115':
        first=t.index('好的，');end=t.index('\n\n',first)
        t=t[:first]+'用户提供了论坛解谜场景，没有要求展示思考过程，也没有提供额外示例。这里按虚构续写和活动设计来回应，沿用题给的论坛、地点和解谜情节；新增事件是创作设定，不当作真实报道。'+t[end:]
        t=replace(t,'用户希望这个解谜活动能够吸引人，并且有逻辑性，同时推动后续发展。','续写可以让解谜活动具有吸引力和连贯性，同时推动后续发展。')
        t=replace(t,'最后，需要检查整个设计是否符合用户的要求','最后，需要检查整个设计是否与用户提供的场景一致')
        b=b[:len(b)-len(b.lstrip())]+'以下是基于所给场景的虚构续写与活动设计；新增人物、品牌事件、年份和报告内容均为创作设定，不是事实报道。\n\n'+b.lstrip()
    elif sample_id=='G0334':
        t=replace(t,'Python的列表确实是基于动态数组实现的','常用的CPython实现中，列表基于动态数组，连续存储的是对象引用')
        t=replace(t,'比如1.5倍或2倍','具体增长规则由实现和版本决定')
        t=replace(t,'如果需要频繁在列表中间插入或删除元素，可能链表更合适，但Python的列表并不基于链表，所以这时候可能需要使用其他模块如collections.deque或者手动管理数据结构。','频繁在两端插入或删除可考虑collections.deque；它不保证中间操作为O(1)。链表在已知节点位置时可快速更新链接，但查找位置仍有成本。')
        t=replace(t,'Python会分配一个更大的数组（比如原来大小的1.5倍或2倍），然后将所有元素复制过去。','CPython会在需要时调整底层引用数组并预留额外空间；不假定固定增长倍率，移动的是对象引用。')
        b=replace(b,'在Python中，**动态数组**是一种可以在运行时动态调整大小的数据结构，而**列表（list）正是基于动态数组实现的**。','**动态数组**是一种可以在运行时动态调整大小的数据结构。常用的**CPython实现中，列表（list）基于动态数组**；连续存储的是对象引用，对象本身不必连续。其他Python实现不必采用相同内部结构。')
        b=replace(b,'Python的列表（`list`）底层实现就是动态数组。','CPython的列表（`list`）底层使用动态引用数组。')
        b=replace(b,'Python会分配一个更大的数组（通常是当前大小的 **1.5~2倍**），并将原有元素复制到新数组中。','CPython会按需要扩展引用数组并预留空间，具体增长规则随实现版本而异，不保证固定倍率。')
        b=replace(b,'Python列表是动态数组，而不是链表。链表的插入/删除操作更快（$O(1)$），但访问元素需要遍历（$O(n)$），而列表的访问是 $O(1)$。','CPython列表是动态数组，而不是链表。链表在已定位节点及所需前驱时更新链接可为 $O(1)$，查找位置仍可能为 $O(n)$；列表索引访问为 $O(1)$。')
        b=replace(b,'如果已知数据规模，可以预先分配足够容量（例如使用 `list.reserve()` 或 `*[None]*n`）。','标准 `list` 没有 `reserve()` 方法。如果已知最终长度，可用 `[None] * n` 创建含n个占位元素的列表，再按索引赋值；这会改变长度，不是只预留容量。')
        b=replace(b,'如果需要频繁在**头部或中间插入/删除**元素，可以考虑以下替代方案：','如果需要频繁插入/删除，应按操作位置选择结构：')
        b=replace(b,'- **`collections.deque`**：双端队列，适合在两端操作（时间复杂度 $O(1)$）。','- **`collections.deque`**：适合频繁在两端操作；中间访问或修改仍可能为 $O(n)$。')
        b=replace(b,'- **链表实现（如 `LinkedList`）**：手动实现或使用第三方库（如 `blist`），但Python本身不提供原生链表。','- **中间插入/删除**：结合是否已定位节点、索引访问频率与内存成本选择结构，不能笼统认为换成deque就会更快。')
        b=replace(b,'**Python列表是动态数组的实现**','**CPython列表使用动态引用数组**')
    else:raise KeyError(sample_id)
    result='<think>'+t+'</think>'+b
    assert result!=content and t.strip() and b.strip()
    return result
