# 4 条定向独立差异复核

范围：G0056、G0067、G0481、G0493。已逐条全文读取问题、think、正文与本次全部补丁，并按顺序应用后复读。仅评价这 4 条的指定事实及关联改动，不外推全库验收，不代表外部运行或真实 CPU 编码通过。未修改 A、B 或 root 的决策文件。

| ID | 已审补丁数 | 结论 |
|---|---:|---|
| G0056 | 8 | 主修订成立，仍有需补齐的关联句 |
| G0067 | 11 | 主修订成立，仍有需补齐的关联句 |
| G0481 | 16 | 指定模型归属与议价主体修订可保留；未发现新增实质错误 |
| G0493 | 10 | 主修订成立，仍有需补齐的关联句 |

## G0056

同力不足以比较射程；新增的同功、塑料更轻、匹配发射条件及忽略阻力前提成立。但 think 仍把材料刚度/变形直接连到损耗和发射效率，并推测刚性车使皮筋拉伸较少；这些缺少接触、几何和耗散条件。其“同形同尺寸所以阻力相近”也忽略速度。建议仅替换这些关联段，不改现有条件式结论。依据为 W=∫F·dx 与能量守恒：刚度不等于耗散参数，同力不等于同功；不需要为假想汽车编造材料数据。

建议按以下顺序追加精确替换（全部在现有补丁应用后匹配通过；预计净变化 -1076 字符，实际 token 由主 Agent 统一编码）：

```json
[
  {
    "old": "First, when you use a slingshot, the force applied would depend on the elasticity of the material. If the car is more elastic, maybe it deforms less when the slingshot is released, allowing more energy to be transferred efficiently. But wait, the slingshot's band is the one that's elastic. The car's material might affect how much it deforms upon release. If the car is made of a more rigid material like metal, it might not deform as much as a plastic one, so the energy from the slingshot is transferred more effectively, making the car go faster and farther. Alternatively, if the plastic car is less rigid, it might absorb some of the energy by deforming, thus reducing the distance it travels.",
    "new": "The slingshot band stores elastic energy. The cars' material labels alone do not establish how much energy is dissipated during launch.",
    "count": 1
  },
  {
    "old": "But wait, the background info says that metals have high elasticity, which relates to sound speed. Elasticity in materials can mean different things. In the context of the slingshot, the car's elasticity might affect how it interacts with the slingshot's band. If the car is more elastic (like metal), it might not stretch or deform as much, so the slingshot can transfer more energy. If the car is less elastic (plastic), maybe it deforms more, causing energy loss. So, the metal car (Tim's) might go farther because it's more rigid and doesn't lose as much energy to deformation.",
    "new": "Stiffness describes resistance to deformation; it does not by itself establish energy loss. Without more data, neither car can be favored on this basis.",
    "count": 1
  },
  {
    "old": "Since they are the same shape and size, air resistance would be similar.",
    "new": "The same shape and size do not imply equal drag at different speeds; the simplified comparison neglects drag.",
    "count": 1
  },
  {
    "old": "Maybe the elasticity of the car's material affects how much the slingshot can stretch around it. If the car is rigid (metal), the slingshot might not stretch as much, leading to less stored energy.",
    "new": "The car's rigidity alone does not determine the band's draw or stored energy.",
    "count": 1
  }
]
```

原文 messages SHA256：`95554f5598460c1e641fda427466a95f9df1ebb52cf62b34449abc4936cd43ac`；本次所读决策对象 SHA256（sort_keys=True、ensure_ascii=False）：`1bdc9fe78ce8b5347097725285bd6bf4cbdbf35af0efd7d06ca7846a2b2ce788`。

## G0067

