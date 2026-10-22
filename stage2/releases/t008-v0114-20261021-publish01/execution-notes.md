# 发布执行记录

- 用户授权：发布 v0.1.14；保留基座，加载 LoRA 并应用修正模板；不暂停 UAT 应用、不改应用配置。
- 仅操作 vllm namespace 的模型服务及本次暂存 Pod／模板 ConfigMap；其他 Deployment 已保存规格哈希。
- 使用现有 Recreate 策略替换模型 Pod，保持 Deployment replicas=1，不对应用执行 scale。
- 原始基座 16 个文件哈希与训练父对象一致；LoRA ZIP 及两个文件哈希一致。
- 本地 Python 证书链缺少发行者，改用系统 curl 保留 HTTPS 证书验证；不是服务故障。
- API server dry-run 自动补充 ConfigMap defaultMode=420（0644）；本次发布／回退补丁显式包含该默认值，避免精确回退测试不匹配。没有其他准入修改。
- 应用端路由、System、Schema、模式预算不在本次修改范围。当前应用如继续请求基座别名，仍使用基座。
- CPU 暂存 Pod 正常进入终止；30 秒删除等待超时，随后最终列表确认 Pod 已消失。模型服务未受清理影响。
