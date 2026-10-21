# 首次 CPU 检查

原生加载1327条成功，进入编码前，既有local_data_guard读取新manifest时发现缺少files_sha256键。尚未产生编码通过结果。只在新版本生成器中补齐该清单字段，数据和训练参数不改；UAT保持原配置1/1，临时CPU Pod已删除。
