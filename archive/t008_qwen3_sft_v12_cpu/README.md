# T-008 Qwen3-8B v1.2 CPU 准备证据包

先读 `reports/execution_report.md` 与 `evidence/gpu_gate_checklist.json`。

**当前状态：GPU No-Go；没有执行 Smoke、Full 或模型发布。英文官方名称及开发/商业名称用途已由负责人确认，见 `evidence/identity_confirmation_overlay.json`。早期审查中的英文 pending 是该确认之前的历史状态。身份研发归属语义和实际衍生数据仍待裁定。**

- `inputs/`、`baseline/`：指定 Drive v1.2 原件及解包，不使用旧版本覆盖。
- `work/upstream-raw/`：实际官方原始下载与 hash。
- `work/original-quarantined-v1.2/`：原脚本误报时保留的真实 loader 输出；包含来源列，不是训练准入批准。
- `work/original-v1.2/`：修复误报后的完整 2600 行；训练消息字节与前次诊断捕获一致。
- `work/length-candidate-v1.2/`：仅排除 958 个超长曝光后的 1642 行候选；仍未批准。
- `work/code/`：修复后的脚本；独立 Git 历史见 `evidence/preparation-code.git.bundle`。
- `evidence/`：真实版本、逐行 token/mask、异常与源模板映射、基座 hash、环境、只读 ClearML、23 项测试和增量审查。
- `scripts/`：CPU 探针、来源捕获/映射及离线完整性复算。
- `LICENSES/`、`NOTICE.md`：公开来源许可与变更说明。

解压后复算（不访问 GPU 或服务）：

```bash
python3 scripts/verify_package.py .
cd work/code
python3 -W error::ResourceWarning -m unittest discover -s tests -v
```

真实环境重算模板请按 `reports/template_cli_audit.md` 的命令使用新输出目录。原始数据和已绑定预检文件不要覆盖；任何新处理另建版本。基镜像的 AST、USER/cache 与 ClearML overlay 修复细节见执行回报及 `evidence/runtime-bom.json`。未来 GPU 作业必须重新绑定实际部署，不能将 CPU 核验直接当成 GPU 运行结果。

本包 `MANIFEST.json` 对所有载荷文件逐项列 bytes/SHA-256；Manifest 不自哈希。ZIP 自身 SHA 和真实 Drive 下载回读结果在外部交付回执中，避免循环自证。
