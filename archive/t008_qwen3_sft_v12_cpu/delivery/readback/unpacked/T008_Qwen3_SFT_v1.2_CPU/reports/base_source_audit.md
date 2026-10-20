# T-008 Qwen3-8B 实际基座与官方版本内容核验

核验时间：2026-10-19T05:56:24Z。只读 CPU 工作；未下载权重、未训练、未用 GPU、未改服务。状态：**CONTENT_IDENTITY_MATCH；历史下载 revision 仍 UNKNOWN**。

实际只读 `/base` 的 16 个文件、16,397,461,896 bytes，其 size/SHA-256 全部与官方 ModelScope `Qwen/Qwen3-8B` 固定 revision `26028140be3ee69b82b1d1450179ab71bb1121b9` 的完整 tree 元数据一致。五个权重分片同时与官方 Hugging Face revision `b968826d9c46dd6066d109eabc6255188de91218` 的 LFS size/SHA-256 一致。

这证明本轮实际基座具有上述官方版本的文件内容身份；不证明当年从哪一个站点、哪个分支或哪个 commit 下载。没有用当前 HEAD 替代未知的历史下载 revision。

## 实际输入与不可变上游

- 实际清单由独立 CPU 模板审查 Agent 从隔离容器只读 `/base` 完整逐文件计算，本审查消费已保存的 `evidence/template/original-exact/base-files.json`；实际项数为 **16**（不是即时协调消息的 15）。
- 清单原始文件 SHA-256：`a1b77d34bda8a913bc050ba2b8b343b6104f77fa701c8b5275a0b438baedfd56`。
- 清单按项目 `json.dumps(list, sort_keys=True, ensure_ascii=False)` 聚合 SHA-256：`39c6b79bcc9813377a48e65da1ad614151748389d0bf526f5d816dc581e54374`。两者序列化字节不同，不能互换。
- [ModelScope 固定版完整文件元数据](https://modelscope.cn/api/v1/models/Qwen/Qwen3-8B/repo/files?Revision=26028140be3ee69b82b1d1450179ab71bb1121b9&Recursive=true)：16 项，全部匹配；文件自己的 last-changed revision 另存，不误称所有文件都在 LICENSE commit 修改。
- [Hugging Face 固定版 API 元数据](https://huggingface.co/api/models/Qwen/Qwen3-8B/revision/b968826d9c46dd6066d109eabc6255188de91218?blobs=true)：15 项。LFS 文件直接比对官方 SHA-256；非 LFS 小文件按固定 revision 下载并计算 SHA-256，不将 Git blob SHA-1 当成文件 SHA-256。
- 先读取 main/master 只是发现候选固定版本，随后已按不可变 revision 再次取得元数据并完成匹配。

## 权重匹配

| 文件 | bytes | SHA-256（本地、MS、HF 相同） |
|---|---:|---|
| model-00001-of-00005.safetensors | 3,996,250,744 | `31d6a825ae35f11fb85b195b4c42c146c051e446433125a215336abdf95cbf5f` |
| model-00002-of-00005.safetensors | 3,993,160,032 | `5991236cea6fe21f3d43cab0f0e84448734fbbe0789816202989f2ddc9d18282` |
| model-00003-of-00005.safetensors | 3,959,604,768 | `c5185c4794be2d8a9784d5753c9922db38df478ce11f9ed0b415b7304d896836` |
| model-00004-of-00005.safetensors | 3,187,841,392 | `b5ee7de71fbf17db3d5704e0c8f2bc7d005ca9e1d7ca2aeb19827b0cfcaa917a` |
| model-00005-of-00005.safetensors | 1,244,659,840 | `20c2d6366ab85c90786ccdd829cd2b9e7d30ef3b2ebbb998280e7e4014b542ff` |

权重合计 16,381,516,776 bytes。ModelScope 所列五分片最后修改 revision 为 `7c9709d23bd2136dac1d6ea1fe30f4107d681cd6`。本审查只下载 API 元数据和非权重小文件，没有下载上述五分片。

## 配置、Tokenizer 与平台差异

实际 `config.json`、`generation_config.json`、`merges.txt`、`model.safetensors.index.json`、`tokenizer.json`、`tokenizer_config.json`、`vocab.json`、`README.md`、`LICENSE` 均与两个官方固定版本相同。Tokenizer JSON 通过官方 LFS SHA-256 比对，未重复下载。实际 `tokenizer_config.json` SHA-256 为 `d5d09f07b48c3086c508b30d1c9114bd1189145b74e982a265350c923acd8101`，可绑定本轮模板核验。

HF 与本地有两项平台附属差异：

1. `.gitattributes`：本地/ModelScope 为 2,127 bytes、SHA-256 `088e25d6bceaa8943f4f292006210358292349cc36e7578f80c62fce75535f46`；HF 为 1,570 bytes，内容不同。
2. `configuration.json`：ModelScope 与本地有 73 bytes 的同一文件，HF 仓库没有此文件。

因此结果准确表述为“MS 16/16；HF 14 个同名内容匹配、1 个附属文件不同、1 个仅 MS 存在”，不是全部文件与 HF 仓库完全相同。实际 LICENSE 已匹配官方 Apache 2.0 文本，SHA-256 `832dd9e00a68dd83b3c3fb9f5588dad7dcf337a0db50f7d9483f310cd292e92e`。

## 证据位置与范围

全部上游 API 原件、固定版小文件及请求/时间/hash 在 `evidence/source_identity/base_upstream/`；完整逐项比较为 `base_content_comparison.json`，原件清单为 `evidence_manifest.json`。本次新增报告不改先前来源身份报告。

本结论只闭合本轮实际基础文件的内容身份，不新增训练或来源批准，也不改变英文身份、定制/基座研发语义待裁定状态。主 Agent 已报告原始训练快照 958 行超长及待批长度衍生候选；这些数据门禁与本基座内容匹配分别记录，不能因匹配成功放行训练。
