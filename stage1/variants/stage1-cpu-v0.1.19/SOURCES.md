# 本轮修正依据

既有主复核19条证据及原文哈希冻结于 source-audit.json；本轮完整回读13条中文／以中文提问的记录。以下新增核对用于支持局部修正，不表示全库事实均已核实。

- G0002：WHERE过滤发生在窗口统计之前；采用内层部门全员均值、外层角色过滤。依据：[PostgreSQL 窗口函数说明](https://www.postgresql.org/docs/current/tutorial-window.html)。另用内存 SQLite 对不同岗位薪资及人数边界做反例核算，见 content-verification.json。
- G0008：0.01÷100×1,000,000=100，w/w是质量基准；原答案附加的露点、设备阈值不由该换算推出，删除而不填新参数。
- G0038：对外做功为正时，绝热过程ΔU=−W；PV^γ关系须有限定条件。依据：[OpenStax 理想气体绝热过程](https://openstax.org/books/university-physics-volume-2/pages/3-6-adiabatic-processes-for-an-ideal-gas)。常量热容及可逆路径前提写入样本，未改变问题。
- G0115：依据题面全文，用户没有提供额外示例或索求思考过程；正文保留为创作并明确标注虚构。
- G0334：依据[Python 官方实现说明](https://docs.python.org/3/faq/design.html#how-are-lists-implemented-in-cpython)、[list方法清单](https://docs.python.org/3/tutorial/datastructures.html#more-on-lists)及[deque说明](https://docs.python.org/3/library/collections.html#collections.deque)，修正引用数组、容量/长度及两端/中间操作的区别。不指定扩容倍率，不新增第三方库推荐。

查阅日期：2026-10-31。隔离记录的原有来源保留在 source-audit.json；未将无法完整核验的回答改写成新的专业指南。
