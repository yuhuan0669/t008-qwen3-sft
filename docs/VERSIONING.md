# 版本管理、更新与恢复

## 管理单元

- Git分支 `main`：当前统一入口、控制状态、代码、历史文档/证据/冻结数据及资产登记。
- `archive-v1.0.0`：首次统一归档标签，仅表示归档版本。
- `history/v1.2-original`、`history/v1.2-cpu-fixed`、`history/native-entry-trained`：原提交定位。
- `archive/`：来源原字节快照，后续不覆盖；新材料放入新的阶段/版本路径。
- `registry/`：本地文件、对象、代码提交、数据/模型版本及Drive引用。
- 相邻 `t008_qwen3_assets/sha256/<前两位>/<完整SHA256>`：完整冻结ZIP、Adapter等19个去重对象。

任务单v1.5、流程v1.2/R1、代码commit、数据SHA、模型权重SHA与归档tag相互关联，但不可互相替代。`TRAINED_CANDIDATE`与`QUALITY_ACCEPTED`也不能互换。

## 方案审阅版本

`registry/plans.json`单独登记方案路径、SHA、状态、云端审阅副本和标签。`plan-review-v0.1`仅定位完整讨论稿；Git提交或创建标签不批准方案实施。修改讨论稿时产生新版本和commit，不移动既有标签。原始归档bundle及`archive-v1.0.0`不包含后续文档增量；后续方案可从Git远端或其单独bundle恢复。本次没有新增模型/数据对象，无需重传旧对象库。

## 原地核验

```sh
cd /Users/ben/aiws/codex/keywords/t008_qwen3_sft
python3 tools/verify_archive.py \
  --source-root /Users/ben/aiws/codex/keywords
python3 tools/audit_frozen_packages.py
git fsck --full
git status --short
```

第一条还比较原始文件是否被改动；若恢复到另一台机器且没有原目录，省略 `--source-root`，仍能验证本库载荷、对象和代码历史。核验不启动训练或服务。

## 离线恢复

本次交付一个Git bundle和一个对象库tar包，外部回执记录两者大小、SHA和Git提交；两件必须一起保存。先按交付回执核对文件SHA：

已指定私有远端为 `https://github.com/yuhuan0669/t008-qwen3-sft`。可用已认证GitHub客户端取得归档发布附件：

```sh
gh release download archive-v1.0.0 --repo yuhuan0669/t008-qwen3-sft --dir /path/to/backup
```

```sh
git clone /path/to/t008-qwen3-archive-v1.0.0.bundle /restore/t008_qwen3_sft
tar -xzf /path/to/t008-qwen3-archive-v1.0.0.assets.tar.gz -C /restore
cd /restore/t008_qwen3_sft
git switch main
python3 tools/verify_archive.py
python3 tools/audit_frozen_packages.py
git fsck --full
```

tar恢复出的目录名为 `t008_qwen3_assets`。如对象库放在别处，两个核验命令均支持 `--asset-root /absolute/path`。

查看任一冻结原件：在 `registry/local-files.json` 查 `source_path`。存储为 `git` 时读取 `repository_path`；为 `local_object` 时从对象库按 `object_path`读取完整字节，可复制到新的临时文件并恢复原扩展名。不要覆盖现有来源文件。

16个旧Adapter下载分块使用 `local_object_range` 保存：从其 `object_path` 指向的完整ZIP中，自 `offset` 起读取 `bytes` 字节，结果必须匹配该分块 `sha256`。这些分块可精确恢复，但不重复占用Git或对象库。核验脚本会逐块验证。

还原历史代码提交：

```sh
git show history/native-entry-trained:README.md
git log --all --oneline --decorate
```

历史提交内代码在根目录，统一后的代码在 `code/`。执行训练前仍须经过当前任务的准入与环境核验；归档恢复只证明文件可恢复。

## 之后如何更新

1. 从 `main` 建立本次工作分支，记录范围与真实决定引用。
2. 在 `code/`修改实现；数据快照保持不可变，需要变更时生成新目录、父SHA及真实审核记录。
3. 添加新阶段原件和对象，只新增内容寻址对象，不覆盖旧hash路径。更新当前状态与版本登记；旧manifest/旧包不重写。
4. 对新增范围执行适当验证，保存结果。归档清单之外的新文件必须登记新版本，不能把旧核验PASS用于新增内容。
5. 提交并建立新的归档标签；更新bundle、对象备份和外部交付回执。
6. 远端Git仅在目标仓库明确后配置与推送。Git远端不自动包含对象库，必须为对象库明确另一个可访问的备份位置。

`tools/import_archive.py`为本次首次导入工具，已有清单时会拒绝覆盖。不要把重跑首次导入当作常规更新流程。

## 保存范围和限制

- Git与对象库包含已取得的代码、阶段材料、冻结数据、依赖包和Adapter；数据入库只表示版本保存，不代表批准训练。
- 7项private材料只有路径/hash索引，原始聊天和SSE不进入Git或备份包；核查这些材料仍需原受控存储。
- 49项生成缓存只登记，不备份。
- 16GB基座、远端完整checkpoint/优化器及运行镜像保留精确定位和历史hash清单；本次没有复制其全部远端字节，不构成完整环境灾备。
- 本地离线包与本机仓库属于同一故障域；私有GitHub及其Release作为额外远端备份，实际上传、回读结果记录在Release交付回执。未在本机取得的远端基座/checkpoint不在这些附件中。
- 归档可能包含内部基础设施地址与受控训练资料，不默认允许公开发布。