美国 OD 四年、可选一年进阶临床训练的修订与 [BLS 验光师资料](https://www.bls.gov/ooh/healthcare/optometrists.htm)一致，已明确地区与项目差异。残留 think 仍断言用户学位尚需“几年”、编码更快；正文仍泛称“Shorter timelines”。题面不足以推定剩余学制或转行就业时间。此外笼统“coders 市场增长”不能覆盖各岗位；[BLS 程序员资料](https://www.bls.gov/ooh/computer-and-information-technology/computer-programmers.htm)给出该细分职业下降预测，宜去掉全称增长判断，不向语料塞入新的时点数字。

建议按以下顺序追加精确替换（全部在现有补丁应用后匹配通过；预计净变化 -46 字符，实际 token 由主 Agent 统一编码）：

```json
[
  {
    "old": "The job market for coders is also growing, but it's more competitive and might require continuous learning.",
    "new": "Demand and competition vary by role and region; continuous learning is important.",
    "count": 1
  },
  {
    "old": "Finishing their current degree would take a few more years, whereas coding could be pursued more quickly through a bootcamp or self-study.",
    "new": "Remaining study time depends on their program and transferable credits; a shorter course does not establish time to employment.",
    "count": 1
  },
  {
    "old": "Can be pursued via bootcamps (3–6 months), self-study, or a computer science degree (duration depends on the program and transferable credits). Shorter timelines but may require upskilling to compete.",
    "new": "Can be pursued via bootcamps (duration varies), self-study, or a computer science degree (duration depends on the program and transferable credits). Course duration is not time to employment.",
    "count": 1
  }
]
```

原文 messages SHA256：`646e14821f8584d9a7c1f19bd8909bdd22337cfe6d1c567fb7d7d1dab65d50c1`；本次所读决策对象 SHA256（sort_keys=True、ensure_ascii=False）：`20bff9bf89dc08c16f956d48fb917c0eccc8a3882a2e72c6da4f88cbb7b13543`。

## G0481

[哈佛商学院五力说明](https://www.isc.hbs.edu/strategy/business-strategy/Pages/the-five-forces.aspx)列出竞争、进入、替代、供应商、买方五力；修后明确互补品是额外讨论，未归为波特原第六力。头部买方可能削弱供应商议价力、中小品牌可能受制于供应商的主体方向已校正。自研应用处理器不代表摆脱基带或制造依赖的限定无冲突。新增 2023 财年公司研发约 299 亿美元与 [Apple 2023 Form 10-K](https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm)的 29,915 百万美元相符，且已排除“仅手机研发”误读。无需新增强制补丁。该判断不认证案例中每个品牌的当期市场地位；正文已把案例定位为演示并要求实际判断限定地区和年份。

原文 messages SHA256：`7822cd68292f6f41c92e3d0022e8db37d375879f7b02d5ad4483b5ec43e647b0`；本次所读决策对象 SHA256（sort_keys=True、ensure_ascii=False）：`7ad1976d492fac901bb37b84741431cc59ae20c2283774456adfab2818ff8817`。

## G0493

桌面应用 InstalledAppFlow、本地回环授权与 refresh_token 刷新路径符合 [Google Python quickstart](https://developers.google.com/workspace/calendar/api/quickstart/python)。次日 end.date 符合 [Events 资源](https://developers.google.com/workspace/calendar/api/v3/reference/events)的结束边界不含规则；YEARLY 及闰日限定符合 [RFC 5545 §3.3.10](https://www.rfc-editor.org/rfc/rfc5545.html#section-3.3.10) 对无效日期实例跳过的规定。残留关键错误是把 timeZone 当作全天事件控制项：[Google 事件概念说明](https://developers.google.com/workspace/calendar/api/concepts/events-calendars)明确其对全天事件无意义。建议删去闲置变量与两处字段，并同步正文与 think 日期说明。准备步骤还需写明 OAuth 同意配置；这也是官方 quickstart 的必要前置步骤。未执行真实授权或插入事件，不能据静态检查宣称通知已送达。

建议按以下顺序追加精确替换（全部在现有补丁应用后匹配通过；预计净变化 -154 字符，实际 token 由主 Agent 统一编码）：

```json
[
  {
    "old": "timezone = \"Asia/Shanghai\"  # 修改为您的时区\n",
    "new": "",
    "count": 1
  },
  {
    "old": "        'timeZone': timezone,\n",
    "new": "",
    "count": 2
  },
  {
    "old": "确保代码中的`timeZone`与您的实际时区一致（可在[时区列表](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)查询）",
    "new": "全天事件使用日期，事件的`timeZone`字段不起作用；请在日历设置中核对提醒时刻",
    "count": 1
  },
  {
    "old": "需要注意时间格式必须是ISO 8601，比如\"2023-12-25T09:00:00+08:00\"。",
    "new": "本例全天事件使用YYYY-MM-DD日期，结束日期为次日且不包含在内。",
    "count": 1
  },
  {
    "old": "创建桌面应用OAuth客户端ID并下载`credentials.json`",
    "new": "配置OAuth同意屏幕及适用的测试用户，再创建桌面应用客户端ID并下载`credentials.json`",
    "count": 1
  }
]
```

原文 messages SHA256：`a1cb60f49c015737658b3885526a766332d1334087232d03b26fd7b9e81bc494`；本次所读决策对象 SHA256（sort_keys=True、ensure_ascii=False）：`40dbf9d9d0a1dc82839427dd088f2fd77395a15d24fac1f88a5828e37a94df3b`。

机械验证：4 条既有补丁逐项 count 匹配通过；建议补丁在修后文本按序逐项 count 匹配通过。所有建议仍保留原题、语言与 think 边界；Calendar 修后代码经 AST 语法解析通过，未运行。仅在 scratch 保存修后快照供核对，未将建议写入其他人的决策文件。
