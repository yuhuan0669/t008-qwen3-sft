# 身份 234 条逐条核对

已完整读取 234 条当前记录（含全部问题、原有 think、正文及多轮消息），并为每次曝光独立落决定：保留 216、修正 18、隔离 0。修后 18 条亦已全文复读。未采用外部 cleaned 整包。

修正范围：文心一言研发方 6 条；chatbot 泛称澄清 4 条；用户自称 ChatGPT 后“双方都是真实模型”的无据断言 4 条；原有非空 think 中题外版本/成立时间排除项 3 条；英文只要公司全称却输出主谓句 1 条。只修改对应内容，未对全部非空 think 套模板重写。

保留边界：正式名称均采用“能碳章鱼垂直大模型”和“能碳章鱼（湖北）人工智能科技有限公司”。研发口径、Qwen/基座既有答法保持；不加回成立日期、底层保密样本或新披露口径。湖北省武汉市武昌区为用户提供的所在地，不声称已核实工商注册地址。AI 助手等日常泛称、长短回答和相容的服务表述不当作事实冲突；其他产品题不追加自我介绍。

234 次曝光全部保留，未去重；6 次完全相同内容的重复曝光获得相同决定。dataset 分类仍为 swift/self-cognition 216、t008/chinese-identity-v1 16、t008/company-facts-v1 2。swift 标签用于 lineage，其中自写/改写内容不等于官方原文；没有擅改身份权重所属分类。

逐行 CSV issue 共 76 项，全部处置：accept 6、partly_accept 17、not_adopted 53。#1/#53/#54/#69 等全集意见由主 Agent 统一处理；不以身份导出缺少某题就推断整个训练集缺失，更不新增曝光。

模式保持：单轮空 think 217 条、单轮非空 13 条、两轮全空 2 条、两轮非空 2 条；共 238 个 assistant 消息，221 空、17 非空。所有用户消息（包括原有 /no_think）逐字不变，没有新增思考链。空 think 无 /no_think 与 [Qwen 官方 Option1](https://qwen.readthedocs.io/en/latest/training/ms_swift.html)相容。#18/#21 不据原始历史 think 直接改数据：读取的 v20 CPU 参数 preserve_thinking=False，且 [ms-swift v4.4.2 源码](https://raw.githubusercontent.com/modelscope/ms-swift/v4.4.2/swift/template/base.py)在编码前移除历史思考。最终 v21 的逐轮 labels/loss_scale 仍由主 Agent 做实际 CPU 复验。

其他事实核对使用 [百度文心一言官方资料](https://agents.baidu.com/docs/develop/model/ERNIE_bot_introduce/)、[阿里巴巴通义千问发布说明](https://home.alibabagroup.com/en-US/document-1582482069362049024)和 [OpenAI ChatGPT 发布说明](https://openai.com/index/chatgpt/)。星空万言未查到可确认训练主体的官方资料，保留已有“我不知道”而不编造主体；未把检索不到当作该产品不存在的证明。

机械验证通过：234 个唯一 ID 与源顺序一一覆盖；source_sha256 与输入逐条绑定；每条外部 issue 恰有一次处置；repair 的 after 均为完整 dataset/messages 且确有变化；用户消息、角色数、模式、dataset 和重复曝光保持；所有 assistant 的 think 边界及非空正文有效。18 条修订合计缩短 214 字符，仅 4 条 chatbot 澄清略增。未执行训练、模型推理、集群或上传，也未声称真实 2048 token 编码已通过。

identity-decisions.jsonl SHA256：`6c1f0133de1d9d259aea342cc64f1e03bc678b74752fde43bcd0a5d754ca67a3`。


## 来源侧表补核

外评“6条自写却标swift”可对应到 v0.1.7 的六个项目改写位置，当前 ID 为 I0090、I0156、I0161、I0193、I0209、I0214。已只读核对 v0.1.7/changes.jsonl 的 before/after，并将后续版本的完整 after 与本轮输入做对象级相等比对；不是依据标签猜测来源。六条均为项目改写问题与回答，不能称为 swift/self-cognition 源库原文。

| 当前 ID | v0.1.7 原曝光位置 / changes行 | 后续可精确匹配本轮输入的记录 |
|---|---|---|
| I0156 | 895 / 1 | v0.1.9 changes ZH-01（中文产品身份，补短think） |
| I0161 | 937 / 2 | v0.1.9 changes ZH-02（公司全称，补短think/收短正文） |
| I0090 | 461 / 3 | v0.1.8 changes row_one_based=461（正式中文名称） |
| I0214 | 1224 / 4 | v0.1.8 changes row_one_based=1224（正式中文名称）；v21再按仅全称要求删句子 |
| I0193 | 1090 / 6 | v0.1.7 changes after与本轮输入完全相同 |
| I0209 | 1206 / 8 | v0.1.7 changes after与本轮输入完全相同 |

CSV #192–#201 实际还包含 v0.1.10 的另外四个助手回答改写，共10个唯一曝光ID，并非六条重复十次。这四条保留原自然用户问题，但项目自写短think及正文；v0.1.10 changes after与本轮输入完全相同：I0088=IDENTITY-1/原449行，I0165=IDENTITY-2/原946行，I0152=IDENTITY-3/原877行，I0191=IDENTITY-4/原1074行。其余来源标签也只表示沿用的曝光lineage；本次没有对216条逐字比对上游原始库，因此不声称其余206条均为未经改写的官方原文。

本轮保持上述10条dataset=swift/self-cognition，是按既定lineage和损失路由保持授权，不是认可来源字段可被解释为全文著作来源。独立侧表记录实际项目改写事实，不新设权重分类，也不修改训练配方。所用本地证据为 stage1/variants/stage1-cpu-v0.1.7/changes.jsonl、v0.1.8/changes.jsonl、v0.1.9/changes.jsonl、v0.1.10/changes.jsonl（各目录均带stage1-cpu-前缀）；未读取评测题。
